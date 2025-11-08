# QueueCTL

QueueCTL is a lightweight local job queue and worker system written in Python.  
It allows you to enqueue shell commands as jobs and process them asynchronously using worker threads or processes.

---

## 1. Setup Instructions

### Clone the repository and install locally

```bash
git clone https://github.com/devaduttnandan/QueueCTL.git
cd QueueCTL
pip install .
```

##Commands

```bash
-queuectl enqueue <command>
-queuectl status
-queuectl worker
-queuectl worker start --<number of workers>
-queuectl worker stop
-queuectl dlq
-queuectl dlq retry <worker id>
-queuectl list <status that you want to see eg pending>
-queuectl congfig get
-queuectl config set <key> <value>
```

2. Usage examples
---
  enqueue job
```bash
queuectl enqueue "echo hello world"
```
#Outptut
```bash
Job 1 enqueued!
```

#status
```bash
queuectl status
```
#output
```bash
id   state        attempts  COMMAND
------------------------------------------------------------
1    pending      0         echo hello world
------------------------------------------------------------
Total jobs: 1
```


3.Architecture Overview
---

#Job Lifecycle
---

Enqueue:
A job (shell command) is added to jobs.json with state = "pending".

Worker picks job:
A worker thread locks and updates job state to "processing".

Execution:
The command runs in a subprocess.

Completion or Retry:

If successful → "completed"

If failed → "pending" (after exponential backoff)

If retries exhausted → "dead" (moved to DLQ)

#Data Persistence
---

jobs.json → Stores job queue state (pending, processing, completed, dead).

config.json → Stores global configuration like max retries and backoff base.

worker.stop → File-based signal used to stop workers gracefully.

#Worker Logic
---

Workers continuously poll for "pending" jobs.

Lock-based file access prevents race conditions.

Retry delays are exponential:
Delay = backoff_base ** attempts.

4.Assumptions and trade offs
---

#Persistence
---

Jobs are stored in a local JSON file (jobs.json) for simplicity.

Trade-off: JSON file is sufficient for small workloads but may not scale well for thousands of concurrent jobs. No database locking mechanism beyond threading lock is used.

#Worker Concurrency
---

Multiple workers can run in parallel threads, picking one job at a time.

Trade-off: Uses Python threading rather than multiprocessing for simplicity. Threads share memory, so CPU-bound tasks may not fully utilize multiple cores.

#Retry & Backoff
---

Exponential backoff is applied: delay = base ^ attempts seconds.

Assumption: All jobs are retryable unless explicitly moved to DLQ.

Trade-off: No maximum delay cap; very high attempts could result in long delays.

#Command Execution
---

Jobs execute arbitrary shell commands using subprocess.run.

Trade-off: Security risk if commands come from untrusted sources (not sanitized).

#DLQ (Dead Letter Queue)
---

Jobs that exceed max_retries are marked as dead and can be manually retried.

Assumption: Users will manually monitor and retry DLQ jobs if needed.

#Configuration
---

Configurable values are stored in config.json.

Trade-off: No live config reload during runtime; changes affect only future jobs.

#Graceful Shutdown
---

Workers check for a stop signal and finish the current job before stopping.

Trade-off: No interruptible jobs; long-running jobs will block shutdown until complete.

#Job Ordering
---

Jobs are picked in the order they are listed in the JSON file.

Trade-off: No priority queue implemented (bonus feature in assignment)

5.Testing Instructions
---

#Setup
---
Ensure that you have installed the setup correctly

#Basic Enqueue & Status
---

```bash
queuectl enqueue "echo 'Hello World'"
queuectl status
```

verify the job appears as pending

#Worker Execution
---
```bash
queuectl worker start
```

worker should pick up the job and complete it
check status again; job should be completed

#Failed job & retry
---
```bash
queuectl enqueue "exit 1"
queuectl worker start
```

verify job retries according to max_retries
check that it moves to dead after exhausting tries

#DLQ operations
---
```bash
queuectl dlq
queuectl dlq retry <job_id>
```

verify dead jobs can be listed and retried

#Multiple workers
---
```bash
queuectl worker start --3
```
enqueue multiple jobs and confirm that no job is processed twice

#configuration
---
```bash
queuectl config get
queuectl config set max_retries 5
```
verify configuration persists in config.json

Working CLI Demo Link
---
Link to the demo: https://drive.google.com/file/d/1OWxqPT5jpIT_MRY9ugE7MuNM9ZxEHuUe/view?usp=sharing

Architecture Design
----
<img width="1115" height="459" alt="image" src="https://github.com/user-attachments/assets/629eea4f-a3cf-431d-ace5-fae39f08cc1d" />






