import json
import queue
import socket

HOST = "localhost"

def start_servers(num_servers):
    for i in range(num_servers):
        multiprocessing.Process(target=replica, args=(i, num_servers)).start()

def replica(replica_id, num_replicas):
    holdback_queue = list()
    clock_i = 0
    progress = [0 for _ in range(num_replicas)]


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 5000 + replica_id))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024)
                if not data:
                    continue
                data = json.loads(data.decode('UTF-8'))
                if data["type"] != "REQUEST":
                    clock_i = max(clock_i, data["timestamp"])
                clock_i += 1
                progress[replica_id] = clock_i

                if data["type"] == "REQUEST":
                    data = {"type" : "TOBCAST", "operation" : data["operation"], "timestamp" : clock_i, "sender" : replica_id}
                    holdback_queue.append((data["timestamp"], data["sender"], data))
                    holdback_queue.sort(key=lambda x: (x[0], x[1]))
                    for i in range(num_replicas):
                        if i != replica_id:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as z:
                                z.connect((HOST, 5000 + i))
                                z.sendall(json.dumps(data).encode('UTF-8'))

                elif data["type"] == "TOBCAST":
                    holdback_queue.append((data["timestamp"], data["sender"], data))
                    holdback_queue.sort(key=lambda x: (x[0], x[1]))
                    progress[data["sender"]] = data["timestamp"]
                    data = {"type" : "ACK", "timestamp" : data["timestamp"], "sender" : data["sender"]}
                    for i in range(num_replicas):
                        if i != replica_id:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as z:
                                z.connect((HOST, 5000 + i))
                                z.sendall(json.dumps(data).encode('UTF-8'))

                elif data["type"] == "ACK":
                    progress[data["sender"]] = data["timestamp"]

                while len(holdback_queue) != 0:
                    message = holdback_queue[0]
                    safe = True
                    for e in progress:
                        if message[2]["timestamp"] >= e:
                            safe = False

                    if safe:
                        pass # apply operation

                    else:
                        break