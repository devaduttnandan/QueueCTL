# QueueCTL

QueueCTL is a lightweight local job queue and worker system written in Python.  
It allows you to enqueue shell commands as jobs and process them asynchronously using worker threads or processes.

---

## 1. ⚙️ Setup Instructions

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
#enqueue job
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



