# dns_app

Three microservices implementing a tiny DNS + Fibonacci system.

- **US/** — User Server (HTTP, port `8080`)
- **FS/** — Fibonacci Server (HTTP, port `9090`)
- **AS/** — Authoritative Server (UDP, port `53533`)

## Build & Run (Docker)

From the `dns_app` directory:

```bash
# Build
docker build -t as ./AS
docker build -t fs ./FS
docker build -t us ./US

# Run Authoritative Server (UDP 53533) with persistent storage
docker run -d --name as -p 53533:53533/udp -v $(pwd)/as_data:/data as

# Run Fibonacci Server (HTTP 9090)
# Replace FS_IP below with the container IP (e.g., from `docker inspect fs`) or publish 9090
docker run -d --name fs -p 9090:9090 fs

# Register FS with AS
curl -X PUT http://127.0.0.1:9090/register \
  -H 'Content-Type: application/json' \
  -d '{
    "hostname":"fibonacci.com",
    "ip":"127.0.0.1",
    "as_ip":"127.0.0.1",
    "as_port":"53533"
  }'

# Run User Server (HTTP 8080)
docker run -d --name us -p 8080:8080 us
```

## Try it

```bash
# Ask US to compute Fibonacci(10)
curl "http://127.0.0.1:8080/fibonacci?hostname=fibonacci.com&fs_port=9090&number=10&as_ip=127.0.0.1&as_port=53533"
# -> 55
```

## Message Formats

**Registration (FS -> AS via UDP 53533):**
```
TYPE=A
NAME=fibonacci.com VALUE=IP_ADDRESS TTL=10
```

**Query (US -> AS via UDP 53533):**
```
TYPE=A
NAME=fibonacci.com
```

**Response (AS -> client):**
```
TYPE=A
NAME=fibonacci.com VALUE=IP_ADDRESS TTL=10
```

## Notes

- US returns **400** if any required query parameter is missing.
- FS `/fibonacci?number=X` returns **200** with the number or **400** if `X` is not a non-negative integer.
- FS `/register` returns **201** after attempting registration.
- AS stores records in `/data/dns_records.json` (persisted via a container volume).
```