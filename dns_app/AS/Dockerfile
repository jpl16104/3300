FROM python:3.11-slim
WORKDIR /app
COPY server.py .
RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 53533/udp
ENV AS_DB_FILE=/data/dns_records.json
CMD ["python", "server.py"]