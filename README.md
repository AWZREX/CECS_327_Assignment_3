# Total-Order Multicast — Replicated Key-Value Store

A replicated key-value store where every replica delivers updates in the same
total order, implemented with Lamport clocks, TOBCAST + ACK messages, and
holdback queues. No third-party libraries required — Python 3.8+ stdlib only.

## Architecture

```
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
```

Each replica listens on port `5000 + replica_id` (e.g., R0 → 5000, R1 → 5001, R2 → 5002).

## Files

| File | Purpose |
|------|---------|
| `server.py` | Replica server — Lamport clocks, TOBCAST/ACK protocol, holdback queue, delivery loop |
| `client.py` | CLI client — sends a single UPDATE to a chosen replica |
| `test_harness.py` | Part B — launches replicas, fires concurrent operations, verifies consistency |



## How to Run

### Start replicas manually


python server.py 3


Starts `N` replicas (default 3) as separate processes. Each replica prints its port and logs every message received and delivered. Press `Ctrl+C` to stop all replicas.

### Send updates via CLI (while replicas are running)


Open separate terminals for each command, or run sequentially:<br>
python client.py 0 put    key1 hello <br>
python client.py 1 append key1 _world <br>
python client.py 2 incr   counter <br>


**Usage:** python client.py <replica_id> <op> <key> [value]

**Supported operations:**

| Op | Example | Description |
|----|---------|-------------|
| `put` | `put balance 1000` | Sets `key = value` |
| `append` | `append balance _bonus` | Appends suffix to existing string value |
| `incr` | `incr counter` | Increments integer value by 1 (starts at 0) |
| `mult` | `mult counter 2` | Multiplies integer value by the given number |

The client connects to `localhost:5000 + replica_id`, sends a `REQUEST` message, and exits.

### Run the test harness (Part B)


python test_harness.py


The harness starts and stops its own replicas for each experiment — no need to run `server.py` separately. It launches `NUM_REPLICAS = 3` replicas, sends concurrent operations with randomised delays, waits for delivery to complete, then terminates the replicas and prints a log of what was sent.


## Part A — Protocol Details

### Message types

| Type | Fields | Direction |
|------|--------|-----------|
| `REQUEST` | `type`, `operation` | Client → any Replica |
| `TOBCAST` | `type`, `update_id`, `operation`, `timestamp`, `sender` | Replica → all other Replicas |
| `ACK` | `type`, `update_id`, `timestamp`, `sender` | Replica → all other Replicas |

All messages are JSON-encoded over TCP connections (one message per connection).

### Lamport clock rule

```
Send:    clock_i += 1;  stamp message with clock_i
Receive: clock_i = max(clock_i, msg.timestamp) + 1
```

`REQUEST` messages from clients do not carry a timestamp and do not trigger a clock update; the replica increments its clock when creating the outgoing `TOBCAST`.

### Holdback queue

Each replica maintains a `holdback_queue` dict keyed by `update_id`. Each entry stores:

```
(timestamp, sender_id, full_message, ack_set)
```

The queue is sorted ascending by `(timestamp, sender_id)` to produce a deterministic total order — ties in timestamp are broken by replica ID (lower wins).

### ACK tracking and ack cache

When a replica receives a `TOBCAST` from another replica it immediately broadcasts an `ACK` to all other replicas. ACKs that arrive before their corresponding `TOBCAST` (a race condition) are stored in `ack_cache` and applied once the `TOBCAST` is received.

### Delivery condition

The replica tracks `progress[k]` — the largest Lamport timestamp seen from replica `k` (across both `TOBCAST` and `ACK` messages). The message `m` at the head of the holdback queue is delivered when:

```
for all k in {0 .. N-1}:  progress[k] >= m.timestamp
```

This guarantees that no replica `k` can later produce a `TOBCAST` with a timestamp smaller than `m.timestamp`, so the delivered order is globally consistent.

