# QueueCTL

QueueCTL is a lightweight local job queue and worker system written in Python.  
It allows you to enqueue shell commands as jobs and process them asynchronously using worker threads or processes.

---

## Features

- Simple file-based queue using `jobs.json`
- Worker management with graceful shutdown
- Retry with exponential backoff
- Dead-letter queue (DLQ) handling for failed jobs
- Safe, atomic file writes
- CLI commands for enqueueing, status checking, and managing workers

---

## Installation

Clone the repository and install locally:

```
git clone https://github.com/devaduttnandan/QueueCTL.git
cd QueueCTL
pip install .

Commands

-queuectl enqueue <command>
-queuectl status
-queuectl worker
-queuectl worker start --<number of workers>
-queuectl stop
-queuectl dlq
-queuectl dlq retry <worker id>
-queuectl list <status that you want to see eg pending>
