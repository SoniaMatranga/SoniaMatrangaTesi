from kubernetes import client, config
import subprocess
import numpy as np
import requests
import socket
from multiprocessing import Manager
import json
import time
import threading



config.load_kube_config()
v1 = client.CoreV1Api()


manager = Manager()
suggestion_dict = manager.dict()
step = manager.Value('b', False)
# Crea una lista di tuple per rappresentare i valori delle risorse
resource_values = manager.list()

# Aggiungi i valori iniziali delle risorse
resource_values.append(("cpuRequest", "0"))
resource_values.append(("memoryRequest", "0"))
resource_values.append(("latencySoftConstraint", -1))
resource_values.append(("latencyHardConstraint", -1))

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

def setResourceValues(values):
    global resource_values
    for key, value in values.items():
        for i, (k, v) in enumerate(resource_values):
            if k == key:
                resource_values[i] = (k, value)
                break


def getResourceValues():
    global resource_values
    return {key: value for key, value in resource_values}




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

def get_nodes_state(policy, ips): 
    num_ips = len(ips)
    if policy == "LA" or policy == "MA":   
        """ while True:
                pods_number = get_nodes_running_pods(ips)
                cpu_values = get_nodes_cpu_usage(ips)
                mem_values = get_nodes_mem_usage(ips)
                net_values = get_nodes_network_usage(ips)
                #disk_values = get_nodes_disk_usage(ips)
                
                if len(pods_number) == num_ips and len(cpu_values) == num_ips and len(mem_values) == num_ips and len(net_values) == num_ips:
                    avg_values = np.mean(np.array([pods_number, cpu_values, mem_values, net_values]), axis=0)
                    return avg_values
                else:
                    print("Number of returned values is different from number of nodes. Repeat the request.")
                    continue  """
        while True:
            cpu_values = get_nodes_running_pods(ips)
            if len(cpu_values) == num_ips:
                return cpu_values
            
    elif policy == "LC": #least connections policy
        return get_nodes_network_connections(ips)
    elif policy == "P0":
        while True:
                pods_number = get_nodes_running_pods(ips)
                cpu_values = get_nodes_cpu_usage(ips)
                mem_values = get_nodes_mem_usage(ips)
                """ if len(pods_number) == num_ips and len(cpu_values) == num_ips and len(mem_values) == num_ips:
                    avg_values = np.mean(np.array([pods_number, cpu_values, mem_values]), axis=0)
                    return np.concatenate((avg_values, throughput))
                else:
                    print("Number of returned values is different from number of nodes. Repeat the request.")
                    continue """
                if len(pods_number) == num_ips and len(cpu_values) == num_ips and len(mem_values) == num_ips :
                    return np.concatenate((pods_number, cpu_values, mem_values))
                else:
                    print("Number of returned values is different from number of nodes. Repeat the request.")
                    continue
    else:
        return {"status": "error", "message": f"Unknown policy: {policy}"}
        

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

    return metrics

        

#####################################  DISK METRICS  ################################################

def get_disk_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'100 - (node_filesystem_free_bytes{{mountpoint="/run",instance="{internal_ip}:9100"}} / node_filesystem_size_bytes{{mountpoint="/run",instance="{internal_ip}:9100"}} * 100)' #Results are in the shape [metadata, disk_percentage_value]

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

    return metrics

#####################################  PODS METRICS  ################################################

def get_pods_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'kubelet_running_pods{{instance="{internal_ip}:10250"}}' #Results are in the shape [metadata, number of pods]

    try:
        response = requests.get(prometheus_url, params={'query': prometheus_query})
        if response.status_code == 200:
            metrics_data = response.json()
            return metrics_data
        else:
            print(f"Error on HTTP request: status code {response.status_code}")
    except Exception as e:
        print(f"Error on HTTP request: {str(e)}")

