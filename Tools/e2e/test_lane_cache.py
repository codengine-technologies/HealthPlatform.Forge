"""Tests de Tools/e2e/lane_cache.py — sur des dépôts git temporaires, voie simulée.

    python -m unittest Tools/e2e/test_lane_cache.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_cache  # noqa: E402


def sh(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def init_repo(path: Path, files: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    sh(path, 'git', 'init', '-q')
    sh(path, 'git', 'config', 'user.email', 't@t')
    sh(path, 'git', 'config', 'user.name', 't')
    for name, content in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(content, encoding='utf-8')
    sh(path, 'git', 'add', '.')
    sh(path, 'git', 'commit', '-q', '-m', 'init')


class LaneCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        init_repo(self.root / 'Api' / 'Mail', {'e2e/scenarios.yml': 'v1'})
        # Les sorties des voies sont ignorées par git, comme dans les vrais dépôts : sans cela, le
        # rapport écrit par la voie changerait l'empreinte, et aucune voie ne serait mémorisée.
        init_repo(self.root / 'Client' / 'Mobile',
                  {'src/app.ts': 'a', 'e2e/run.mjs': 'r', 'e2e/.gitignore': 'headless/out/\n'})
        init_repo(self.root / 'Client' / 'Angular',
                  {'front/app.ts': 'a', 'other/x.txt': 'x', 'front/e2e/mss-e2e/.gitignore': 'out/\n'})
        self.saved = (lane_cache.ROOT, lane_cache.CACHE, lane_cache.measure)
        lane_cache.ROOT = self.root
        lane_cache.CACHE = self.root / 'cache'
        self.out = self.root / 'out'
        self.calls: list[str] = []
        self.codes: list[int] = []
        lane_cache.measure = self.fake_measure

    def tearDown(self) -> None:
        lane_cache.ROOT, lane_cache.CACHE, lane_cache.measure = self.saved
        self.tmp.cleanup()

    def fake_measure(self, task, lane, label, command, cwd, env) -> int:
        """Une voie simulée : écrit son rapport et rend le prochain code programmé."""
        self.calls.append(label)
        if label.endswith('-reused'):
            return 0
        code = self.codes.pop(0) if self.codes else 0
        if code != 2:
            report = self.root / lane_cache.LANES[lane]['report']
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({'code': code, 'run': len(self.calls)}), encoding='utf-8')
        return code

    def key(self, lane: str) -> str:
        return lane_cache.fingerprint(lane)['key']

    # --- empreinte -----------------------------------------------------------------------------

    def test_fingerprint_changes_with_a_commit_a_diff_or_an_untracked_file(self) -> None:
        mobile = self.root / 'Client' / 'Mobile'
        k0 = self.key('mobile')
        (mobile / 'src/app.ts').write_text('b', encoding='utf-8')
        k1 = self.key('mobile')
        sh(mobile, 'git', 'commit', '-q', '-am', 'b')
        k2 = self.key('mobile')
        (mobile / 'src/new.ts').write_text('n', encoding='utf-8')
        k3 = self.key('mobile')
        self.assertEqual(4, len({k0, k1, k2, k3}))

    def test_angular_lane_ignores_the_mobile_app_but_not_the_mobile_e2e_orchestrator(self) -> None:
        mobile = self.root / 'Client' / 'Mobile'
        k0 = self.key('angular')
        (mobile / 'src/app.ts').write_text('changed', encoding='utf-8')
        self.assertEqual(k0, self.key('angular'))
        (mobile / 'e2e/run.mjs').write_text('changed', encoding='utf-8')
        self.assertNotEqual(k0, self.key('angular'))

    def test_angular_lane_covers_the_uncommitted_weda2_tree_only(self) -> None:
        angular = self.root / 'Client' / 'Angular'
        k0 = self.key('angular')
        (angular / 'other/x.txt').write_text('y', encoding='utf-8')
        self.assertEqual(k0, self.key('angular'))
        (angular / 'front/app.ts').write_text('b', encoding='utf-8')
        self.assertNotEqual(k0, self.key('angular'))

    # --- jouer ou réutiliser -------------------------------------------------------------------

    def test_a_green_lane_is_reused_while_its_code_is_unchanged(self) -> None:
        self.assertEqual(0, lane_cache.run('task-1', 'mobile', self.out))
        self.assertEqual(['mobile'], self.calls)

        self.assertEqual(0, lane_cache.run('task-1', 'mobile', self.out))
        self.assertEqual(['mobile', 'mobile-reused'], self.calls)
        self.assertTrue((self.out / 'mobile-report.json').is_file())
        state = json.loads((self.out / 'mobile-lane.json').read_text(encoding='utf-8'))
        self.assertEqual('reused', state['how'])

    def test_a_change_in_a_covered_repo_replays_the_lane(self) -> None:
        lane_cache.run('task-1', 'mobile', self.out)
        (self.root / 'Api' / 'Mail' / 'e2e/scenarios.yml').write_text('v2', encoding='utf-8')
        lane_cache.run('task-1', 'mobile', self.out)
        self.assertEqual(['mobile', 'mobile'], self.calls)

    def test_a_red_lane_is_never_remembered(self) -> None:
        self.codes = [1, 0]
        self.assertEqual(1, lane_cache.run('task-1', 'mobile', self.out))
        self.assertEqual(0, lane_cache.run('task-1', 'mobile', self.out))
        self.assertEqual(['mobile', 'mobile'], self.calls)

    def test_a_tooling_failure_is_replayed_once(self) -> None:
        self.codes = [2, 0]
        self.assertEqual(0, lane_cache.run('task-1', 'mobile', self.out))
        self.assertEqual(['mobile', 'mobile'], self.calls)

    def test_the_real_measure_reports_any_unknown_exit_code_as_tooling(self) -> None:
        lane_cache.measure = self.saved[2]
        conf = lane_cache.LANES['mobile']
        saved_cwd, saved_cmd = conf['cwd'], conf['command']
        try:
            conf['cwd'] = '.'
            code = lane_cache.measure('task-1', 'mobile', 'mobile', ['sh', '-c', 'exit 127'], '.', {})
        finally:
            conf['cwd'], conf['command'] = saved_cwd, saved_cmd
        self.assertEqual(2, code)

    def test_two_tooling_failures_block(self) -> None:
        self.codes = [2, 2]
        self.assertEqual(2, lane_cache.run('task-1', 'mobile', self.out))
        self.assertFalse((self.out / 'mobile-report.json').exists())
        self.assertIsNone(lane_cache.lookup('mobile', lane_cache.fingerprint('mobile')))

    def test_a_lane_whose_code_changed_while_it_ran_is_not_remembered(self) -> None:
        def changing_measure(task, lane, label, command, cwd, env) -> int:
            code = self.fake_measure(task, lane, label, command, cwd, env)
            (self.root / 'Client' / 'Mobile' / 'src/app.ts').write_text('edited meanwhile', encoding='utf-8')
            return code

        lane_cache.measure = changing_measure
        self.assertEqual(0, lane_cache.run('task-1', 'mobile', self.out))
        self.assertIsNone(lane_cache.lookup('mobile', lane_cache.fingerprint('mobile')))

    def test_the_report_of_a_previous_run_never_stands_for_this_one(self) -> None:
        self.out.mkdir()
        (self.out / 'mobile-report.json').write_text('stale', encoding='utf-8')
        self.codes = [2, 2]
        lane_cache.run('task-1', 'mobile', self.out)
        self.assertFalse((self.out / 'mobile-report.json').exists())


if __name__ == '__main__':
    unittest.main()
