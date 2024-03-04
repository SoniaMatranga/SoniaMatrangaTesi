[![Go Report Card](https://goreportcard.com/badge/kubernetes-sigs/scheduler-plugins)](https://goreportcard.com/report/kubernetes-sigs/scheduler-plugins) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/kubernetes-sigs/scheduler-plugins/blob/master/LICENSE)

# Scheduler Plugins

Repository che estende il progetto originale [scheduler plugins](https://github.com/kubernetes-sigs/scheduler-plugins) basato su [scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/).

Questo repository fornisce plugin di schedulazione che vengono utilizzati nelle grandi aziende. Questi plugin possono essere incorporati come librerie SDK Golang o utilizzati direttamente tramite immagini pre-compilate o grafici Helm. Inoltre, questo repository incorpora le migliori pratiche e utilità per comporre un plugin di schedulazione custom di alta qualità.

## Plugins

Il kube-scheduler include la seguente lista di plugins. Questi possono essere configurati creando o modificando gli
[scheduler profiles](https://kubernetes.io/docs/reference/scheduling/config/#multiple-profiles), come fatto nel file [networktraffic-config.yaml](../networktraffic-config.yaml)

* [Capacity Scheduling](pkg/capacityscheduling/README.md)
* [Coscheduling](pkg/coscheduling/README.md)
* [Node Resources](pkg/noderesources/README.md)
* [Node Resource Topology](pkg/noderesourcetopology/README.md)
* [Preemption Toleration](pkg/preemptiontoleration/README.md)
* [Trimaran](pkg/trimaran/README.md)
* [Network-Aware Scheduling](pkg/networkaware/README.md)
* [NetworkTraffic Scheduling](pkg/networktraffic/README.md)

## Utilizzo

La nuova immagine dello scheduler viene creata localmente tramite il comando `make local-image` che andrà a generare una nuova immagine docker `localhost:5000/scheduler-plugins/kube-scheduler:latest`.

A questo punto l'immagine viene caricata sui nodi del cluster affinchè sia presente localmente nel nodo master:

``` kind load docker-image --name  vbeta3 localhost:5000/scheduler-plugins/kube-scheduler:latest  ```

In alternativa può essere caricata in DockerHub se si modifica il file di configurazione [kube-scheduler.yaml](../kube-scheduler.yaml) indicando tra le specifiche l'url corretto da cui il nodo master deve scaricare l'immagine.

## Elementi chiave

L'immagine base dello scheduler è stata modificata da `alpine:3.16` in `debian:11` per poter eseguire il modello RL all'interno dello scheduler. Nel [dockerfile](bulid/scheduler/Dockerfile) dello scheduler inoltre è configurata l'installazione delle librerie per eseguire l'agente e viene attivato il venv.

La registrazione del custom plugin avviene in  `scheduler-plugins/cmd/sheduler/main.go` che inoltre avvia il modello e registra il custom plugin per lo scheduler.
In particolare per registrare il nuovo plugin basta aggiungere nel file:
```app.WithPlugin(networktraffic.Name, networktraffic.New)```

La directory pkg contiene tutti i possibili plugins tra cui networktraffic dove sono inclusi:
- [networktraffic.go](pkg/networktraffic/networktraffic.go): file che definisce il custom plugin, al quale vengono mandati in input l'indirizzo di prometheus e l'interfaccia da cui richiedere le metriche.
- [prometheus.go](pkg/networktraffic/prometheus.go): contiene funzioni di interazione tra custom plugin e  prometheus nel caso in cui la comunicazione con l'agente dovesse fallire

In generale sono presenti modifiche a versioni di librerie per far funzionare correttamente le repo rispetto al repository originale.
