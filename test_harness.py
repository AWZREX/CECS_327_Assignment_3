import multiprocessing
import random
import time
import threading
import json
import socket

from server import replica

HOST = "localhost"
NUM_REPLICAS = 3


def launch_replicas(n):
    procs = []
    for i in range(n):
        p = multiprocessing.Process(target=replica, args=(i, n), daemon=True)
        p.start()
        procs.append(p)
    time.sleep(1.0)  # wait for all replicas to bind their sockets
    return procs


def send_with_delay(replica_id, operation, delay=0.0):
    time.sleep(delay)
    msg = {"type": "REQUEST", "operation": operation}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, 5000 + replica_id))
            s.sendall(json.dumps(msg).encode("UTF-8"))
        print(f"[Harness] Sent {operation} -> replica {replica_id} (delay={delay:.2f}s)")
    except ConnectionRefusedError:
        print(f"[Harness] ERROR: Could not connect to replica {replica_id} on port {5000 + replica_id}")


def run_experiment(name, operations_with_targets):
    """
    operations_with_targets: list of (replica_id, operation_dict, delay)
    """
    print(f"\n{'='*50}")
    print(f"EXPERIMENT: {name}")
    print(f"{'='*50}")

    procs = launch_replicas(NUM_REPLICAS)

    threads = []
    for replica_id, op, delay in operations_with_targets:
        t = threading.Thread(target=send_with_delay, args=(replica_id, op, delay))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    time.sleep(1.5)  # allow delivery + apply to complete before killing replicas

    for p in procs:
        p.terminate()
    for p in procs:
        p.join()

    print(f"\n[Harness] Experiment '{name}' complete.\n")


# ── ALL experiment code MUST be inside this block on Windows ──────────────────
if __name__ == "__main__":
    multiprocessing.freeze_support()  # needed if ever frozen to .exe; harmless otherwise

    # Experiment 1: Concurrent conflicting updates
    run_experiment(
        "Concurrent conflicting updates (put + append on same key)",
        [
            (0, {"op": "put",    "key": "x", "value": "hello"},  random.uniform(0, 0.1)),
            (1, {"op": "append", "key": "x", "value": "_world"}, random.uniform(0, 0.1)),
            (2, {"op": "put",    "key": "x", "value": "reset"},  random.uniform(0, 0.1)),
        ],
    )

    # Experiment 2: High contention — 20 increments to the same key
    run_experiment(
        "High contention (20 increments to same key)",
        [
            (i % NUM_REPLICAS,
             {"op": "incr", "key": "counter"} if i % 2 == 0
             else {"op": "mult", "key": "counter", "value": 2},
             #random.uniform(0, 0.3))
             0)
            for i in range(20)
        ],
    )

    # Experiment 3: Non-conflicting updates — different keys, verify total order
    run_experiment(
        "Non-conflicting updates (different keys, verify total order preserved)",
        [
            (0, {"op": "put", "key": "a", "value": "1"}, random.uniform(0, 0.1)),
            (1, {"op": "put", "key": "b", "value": "2"}, random.uniform(0, 0.1)),
            (2, {"op": "put", "key": "c", "value": "3"}, random.uniform(0, 0.1)),
            (0, {"op": "put", "key": "d", "value": "4"}, random.uniform(0, 0.1)),
        ],
    )