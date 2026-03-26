import json
import multiprocessing
import socket
import uuid

HOST = "localhost"


def apply_operation(store, delivered_log, operation, update_id):
    op = operation["op"]
    key = operation["key"]

    if op == "put":
        store[key] = operation["value"]
    elif op == "append":
        store[key] = store.get(key, "") + operation["value"]
    elif op == "incr":
        store[key] = store.get(key, 0) + 1

    delivered_log.append(update_id)
    print(f"  [DELIVERED] update_id={update_id} op={operation} store={store}")


def _broadcast(msg, my_id, num_replicas):
    for i in range(num_replicas):
        if i != my_id:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as z:
                    z.connect((HOST, 5000 + i))
                    z.sendall(json.dumps(msg).encode("UTF-8"))
            except ConnectionRefusedError:
                print(f"  [WARN] Could not reach replica {i}")


def replica(replica_id, num_replicas):
    holdback_queue = []
    clock_i = 0
    progress = [0] * num_replicas
    store = {}
    delivered_log = []

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, 5000 + replica_id))
        s.listen()
        print(f"[Replica {replica_id}] Listening on port {5000 + replica_id}")

        while True:
            conn, addr = s.accept()
            with conn:
                raw = conn.recv(4096)
                if not raw:
                    continue
                data = json.loads(raw.decode("UTF-8"))

                # Lamport clock update
                if data["type"] != "REQUEST":
                    clock_i = max(clock_i, data["timestamp"])
                clock_i += 1
                progress[replica_id] = clock_i

                if data["type"] == "REQUEST":
                    update_id = str(uuid.uuid4())
                    msg = {
                        "type": "TOBCAST",
                        "update_id": update_id,
                        "operation": data["operation"],
                        "timestamp": clock_i,
                        "sender": replica_id,
                    }
                    holdback_queue.append((msg["timestamp"], msg["sender"], msg))
                    holdback_queue.sort(key=lambda x: (x[0], x[1]))
                    _broadcast(msg, replica_id, num_replicas)

                elif data["type"] == "TOBCAST":
                    holdback_queue.append((data["timestamp"], data["sender"], data))
                    holdback_queue.sort(key=lambda x: (x[0], x[1]))
                    progress[data["sender"]] = max(progress[data["sender"]], data["timestamp"])
                    ack = {
                        "type": "ACK",
                        "update_id": data["update_id"],
                        "timestamp": data["timestamp"],
                        "sender": data["sender"],
                    }
                    _broadcast(ack, replica_id, num_replicas)

                elif data["type"] == "ACK":
                    progress[data["sender"]] = max(progress[data["sender"]], data["timestamp"])

                # Delivery loop
                while holdback_queue:
                    ts, sender, msg = holdback_queue[0]
                    if all(progress[k] > ts for k in range(num_replicas)):
                        holdback_queue.pop(0)
                        apply_operation(store, delivered_log, msg["operation"], msg["update_id"])
                    else:
                        break


def start_servers(n):
    for i in range(n):
        multiprocessing.Process(target=replica, args=(i, n), daemon=True).start()


# Need this to prevent Windows from trying to spawn new processes recursively when we start servers
if __name__ == "__main__":
    import sys
    import time
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    start_servers(n)
    print(f"[Main] {n} replicas started. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Main] Shutting down.")