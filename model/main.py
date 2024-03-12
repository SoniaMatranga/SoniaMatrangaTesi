from kubernetes import client, config
import subprocess
import numpy as np
import requests
import socket
from multiprocessing import Manager
import json
import time


config.load_kube_config()
v1 = client.CoreV1Api()



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



###################################   CLUSTER NODES   ###############################################

def node_count():
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        nodes = v1.list_node()
        node_count = len(nodes.items)
        return node_count

    except Exception as e:
        print(f"Error while retrieving the number of nodes: {str(e)}")

def get_nodes_names():
    names = []
    try:
        command = ["kubectl", "top", "nodes"]
        output = subprocess.check_output(command, universal_newlines=True)
        lines = output.split('\n')

        lines = lines[1:]  # fist line contains header
    
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
        return 

#####################################   ENV STATE   ###############################################

def get_nodes_state( resource, ips):     
    if resource == "CPU":
        return get_nodes_cpu_usage(ips)
    elif resource == "MEM":
        return get_nodes_mem_usage(ips)
    elif resource == "NET":
        return get_nodes_network_usage(ips)
    elif resource == "DISK":
        return get_nodes_disk_usage(ips)
    else:
        return {"status": "error", "message": f"Unknown resource: {resource}"}
        

#####################################  CPU METRICS  ################################################

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

#####################################  MEM METRICS  ################################################

def get_mem_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'node_memory_MemAvailable_bytes{{instance="{internal_ip}:9100"}}/10^9' #Results are in the shape [metadata, cpu_percentage_value]

    try:
        response = requests.get(prometheus_url, params={'query': prometheus_query})
        if response.status_code == 200:
            metrics_data = response.json()
            return metrics_data
        else:
            print(f"Error on HTTP request: status code {response.status_code}")
    except Exception as e:
        print(f"Error on HTTP request: {str(e)}")

def get_nodes_mem_usage(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        mem_usage = get_mem_prometheus(node)
        if mem_usage and 'data' in mem_usage and 'result' in mem_usage['data']:
                result_list = mem_usage['data']['result']
                if result_list:
                    value_list = result_list[0].get('value')
                    if value_list:
                        # add metric to  list
                        metrics.append(float(value_list[1]))

    print(metrics)
    return metrics

        
#################################    NET  METRICS   ##############################################

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


#####################################  DISK METRICS  ################################################

def get_disk_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'100 - (node_filesystem_free_bytes{{mountpoint="/var",instance="{internal_ip}:9100"}} / node_filesystem_size_bytes{{mountpoint="/var",instance="{internal_ip}:9100"}} * 100)' #Results are in the shape [metadata, disk_percentage_value]

    try:
        response = requests.get(prometheus_url, params={'query': prometheus_query})
        if response.status_code == 200:
            metrics_data = response.json()
            return metrics_data
        else:
            print(f"Error on HTTP request: status code {response.status_code}")
    except Exception as e:
        print(f"Error on HTTP request: {str(e)}")

def get_nodes_disk_usage(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        disk_usage = get_disk_prometheus(node)
        if disk_usage and 'data' in disk_usage and 'result' in disk_usage['data']:
                result_list = disk_usage['data']['result']
                if result_list:
                    value_list = result_list[0].get('value')
                    if value_list:
                        # add metric to  list
                        metrics.append(float(value_list[1]))

    print(metrics)
    return metrics




##################################  SUGGESTIONS SERVER  #########################################

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
