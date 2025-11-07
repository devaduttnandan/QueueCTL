import json
import os
import subprocess
import time
from datetime import datetime
import threading
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR,"jobs.json")
CONFIG_FILE = os.path.join(BASE_DIR,"config.json")
STOP_FILE = os.path.join(BASE_DIR,"worker.stop")

stop_event = threading.Event()
lock = threading.Lock()
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
    with lock:
        if not os.path.exists(DB_FILE):
            return []
        with open(DB_FILE,"r") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    
def save_jobs(jobs):
    with lock:
        tmp_file = DB_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(jobs, f, indent=3)
        os.replace(tmp_file, DB_FILE)


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

def run_worker(name="worker"):
    print(f"[{name}] Worker started (pid={os.getpid()}).")
    
    try:
        while not stop_event.is_set() and not os.path.exists(STOP_FILE):
            jobs = load_jobs()
            target_job = None
            for job in jobs:
                if job.get("state") == "pending":
                    job["state"] = "processing"
                    job["updated_at"] = datetime.now().isoformat()
                    target_job = job.copy()
                    save_jobs(jobs)
                    print(f"[{name}] Picked job {job['id']} -> {job['command']}")
                    break

            if not target_job:
                time.sleep(1)
                continue

            print(f"[{name}] Executing job {target_job['id']}")
            result = subprocess.run(target_job["command"], shell=True)
            rc = result.returncode

            jobs = load_jobs()
            for j in jobs:
                if j["id"] == target_job["id"]:
                    if rc == 0:
                        j["state"] = "completed"
                        print(f"[{name}] Job {j['id']}:  completed ")
                    else:
                        j["attempts"] = j.get("attempts", 0) + 1
                        cfg = load_config()
                        base = cfg.get("backoff_base", 2)
                        max_retries = j.get("max_retries", cfg.get("max_retries", 3))

                        if j["attempts"] >= max_retries:
                            j["state"] = "dead"
                            print(f"[{name}] Job {j['id']} moved to DLQ")
                        else:
                            delay = base ** j["attempts"]
                            print(f"[{name}] Job {j['id']} failed, retrying in {delay}s...")
                            j["state"] = "pending"
                            time.sleep(delay)

                    j["updated_at"] = datetime.now().isoformat()
                    break

            save_jobs(jobs)
            time.sleep(0.5)

    except Exception as e:
        print(f"[{name}] ERROR: {e}")
        time.sleep(1)
    finally:
        print(f"[{name}] shutting down cleanly.")

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
        if len(sys.argv) < 3:
            print("Starting single worker...")
            if os.path.exists(STOP_FILE):
                os.remove(STOP_FILE)
            t = threading.Thread(target=run_worker, args=("worker-1",), daemon=True)
            t.start()
            try:
                while True:
                    if os.path.exists(STOP_FILE):
                        print("Stop file detected. Stopping worker gracefully...")
                        stop_event.set()
                        break
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("Shutting down worker gracefully...")
            finally:
                stop_event.set()
                t.join()
                if os.path.exists(STOP_FILE):
                    os.remove(STOP_FILE)
                print("Worker stopped.")
        else:
            subcmd = sys.argv[2]
            if subcmd == "start":
                count = 1
                if "--count" in sys.argv:
                    idx = sys.argv.index("--count")
                    if idx + 1 < len(sys.argv):
                        count = int(sys.argv[idx+1])
                print(f"starting {count} workers...")
                if os.path.exists(STOP_FILE):
                    os.remove(STOP_FILE)
                threads = []
                for i in range(count):
                    t = threading.Thread(target=run_worker, args = (f"worker-{i+1}",),daemon=True)
                    threads.append(t)
                    t.start()
                try:
                    while True:
                        if os.path.exists(STOP_FILE):
                            print("stop file detected. Stopping workers gracefully")
                            stop_event.set()
                            break
                        time.sleep(0.5)
                except KeyboardInterrupt:
                    print("Shutting down workers gracefully...")
                finally:
                    print("stopping workers gracefully...")
                    stop_event.set()
                    for t in threads:
                        t.join()
                    if os.path.exists(STOP_FILE):
                        os.remove(STOP_FILE)
                    print("All workers stopped.")
            elif subcmd == "stop":
                print("stopping all workers")
                with open(STOP_FILE,"w") as f:
                    f.write("stop")
                print("Stop signal written. Workers will exit gracefully")
            else:
                print("Usage: queuectl worker start --count N")

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
    elif cmd == "list":
        if len(sys.argv) < 4 or sys.argv[2] != "--state":
            print("Usage: queuectl list --state <pending|processing|completed|dead>")
            sys.exit(0)

        state = sys.argv[3].lower()
        jobs = load_jobs()
        filtered = [job for job in jobs if job.get("state") == state]

        if not filtered:
            print(f"No jobs found with state '{state}'.")
            sys.exit(0)

        print(f"{'id':<4} {'state':<12} {'attempts':<9} COMMAND")
        print("-" * 60)
        for job in filtered:
            print(f"{job['id']:<4} {job['state']:<12} {job['attempts']:<9} {job['command']}")
        print("-" * 60)
        print(f"Total {state} jobs: {len(filtered)}")

    
        
