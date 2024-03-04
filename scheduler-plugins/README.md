[![Go Report Card](https://goreportcard.com/badge/kubernetes-sigs/scheduler-plugins)](https://goreportcard.com/report/kubernetes-sigs/scheduler-plugins) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/kubernetes-sigs/scheduler-plugins/blob/master/LICENSE)

# Scheduler Plugins

Repository basato su [scheduler plugins](https://github.com/kubernetes-sigs/scheduler-plugins) basato su [scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/).

Questo repository fornisce plugin di schedulazione che vengono utilizzati nelle grandi aziende. Questi plugin possono essere incorporati come librerie SDK Golang o utilizzati direttamente tramite immagini pre-compilate o grafici Helm. Inoltre, questo repository incorpora le migliori pratiche e utilità per comporre un plugin di schedulazione custom di alta qualità.

## Utilizzo


## Plugins

Il kube-scheduler include la seguente lista di plugins. Questi possono essere configurati creando o modificando gli
[scheduler profiles](https://kubernetes.io/docs/reference/scheduling/config/#multiple-profiles), come fatto nel file [FILE.yaml]

* [Capacity Scheduling](pkg/capacityscheduling/README.md)
* [Coscheduling](pkg/coscheduling/README.md)
* [Node Resources](pkg/noderesources/README.md)
* [Node Resource Topology](pkg/noderesourcetopology/README.md)
* [Preemption Toleration](pkg/preemptiontoleration/README.md)
* [Trimaran](pkg/trimaran/README.md)
* [Network-Aware Scheduling](pkg/networkaware/README.md)
* [NetworkTraffic Scheduling](pkg/networktraffic/README.md)

## Compatibility Matrix
