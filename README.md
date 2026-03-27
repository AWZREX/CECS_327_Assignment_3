# Total-Order Multicast — Replicated Key-Value Store

A replicated key-value store where every replica delivers updates in the same
total order, implemented with Lamport clocks, TOBCAST + ACK messages,
and holdback queues.  No third-party libraries required — stdlib only.

## Architecture
        Clients
        |     \         (clients may send to any replica)
        v      v
    +------+ +------+ +------+ +------+
    |  R0  | |  R1  | |  R2  | |  R3  |
    +------+ +------+ +------+ +------+
         \      |      /      |
          \-----|-----/-------|
            Total-Order Multicast
        (TOBCAST + ACK, holdback queues,
         deliver only when safe)
## Files
`server.py`  Replica server — Lamport clocks, TOBCAST/ACK, holdback queue, delivery <br />
`client.py`  CLI client — sends one UPDATE to a chosen replica <br />
`test_harness.py`  Part B — launches replicas, fires concurrent ops, verifies consistency <br />
`part_c_answers.md`  Part C — written answers <br />



## How to Run

Requirements: Python 3.8+, no third-party packages.

### Start replicas manually
python server.py 3


### Send updates via CLI

```bash
# In separate terminals while replicas are running:
python client.py 0 put    balance 1000
python client.py 1 append balance _bonus
python client.py 2 incr   counter
```

Supported operations: `put <key> <value>`, `append <key> <suffix>`, `incr <key>`.

### Run the test harness (Part B)
python test_harness.py


The harness starts and stops its own replicas for each experiment and prints
a PASS/FAIL summary with verification results.



## Part A (Message types)
| Type | Fields | Direction |
|------|--------|-----------|
| `REQUEST` | `operation` | Client → any Replica |
| `TOBCAST` | `update_id`, `operation`, `timestamp`, `sender` | Replica → all others |
| `ACK` | `update_id`, `timestamp`, `sender` | Replica → all others |
| `STATE_QUERY` | `reply_port` | Harness → Replica  |

### Lamport clock rule


Send:    clock_i += 1;  stamp message with clock_i <br />
Receive: clock_i = max(clock_i, msg.timestamp) + 1


### Holdback queue ordering

Messages are sorted ascending by (timestamp, sender_id).
Equal timestamps are broken deterministically by replica ID (lower wins).

### Delivery condition

Message m at the head of the holdback queue is delivered when:
for all k in {0 .. N-1}:  progress[k]  >  m.timestamp
progress[k] is the largest timestamp seen from replica k.


