import os
import re
import subprocess
import time
from pathlib import Path

import docker
import requests
import urllib3
from flask import Flask, jsonify, render_template
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from werkzeug.middleware.proxy_fix import ProxyFix

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

HOST_ROOT = Path(os.getenv("HOST_ROOT", "/host"))
CHECK_TIMEOUT = float(os.getenv("CHECK_TIMEOUT", "4"))
PING_TIMEOUT = int(os.getenv("PING_TIMEOUT", "2"))

SERVICES = [
    {
        "id": "nx",
        "name": "NEXT CLOUD",
        "description": "Sistema de Armazenamento em Núvem",
        "type": "https",
        "url": os.getenv("NXT_URL", "Seguir o link (ctrl + clique)"),
        "container": "",
    },
    {
        "id": "otobo_cliente",
        "name": "OTOBO Cliente",
        "description": "Portal de abertura de chamados",
        "type": "http",
        "url": os.getenv("OTOBO_CLIENTE_URL", "http://10.133.212.56/otobo/customer.pl"),
        "container": "",
    },
    {
        "id": "vs",
        "name": "Visual Studio",
        "description": "Ambiente de Desenvolvimento Web",
        "type": "https",
        "url": os.getenv("vs_URL", "https://vs.codewelter.cloud"),
        "container": "",
    },
    {
        "id": "fire",
        "name": "NGINX",
        "description": "Sistema de Gerenciamento PROXY",
        "type": "http",
        "url": os.getenv("PRX_URL", "http://82.25.70.30:81"),
        "container": "",
    },

    {
	"id": "tool",
	"name": "Site WSystemX",
	"description": "Site de Download do Sistema X",
	"type": "https",
	"host": "10.133.212.222",
	"url": os.getenv("tool_URL", "https://tool.codewelter.cloud"),
	"container": "",
    },
]

_session = requests.Session()
_retry = Retry(total=1, connect=1, read=0, backoff_factor=0.2)
_session.mount("http://", HTTPAdapter(max_retries=_retry))
_session.mount("https://", HTTPAdapter(max_retries=_retry))


def read_host_cpu_percent(sample_delay=0.20):
    stat = HOST_ROOT / "proc" / "stat"

    def read_cpu():
        parts = stat.read_text().splitlines()[0].split()[1:]
        values = [int(v) for v in parts]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return idle, sum(values)

    try:
        idle1, total1 = read_cpu()
        time.sleep(sample_delay)
        idle2, total2 = read_cpu()
        total_delta = total2 - total1
        idle_delta = idle2 - idle1
        if total_delta <= 0:
            return 0
        return round((1 - idle_delta / total_delta) * 100, 1)
    except Exception:
        return None


def read_host_memory():
    try:
        values = {}
        for line in (HOST_ROOT / "proc" / "meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
        total = values["MemTotal"]
        available = values.get("MemAvailable", values.get("MemFree", 0))
        used = total - available
        return {
            "percent": round(used / total * 100, 1),
            "used_gb": round(used / 1024**3, 1),
            "total_gb": round(total / 1024**3, 1),
        }
    except Exception:
        return {"percent": None, "used_gb": None, "total_gb": None}


def read_host_disk():
    try:
        stat = os.statvfs(HOST_ROOT)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        return {
            "percent": round(used / total * 100, 1),
            "used_gb": round(used / 1024**3, 1),
            "total_gb": round(total / 1024**3, 1),
        }
    except Exception:
        return {"percent": None, "used_gb": None, "total_gb": None}


def read_host_uptime():
    try:
        seconds = int(float((HOST_ROOT / "proc" / "uptime").read_text().split()[0]))
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, _ = divmod(seconds, 60)
        return f"{days}d {hours}h {minutes}min"
    except Exception:
        return "Indisponível"


def docker_client():
    try:
        return docker.from_env()
    except Exception:
        return None


def container_state(client, container_name):
    if not container_name or client is None:
        return None
    try:
        container = client.containers.get(container_name)
        container.reload()
        health = container.attrs.get("State", {}).get("Health", {}).get("Status")
        return {"status": container.status, "health": health}
    except Exception:
        return {"status": "not_found", "health": None}


def check_ping(service):
    host = service["host"]
    start = time.perf_counter()
    error = None
    latency_ms = None

    try:
        result = subprocess.run(
            ["ping", "-n", "-c", "1", "-W", str(PING_TIMEOUT), host],
            capture_output=True,
            text=True,
            timeout=PING_TIMEOUT + 2,
        )
        online = result.returncode == 0
        if online:
            match = re.search(r"time[=<]([0-9.]+)\s*ms", result.stdout)
            if match:
                latency_ms = round(float(match.group(1)), 1)
        else:
            error = result.stderr.strip() or "Sem resposta ao ping"
    except subprocess.TimeoutExpired:
        online = False
        error = "Tempo limite do ping excedido"
    except FileNotFoundError:
        online = False
        error = "Comando ping não instalado no container"
    except Exception as exc:
        online = False
        error = str(exc)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    return {
        **service,
        "online": online,
        "status_code": None,
        "response_ms": latency_ms if latency_ms is not None else elapsed_ms,
        "error": error,
        "container_state": None,
    }


def check_http(service, client):
    start = time.perf_counter()
    ok = False
    status_code = None
    error = None
    try:
        response = _session.get(
            service["url"],
            timeout=CHECK_TIMEOUT,
            allow_redirects=True,
            verify=service.get("verify_tls", True),
        )
        status_code = response.status_code
        ok = status_code < 500
    except Exception as exc:
        error = str(exc)

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    return {
        **service,
        "online": ok,
        "status_code": status_code,
        "response_ms": elapsed_ms,
        "error": error,
        "container_state": container_state(client, service.get("container")),
    }


def check_service(service, client):
    if service.get("type") == "ping":
        return check_ping(service)
    return check_http(service, client)


@app.get("/")
def index():
    return render_template(
        "index.html",
        title=os.getenv("PORTAL_TITLE", "PAINEL DE SERVIÇOS"),
        subtitle=os.getenv("PORTAL_SUBTITLE", "Code Welter Monitor"),
        refresh_seconds=int(os.getenv("REFRESH_SECONDS", "15")),
    )


@app.get("/api/status")
def api_status():
    client = docker_client()
    services = [check_service(service, client) for service in SERVICES]

    container_names = {item.get("container") for item in services if item.get("container")}
    running_names = {
        item.get("container")
        for item in services
        if item.get("container") and (item.get("container_state") or {}).get("status") == "running"
    }

    return jsonify(
        {
            "timestamp": int(time.time()),
            "services": services,
            "server": {
                "cpu_percent": read_host_cpu_percent(),
                "memory": read_host_memory(),
                "disk": read_host_disk(),
                "uptime": read_host_uptime(),
                "containers_running": len(running_names),
                "containers_total": len(container_names),
            },
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200
