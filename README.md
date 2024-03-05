
# "Orchestrating tasks in the cloud continuum with reinforcement learning"
### s302948 MATRANGA SONIA 

This thesis proposes and develops a new approach to scheduling within Kubernetes clusters. In particular, the proposed scheduler leverages a reinforcement-learning algorithm of type DQN by integrating a custom plugin used in the scoring phase of the scheduling chain, in order to optimize load distribution across available nodes with an innovative and intelligent approach.

The reinforcement-learning algorithm used in the plugin dynamically evaluates the available resources on the cluster nodes and, through reinforcement, learns to manage them by assigning a score to each node that reflects its suitability for hosting new pods. This intelligent evaluation thus provides a decision-making but also predictive tool to the scheduling system, which over time can make informed and increasingly better decisions about the optimal distribution of new workloads. The implementation has been tested in a Kind Kubernetes environment.

## Architecture

In the proposed solution, there are four fundamental communication units:

- Plugin: It intercepts the scoring phase and intervenes by requesting scheduling suggestions from the RL model, leveraging the exposed APIs.
- Suggestions server: It exposes the APIs to obtain scheduling suggestions.
- RL Model: It utilizes node metrics obtained from Prometheus to suggest on which node the new pod should be scheduled.
- Prometheus: It exposes various metrics collected on the nodes.

![Architettura](./img/Architettura.jpg)

The communication between these elements occurs during the scoring phase, although the plugin can be extended to work on other phases if the extensible APIs are used as indicated [here](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/#interfaces).

## Usage

To test the scheduler, you need to follow all the steps outlined below:

1. **Setup Kind Cluster**:

   Create a Kind cluster with 4 nodes using the configuration file [kind-config.yaml](kind-config.yaml), , where the paths of the model and venv need to be correctly configured. Execute it with:
   ```
   kind create cluster --name vbeta3 --config kind-config.yaml
   ```

3. **Configure Prometheus with Node Exporter**:

   Install [Prometheus configured with Node Exporter](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-node-exporter) into the cluster to provide metrics to the RL model.
   ```
   kubectl create namespace monitoring
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   helm install prometheus prometheus-community/prometheus-node-exporter -n monitoring
   ```
   Follow the steps outlined in the article [kind-fix missing prometheus operator targets](https://medium.com/@charled.breteche/kind-fix-missing-prometheus-operator-targets-1a1ff5d8c8ad) to let prometheus work on a kind cluster.

4. **Configure custom scheduler on master node**:

    After automatically creating the cluster, it is needed to add the configuration of the new scheduler into the master node (control-plane of the cluster).
   So, it's necessary to add files to the following paths:
   - `etc/kubernetes/manifests`: Copy the [kube-scheduler.yaml](../kube-scheduler.yaml) file containing the new configuration of the scheduler pod that will be created locally.
   - `etc/kubernetes`: Copy the [networktraffic-config.yaml](../networktraffic-config.yaml) file containing the configuration of the scheduler plugins, from which you can enable or disable default behaviors.

5. **Build and Load Local Scheduler Image**:

    The new scheduler image to be created in the cluster should be generated locally using the files from the directory [scheduler-plugins](scheduler-plugins), which contains the code of the plugins from the repository [scheduler-plugins](https://github.com/kubernetes-sigs/scheduler-plugins) to which the custom plugin NetworkTraffic has been added. This plugin performs scoring based on the suggestions of the reinforcement learning model.
   The command `make local-image` will generate a new Docker image `localhost:5000/scheduler-plugins/kube-scheduler:latest`.
   At this point, the image is loaded onto the cluster nodes so that it is locally available on the node:
   ```
   make local-image
   kind load docker-image --name  vbeta3 localhost:5000/scheduler-plugins/kube-scheduler:latest
   ```
   Alternatively, the image can be uploaded to DockerHub by modifying the kube-scheduler.yaml configuration file to specify to the master node from where to download the image, as it is set in spec section of [kube-scheduler.yaml](../kube-scheduler.yaml) configuration file.

6. **Restart the control-plane**
   It is necessary to restart the control-plane and delete the scheduler pod to create the new scheduler with the correct configuration and the local image. The scheduler pod can be obtained if using kubectl with the command:
   ```
    kubectl get pods -n kube-system
   ```
   where the pod scheduler is named like `kube-scheduler-vbeta3-control-plane` .


## Scheduling Test

The [nginx-deployment.yaml](../nginx-deployment.yaml) can be applyed to the cluster to test scheduling: 
   ```
   kubectl create -f nginx-deployment.yaml
   ```
Then, by observing scheduler logs it is possible to analyze the behavoiour when a new pod is scheduled:
   ```
   kubectl logs -f kube-scheduler-vbeta3-control-plane  -n kube-system | grep "NetworkTraffic
   ```
At this point an output like this will appear so that pods are scheduled on the worker node with maximum score.

![Screenshot](./img/Screenshot.jpg)

## Key paths

Model directory:
- `model/cleanrl`: contains all files of [cleanrl](https://docs.cleanrl.dev/) that must be mounted on scheduler pod
- `model/main.py`: contains functions to expose agent suggestions and to allow communication between venv and prometheus
- other files used on previous versions 

Scheduler-plugins directory:
- `scheduler-plugins/bulid/scheduler/Dockerfile`: scheduler dockerfile where it is configured the installation of new libraries to exec the mnodel and the venv is activated 
- `scheduler-plugins/cmd/sheduler/main.go`: starts the model and registers the custom plugin for the scheduler
- `scheduler-plugins/pkg/networktraffic/networktraffic.go`: defines the custom plugin
- `scheduler-plugins/pkg/networktraffic/prometheus.go`:functions for interaction between the custom plugin and Prometheus in case communication with the agent fails. Additionally, there are changes to library versions to ensure the repositories work correctly
See scheduler-plugins [README.md](scheduler-plugins/README.md) for more details.

Venv directory:
- `venv/lib/python3.9/site-packages/gymnasium/envs/classic_control/scheduling.py`: definition of the environment used by the DQN agent, which is located in the model. It also starts an app to visualize graphs on the agent.
- `venv/lib/python3.9/site-packages/gymnasium/envs/classic_control/__init__.py`: registers the new custom environment in Gymnasium
- `venv/lib/python3.9/site-packages/gymnasium/envs/classic_control/graph.py`: manages the creation of graphs to evaluate the agent

Configuration files:
- `kind-config.yaml`: Initial cluster configuration where Prometheus needs to be added
- `kube-scheduler.yaml`: Configuration of the scheduler pod where volumes of plugins, model, and venv are inserted
- `networktraffic-config`: Configuration file for the custom scheduler where plugins and default scheduler behaviors can be enabled or disabled. It passes Prometheus address as an argument.

 
 



