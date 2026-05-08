"""Start a local Neo4j instance (Docker) and optionally wait for it to be ready."""
import argparse
import subprocess
import sys
import time
import os

def docker_start(password: str, data_dir: str, port_http: int, port_bolt: int):
    data_dir = os.path.abspath(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    cmd = [
        "docker", "run", "-d",
        "--name", "malimgraph-neo4j",
        "-p", f"{port_http}:7474",
        "-p", f"{port_bolt}:7687",
        "-e", f"NEO4J_AUTH=neo4j/{password}",
        "-v", f"{data_dir}:/data",
        "neo4j:latest",
    ]
    print("Starting Neo4j Docker container...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if "already in use" in result.stderr or "already exists" in result.stderr:
            print("Container 'malimgraph-neo4j' already exists — starting it...")
            subprocess.run(["docker", "start", "malimgraph-neo4j"], check=True)
        else:
            print(f"ERROR: {result.stderr}", file=sys.stderr)
            sys.exit(1)
    print(f"Neo4j started  →  http://localhost:{port_http}")
    print(f"Bolt URI       →  bolt://localhost:{port_bolt}")
    print(f"Credentials    →  neo4j / {password}")
    print(f"Data folder    →  {data_dir}")


def wait_for_neo4j(uri: str, user: str, password: str, timeout: int = 60):
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("neo4j driver not installed — skipping readiness check.")
        print("Run: pip install neo4j")
        return

    print(f"Waiting for Neo4j at {uri} (up to {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            driver.close()
            print("Neo4j is ready! ✓")
            return
        except Exception:
            print("  Not ready yet — retrying in 3s...")
            time.sleep(3)
    print("Timed out waiting for Neo4j.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Start a local Neo4j Docker instance for MalimGraph")
    parser.add_argument("--method", default="docker", choices=["docker"], help="Startup method (default: docker)")
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "malimgraph"), help="Neo4j password")
    parser.add_argument("--data-dir", default="./neo4j-data", help="Local folder to persist graph data")
    parser.add_argument("--port-http", type=int, default=7474, help="HTTP browser port (default: 7474)")
    parser.add_argument("--port-bolt", type=int, default=7687, help="Bolt port (default: 7687)")
    parser.add_argument("--wait", action="store_true", help="Wait until Neo4j is accepting connections")
    parser.add_argument("--uri", default=None, help="Bolt URI for --wait (auto-detected from ports)")
    parser.add_argument("--user", default="neo4j", help="Neo4j username for --wait")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds to wait (default: 60)")
    args = parser.parse_args()

    if args.method == "docker":
        docker_start(args.password, args.data_dir, args.port_http, args.port_bolt)

    if args.wait:
        uri = args.uri or f"bolt://localhost:{args.port_bolt}"
        wait_for_neo4j(uri, args.user, args.password, args.timeout)


if __name__ == "__main__":
    main()
