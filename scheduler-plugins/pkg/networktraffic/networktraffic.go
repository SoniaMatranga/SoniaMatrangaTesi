package networktraffic

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"strconv"
	"time"

	v1 "k8s.io/api/core/v1"
	v1k8s "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/klog/v2"
	framework "k8s.io/kubernetes/pkg/scheduler/framework"
	"sigs.k8s.io/scheduler-plugins/apis/config"
)

type NetworkTraffic struct {
	handle     framework.Handle
	prometheus *PrometheusHandle
}

// Name is the name of the plugin used in the Registry and configurations.
const Name = "NetworkTraffic"

var _ = framework.ScorePlugin(&NetworkTraffic{})

// ================= INITIALIZE a new plugin and returns it =================
func New(obj runtime.Object, h framework.Handle) (framework.Plugin, error) {

	args, ok := obj.(*config.NetworkTrafficArgs)
	if !ok {
		return nil, fmt.Errorf("[NetworkTraffic] want args to be of type NetworkTrafficArgs, got %T", obj)
	}

	klog.Infof("[NetworkTraffic] args received. NetworkInterface: %s; TimeRangeInMinutes: %d, Address: %s", args.NetworkInterface, args.TimeRangeInMinutes, args.Address)

	return &NetworkTraffic{
		handle:     h,
		prometheus: NewPrometheus(args.Address, args.NetworkInterface, time.Minute*time.Duration(args.TimeRangeInMinutes)),
	}, nil
}

// Name returns name of the plugin. It is used in logs, etc.
func (n *NetworkTraffic) Name() string {
	return Name
}

func (n *NetworkTraffic) Score(ctx context.Context, state *framework.CycleState, p *v1.Pod, nodeName string) (int64, *framework.Status) {
	nodeBandwidth, err := n.prometheus.GetNodeBandwidthMeasure(nodeName)
	if err != nil {
		return 0, framework.NewStatus(framework.Error, fmt.Sprintf("Error getting node bandwidth measure: %s", err))
	}
	return int64(nodeBandwidth.Value), nil
}

func (n *NetworkTraffic) ScoreExtensions() framework.ScoreExtensions {
	return n
}

func (n *NetworkTraffic) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {

	memoryRequest, cpuRequest, latencySoftConstraint, latencyHardConstraint, err := getPodResourceRequests(pod)
	var memoryRequestStr, cpuRequestStr string

	if err != nil {
		klog.Infof("[NetworkTraffic] Error NormalizeScore in parsing pod resources request: %v\n", err)
		return framework.NewStatus(framework.Error, err.Error())
	}
	if memoryRequest.IsZero() {
		memoryRequestStr = "Not requested"
	} else {
		memoryRequestStr = memoryRequest.String()
	}

	if cpuRequest.IsZero() {
		cpuRequestStr = "Not requested"
	} else {
		cpuRequestStr = cpuRequest.String()
	}

	klog.Infof("[NetworkTraffic] POD REQUESTED - Memory: %s,CPU: %s, Latency Soft Constraint: %f, Latency Hard Constraint: %f\n", memoryRequestStr, cpuRequestStr, latencySoftConstraint, latencyHardConstraint)

	//###################### Check if a specific node is requested in YAML #########################
	//##############################################################################################
	nodeName := pod.Spec.NodeName
	if nodeName != "" {
		// Assign the highest score to the requested node and lowest score to others
		for i, node := range scores {
			if node.Name == nodeName {
				scores[i].Score = framework.MaxNodeScore
			} else {
				scores[i].Score = framework.MinNodeScore
			}
		}
		klog.Infof("[NetworkTraffic] Nodes final score with requested node '%s' is: %v\n", nodeName, scores)
		return nil

	} else {

		//############################# Agent suggestion #########################################
		//#########################################################################################

		conn, err := net.Dial("tcp", "localhost:8765")
		if err != nil {
			klog.Infof("[NetworkTraffic] Error creating tcp connection to localhost:8765. Scheduling with default scoring without suggestion.\n")
			var higherScore int64
			for _, node := range scores {
				if higherScore < node.Score {
					higherScore = node.Score
				}
			}
			for i, node := range scores {
				scores[i].Score = 100 * (framework.MaxNodeScore - (node.Score * framework.MaxNodeScore / higherScore)) / higherScore
			}
			klog.Infof("[NetworkTraffic] Nodes final scores without suggestion from model: %v\n", scores)
		} else {

			// Marshal resource values to JSON
			resourceValues := struct {
				CPURequest            string  `json:"cpuRequest"`
				MemoryRequest         string  `json:"memoryRequest"`
				LatencySoftConstraint float64 `json:"latencySoftConstraint"`
				LatencyHardConstraint float64 `json:"latencyHardConstraint"`
			}{
				CPURequest:            cpuRequestStr,
				MemoryRequest:         memoryRequestStr,
				LatencySoftConstraint: latencySoftConstraint,
				LatencyHardConstraint: latencyHardConstraint,
			}

			resourceData, err := json.Marshal(resourceValues)
			if err != nil {
				klog.Infof("[NetworkTraffic] Error marshalling resource values.\n")
			}

			fmt.Fprintln(conn, "setResourceValues", string(resourceData)) // Send resource values to server
			klog.Infof("[NetworkTraffic] ResourceValues set.\n")

			connTest, err := net.Dial("tcp", "localhost:8765")
			fmt.Fprintln(connTest, "getResourceValues") // Request nodes suggestions
			responseTest, err := bufio.NewReader(connTest).ReadString('\n')
			klog.Infof("[NetworkTraffic] SET RESOURCES:\n %s", responseTest)

			conn, err := net.Dial("tcp", "localhost:8765")
			fmt.Fprintln(conn, "getSuggestion") // Request nodes suggestions

			response, err := bufio.NewReader(conn).ReadString('\n')
			if err != nil {
				if err == io.EOF {
					klog.Infof("[NetworkTraffic] Connection closed by server. Model suggestion successfully acquired.\n")
				} else {
					klog.Infof("[NetworkTraffic] Error while reading agent suggestion: %s\n", err)
					return framework.NewStatus(framework.Error, err.Error())
				}
			}
			var suggestionMap map[string]int64

			if err := json.Unmarshal([]byte(response), &suggestionMap); err != nil {
				log.Fatal(err)
			}
			nodeNameMap := make(map[string]int64)

			// get nodenames and set new scores
			for ip, value := range suggestionMap {
				nodeName, err := getNodeNameFromInternalIP(ip)
				if err == nil {
					nodeNameMap[nodeName] = value
				}
			}

			for i, node := range scores {
				externalScore, exists := nodeNameMap[node.Name]
				if exists {
					scores[i].Score = externalScore
				}
			}
			klog.Infof("[NetworkTraffic] Nodes final scores with model suggestion: %v\n", scores)

		}
		defer conn.Close()
		return nil

	}

}

