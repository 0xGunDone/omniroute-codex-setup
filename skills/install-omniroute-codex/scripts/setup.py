#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["tomlkit==0.13.3"]
# ///
"""Install OmniRoute; connect Codex with reversible, offline history migration."""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import getpass
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from pathlib import Path

import tomlkit

IMAGE = "diegosouzapw/omniroute:3.8.52"
CATALOG_COMMIT = "716b4ec6dffc7b23b1c598400bccb622551bf787"
CATALOG_URL = f"https://raw.githubusercontent.com/openai/codex/{CATALOG_COMMIT}/codex-rs/models-manager/models.json"
CATALOG_SHA256 = "943ca7fe1d19ed019054158303f0dbbd80b3bef43b3aa425a71aa7cb3fb52c2b"
MAX_BODY = 32 * 1024 * 1024
BLOCKED = "gpt-5.1-codex-mini"
MANAGED_FILES = ("config.toml", "auth.json", "omniroute-model-catalog.json")


class SetupError(Exception):
    pass


def restrict(path: Path, directory=False):
    if os.name != "nt":
        os.chmod(path, 0o700 if directory else 0o600)
        return
    identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                              capture_output=True, text=True, check=True)
    sid = next(csv.reader(identity.stdout.splitlines()))[1]
    if not re.fullmatch(r"S-1-[0-9-]+", sid):
        raise SetupError("Cannot determine Windows user SID")
    access = f"*{sid}:" + ("(OI)(CI)F" if directory else "F")
    subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", access],
                   capture_output=True, check=True)