def get_nodes_running_pods(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        cpu_usage = get_pods_prometheus(node)
        if cpu_usage and 'data' in cpu_usage and 'result' in cpu_usage['data']:
                result_list = cpu_usage['data']['result']
                if result_list:
                    value_list = result_list[0].get('value')
                    if value_list:
                        # add metric to  list
                        metrics.append(float(value_list[1]))

    return metrics

#####################################  LATENCY METRICS  ################################################


def get_nodeuser_latency(internal_ip):
    try:
        response = requests.get(f"http://{internal_ip}:8100/")
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to get latency for node {internal_ip}. Status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Something went wrong in getting latency for node {internal_ip}... \n{e}")
        return None

def get_nodes_latency(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        latency = get_nodeuser_latency(node)
        if latency: 
             metrics.append(float(latency))
        else:
            print(f"Something went wrong in getting latency... \n")

    return metrics

#################################    NET  METRICS   ##############################################

def get_networking_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'(rate(node_network_receive_bytes_total{{instance="{internal_ip}:9100", device="eth0"}}[5m]))/10^3' #Results are in the shape [timestamp, recieved_bytes_value]

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

    return metrics

def get_node_connections_prometheus(internal_ip):
    prometheus_url = "http://10.96.105.208:9090/api/v1/query"
    prometheus_query = f'node_netstat_Tcp_CurrEstab{{instance="{internal_ip}:9100"}}' #Results are in the shape [timestamp, recieved_bytes_value]

    try:
        response = requests.get(prometheus_url, params={'query': prometheus_query})
        if response.status_code == 200:
            metrics_data = response.json()
            return metrics_data
        else:
            print(f"Error on HTTP request: status code {response.status_code}")
    except Exception as e:
        print(f"Error on HTTP request: {str(e)}")

def get_nodes_network_connections(ips):
    metrics = [] 

    for i, node in enumerate(ips): 
        network_usage = get_node_connections_prometheus(node)
        if network_usage and 'data' in network_usage and 'result' in network_usage['data']:
                result_list = network_usage['data']['result']
                if result_list:
                    value_list = result_list[0].get('value')                    
                    if value_list:
                        metrics.append(float(value_list[1]))

    return metrics




##################################  SUGGESTIONS SERVER  #########################################

def handle_request(request):
    command, value = request.strip().split(' ', 1) if ' ' in request else (request.strip(), None)

    if command == "getSuggestion":
        """ setStep(True)      
        while getStep() == True:
            time.sleep(0.1)  """

        return getSuggestion()
  
    
    elif command == "setSuggestion":

        if value is not None:
            suggestion_data = json.loads(value)
            setSuggestion(suggestion_data)
            return {"status": "success", "message": "Suggestion set successfully."}
        else:
            return {"status": "error", "message": "Missing value for setSuggestion command."}
        
    elif command == "getStep":
        step = getStep()
        return step
    
    elif command == "setStep":

        if value is not None:
            step_data = json.loads(value)
            setStep(step_data)
            return {"status": "success", "message": "Step flag set successfully."}
        else:
            return {"status": "error", "message": "Missing value for setStep command."}
        
    elif command == "setResourceValues":
        if value is not None:
            resource_data = json.loads(value)
            setResourceValues(resource_data)
            setStep(True) 
            return {"status": "success", "message": "Resource values set successfully."}
        else:
            return {"status": "error", "message": "Missing value for setResourceValues command."}
        
    elif command == "getResourceValues":
        return getResourceValues()    
    else:
        return {"status": "error", "message": f"Unknown command: {command}"}
    

def handle_client(client_socket):
    request = client_socket.recv(1024).decode("utf-8").strip()
    response_data = handle_request(request)
    response_json = json.dumps(response_data)
    client_socket.send(response_json.encode("utf-8"))
    client_socket.close()
    



if __name__ == "__main__":
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("localhost", 8765))
        server_socket.listen(55)
        print("Server is listening on  http://localhost:8765")
    except socket.error as e:
        print(f"something went wrong when starting the server...\n {e}")

    while True:
        client_socket, client_address = server_socket.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
        
        
        


