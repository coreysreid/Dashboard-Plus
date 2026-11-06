"""Tests for the privacy check."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_privacy  # noqa: E402


def scan_files(files: dict[str, str | bytes]):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        return check_privacy.scan(root)


class PrivacyCheckTests(unittest.TestCase):
    def test_clean_files_pass(self):
        self.assertEqual(scan_files({"a.md": "Nothing private here.\n", "src/b.py": "x = 1\n"}), [])

    def test_database_and_key_files_are_flagged(self):
        for name in ("home.db", "x/y.sqlite3", "cert.pem", "id.key"):
            self.assertTrue(scan_files({name: "x"}), name)

    def test_real_config_is_flagged_but_example_is_not(self):
        self.assertTrue(scan_files({"config.toml": "a = 1\n"}))
        self.assertTrue(scan_files({"x/config.toml": "a = 1\n"}))
        self.assertEqual(scan_files({"config.example.toml": "a = 1\n"}), [])

    def test_data_and_secrets_folders_are_flagged(self):
        self.assertTrue(scan_files({"data/notes.txt": "hello"}))
        self.assertTrue(scan_files({"secrets/x.txt": "hello"}))
        self.assertEqual(scan_files({"tests/data/notes.txt": "hello"}), [])

    def test_token_is_flagged_and_not_echoed(self):
        token = "ghp_" + "a1B2c3D4e5" * 4
        found = scan_files({"notes.md": f"token {token}\n"})
        self.assertEqual(len(found), 1)
        self.assertNotIn(token, str(found[0]))

    def test_secret_assignment(self):
        real = "api_key = \"" + "Ab3dEf6hIj9kLm2nOp5qRs8tUv" + "\"\n"
        self.assertTrue(scan_files({"a.py": real}))
        placeholder = 'api_key = "your-api-key-goes-here-123456789"\n'
        self.assertEqual(scan_files({"a.py": placeholder}), [])

    def test_personal_paths_are_flagged(self):
        win = "C:" + "\\Us" + "ers\\jsmith\\Desktop"
        mac = "/Us" + "ers/jsmith/Documents"
        lin = "/ho" + "me/jsmith/project"
        for text in (win, mac, lin):
            self.assertTrue(scan_files({"a.md": f"see {text}\n"}), text)

    def test_placeholder_paths_are_allowed(self):
        text = "use /ho" + "me/<name>/data or C:" + "\\Us" + "ers\\<name>\\data or /Us" + "ers/you/data\n"
        self.assertEqual(scan_files({"a.md": text}), [])

    def test_real_email_flagged_example_allowed(self):
        self.assertTrue(scan_files({"a.md": "mail person@" + "gmail.com\n"}))
        self.assertEqual(scan_files({"a.md": "mail person@example.com\n"}), [])

    def test_binary_files_are_not_text_scanned(self):
        self.assertEqual(scan_files({"logo.png": b"\x00\x01ghp_" + b"a" * 40}), [])


if __name__ == "__main__":
    unittest.main()
