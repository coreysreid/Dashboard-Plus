"""Tests for decision 0139: a strict Content-Security-Policy on every response, and no inline scripts or event handlers left in any page."""
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from support import ROOT

WEB = ROOT / "src" / "dashboard" / "web"


class PolicyIsSentEverywhere(unittest.TestCase):
    def setUp(self):
        from dashboard.core import db, settings, startup
        from dashboard.web.app import create_app
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copytree(ROOT / "modules" / "people", self.tmp / "modules" / "people")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        settings.put(conn, "setup.done", True)
        conn.close()
        app = create_app("t", lambda: None, report, data_dir=self.tmp / "data", session_key="k")
        app.config["PORT"] = 5139
        self.base = "http://127.0.0.1:5139"
        self.client = app.test_client()
        self.client.get("/?key=k", base_url=self.base)

    def policy(self, path):
        response = self.client.get(path, base_url=self.base)
        self.assertIn("Content-Security-Policy", response.headers, path)
        return response, response.headers["Content-Security-Policy"]

    def test_html_pages_carry_the_strict_policy(self):
        _, policy = self.policy("/")
        for part in ("default-src 'self'", "script-src 'self'", "object-src 'none'", "base-uri 'none'",
                     "form-action 'self'", "frame-ancestors 'none'", "img-src 'self' data:"):
            self.assertIn(part, policy)
        self.assertNotIn("unsafe-eval", policy)
        self.assertNotIn("script-src 'self' 'unsafe", policy)
        self.assertNotRegex(policy, r"https?:")  # nothing is loaded from another site

    def test_json_and_helper_answers_carry_it(self):
        self.assertEqual(self.policy("/api/ping")[0].mimetype, "application/json")
        refused, _ = self.policy("/api/v1/tables")  # no key: a plain JSON refusal
        self.assertEqual(refused.mimetype, "application/json")

    def test_error_pages_and_static_files_carry_it(self):
        response, _ = self.policy("/no/such/page")
        self.assertEqual(response.status_code, 404)
        script, _ = self.policy("/static/common.js")
        self.assertEqual(script.status_code, 200)
        self.assertEqual(script.headers["X-Content-Type-Options"], "nosniff")
        script.close()

    def test_the_launch_page_carries_it_without_a_cookie(self):
        response = self.client.get("/start", base_url=self.base, headers={"Cookie": ""})
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])


class NoInlineCodeInTemplates(unittest.TestCase):
    TEMPLATES = sorted((WEB / "templates").glob("*.html"))

    def test_there_are_templates_to_scan(self):
        self.assertGreater(len(self.TEMPLATES), 50)

    def test_no_script_tag_has_a_body(self):
        for path in self.TEMPLATES:
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"<script\b([^>]*)>(.*?)</script>", text, re.S | re.I):
                self.assertIn("src=", match.group(1), f"{path.name} has an inline script")
                self.assertEqual(match.group(2).strip(), "", f"{path.name}: a script with a src must be empty")

    def test_no_event_handler_attributes_or_javascript_links(self):
        for path in self.TEMPLATES:
            text = re.sub(r"\{%.*?%\}|\{\{.*?\}\}", "", path.read_text(encoding="utf-8"), flags=re.S)  # Jinja tags are not attributes
            self.assertIsNone(re.search(r"<[a-z][^>]*\son[a-z]+\s*=", text, re.I), f"{path.name} has an on... handler")
            self.assertNotIn("javascript:", text.lower(), path.name)

    def test_python_that_builds_html_has_no_handlers_either(self):
        for path in WEB.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"<[a-z][^>]*\son(click|submit|change|load|error|input)\s*=", text, re.I), path.name)
            self.assertNotIn("<script", text, path.name)

    def test_every_script_source_is_a_file_this_program_serves(self):
        for path in self.TEMPLATES:
            for src in re.findall(r"<script[^>]*\ssrc=\"([^\"]+)\"", path.read_text(encoding="utf-8")):
                self.assertTrue(src.startswith("/static/"), f"{path.name}: {src}")
                self.assertTrue((WEB / src.lstrip("/")).is_file(), f"{path.name}: {src} is missing")

    def test_static_scripts_load_nothing_from_another_site(self):
        for path in (WEB / "static").glob("*.js"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"https?://", path.name)
