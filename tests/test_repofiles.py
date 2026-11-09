"""Tests for the shared list of repository files, including during a merge with conflicts."""
import shutil
import subprocess
import unittest

from support import TempDirTestCase
import repofiles


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                   cwd=cwd, check=True, capture_output=True)


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class RepoFilesTests(TempDirTestCase):
    def test_a_conflicted_file_is_listed_once(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        (repo / "INDEX.md").write_text("start\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "start")
        git(repo, "checkout", "-q", "-b", "other")
        (repo / "INDEX.md").write_text("other side\n", encoding="utf-8")
        git(repo, "commit", "-q", "-am", "other")
        git(repo, "checkout", "-q", "main")
        (repo / "INDEX.md").write_text("main side\n", encoding="utf-8")
        git(repo, "commit", "-q", "-am", "main")
        result = subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                                 "merge", "other"], cwd=repo, capture_output=True)
        self.assertNotEqual(result.returncode, 0, "the merge should stop with a conflict")
        self.assertEqual(repofiles.repo_files(repo), ["INDEX.md"])
