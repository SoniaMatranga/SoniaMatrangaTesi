# Scheduler Plugins

Repository extending the original [scheduler plugins](https://github.com/kubernetes-sigs/scheduler-plugins) project based on the [scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/).

This repository provides scheduling plugins that are used in large enterprises. These plugins can be embedded as Golang SDK libraries or used directly through pre-built images or Helm charts. Additionally, this repository incorporates best practices and utilities for composing high-quality custom scheduling plugins.

## Plugins

The kube-scheduler includes the following list of plugins. These can be configured by creating or modifying [scheduler profiles](https://kubernetes.io/docs/reference/scheduling/config/#multiple-profiles), as it is done in the file [networktraffic-config.yaml](../networktraffic-config.yaml):

* [Capacity Scheduling](pkg/capacityscheduling/README.md)
* [Coscheduling](pkg/coscheduling/README.md)
* [Node Resources](pkg/noderesources/README.md)
* [Node Resource Topology](pkg/noderesourcetopology/README.md)
* [Preemption Toleration](pkg/preemptiontoleration/README.md)
* [Trimaran](pkg/trimaran/README.md)
* [Network-Aware Scheduling](pkg/networkaware/README.md)
* [NetworkTraffic Scheduling](pkg/networktraffic/README.md)

The networktraffic plugin is based on the [k8s creating a kube-scheduler plugin](https://medium.com/@juliorenner123/k8s-creating-a-kube-scheduler-plugin-8a826c486a1) guide.

## Usage

The new scheduler image is created locally using the command `make local-image`, which will generate a new Docker image `localhost:5000/scheduler-plugins/kube-scheduler:latest`.

At this point, the image is loaded onto the cluster nodes so that it is locally available on the master node:

``` kind load docker-image --name  vbeta3 localhost:5000/scheduler-plugins/kube-scheduler:latest  ```

Alternatively, it can be uploaded to DockerHub by modifying the configuration file [kube-scheduler.yaml](../kube-scheduler.yaml) and specifying the correct URL from which the master node should download the image.

For the plugin to work properly, it's essential to have Prometheus pre-installed within the cluster and to follow the steps outlined in the [README.md](../README.md)  before loading the new local image into the cluster, in order to enable communication between the model and the plugin.

## Key elements

The base image of the scheduler has been modified from `alpine:3.16` to `debian:11` to enable the execution of the RL model within the scheduler. Additionally, in the [dockerfile](build/scheduler/Dockerfile) of the scheduler, the installation of libraries to run the agent is configured, and the venv is activated.

Custom plugin registration occurs in `scheduler-plugins/cmd/sheduler/main.go`, which also initializes the model and registers the custom plugin for the scheduler.
To register the new plugin, simply add the following line in the file:

```app.WithPlugin(networktraffic.Name, networktraffic.New)```

The pkg directory contains all possible plugins, including networktraffic, which includes:

- [networktraffic.go](pkg/networktraffic/networktraffic.go): This file defines the custom plugin, which takes the Prometheus address and the interface from which to request metrics as inputs.
- [prometheus.go](pkg/networktraffic/prometheus.go): It contains functions for interaction between the custom plugin and Prometheus in case communication with the agent fails.

In general, there are changes to library versions to ensure that the repositories work correctly compared to the original repository.
