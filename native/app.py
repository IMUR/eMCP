"""eMCP Native Manager — single-file Flask app, no Docker.

Backend pattern:
  - Read ops via mcpjungle's HTTP admin API (/api/v0/tools, /api/v0/servers).
  - Mutations (register, group create/delete) via local mcpjungle CLI subprocess.
  - Groups + server configs persisted as JSON files in DATA_DIR.
"""
import json
import os
import subprocess
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:3700")
DATA_DIR = Path(os.getenv("DATA_DIR", "/var/lib/emcp-native"))
GROUPS_DIR = DATA_DIR / "groups"
CONFIGS_DIR = DATA_DIR / "configs"
MCPJUNGLE_BIN = os.getenv("MCPJUNGLE_BIN", "/usr/local/bin/mcpjungle")
PORT = int(os.getenv("EMCP_MANAGER_PORT", os.getenv("PORT", "3701")))

app = Flask(__name__, static_folder=None)


def mcpj(*args, timeout=180):
    """Run mcpjungle CLI; long timeout because stdio MCP servers may be slow to init."""
    cmd = [MCPJUNGLE_BIN, "--registry", GATEWAY_URL, *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def gw_get(path):
    r = requests.get(f"{GATEWAY_URL}{path}", timeout=5)
    r.raise_for_status()
    return r.json()


@app.route("/")
def index():
    return send_from_directory(Path(__file__).parent, "index.html")


@app.route("/api/health")
def health():
    try:
        gw_get("/api/v0/tools")
        gw = "ok"
    except Exception as e:
        gw = f"down: {e}"
    return jsonify({
        "manager": "ok",
        "gateway": gw,
        "gateway_url": GATEWAY_URL,
        "data_dir": str(DATA_DIR),
    })


@app.route("/api/tools")
def list_tools():
    return jsonify(gw_get("/api/v0/tools"))


@app.route("/api/servers", methods=["GET"])
def list_servers():
    return jsonify(gw_get("/api/v0/servers"))


@app.route("/api/servers", methods=["POST"])
def add_server():
    cfg = request.get_json(force=True)
    name = cfg.get("name")
    if not name:
        return jsonify({"error": "name required"}), 400
    cfg_path = CONFIGS_DIR / f"{name}.json"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    res = mcpj("register", "-c", str(cfg_path))
    if res.returncode != 0:
        return jsonify({"error": res.stderr.strip() or res.stdout.strip()}), 500
    return jsonify({"name": name, "stdout": res.stdout.strip()})


@app.route("/api/servers/<name>", methods=["DELETE"])
def remove_server(name):
    res = mcpj("deregister", name)
    cfg_path = CONFIGS_DIR / f"{name}.json"
    cfg_path.unlink(missing_ok=True)
    return jsonify({
        "name": name,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip(),
    })


@app.route("/api/groups", methods=["GET"])
def list_groups():
    out = []
    for f in sorted(GROUPS_DIR.glob("*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except Exception as e:
            out.append({"name": f.stem, "error": str(e)})
    return jsonify(out)


@app.route("/api/groups/<name>", methods=["GET"])
def get_group(name):
    f = GROUPS_DIR / f"{name}.json"
    if not f.exists():
        return jsonify({"error": "not found"}), 404
    return jsonify(json.loads(f.read_text()))


def _apply_group(name, body):
    f = GROUPS_DIR / f"{name}.json"
    f.write_text(json.dumps(body, indent=2))
    mcpj("delete", "group", name)
    res = mcpj("create", "group", "--conf", str(f))
    return res


@app.route("/api/groups", methods=["POST"])
def create_group():
    body = request.get_json(force=True)
    name = body.get("name")
    if not name:
        return jsonify({"error": "name required"}), 400
    res = _apply_group(name, body)
    if res.returncode != 0:
        return jsonify({"error": res.stderr.strip() or res.stdout.strip()}), 500
    return jsonify({"name": name, "endpoint": f"/v0/groups/{name}/mcp"})


@app.route("/api/groups/<name>", methods=["PUT"])
def update_group(name):
    body = request.get_json(force=True)
    body["name"] = name
    res = _apply_group(name, body)
    if res.returncode != 0:
        return jsonify({"error": res.stderr.strip() or res.stdout.strip()}), 500
    return jsonify({"name": name, "endpoint": f"/v0/groups/{name}/mcp"})


@app.route("/api/groups/<name>", methods=["DELETE"])
def delete_group(name):
    res = mcpj("delete", "group", name)
    f = GROUPS_DIR / f"{name}.json"
    f.unlink(missing_ok=True)
    return jsonify({"name": name, "stdout": res.stdout.strip()})


if __name__ == "__main__":
    GROUPS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=PORT)
