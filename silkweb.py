from printables_spider import PrintablesSpider
import json
import random
import time
import socket
import pickle
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# Define constants
BASE_DELAY = 5  # Base delay in seconds
MAX_JITTER = 3  # Maximum jitter in seconds
MAX_SESSIONS = 5
THINK_TIME_CHANCE = 0.1  # 10% chance of a longer pause
THINK_TIME_RANGE = (30, 120)  # Range for think time in seconds

MASTER_HOST = '192.168.0.39'  # Change this to the IP of your master spider
MASTER_PORT = 5000  # Change this to the port your master spider is listening on

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/107.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 12; SM-S908E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
]

spider_creation_lock = Lock()
consecutive_requests = 0

def get_random_user_agent():
    return random.choice(user_agents)

def get_delay():
    global consecutive_requests
    delay = BASE_DELAY + (consecutive_requests * 0.5)
    jitter = random.uniform(0, MAX_JITTER)
    return delay + jitter

def report_to_master(message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((MASTER_HOST, MASTER_PORT))
        s.sendall(pickle.dumps(message))

def request_model_ids():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((MASTER_HOST, MASTER_PORT))
        request_message = {'request': 'model_ids'}
        s.sendall(pickle.dumps(request_message))
        data = s.recv(4096)
        model_ids = pickle.loads(data)
        return model_ids

def report_data_to_master(model_id, data):
    message = {'status': 'data', 'model_id': model_id, 'data': data}
    report_to_master(message)

def report_skipped_to_master(model_id):
    message = {'status': 'skipped', 'model_id': model_id}
    report_to_master(message)

def process_model(model_id):
    global consecutive_requests
    with spider_creation_lock:
        time.sleep(get_delay())
        user_agent = get_random_user_agent()
        spider = PrintablesSpider(model_id, user_agent)
    
    try:
        start_time = time.time()
        data = spider.run()
        end_time = time.time()
        request_time = end_time - start_time

        if data is None:
            report_skipped_to_master(model_id)
        elif data:
            report_data_to_master(model_id, data)
            consecutive_requests += 1

            if random.random() < THINK_TIME_CHANCE:
                think_time = random.uniform(*THINK_TIME_RANGE)
                report_to_master({"status": "think_time", "duration": think_time})
                time.sleep(think_time)
                consecutive_requests = 0
        else:
            report_to_master({"status": "unknown", "model_id": model_id})
    except Exception as exc:
        report_to_master({"status": "exception", "model_id": model_id, "exception": str(exc)})
        consecutive_requests = 0

def main():
    report_to_master({"status": "start"})
    
    while True:
        model_ids = request_model_ids()
        if not model_ids:
            break  # No more model IDs to process
        
        with ThreadPoolExecutor(max_workers=MAX_SESSIONS) as executor:
            futures = []
            for model_id in model_ids:
                future = executor.submit(process_model, model_id)
                futures.append(future)
            
            # Wait for all futures to complete
            for future in futures:
                future.result()

    report_to_master({"status": "complete"})

if __name__ == "__main__":
    main()