
# "Orchestrating tasks in the cloud continuum with reinforcement learning"
### Tesista: s302948 MATRANGA SONIA 

In questa tesi viene proposto e sviluppato un nuovo approccio alla schedulazione all’interno dei cluster Kubernetes. In particolare, lo scheduler proposto sfrutta un algoritmo di apprendimento per rinforzo (reinforcement-learning) di tipo DQN integrando un custom plugin utilizzato nella fase di scoring della catena di schedulazione, al fine di ottimizzare la distribuzione del load sui nodi disponibili con un approccio innovativo e intelligente.
L'algoritmo di reinforcement-learning usato nel plugin valuta dinamicamente le risorse disponibili sui nodi del cluster e, tramite rinforzo, impara a gestirle assegnando ad ogni nodo uno score che riflette la sua idoneità per ospitare nuovi pod. Questa valutazione intelligente fornisce dunque uno strumento decisionale ma anche predittivo al sistema di schedulazione, che nel tempo può quindi prendere decisioni informate e sempre migliori sulla distribuzione ottimale dei nuovi carichi di lavoro. L'implementazione è stata testata su un ambiente Kubernetes Kind.

## Cluster Kind

Il cluster realizzato con Kind contiene 4 nodi ed è stato creato tramite file kind-config.yaml dove vanno configurati correttamente i path di model e venv:

   ```kind create cluster --name vbeta3 --config kind-config.yaml ``` 

## Configurazione Prometheus con node-exporter

All'interno del cluster prometheus viene usato per fornire metriche al modello dello scheduler e viene configurato seguendo:


## Scheduler 

La nuova immagine dello scheduler da creare nel cluster viene creata localmente tramite i file della directory scheduler-plugins, contenente il codice dei plugins contenuti nel repository [scheduler-plugins](https://github.com/kubernetes-sigs/scheduler-plugins) ai quali è stato aggiunto il custom plugin pNetworkTraffic, che effettua lo scoring in base ai suggerimenti del modello di reinforcement learning.
Viene quindi creata l'immagine locale tramite il comando `make local-image` che andrà a creare una nuova immagine docker `localhost:5000/scheduler-plugins/kube-scheduler:latest`.
A questo punto l'immagine viene caricata sui nodi del cluster affinchè sia presente localmente nel nodo:

``` kind load docker-image --name  vbeta3 localhost:5000/scheduler-plugins/kube-scheduler:latest  ```

In alternativa può essere caricata in DockerHub se si modifica il file di configurazione kube-scheduler.yaml indicando al nodo master da dove scaricare l'immagine.

## Configurazione scheduler nel master node
Dopo aver creato automaticamente il cluster, si aggiunge la configurazione del nuovo scheduler nel nodo master (control-plane del cluster):
- `etc/kubernetes/manifests`: copiare il file kube-scheduler.yaml contenente la nuova configurazione del pod scheduler creato a partire dall'immagine creata localmente
- `etc/kubernetes`: copiare i file networktraffic-config.yaml che contiene la configurazione dei plugin dello scheduler, da cui è possibile abilitare o disabilitare comportamenti di default

é necessario riavviare il control-plane e cancellare il pod scheduler per creare il nuovo scheduler con la configurazione corretta e l'immagine locale. Il pod scheduler può essere ricavato se si usa kubectl con il comando:
``` kubectl get pods -n kube-system ```
dal quale tra i pod si ottiene anche `kube-scheduler-vbeta3-control-plane` che  è il pod scheduler.

## Test di funzionamento

Il file nginx-deployment.yaml può essere eseguito per testare la schedulazione eseguendo:

```kubectl create -f nginx-deployment.yaml ```

Osservando i log dello scheduler è possibile osservarne il comportamento quando viene effettuata una nuova schedulazione:

 ```kubectl logs -f kube-scheduler-vbeta3-control-plane  -n kube-system | grep "NetworkTraffic ```

 Si ottiene un output simile per cui i pod sono schedulati sul nodo worker con score maggiore.

![Screenshot](./Screenshot.jpg)
 
 



