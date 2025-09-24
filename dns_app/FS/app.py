from flask import Flask, request, jsonify, abort
import socket
import json

app = Flask(__name__)

def send_registration(hostname: str, ip: str, as_ip: str, as_port: int, ttl: int = 10, timeout=2.0):
    """
    Registration message per spec (each line ends with newline):
      TYPE=A
      NAME=fibonacci.com VALUE=IP_ADDRESS TTL=10
    """
    msg = f"TYPE=A\nNAME={hostname} VALUE={ip} TTL={ttl}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(msg.encode("utf-8"), (as_ip, as_port))
        try:
            data, _ = s.recvfrom(1024)  # optional ack from AS
            ack = data.decode("utf-8", errors="replace").strip()
            return ack
        except socket.timeout:
            return "NO_ACK"

@app.put("/register")
def register():
    try:
        payload = request.get_json(force=True)
    except Exception:
        abort(400, description="Body must be JSON")

    # Required fields
    for key in ("hostname", "ip", "as_ip", "as_port"):
        if key not in payload:
            abort(400, description=f"Missing field: {key}")

    hostname = payload["hostname"]
    ip = payload["ip"]
    as_ip = payload["as_ip"]
    as_port = int(payload["as_port"])

    send_registration(hostname, ip, as_ip, as_port, ttl=10)
    # As soon as we send the registration, consider it successful (per spec)
    return jsonify({"status": "registered", "hostname": hostname, "ip": ip}), 201

def fib(n: int) -> int:
    if n < 0:
        raise ValueError("n must be >= 0")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

@app.get("/fibonacci")
def fibonacci():
    number = request.args.get("number")
    if number is None:
        abort(400, description="Missing 'number' parameter")
    try:
        n = int(number)
        if n < 0:
            raise ValueError
    except Exception:
        abort(400, description="'number' must be a non-negative integer")

    return str(fib(n)), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090, debug=False)