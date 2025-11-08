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

##Usage examples
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

---
##Architecture Overview
---

#Job Lifecycle

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

jobs.json → Stores job queue state (pending, processing, completed, dead).

config.json → Stores global configuration like max retries and backoff base.

worker.stop → File-based signal used to stop workers gracefully.

#Worker Logic

Workers continuously poll for "pending" jobs.

Lock-based file access prevents race conditions.

Retry delays are exponential:
Delay = backoff_base ** attempts.


