package networktraffic

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"time"

	v1 "k8s.io/api/core/v1"
	v1k8s "k8s.io/api/core/v1"
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
		return 0, framework.NewStatus(framework.Error, fmt.Sprintf("error getting node bandwidth measure: %s", err))
	}
	klog.Infof("[NetworkTraffic] node '%s' bandwidth: %s", nodeName, nodeBandwidth.Value)
	return int64(nodeBandwidth.Value), nil
}

func (n *NetworkTraffic) ScoreExtensions() framework.ScoreExtensions {
	return n
}

func (n *NetworkTraffic) NormalizeScore(ctx context.Context, state *framework.CycleState, pod *v1.Pod, scores framework.NodeScoreList) *framework.Status {
	klog.Infof("[NetworkTraffic] NormalizeScore method called...")

	//==== Agent suggestion ======

	conn, err := net.Dial("tcp", "localhost:8765")
	if err != nil {
		klog.Infof("[NetworkTraffic] Error creating tcp connection to localhost:8765")
		klog.Infof("[NetworkTraffic] Something wrong in getting suggestions: using default score")
		var higherScore int64
		for _, node := range scores {
			if higherScore < node.Score {
				higherScore = node.Score
			}
		}
		for i, node := range scores {
			scores[i].Score = framework.MaxNodeScore - (node.Score * framework.MaxNodeScore / higherScore)
		}
		klog.Infof("[NetworkTraffic] Nodes final score without suggestion from model: %v", scores)
	} else {

		fmt.Fprintln(conn, "getSuggestion")
		response, err := bufio.NewReader(conn).ReadString('\n')
		if err != nil {
			if err == io.EOF {
				klog.Infof("[NetworkTraffic] Connection closed by server")
			} else {
				return framework.NewStatus(framework.Error, err.Error())
			}
		}
		klog.Infof("[NetworkTraffic] Got suggestion: %s\n", response)

		// Decode suggestions JSON
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
				klog.Infof("[NetworkTraffic] node.Name: %s new score is %d \n", node.Name, externalScore)
				scores[i].Score = externalScore
			}
		}
		klog.Infof("[NetworkTraffic] Nodes final score: %v", scores)
	}

	defer conn.Close()
	return nil
}

func getNodeNameFromInternalIP(internalIP string) (string, error) {
	config, err := clientcmd.BuildConfigFromFlags("", "/etc/kubernetes/scheduler.conf")

	if err != nil {
		return "", fmt.Errorf("error building Kubernetes config: %v", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "", fmt.Errorf("error creating Kubernetes client: %v", err)
	}

	nodes, err := clientset.CoreV1().Nodes().List(context.Background(), metav1.ListOptions{})
	if err != nil {
		return "", fmt.Errorf("error listing nodes: %v", err)
	}

	for _, node := range nodes.Items {
		for _, address := range node.Status.Addresses {
			if address.Type == v1k8s.NodeInternalIP && address.Address == internalIP {
				klog.Infof("[NetworkTraffic] Internal IP %s corresponds to Node: %s", internalIP, node.Name)
				return node.Name, nil
			}
		}
	}

	return "", fmt.Errorf("node name not found for internal IP %s", internalIP)
}
