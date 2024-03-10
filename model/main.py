from kubernetes import client, config
import subprocess
import numpy as np
import requests
import socket
import multiprocessing
from multiprocessing import Manager
import json
import os
import time


config.load_kube_config()
# Configura l'accesso al cluster Kubernetes
v1 = client.CoreV1Api()
#nodes = v1.list_node()



manager = Manager()
suggestion_dict = manager.dict()
step = manager.Value('b', False)

def getStep():
    global step
    return step.value

def setStep(step_value):
    global step
    step.value = step_value

def setSuggestion(value):
    global suggestion_dict
    suggestion_dict.update(value)

def getSuggestion():
    global suggestion_dict
    return suggestion_dict.copy()



#______________  nodi del cluster _______________

def node_count():
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        nodes = v1.list_node()

        node_count = len(nodes.items)
        print(f"Cluster contains {node_count} nodes.")
        return node_count

    except Exception as e:
        print(f"Error while retrieving the number of nodes: {str(e)}")

def get_nodes_names():
    names = []
    try:
        # Esegui il comando "kubectl top nodes" 
        command = ["kubectl", "top", "nodes"]
        output = subprocess.check_output(command, universal_newlines=True)
        lines = output.split('\n')

        lines = lines[1:]  # Scarta la prima riga poiché contiene gli header
        
        # Stampa le metriche
        for line in lines:
            if line:
                parts = line.split()
                node_name, cpu_usage, _, memory_usage, _ = parts
                names.append(f"{node_name}")

    except subprocess.CalledProcessError as e:
        print(f"Error while exectuing kubectl: {e}")
    except Exception as e:
        print(f"General error: {e}")
    print(names)
    return np.array(names)

def get_worker_nodes_internal_ips():
    try:
        config.load_kube_config()
        # Configura l'accesso al cluster Kubernetes
        v1 = client.CoreV1Api()
        nodes = v1.list_node()

        worker_ips = []
        for node in nodes.items:
            for label in node.metadata.labels:
                if label.endswith("/worker"):
                    for address in node.status.addresses:
                        if address.type == "InternalIP":
                            worker_ips.append(address.address)

        print(f"IP ADDRESSES: {worker_ips}")

        return worker_ips

    except Exception as e:
        print(f"Error while retrieving internal IPs of worker nodes: {str(e)}")
        return ["172.19.0.4", "172.19.0.5", "172.19.0.3"]


#____________ metriche da metric server ____________


def get_memory_usage_metrics_server():

    metrics = []
    try:
        # Esegui il comando "kubectl top nodes" 
        command = ["kubectl", "top", "nodes"]
        output = subprocess.check_output(command, universal_newlines=True)
        lines = output.split('\n')

        lines = lines[1:]  # Scarta la prima riga poiché contiene gli header
        
        # Stampa le metriche
        for line in lines:
            if line:
                parts = line.split()
                node_name, cpu_usage, _, memory_usage, _ = parts
                #print(f"Name: {node_name}  Memory_usage: {memory_usage}")
                metrics.append(f"{memory_usage}".strip("Mi"))

    except subprocess.CalledProcessError as e:
        print(f"Error while exectuing kubectl: {e}")
    except Exception as e:
        print(f"General error: {e}")
    print(metrics)
    return np.array(metrics, dtype=np.float32)

def get_usage_metrics_server():

    metrics = []
    try:
        # Esegui il comando "kubectl top nodes" 
        command = ["kubectl", "top", "nodes"]
        output = subprocess.check_output(command, universal_newlines=True)
        lines = output.split('\n')

        lines = lines[1:]  # Scarta la prima riga poiché contiene gli header
        
        # Stampa le metriche
        for line in lines:
            if line:
                parts = line.split()
                node_name, cpu_usage, _, memory_usage, _ = parts
                #print(f"Name: {node_name}  Memory_usage: {memory_usage}")
                metrics.append(f"{node_name}:{memory_usage}")

    except subprocess.CalledProcessError as e:
        print(f"Error while exectuing kubectl: {e}")
    except Exception as e:
        print(f"General error: {e}")
    print(metrics)
    return np.array(metrics)

