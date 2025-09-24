import socket, json, os, threading, time

PORT = 53533
DB_FILE = os.environ.get("AS_DB_FILE", "/data/dns_records.json")

os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(db):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f)
    os.replace(tmp, DB_FILE)

def handle_message(msg: str, addr, sock, db):
    """
    Two message shapes:
      Registration:
        TYPE=A\n
        NAME=fibonacci.com VALUE=IP_ADDRESS TTL=10\n
      Query:
        TYPE=A\n
        NAME=fibonacci.com\n
    Response (for query or after registration ack):
        TYPE=A\n
        NAME=fibonacci.com VALUE=IP_ADDRESS TTL=10\n
    """
    # Normalize whitespace to single spaces except keep newlines if needed
    parts = {}
    for token in msg.replace("\n", " ").split():
        if "=" in token:
            k, v = token.split("=", 1)
            parts[k.strip().upper()] = v.strip()

    mtype = parts.get("TYPE", "")
    name = parts.get("NAME", "")

    # Registration if both VALUE and TTL present
    if mtype == "A" and "VALUE" in parts and "TTL" in parts:
        value = parts["VALUE"]
        ttl = int(parts["TTL"])
        # store with expiry
        db[name] = {"TYPE": "A", "VALUE": value, "TTL": ttl, "stored_at": int(time.time())}
        save_db(db)
        resp = f"TYPE=A\nNAME={name} VALUE={value} TTL={ttl}\n"
        sock.sendto(resp.encode("utf-8"), addr)
        return

    # Query path
    if mtype == "A" and name:
        rec = db.get(name)
        if rec:
            # Optionally honor TTL; if expired, treat as not found
            stored_at = rec.get("stored_at", int(time.time()))
            if rec.get("TTL", 0) > 0 and (time.time() - stored_at) > rec["TTL"]:
                # expired
                resp = f"TYPE=A\nNAME={name} VALUE=NOT_FOUND TTL=0\n"
            else:
                resp = f"TYPE=A\nNAME={name} VALUE={rec['VALUE']} TTL={rec['TTL']}\n"
        else:
            resp = f"TYPE=A\nNAME={name} VALUE=NOT_FOUND TTL=0\n"
        sock.sendto(resp.encode("utf-8"), addr)
        return

    # Unknown message; send minimal error
    sock.sendto(b"ERROR\n", addr)

def main():
    db = load_db()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", PORT))
        print(f"AS listening on UDP {PORT}")
        while True:
            data, addr = sock.recvfrom(4096)
            msg = data.decode("utf-8", errors="replace")
            handle_message(msg, addr, sock, db)

if __name__ == "__main__":
    main()