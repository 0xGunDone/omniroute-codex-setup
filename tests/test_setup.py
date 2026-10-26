import argparse
import copy
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import tomlkit

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/install-omniroute-codex/scripts/setup.py"
spec = importlib.util.spec_from_file_location("setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
FAKE_KEY = "demo-router-key-not-a-credential"
MODEL = "codex/gpt-6.1-sol"
TEMPLATE = {"models": [{"slug": "gpt-6.1-sol", "display_name": "GPT-6.1 Sol",
    "supported_reasoning_levels": [{"effort": "max"}, {"effort": "low"}],
    "shell_type": "unified_exec", "available_in_plans": ["plus"],
    "model_messages": {"instructions_template": "Public upstream instructions"}},
    {"slug": "gpt-6-luna", "supported_reasoning_levels": [{"effort": "low"}]}]}
API = {"data": [{"id": MODEL}, {"id": "codex/gpt-6-luna"}]}


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "codex"
        self.home.mkdir()
        self.old = '# Keep comments\nmodel_provider = "openai"\n\n[permissions]\nmode = "existing"\n\n[mcp_servers.demo]\nurl = "https://example.invalid/mcp"\n'
        (self.home / "config.toml").write_text(self.old)
        (self.home / "auth.json").write_text(json.dumps({"tokens": {"access_token": "old-demo-session"}}))
        (self.home / "sessions").mkdir()
        (self.home / "sessions/session.jsonl").write_text('unchanged transcript\n')
        self.db = self.home / "state_5.sqlite"
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("CREATE TABLE threads(id TEXT PRIMARY KEY,model_provider TEXT,title TEXT,archived INTEGER,is_pinned INTEGER)")
            db.executemany("INSERT INTO threads VALUES(?,?,?,?,?)", [
                ("current", "openai", "Current chat", 0, 1),
                ("archived", "openai", "Archive", 1, 0),
                ("other", "other-provider", "Leave me", 0, 1)])

    def args(self):
        return argparse.Namespace(codex_home=self.home, base_url="http://127.0.0.1:20128/v1", model=MODEL,
                                  effort="max", catalog_template=None, from_provider=["openai"], native_tools=True,
                                  subagents=True, apply=True, wait_for_exit=0)

    def apply(self, **overrides):
        args = self.args()
        for k, v in overrides.items():
            setattr(args, k, v)
        with patch.object(setup, "read_key", return_value=FAKE_KEY), patch.object(setup, "request_json", return_value=API), \
             patch.object(setup, "load_template", return_value=TEMPLATE), patch.object(setup, "probe", return_value={"completed": True}), \
             patch.object(setup, "client_running", return_value=False):
            setup.client_apply(args)
        return next((self.home / "omniroute-backups").iterdir()) if args.apply else None

    def rows(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            return db.execute("SELECT * FROM threads ORDER BY id").fetchall()

    def test_preserves_toml_and_capabilities(self):
        text = setup.config_text(self.old, "http://127.0.0.1:20128/v1", FAKE_KEY, self.home, MODEL, "max", True, True)
        d = tomlkit.parse(text)
        self.assertIn("# Keep comments", text)
        self.assertEqual(d["mcp_servers"]["demo"]["url"], "https://example.invalid/mcp")
        self.assertEqual(d["permissions"]["mode"], "existing")
        self.assertEqual(d["model_providers"]["omniroute"]["http_headers"]["x-openai-actor-authorization"], "Bearer " + FAKE_KEY)
        self.assertFalse(d["model_providers"]["omniroute"]["requires_openai_auth"])

    def test_migration_preserves_archives_pins_transcripts(self):
        before = self.rows()
        folder = self.apply()
        after = self.rows()
        for old, new in zip(before, after):
            self.assertEqual(old[0], new[0])
            self.assertEqual(old[2:], new[2:])
            self.assertEqual(new[1], "omniroute" if old[1] == "openai" else old[1])
        self.assertEqual((self.home / "sessions/session.jsonl").read_text(), "unchanged transcript\n")
        self.assertEqual(json.loads((folder / "auth.json").read_text())["tokens"]["access_token"], "old-demo-session")
        self.assertEqual(json.loads((self.home / "auth.json").read_text()), {"OPENAI_API_KEY": FAKE_KEY})
        if os.name != "nt":
            self.assertEqual((self.home / "auth.json").stat().st_mode & 0o777, 0o600)

    def test_restore_keeps_chats_created_later(self):
        folder = self.apply()
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("INSERT INTO threads VALUES('new','omniroute','New chat',0,0)")
        with patch.object(setup, "client_running", return_value=False):
            setup.restore(argparse.Namespace(backup=folder, wait_for_exit=0))
        self.assertEqual((self.home / "config.toml").read_text(), self.old)
        self.assertIn(("new", "omniroute", "New chat", 0, 0), self.rows())
        self.assertIn(("archived", "openai", "Archive", 1, 0), self.rows())

    def test_restore_refuses_later_config_changes(self):
        folder = self.apply()
        with (self.home / "config.toml").open("a") as f:
            f.write("# later edit\n")
        with patch.object(setup, "client_running", return_value=False), self.assertRaises(setup.SetupError):
            setup.restore(argparse.Namespace(backup=folder, wait_for_exit=0))
        self.assertIn("# later edit", (self.home / "config.toml").read_text())

    def test_apply_failure_rolls_back_files_and_db_transaction(self):
        before = self.rows()
        with patch.object(setup, "migrate", side_effect=setup.SetupError("test failure")):
            with self.assertRaises(setup.SetupError):
                self.apply()
        self.assertEqual((self.home / "config.toml").read_text(), self.old)
        self.assertEqual(before, self.rows())

    def test_concurrent_thread_changes_roll_back(self):
        path, rows, _ = setup.plan(self.home, ["openai"])
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("UPDATE threads SET model_provider='changed' WHERE id='archived'")
        with self.assertRaises(setup.SetupError):
            setup.migrate(path, rows)
        self.assertIn(("current", "openai", "Current chat", 0, 1), self.rows())

    def test_dry_run_does_not_write(self):
        before = self.rows()
        self.apply(apply=False)
        self.assertFalse((self.home / "omniroute-backups").exists())
        self.assertEqual((self.home / "config.toml").read_text(), self.old)
        self.assertEqual(before, self.rows())

    def test_running_client_blocks_write(self):
        with patch.object(setup, "client_running", return_value=True), self.assertRaises(setup.SetupError):
            setup.require_stopped()

    def test_highest_database_version_and_no_implicit_provider_migration(self):
        (self.home / "state_9.sqlite").write_bytes(self.db.read_bytes())
        self.assertEqual(setup.state_database(self.home).name, "state_9.sqlite")
        self.assertEqual(setup.plan(self.home, [])[1], [])

    def test_unknown_database_schema_is_not_modified(self):
        with closing(sqlite3.connect(self.home / "state_12.sqlite")) as db, db:
            db.execute("CREATE TABLE threads(new_id TEXT)")
        with self.assertRaises(setup.SetupError):
            setup.plan(self.home, ["openai"])

    def test_catalog_intersects_key_scoped_ids_and_preserves_reasoning(self):
        source = copy.deepcopy(TEMPLATE)
        result = setup.make_catalog(API, source, MODEL, "max")
        self.assertEqual(source, TEMPLATE)
        self.assertEqual(result["models"][0]["slug"], MODEL)
        self.assertEqual(result["models"][0]["shell_type"], "unified_exec")
        self.assertNotIn("available_in_plans", result["models"][0])
        self.assertEqual(len(setup.make_catalog({"data": [{"id": MODEL}]}, source, MODEL, "max")["models"]), 1)

    def test_catalog_never_invents_model_access_or_reasoning(self):
        with self.assertRaises(setup.SetupError):
            setup.make_catalog({"data": []}, TEMPLATE, MODEL, "max")
        with self.assertRaises(setup.SetupError):
            setup.make_catalog(API, TEMPLATE, MODEL, "ultra")

    def test_url_rejects_remote_http_credentials_and_bad_paths(self):
        for url in ["http://example.com/v1", "https://user:pass@example.com/v1", "https://example.com/v1?key=x", "https://example.com/responses"]:
            with self.subTest(url=url), self.assertRaises(setup.SetupError):
                setup.normalize_url(url)
        self.assertEqual(setup.normalize_url("https://router.example/v1/"), "https://router.example/v1")

    def test_no_model_probe_when_blocked(self):
        with patch.object(setup.urllib.request, "build_opener") as request:
            with self.assertRaises(setup.SetupError):
                setup.probe("http://localhost/v1", "fake", "codex/" + setup.BLOCKED, "low")
            request.assert_not_called()

    def test_probe_requires_completed_marker_not_http200(self):
        good = b'data: {"type":"response.output_text.delta","delta":"OMNI_SETUP_OK"}\n\ndata: {"type":"response.completed","response":{"status":"completed"}}\n\n'
        for stream, should_pass in [(good, True), (good.split(b'data: {"type":"response.completed"')[0], False),
                                    (good.replace(b'OMNI_SETUP_OK', b'wrong'), False),
                                    (b'data: {"type":"response.failed"}\n', False)]:
            with self.subTest(stream=stream), patch.object(setup.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value = io.BytesIO(stream)
                if should_pass:
                    self.assertTrue(setup.probe("http://localhost/v1", FAKE_KEY, MODEL, "max")["completed"])
                else:
                    with self.assertRaises(setup.SetupError):
                        setup.probe("http://localhost/v1", FAKE_KEY, MODEL, "max")

    def test_http_error_does_not_echo_upstream_secrets(self):
        error = setup.urllib.error.HTTPError("https://router.invalid/v1/responses", 401, "secret-upstream-token", {}, io.BytesIO(b'secret-body'))
        with patch.object(setup.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(setup.SetupError) as caught:
                setup.probe("http://localhost/v1", FAKE_KEY, MODEL, "max")
            self.assertNotIn("secret", str(caught.exception))

    def test_bearer_requests_never_follow_redirect(self):
        self.assertIsNone(setup.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid"))

    @unittest.skipIf(os.name == "nt", "Unix symlink semantics")
    def test_symlink_target_is_not_replaced(self):
        target = Path(self.temp.name) / "unrelated"
        target.write_text("keep")
        link = self.home / "symlink"
        link.symlink_to(target)
        with self.assertRaises(setup.SetupError):
            setup.atomic_write(link, b"replace")
        self.assertEqual(target.read_text(), "keep")

    def test_repeated_config_is_idempotent(self):
        first = setup.config_text(self.old, "http://localhost:20128/v1", FAKE_KEY, self.home, MODEL, "max", True, True)
        self.assertEqual(first, setup.config_text(first, "http://localhost:20128/v1", FAKE_KEY, self.home, MODEL, "max", True, True))

    def test_legacy_profiles_and_base_url_fail_closed(self):
        for extra in ['openai_base_url = "https://example.invalid"\n', '[profiles.legacy]\nmodel = "something"\n']:
            with self.assertRaises(setup.SetupError):
                setup.config_text(extra + self.old, "http://localhost:20128/v1", FAKE_KEY, self.home, MODEL, "max")

    def test_server_secrets_unique_loopback_and_repeated_install_refused(self):
        folder = Path(self.temp.name) / "server"
        args = argparse.Namespace(directory=folder, port=20128, heap_mb=8192, memory_gb=10, start=False)
        setup.server(args)
        env = (folder / ".env").read_text()
        self.assertIn("REQUIRE_API_KEY=true", env)
        self.assertIn('127.0.0.1:20128:20128', (folder / "compose.yaml").read_text())
        values = [line.split("=", 1)[1] for line in env.splitlines()[:4]]
        self.assertEqual(len(set(values)), 4)
        if os.name != "nt":
            self.assertEqual((folder / ".env").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(setup.SetupError):
            setup.server(args)


if __name__ == "__main__":
    unittest.main()
