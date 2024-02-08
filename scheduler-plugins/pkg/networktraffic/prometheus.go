package networktraffic

import (
	"context"
	"fmt"
	"time"

	v1k8s "k8s.io/api/core/v1"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"

	"github.com/prometheus/client_golang/api"
	v1 "github.com/prometheus/client_golang/api/prometheus/v1"
	"github.com/prometheus/common/model"
	"k8s.io/klog/v2"
)

const (
	// nodeMeasureQueryTemplate is the template string to get the query for the node used bandwidth
	nodeMeasureQueryTemplate = "sum_over_time(node_network_receive_bytes_total{ instance=\"%s:9100\",device=\"%s\"}[%s])"
)

// Handles the interaction of the networkplugin with Prometheus
type PrometheusHandle struct {
	networkInterface string
	timeRange        time.Duration
	address          string
	api              v1.API
}

func NewPrometheus(address, networkInterface string, timeRange time.Duration) *PrometheusHandle {
	client, err := api.NewClient(api.Config{
		Address: address,
	})
	if err != nil {
		klog.Fatalf("[NetworkTraffic] Error creating prometheus client: %s", err.Error())
	}

	klog.Infof("[NetworkTraffic] Prometheus client created. ")
	return &PrometheusHandle{
		networkInterface: networkInterface,
		timeRange:        timeRange,
		address:          address,
		api:              v1.NewAPI(client),
	}
}

func (p *PrometheusHandle) GetNodeBandwidthMeasure(node string) (*model.Sample, error) {

	// Ottieni l'indirizzo IP interno del nodo
	internalIP, err := p.getInternalIPFromNodeName(node)
	if err != nil {
		return nil, fmt.Errorf("[NetworkTraffic] Error getting internal IP: %v", err)
	}
	query := getNodeBandwidthQuery(internalIP, p.networkInterface, p.timeRange)
	res, err := p.query(query)
	if err != nil {
		return nil, fmt.Errorf("[NetworkTraffic] Error querying prometheus: %w", err)
	}

	nodeMeasure := res.(model.Vector)
	if len(nodeMeasure) == 0 {
		return nil, fmt.Errorf("[NetworkTraffic] No results found for the query")
	}

	if len(nodeMeasure) != 1 {
		return nil, fmt.Errorf("[NetworkTraffic] Invalid response, expected 1 value, got %d", len(nodeMeasure))
	}

	return nodeMeasure[0], nil
}

func (p *PrometheusHandle) getInternalIPFromNodeName(nodeName string) (string, error) {
	config, err := clientcmd.BuildConfigFromFlags("", "/etc/kubernetes/scheduler.conf")

	if err != nil {
		return "", fmt.Errorf("error building Kubernetes config: %v", err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return "", fmt.Errorf("error creating Kubernetes client: %v", err)
	}

	node, err := clientset.CoreV1().Nodes().Get(context.Background(), nodeName, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("error getting node information: %v", err)
	}

	for _, address := range node.Status.Addresses {
		if address.Type == v1k8s.NodeInternalIP {
			klog.Infof("[NetworkTraffic] Node %s internal IP: %s", nodeName, address)
			return address.Address, nil
		}
	}

	return "", fmt.Errorf("internal IP not found for node %s", nodeName)
}

func getNodeBandwidthQuery(node, networkInterface string, timeRange time.Duration) string {
	return fmt.Sprintf(nodeMeasureQueryTemplate, node, networkInterface, timeRange)
}

func (p *PrometheusHandle) query(query string) (model.Value, error) {
	results, warnings, err := p.api.Query(context.Background(), query, time.Now())

	if len(warnings) > 0 {
		klog.Warningf("[NetworkTraffic] Warnings: %v\n", warnings)
	}

	return results, err
}
