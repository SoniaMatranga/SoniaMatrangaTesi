# Overview

This folder holds the NetworkTraffic plugin 

## Maturity Level

- [x] 💡 Sample (for demonstrating and inspiring purpose)
- [ ] 👶 Alpha (used in companies for pilot projects)
- [ ] 👦 Beta (used in companies and developed actively)
- [ ] 👨 Stable (used in companies for production workloads)

## Networktraffic Plugin (Score)

The `Networktraffic` plugin let pods to be scheduled based on the suggestion provided by the RL model.

## Scheduler Config example 

Consider the following scheduler config as an example to enable the plugin:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
clientConnection:
  kubeconfig: "/etc/kubernetes/scheduler.conf"
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      enabled:
      - name: NetworkTraffic
      disabled:
      - name: "*"
  pluginConfig:
  - name: NetworkTraffic
    args:
      prometheusAddress: "http://10.96.105.208:9090"
      networkInterface: "eth0"
      timeRangeInMinutes: 3

```