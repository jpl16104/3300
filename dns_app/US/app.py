from flask import Flask, request, jsonify, abort
import socket
import requests

app = Flask(__name__)

def udp_query(as_ip: str, as_port: int, name: str, qtype: str = "A", timeout=2.0):
    """
    Send a DNS-like query over UDP per assignment spec:
    Request:
      TYPE=A\n
      NAME=fibonacci.com\n
    Response:
      TYPE=A\n
      NAME=fibonacci.com VALUE=IP_ADDRESS TTL=10\n
    """
    msg = f"TYPE={qtype}\nNAME={name}\n"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(msg.encode("utf-8"), (as_ip, as_port))
        data, _ = s.recvfrom(2048)
    text = data.decode("utf-8", errors="replace").strip()
    # Parse response fields into a dict
    fields = {}
    for part in text.replace("\n", " ").split():
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k.strip()] = v.strip()
    return fields

def compute_response(hostname, fs_port, number, as_ip, as_port):
    # Resolve hostname via AS
    resp_fields = udp_query(as_ip, int(as_port), hostname, "A")
    value = resp_fields.get("VALUE")
    if not value or value in ("NOT_FOUND", ""):
        abort(502, description="AS did not return an IP for hostname")
    fs_ip = value

    # Query Fibonacci Server
    fs_url = f"http://{fs_ip}:{int(fs_port)}/fibonacci"
    r = requests.get(fs_url, params={"number": number}, timeout=3)
    # Propagate FS error codes when relevant
    if r.status_code != 200:
        abort(r.status_code, description=r.text)
    return r.text

@app.route("/fibonacci", methods=["GET"])
def fibonacci_proxy():
    # Required params
    hostname = request.args.get("hostname")
    fs_port = request.args.get("fs_port")
    number = request.args.get("number")
    as_ip = request.args.get("as_ip")
    as_port = request.args.get("as_port")

    if not all([hostname, fs_port, number, as_ip, as_port]):
        abort(400, description="Missing required query parameters")

    try:
        body = compute_response(hostname, fs_port, number, as_ip, as_port)
        return body, 200
    except requests.exceptions.RequestException as e:
        abort(502, description=f"Error contacting FS: {e}")
    except socket.timeout:
        abort(504, description="Timeout contacting AS")
    except Exception as e:
        abort(500, description=str(e))

if __name__ == "__main__":
    # Run on port 8080 as specified
    app.run(host="0.0.0.0", port=8080, debug=False)