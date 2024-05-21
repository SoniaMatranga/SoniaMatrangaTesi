import sys

# Aggiungi la directory /usr/lib/python3.9 al percorso di ricerca dei moduli Python
sys.path.append('/usr/lib/python3.8')

import time
import ping3
from flask import Flask, request, jsonify
from prometheus_client import start_http_server, Summary


app = Flask(__name__)

@app.route('/')
def index():
    user_ip = "172.29.29.39"  # Ottieni l'IP dell'utente esterno
    num_pings = 50
    rtt_values = []
    for _ in range(num_pings):
        rtt = ping3.ping(user_ip)
        if rtt is not None:
            rtt_values.append(rtt)

    if rtt_values:
        avg_rtt = sum(rtt_values) / len(rtt_values) 
        return f'{avg_rtt * 1000:.2f}'
    else:
        return 'Failed to ping user\n'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8100)