def get_capacity_metrics_server():
    metrics = []
    try:
        # Ottieni le metriche di utilizzo della CPU e della memoria per i nodi
        node_metrics = v1.list_node(resource_version="0")

        # Stampa le metriche dei nodi
        for node in node_metrics.items:
           # print(f"Nome del nodo: {node.metadata.name}")
            for condition in node.status.conditions:
                if condition.type == "Ready" and condition.status == "True":
                   # print(f"Capacità CPU: {node.status.capacity['cpu']}  Capacità memoria: {node.status.capacity['memory']}")
                    metrics.append(f"{node.metadata.name}:{node.status.capacity['memory']}")
                    break

    except Exception as e:
        print(f"Errore durante il recupero delle metriche dei nodi: {str(e)}")
    #print(metrics)
    return np.array(metrics)

def get_memory_capacity_metrics_server():
    metrics = []
    try:
        # Ottieni le metriche di utilizzo della CPU e della memoria per i nodi
        node_metrics = v1.list_node(resource_version="0")

        # Stampa le metriche dei nodi
        for node in node_metrics.items:
           # print(f"Nome del nodo: {node.metadata.name}")
            for condition in node.status.conditions:
                if condition.type == "Ready" and condition.status == "True":
                    metrics.append(f"{node.status.capacity['memory']}".strip("Ki"))
                    break

    except Exception as e:
        print(f"Errore durante il recupero delle metriche dei nodi: {str(e)}")
    print(metrics)
    return np.array(metrics, dtype=np.float32)

#####################################    NETWORKING   ########################################################## 

def get_networking_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'sum_over_time(node_network_receive_bytes_total{{instance="{internal_ip}:9100",device="eth0"}}[5m])' #Results are in the shape [timestamp, recieved_bytes_value]

    try:
        response = requests.get(prometheus_url, params={'query': prometheus_query})
        if response.status_code == 200:
            metrics_data = response.json()
            return metrics_data
        else:
            print(f"Error on HTTP request: status code {response.status_code}")
    except Exception as e:
        print(f"Error on HTTP request: {str(e)}")

def get_nodes_network_usage(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        network_usage = get_networking_prometheus(node)
        if network_usage and 'data' in network_usage and 'result' in network_usage['data']:
                result_list = network_usage['data']['result']
                if result_list:
                    value_list = result_list[0].get('value')                    
                    if value_list:
                        metrics.append(float(value_list[1]))

    print(metrics)
    return metrics

#########################################  CPU  ###################################################

def get_cpu_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'100 - (avg(irate(node_cpu_seconds_total{{mode="idle", instance="{internal_ip}:9100"}}[1m])) * 100)' #Results are in the shape [metadata, cpu_percentage_value]

    try:
        response = requests.get(prometheus_url, params={'query': prometheus_query})
        if response.status_code == 200:
            metrics_data = response.json()
            return metrics_data
        else:
            print(f"Error on HTTP request: status code {response.status_code}")
    except Exception as e:
        print(f"Error on HTTP request: {str(e)}")

def get_nodes_cpu_usage(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        cpu_usage = get_cpu_prometheus(node)
        if cpu_usage and 'data' in cpu_usage and 'result' in cpu_usage['data']:
                result_list = cpu_usage['data']['result']
                if result_list:
                    value_list = result_list[0].get('value')
                    if value_list:
                        # add metric to  list
                        metrics.append(float(value_list[1]))

    print(metrics)
    return metrics




def handle_request(request):
    command, value = request.strip().split(' ', 1) if ' ' in request else (request.strip(), None)

    if command == "getSuggestion":
        print(f"[NetworkTraffic] Server step value: {getStep()}")
        setStep(True)
        time.sleep(10) 
        return getSuggestion()
    
    elif command == "setSuggestion":
        if value is not None:
            suggestion_data = json.loads(value)
            setSuggestion(suggestion_data)
            return {"status": "success", "message": "Suggestion set successfully."}
        else:
            return {"status": "error", "message": "Missing value for setSuggestion command."}
    elif command == "getStep":
        return getStep()
    elif command == "setStep":
        if value is not None:
            step_data = json.loads(value)
            setStep(step_data)
            return {"status": "success", "message": "Step flag set successfully."}
        else:
            return {"status": "error", "message": "Missing value for setStep command."}
    else:
        return {"status": "error", "message": f"Unknown command: {command}"}

if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 8765))
    server_socket.listen(1)

    print("Server is listening on  http://localhost:8765")

    while True:
        client_socket, client_address = server_socket.accept()
        request = client_socket.recv(1024).decode("utf-8").strip()
        response_data = handle_request(request)
        response_json = json.dumps(response_data)
        client_socket.send(response_json.encode("utf-8"))
        client_socket.close()
