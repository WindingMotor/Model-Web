import socket
import pickle
import json
import random
from threading import Thread, Lock
from rich.console import Console
import os
import time

HOST = '192.168.0.39'
PORT = 5000

STARTING_ID = 1
ENDING_ID = 1000
SKIPPED_IDS_FILE = 'skipped_ids.json'

all_data = {}
skipped_ids = set()
data_lock = Lock()
model_ids_to_process = []

silkweb_connections = []
silkweb_lock = Lock()

console = Console()

def load_existing_data():
    if os.path.exists('printables_data.json'):
        with open('printables_data.json', 'r') as f:
            return json.load(f)
    return {}

def save_data(all_data):
    with open('printables_data.json', 'w') as f:
        json.dump(all_data, f, indent=2)

def load_skipped_ids():
    if os.path.exists(SKIPPED_IDS_FILE):
        with open(SKIPPED_IDS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_skipped_ids(skipped_ids):
    with open(SKIPPED_IDS_FILE, 'w') as f:
        json.dump(list(skipped_ids), f)

def initialize_model_ids():
    global model_ids_to_process, all_data, skipped_ids
    all_data = load_existing_data()
    skipped_ids = load_skipped_ids()
    model_ids_to_process = list(range(STARTING_ID, ENDING_ID + 1))
    model_ids_to_process = [model_id for model_id in model_ids_to_process if str(model_id) not in all_data and model_id not in skipped_ids]
    random.shuffle(model_ids_to_process)

def distribute_model_ids():
    global model_ids_to_process
    while True:
        with silkweb_lock:
            if not model_ids_to_process:
                break
            num_connections = len(silkweb_connections)
            if num_connections > 0:
                ids_per_connection = max(1, len(model_ids_to_process) // num_connections)
                for conn in silkweb_connections:
                    ids_to_send = model_ids_to_process[:ids_per_connection]
                    conn.sendall(pickle.dumps(ids_to_send))
                    model_ids_to_process = model_ids_to_process[ids_per_connection:]
        time.sleep(5)  # Wait before next distribution cycle

def handle_client(conn, addr):
    with conn:
        console.print(f"[cyan]Connected by {addr}")
        with silkweb_lock:
            silkweb_connections.append(conn)
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                message = pickle.loads(data)
                process_message(message, conn)
        finally:
            with silkweb_lock:
                silkweb_connections.remove(conn)

def process_message(message, conn):
    global all_data, skipped_ids, model_ids_to_process
    if message.get('request') == 'model_ids':
        with data_lock:
            ids_to_send = model_ids_to_process[:10]
            model_ids_to_process = model_ids_to_process[10:]
        conn.sendall(pickle.dumps(ids_to_send))
    elif message['status'] == 'data':
        with data_lock:
            all_data[str(message['model_id'])] = message['data']
            save_data(all_data)
        console.print(f"[green]Received data for model {message['model_id']}")
    elif message['status'] == 'skipped':
        with data_lock:
            skipped_ids.add(message['model_id'])
            save_skipped_ids(skipped_ids)
        console.print(f"[yellow]Model {message['model_id']} skipped")
    # Add more status handling as needed

def main():
    initialize_model_ids()
    distribution_thread = Thread(target=distribute_model_ids, daemon=True)
    distribution_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        console.print(f"[cyan]Master spider listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("[bold red]Master spider shutting down...")