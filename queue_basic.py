import json
import os
import subprocess
import time
from datetime import datetime
import threading
import sys


DB_FILE = "jobs.json"
CONFIG_FILE = "config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {"max_retries":3,"backoff_base":2}
        save_config(config)
        return config
    with open(CONFIG_FILE,"r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE,"w") as f:
        json.dump(config, f, indent=3)

def load_jobs():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE,"r") as f:
        return json.load(f)
    
def save_jobs(jobs):
    with open(DB_FILE,"w") as f:
        json.dump(jobs,f, indent=3)


def enqueue_jobs(command, max_retries = 3):
    jobs = load_jobs()
    config = load_config()
    max_retries = config.get("max_retries",3)
    job = {
        "id":str(len(jobs)+1),
        "command": command,
        "state":"pending",
        "attempts":0,
        "max_retries": max_retries,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    jobs.append(job)
    save_jobs(jobs)
    print(f"Job {job['id']} enqueued!")

def show_status():
    jobs = load_jobs()
    if not jobs:
        print("No jobs found")
        return
    print(f"{'id':<4} {'state':<12} {'attempts':<9} COMMAND")
    print("-"*60)
    for job in jobs:
        print(f"{job['id']:<4} {job['state']:<12} {job['attempts']:<9} {job['command']}")
    print("-"*60)
    print(f"Total jobs: {len(jobs)}")

lock = threading.Lock()
def acquire_lock():
    lock.acquire()
def release_lock():
    lock.release()

def run_worker():
    while True:
        jobs = load_jobs()
        for job in jobs:
            if job["state"] == "pending":
                print(f"Processing job {job['id']}: {job['command']}")
                job['state'] = "processing"
                job["updated_at"] = datetime.now().isoformat()
                save_jobs(jobs)

                result = subprocess.run(job["command"], shell=True)
                if result.returncode == 0:
                    print(f"job {job['id']} completed successfully!")
                    job["state"] = "completed"
                else:
                    print(f"job {job['id']} failed!!")
                    job["attempts"] += 1
                    if job["attempts"] >= job["max_retries"]:
                        job["state"] = "dead"
                        print(f"Job {job['id']} moved to DLQ!")
                    else:
                        config = load_config()
                        base = config.get("backoff_base",2)
                        delay = base ** job["attempts"]
                        print(f"Retrying job {job['id']} after {delay} seconds.")
                        job["state"] = "Retrying"
                        save_jobs(jobs)
                        time.sleep(delay)
                        job["state"] = "pending"
                job["updated_at"] = datetime.now().isoformat()
                save_jobs(jobs)
        time.sleep(2)

def list_dlq():
    jobs = load_jobs()
    dead_jobs = [job for job in jobs if job["state"] == "dead"]
    if not dead_jobs:
        print("No jobs in DLQ")
        return
    print(f"{'id':<4} {'attempts':<9} COMMAND")
    print('-'*60)
    for job in dead_jobs:
        print(f"{job['id']:<4} {job['attempts']:<9} {job['command']}")
    print('-'*60)
    print(f"Total DLQ jobs: {len(dead_jobs)}")

def retry_dlq(job_id):
    jobs = load_jobs()
    for job in jobs:
        if job['id'] == job_id and job["state"] == "dead":
            job["state"] = "pending"
            job["attempts"] = 0
            job["updated_at"] = datetime.now().isoformat()
            save_jobs(jobs)
            print(f"Job {job_id} moved back to pending queue.")
            return
    print(f"Job {job_id} not found in DLQ.")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage:")
        print(" python3 queue.py enqueue '<Command>'")
        print(" python3 queue_basic.py worker")
        print(" python3 queue_basic.py status")
        print(" python3 queue_basic.py dlq # List DLQ jobs")
        print(" python3 queue_basic.py dlq retry <job_id> # Retry a DLQ job")
        print(" queuectl config [get|set <key> <value>]")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "enqueue":
        enqueue_jobs(sys.argv[2])
    elif cmd == "worker":
        run_worker()
    elif cmd == "status":
        show_status()
    elif cmd == "dlq":
        if len(sys.argv) == 2:
            list_dlq()
        elif len(sys.argv) == 4 and sys.argv[2] == "retry":
            retry_dlq(sys.argv[3])
    elif cmd == "config":
        if len(sys.argv)<3:
            print(" queuectl config [get|set <key> <value>]")
            sys.exit(0)
        action = sys.argv[2].lower()
        config = load_config()
        if action == "get":
            print(json.dumps(config,indent=3))
        elif action == "set":
            if len(sys.argv) < 5:
                print("usage: queuectl config set <key> <value>")
                sys.exit(0)
            key = sys.argv[3]
            value = sys.argv[4]
            if value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass
            config[key] = value
            save_config(config)
            print(f"Configuration updated: {key} = {value}")
        else:
            print("invalid config command, use 'get' or 'set'")

    
        