def atomic_write(path: Path, content: bytes, mode: int = 0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SetupError(f"Refusing symlink: {path.name}")
    fd, temp = tempfile.mkstemp(prefix=".omni-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        restrict(Path(temp))
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def normalize_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise SetupError("Base URL must be HTTP(S)")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SetupError("Base URL must not contain credentials, query, or fragment")
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise SetupError("Remote endpoints require HTTPS; use an SSH tunnel for HTTP")
    if not parsed.path.rstrip("/").endswith("/v1"):
        raise SetupError("Base URL must end in /v1, not /responses or /dashboard")
    return url.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, key=None, body=None, timeout=30):
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, headers=headers, data=dump(body) if body is not None else None)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            raise SetupError("Response too large")
        return json.loads(raw)
    except urllib.error.HTTPError as error:
        # Provider errors can contain credentials or user input. Never echo their bodies.
        status = error.code
        error.close()
        raise SetupError(f"HTTP {status} from {urllib.parse.urlsplit(url).path}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise SetupError("Endpoint unavailable or invalid JSON; settings were not changed") from None


def read_key(args):
    if args.key_file:
        value = args.key_file.read_text().strip()
        if value.startswith("{"):
            try:
                value = json.loads(value)["OPENAI_API_KEY"]
            except (ValueError, KeyError):
                raise SetupError("Key file must contain a router key or API-key auth.json") from None
    elif args.key_env:
        value = os.environ.get(args.key_env, "").strip()
    else:
        value = getpass.getpass("OmniRoute API key (hidden): ").strip()
    if not isinstance(value, str) or not value or any(ch.isspace() for ch in value):
        raise SetupError("Missing or invalid router key")
    return value


def probe(base, key, model, effort):
    if BLOCKED in model.lower():
        raise SetupError("This model is blocked; no request was sent")
    payload = {"model": model, "input": "Reply exactly OMNI_SETUP_OK.", "store": False,
               "stream": True, "reasoning": {"effort": effort}}
    req = urllib.request.Request(base + "/responses", data=dump(payload), headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept": "text/event-stream"})
    completed = False
    text = ""
    total = 0
    deadline = time.monotonic() + 180
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=180) as response:
            for line in response:
                total += len(line)
                if total > MAX_BODY or time.monotonic() > deadline:
                    raise SetupError("Diagnostic response exceeded its limit")
                if not line.startswith(b"data:") or line[5:].strip() == b"[DONE]":
                    continue
                try:
                    item = json.loads(line[5:])
                except ValueError:
                    continue
                if item.get("type") in ("error", "response.failed", "response.incomplete"):
                    raise SetupError("Diagnostic inference failed; no client settings changed")
                if item.get("type") == "response.output_text.delta":
                    text += item.get("delta", "")
                if item.get("type") == "response.completed":
                    result = item.get("response", {})
                    completed = result.get("status", "completed") == "completed"
                    if not text:
                        text = "".join(c.get("text", "") for o in result.get("output", [])
                                       for c in o.get("content", []) if c.get("type") == "output_text")
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        raise SetupError(f"Inference HTTP {status}; inspect gateway logs privately") from None
    except (urllib.error.URLError, TimeoutError):
        raise SetupError("Diagnostic inference timed out or disconnected") from None
    if not completed or text.strip() != "OMNI_SETUP_OK":
        raise SetupError("HTTP 200 alone is insufficient: completed marker was not received")
    return {"completed": True, "marker": True, "model": model}


def make_catalog(api_models, template, selected, effort):
    available = {m["id"] for m in api_models.get("data", []) if isinstance(m, dict) and isinstance(m.get("id"), str)}
    if selected not in available:
        raise SetupError("Selected exact model ID is absent from the key-scoped /models catalog")
    result = []
    for original in template.get("models", []):
        slug = original.get("slug", "")
        base_slug = re.sub(r"^(?:codex|cx)/", "", slug)
        target = next((candidate for candidate in ("codex/" + base_slug, "cx/" + base_slug, slug, base_slug) if candidate in available), None)
        if not target or BLOCKED in target.lower():
            continue
        item = copy.deepcopy(original)
        item["slug"] = target
        item["visibility"] = "list"
        item["supported_in_api"] = True
        # No product-plan filters locally. Upstream authorization still decides entitlement.
        item.pop("available_in_plans", None)
        result.append(item)
    chosen = next((m for m in result if m["slug"] == selected), None)
    if not chosen:
        raise SetupError("No trusted Codex metadata for selected model; provide a matching catalog template")
    if effort not in {r.get("effort") for r in chosen.get("supported_reasoning_levels", [])}:
        raise SetupError("Reasoning effort absent from selected model's trusted metadata")
    return {"models": result}


def load_template(path=None):
    if path:
        return json.loads(path.read_text())
    try:
        with urllib.request.urlopen(CATALOG_URL, timeout=30) as response:
            raw = response.read(MAX_BODY + 1)
    except (urllib.error.URLError, TimeoutError):
        raise SetupError("Cannot fetch pinned official Codex metadata; use --catalog-template") from None
    if hashlib.sha256(raw).hexdigest() != CATALOG_SHA256:
        raise SetupError("Official catalog checksum mismatch; no changes made")
    return json.loads(raw)


def config_text(old, base, key, home, model, effort, native=False, subagents=False):
    try:
        doc = tomlkit.parse(old)
    except tomlkit.exceptions.ParseError:
        raise SetupError("Invalid existing TOML; parser output suppressed to protect credentials") from None
    if "profiles" in doc or "profile" in doc:
        raise SetupError("Legacy profiles detected; resolve profile precedence before switching")
    if doc.get("openai_base_url"):
        raise SetupError("Legacy openai_base_url found; review it before configuring a custom provider")
    doc["model_provider"] = "omniroute"
    doc["model"] = model
    doc["model_reasoning_effort"] = effort
    doc["cli_auth_credentials_store"] = "file"
    doc["model_catalog_json"] = str(home / "omniroute-model-catalog.json")
    providers = doc.setdefault("model_providers", tomlkit.table())
    provider = providers.setdefault("omniroute", tomlkit.table())
    provider.update({"name": "OmniRoute", "base_url": base, "wire_api": "responses", "requires_openai_auth": False,
                     "experimental_bearer_token": key})
    provider.pop("env_key", None)
    if native:
        provider.setdefault("http_headers", tomlkit.table())["x-openai-actor-authorization"] = "Bearer " + key
        doc.setdefault("features", tomlkit.table())["image_generation"] = True
    elif "http_headers" in provider:
        provider["http_headers"].pop("x-openai-actor-authorization", None)
    if subagents:
        doc.setdefault("agents", tomlkit.table()).update({"default_subagent_model": model,
                                                        "default_subagent_reasoning_effort": effort})
    return tomlkit.dumps(doc)


def client_running():
    if os.name == "nt":
        cmd = ["powershell", "-NoProfile", "-Command", "Get-Process codex,ChatGPT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"]
    else:
        cmd = ["ps", "-axo", "comm="]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise SetupError("Could not check Codex processes; stop the client before proceeding")
    if os.name == "nt":
        return bool(result.stdout.strip())
    return any(Path(line.strip()).name.lower() in ("codex", "codex.app", "chatgpt", "codex-code-mode-host")
               for line in result.stdout.splitlines())


def require_stopped(wait=0):
    until = time.monotonic() + wait
    while client_running():
        if time.monotonic() >= until:
            raise SetupError("Codex is running. Quit Desktop, CLI, VS Code Codex, then retry from an external terminal")
        time.sleep(2)


def state_database(home):
    candidates = [p for p in home.glob("state_*.sqlite") if re.fullmatch(r"state_\d+\.sqlite", p.name)]
    return max(candidates, key=lambda p: int(p.stem.split("_")[1]), default=None)


def connect_db(path, readonly=False):
    if path.is_symlink():
        raise SetupError("Refusing symlinked state database")
    db = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    cols = {r[1] for r in db.execute("PRAGMA table_info(threads)")}
    if not {"id", "model_provider"} <= cols:
        db.close()
        raise SetupError("Unknown threads schema; no migration attempted")
    return db


def selected_rows(db, providers):
    if not providers:
        return []
    placeholders = ",".join("?" for _ in providers)
    return [dict(row) for row in db.execute(f"SELECT id,model_provider FROM threads WHERE model_provider IN ({placeholders})", providers)]


def plan(home, providers):
    path = state_database(home)
    if path:
        with closing(connect_db(path, True)) as db:
            rows = selected_rows(db, providers)
            counts = [dict(row) for row in db.execute("SELECT model_provider,COUNT(*) AS count FROM threads GROUP BY model_provider")]
    else:
        rows, counts = [], []
    return path, rows, counts


def migrate(path, rows, target="omniroute"):
    if not path or not rows:
        return
    with closing(connect_db(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        for row in rows:
            changed = db.execute("UPDATE threads SET model_provider=? WHERE id=? AND model_provider=?",
                                 (target, row["id"], row["model_provider"])).rowcount
            if changed != 1:
                raise SetupError("Thread metadata changed concurrently; transaction rolled back")


def backup(home, path, rows):
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    folder = home / "omniroute-backups" / stamp
    folder.mkdir(parents=True, mode=0o700)
    restrict(folder.parent, True)
    restrict(folder, True)
    files = {}
    for name in MANAGED_FILES:
        src = home / name
        if src.is_symlink():
            raise SetupError("Managed files must not be symlinks")
        files[name] = {"existed": src.exists(), "before_sha256": None}
        if src.exists():
            data = src.read_bytes()
            atomic_write(folder / name, data)
            files[name]["before_sha256"] = hashlib.sha256(data).hexdigest()
    if path:
        with closing(connect_db(path, True)) as src, closing(sqlite3.connect(folder / "state-snapshot.sqlite")) as dest:
            src.backup(dest)
        restrict(folder / "state-snapshot.sqlite")
    manifest = {"home": str(home), "database": path.name if path else None, "rows": rows,
                "files": files, "status": "prepared"}
    atomic_write(folder / "manifest.json", dump(manifest))
    return folder, manifest


def restore_files(home, folder, manifest):
    for name, info in manifest["files"].items():
        if info["existed"]:
            data = (folder / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != info["before_sha256"]:
                raise SetupError("Backup checksum mismatch")
            atomic_write(home / name, data)
        else:
            (home / name).unlink(missing_ok=True)


def client_apply(args):
    home = args.codex_home.expanduser().resolve()
    base = normalize_url(args.base_url)
    key = read_key(args)
    api = request_json(base + "/models", key)
    catalog = make_catalog(api, load_template(args.catalog_template), args.model, args.effort)
    # Verify entitlement before changing files; no real user conversation is replayed.
    status = probe(base, key, args.model, args.effort)
    old = (home / "config.toml").read_text() if (home / "config.toml").exists() else ""
    new = config_text(old, base, key, home, args.model, args.effort, args.native_tools, args.subagents)
    path, rows, counts = plan(home, args.from_provider)
    summary = {"model": args.model, "effort": args.effort, "catalog_models": len(catalog["models"]),
               "thread_provider_counts": counts, "threads_to_migrate": len(rows), "inference": status,
               "apply": args.apply}
    if not args.apply:
        print(json.dumps(summary, indent=2))
        return
    require_stopped(args.wait_for_exit)
    # Re-read after waiting: never overwrite settings made while the app was closing.
    current = (home / "config.toml").read_text() if (home / "config.toml").exists() else ""
    if current != old:
        raise SetupError("Config changed since preflight; rerun")
    path, rows, counts = plan(home, args.from_provider)
    folder, manifest = backup(home, path, rows)
    content = {"config.toml": new.encode(), "auth.json": dump({"OPENAI_API_KEY": key}),
               "omniroute-model-catalog.json": dump(catalog)}
    try:
        require_stopped()
        for name, data in content.items():
            atomic_write(home / name, data)
            manifest["files"][name]["after_sha256"] = hashlib.sha256(data).hexdigest()
        migrate(path, rows)
    except BaseException:
        restore_files(home, folder, manifest)
        manifest["status"] = "rolled-back-after-error"
        atomic_write(folder / "manifest.json", dump(manifest))
        raise
    manifest["status"] = "applied"
    atomic_write(folder / "manifest.json", dump(manifest))
    summary.update({"threads_to_migrate": len(rows), "backup": str(folder)})
    print(json.dumps(summary, indent=2))


def restore(args):
    require_stopped(args.wait_for_exit)
    folder = args.backup.expanduser().resolve()
    manifest = json.loads((folder / "manifest.json").read_text())
    home = Path(manifest["home"])
    if manifest["status"] != "applied":
        raise SetupError("Backup is not an applied migration")
    # Do not overwrite later user edits. A conflict requires manual merge, not --force.
    for name, info in manifest["files"].items():
        path = home / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != info["after_sha256"]:
            raise SetupError(f"{name} changed after setup; review backup and merge manually")
        if info["existed"] and hashlib.sha256((folder / name).read_bytes()).hexdigest() != info["before_sha256"]:
            raise SetupError("Backup checksum mismatch")
    path = home / manifest["database"] if manifest["database"] else None
    if path and state_database(home) != path:
        raise SetupError("Codex state schema version changed; migrate provider IDs manually")
    if path and manifest["rows"]:
        with closing(connect_db(path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            for row in manifest["rows"]:
                current = db.execute("SELECT model_provider FROM threads WHERE id=?", (row["id"],)).fetchone()
                if current and current[0] != "omniroute":
                    raise SetupError("Thread provider changed after setup; restore stopped")
            for row in manifest["rows"]:
                db.execute("UPDATE threads SET model_provider=? WHERE id=?", (row["model_provider"], row["id"]))
    restore_files(home, folder, manifest)
    manifest["status"] = "restored"
    atomic_write(folder / "manifest.json", dump(manifest))
    print("Restored authentication/config and original provider IDs; newer chats were kept.")


def server(args):
    folder = args.directory.expanduser().resolve()
    if folder.exists() and any(folder.iterdir()):
        raise SetupError("Server directory is not empty; existing installation was not changed")
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    restrict(folder, True)
    env = {"INITIAL_PASSWORD": secrets.token_urlsafe(32), "JWT_SECRET": secrets.token_hex(32),
           "API_KEY_SECRET": secrets.token_hex(32), "STORAGE_ENCRYPTION_KEY": secrets.token_hex(32),
           "REQUIRE_API_KEY": "true", "AUTH_COOKIE_SECURE": "false", "DATA_DIR": "/app/data",
           "OMNIROUTE_MEMORY_MB": str(args.heap_mb)}
    atomic_write(folder / ".env", "".join(f"{k}={v}\n" for k, v in env.items()).encode())
    compose = f'''services:
  omniroute:
    image: {IMAGE}
    restart: unless-stopped
    stop_grace_period: 60s
    ports:
      - "127.0.0.1:{args.port}:20128"
    env_file: .env
    environment:
      HOSTNAME: 0.0.0.0
    mem_limit: {args.memory_gb}g
    volumes:
      - omniroute-data:/app/data
volumes:
  omniroute-data:
'''
    atomic_write(folder / "compose.yaml", compose.encode())
    atomic_write(folder / ".gitignore", b".env\n*.sqlite*\nbackups/\n")
    if args.start:
        if not shutil.which("docker"):
            raise SetupError("Files prepared; install Docker Engine/Desktop from its official source, then run docker compose up -d")
        subprocess.run(["docker", "compose", "-f", str(folder / "compose.yaml"), "up", "-d"], cwd=folder, check=True)
    print(f"Prepared {folder}. Dashboard: http://127.0.0.1:{args.port}")
    print("Read INITIAL_PASSWORD from .env privately; add your Codex account and create a router API key in the dashboard.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    srv = sub.add_parser("server", help="Prepare a new loopback-only Docker installation")
    srv.add_argument("--directory", type=Path, required=True)
    srv.add_argument("--port", type=int, default=20128)
    srv.add_argument("--heap-mb", type=int, default=8192)
    srv.add_argument("--memory-gb", type=int, default=10)
    srv.add_argument("--start", action="store_true")
    srv.set_defaults(func=server)
    client = sub.add_parser("client", help="Preflight, then optionally apply Codex configuration")
    client.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))))
    client.add_argument("--base-url", required=True)
    keys = client.add_mutually_exclusive_group()
    keys.add_argument("--key-file", type=Path)
    keys.add_argument("--key-env")
    client.add_argument("--model", default="codex/gpt-6.1-sol")
    client.add_argument("--effort", default="max", choices=["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"])
    client.add_argument("--catalog-template", type=Path)
    client.add_argument("--from-provider", action="append", default=[], help="Migrate only this exact old provider ID; repeat as needed")
    client.add_argument("--native-tools", action="store_true", help="Enable version-dependent native gateway header and image feature")
    client.add_argument("--subagents", action="store_true", help="Use selected model/effort for new Codex subagents")
    client.add_argument("--apply", action="store_true")
    client.add_argument("--wait-for-exit", type=int, default=0)
    client.set_defaults(func=client_apply)
    rst = sub.add_parser("restore", help="Restore a migration without replacing later chat data")
    rst.add_argument("--backup", type=Path, required=True)
    rst.add_argument("--wait-for-exit", type=int, default=0)
    rst.set_defaults(func=restore)
    args = parser.parse_args()
    try:
        if args.command == "server" and (not 1024 <= args.port <= 65535 or args.heap_mb < 512 or args.memory_gb * 1024 < args.heap_mb + 1024):
            raise SetupError("Use port 1024..65535 and leave at least 1 GiB above the V8 heap")
        args.func(args)
    except (SetupError, OSError, sqlite3.Error, subprocess.CalledProcessError):
        # No traceback/config/parser diagnostics: those can contain credentials.
        error = sys.exc_info()[1]
        message = str(error) if isinstance(error, SetupError) else "Operation failed; inspect local files privately. No credentials were printed."
        print("ERROR: " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
