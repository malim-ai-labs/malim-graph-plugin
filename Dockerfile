FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD malimgraph-plugin --transport http --port ${PORT:-8080}