func getPodResourceRequests(pod *v1.Pod) (memoryRequest, cpuRequest resource.Quantity, latencySoftConstraint float64, latencyHardConstraint float64, err error) {
	containers := pod.Spec.Containers
	if len(containers) == 0 {
		return resource.Quantity{}, resource.Quantity{}, -1, -1, errors.New("Error: No containers found in the pod spec")
	}

	container := containers[0]
	resources := container.Resources

	memoryRequest = resources.Requests[v1.ResourceMemory]
	cpuRequest = resources.Requests[v1.ResourceCPU]
	latencySoftConstraintStr, existsSoft := pod.Annotations["latencySoftConstraint"]
	latencyHardConstraintStr, existsHard := pod.Annotations["latencyHardConstraint"]

	if existsSoft {
		latencySoftConstraint, err = strconv.ParseFloat(latencySoftConstraintStr, 64)
		if err != nil {
			return resource.Quantity{}, resource.Quantity{}, -1, -1, errors.New("Error parsing soft latency constraint\n")
		}
	}

	if existsHard {
		latencyHardConstraint, err = strconv.ParseFloat(latencyHardConstraintStr, 64)
		if err != nil {
			return resource.Quantity{}, resource.Quantity{}, -1, -1, errors.New("Error parsing hard latency constraint\n")
		}
	}

	return memoryRequest, cpuRequest, latencySoftConstraint, latencyHardConstraint, nil
}

func getNodeNameFromInternalIP(internalIP string) (string, error) {
	config, err := clientcmd.BuildConfigFromFlags("", "/etc/kubernetes/scheduler.conf")

	if err != nil {
		return "", fmt.Errorf("Error building Kubernetes config: %v", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "", fmt.Errorf("Error creating Kubernetes client: %v", err)
	}

	nodes, err := clientset.CoreV1().Nodes().List(context.Background(), metav1.ListOptions{})
	if err != nil {
		return "", fmt.Errorf("Error listing nodes: %v", err)
	}

	for _, node := range nodes.Items {
		for _, address := range node.Status.Addresses {
			if address.Type == v1k8s.NodeInternalIP && address.Address == internalIP {
				return node.Name, nil
			}
		}
	}

	return "", fmt.Errorf("Node name not found for internal IP %s", internalIP)
}
