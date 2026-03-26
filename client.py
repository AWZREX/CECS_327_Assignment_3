import json
import socket
import sys

HOST = "localhost"

def send_request(replica_id, operation):
    """Send a client REQUEST to replica `replica_id`."""
    msg = {"type": "REQUEST", "operation": operation}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, 5000 + replica_id))
        s.sendall(json.dumps(msg).encode("UTF-8"))
    print(f"[Client] Sent {operation} to replica {replica_id}")

if __name__ == "__main__":
    # Example: python client.py 0 put key1 hello
    replica_id = int(sys.argv[1])
    op = sys.argv[2]
    key = sys.argv[3]
    value = sys.argv[4] if len(sys.argv) > 4 else None

    operation = {"op": op, "key": key, "value": value}
    send_request(replica_id, operation)