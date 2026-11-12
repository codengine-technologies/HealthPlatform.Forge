"""Tests de Tools/green/green.py — sur des dépôts git temporaires.

    python -m unittest Tools/green/test_green.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import green  # noqa: E402


def sh(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    sh(path, 'git', 'init', '-q')
    sh(path, 'git', 'config', 'user.email', 't@t')
    sh(path, 'git', 'config', 'user.name', 't')
    (path / 'a.cs').write_text('class A {}', encoding='utf-8')
    sh(path, 'git', 'add', '.')
    sh(path, 'git', 'commit', '-q', '-m', 'init')


class GreenMarkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'ws'
        self.state = Path(self.tmp.name) / 'state'
        init_repo(self.root / 'Api' / 'Mail')
        init_repo(self.root / 'Client' / 'Angular')
        (self.root / 'Client' / 'Angular' / 'front').mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def check(self, repo: str = 'api-mail') -> int:
        return green.check('task-1', repo, root=self.root, state=self.state)

    def test_no_marker_is_to_replay(self) -> None:
        self.assertEqual(1, self.check())

    def test_same_code_after_mark_is_green(self) -> None:
        green.mark('task-1', 'api-mail', 'develop', root=self.root, state=self.state)
        self.assertEqual(0, self.check())

    def test_a_new_commit_is_to_replay(self) -> None:
        repo = self.root / 'Api' / 'Mail'
        green.mark('task-1', 'api-mail', 'develop', root=self.root, state=self.state)
        (repo / 'a.cs').write_text('class A { int x; }', encoding='utf-8')
        sh(repo, 'git', 'commit', '-qam', 'fix')
        self.assertEqual(1, self.check())

    def test_an_uncommitted_change_is_to_replay(self) -> None:
        green.mark('task-1', 'api-mail', 'develop', root=self.root, state=self.state)
        (self.root / 'Api' / 'Mail' / 'a.cs').write_text('class A { int y; }', encoding='utf-8')
        self.assertEqual(1, self.check())

    def test_an_untracked_file_is_to_replay(self) -> None:
        green.mark('task-1', 'api-mail', 'develop', root=self.root, state=self.state)
        (self.root / 'Api' / 'Mail' / 'b.cs').write_text('class B {}', encoding='utf-8')
        self.assertEqual(1, self.check())

    def test_code_only_repo_is_fingerprinted_by_its_uncommitted_tree(self) -> None:
        front = self.root / 'Client' / 'Angular' / 'front'
        (front / 'x.ts').write_text('export const x = 1', encoding='utf-8')
        green.mark('task-1', 'client-angular', 'develop', root=self.root, state=self.state)
        self.assertEqual(0, self.check('client-angular'))
        (front / 'x.ts').write_text('export const x = 2', encoding='utf-8')
        self.assertEqual(1, self.check('client-angular'))

    def test_a_change_outside_the_scope_does_not_invalidate(self) -> None:
        green.mark('task-1', 'client-angular', 'develop', root=self.root, state=self.state)
        (self.root / 'Client' / 'Angular' / 'notes.md').write_text('hors front', encoding='utf-8')
        self.assertEqual(0, self.check('client-angular'))

    def test_forget_removes_the_markers(self) -> None:
        green.mark('task-1', 'api-mail', 'develop', root=self.root, state=self.state)
        green.forget('task-1', state=self.state)
        self.assertEqual(1, self.check())

    def test_a_broken_repo_never_says_green(self) -> None:
        green.mark('task-1', 'api-mail', 'develop', root=self.root, state=self.state)
        self.assertEqual(1, green.check('task-1', 'api-mail', root=Path(self.tmp.name) / 'absent', state=self.state))

    def test_mark_never_fails(self) -> None:
        self.assertEqual(0, green.mark('task-1', 'api-mail', 'develop', root=Path(self.tmp.name) / 'absent', state=self.state))


if __name__ == '__main__':
    unittest.main()
