#!/usr/bin/env python
"""Voie e2e incrémentale : ne rejouer une voie que si le code qu'elle couvre a changé.

Une voie (mobile, angular) est **réutilisée** quand son empreinte — l'état exact des dépôts
qu'elle couvre — est celle d'un passage vert déjà enregistré : la preuve existe pour ce code,
la rejouer n'apprend rien. Sinon elle est jouée, son rapport copié aussitôt (la voie Angular
vide le dossier de sortie mobile), et un code 2 (outillage) est rejoué **une fois**.

Empreinte d'un dépôt : son HEAD, le diff de l'arbre de travail et le contenu des fichiers non
suivis (hors .gitignore). C'est ce qui couvre `client-angular`, en code-only et jamais commité.

    python Tools/e2e/lane_cache.py run --task task-373 --lane mobile --out "$TEMP/forge-e2e/task-373"
    python Tools/e2e/lane_cache.py fingerprint --lane angular
    python Tools/e2e/lane_cache.py status
    python Tools/e2e/lane_cache.py forget [--lane mobile]

Codes de sortie de `run` : ceux de la voie (0 vert, 1 rouge, 2 outillage). Une voie réutilisée
sort en 0. Voir agents/e2e.md, Step 1.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'metrics' / '.state' / 'e2e-green'

# Une voie, les dépôts qu'elle couvre, et comment la jouer. `scope` borne l'empreinte à un
# sous-dossier : la voie Angular monte son backend par l'orchestrateur mobile (e2e/), pas par
# l'application mobile.
LANES = {
    'mobile': {
        'repos': [('api-mail', 'Api/Mail', None), ('client-mobile', 'Client/Mobile', None)],
        'repo': 'client-mobile',
        'cwd': 'Client/Mobile',
        'command': ['npm', 'run', 'e2e:headless'],
        'report': 'Client/Mobile/e2e/headless/out/report.json',
        'env': {},
    },
    'angular': {
        'repos': [
            ('api-mail', 'Api/Mail', None),
            ('client-angular', 'Client/Angular', 'front'),
            ('client-mobile-e2e', 'Client/Mobile', 'e2e'),
        ],
        'repo': 'client-angular',
        'cwd': 'Client/Angular/front',
        'command': ['npm', 'run', 'e2e:mss'],
        'report': 'Client/Angular/front/e2e/mss-e2e/out/report.json',
        'env': {'NX_PLUGIN_NO_TIMEOUTS': 'true'},
    },
}


def git(path: Path, *args: str) -> bytes:
    return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True).stdout


def repo_state(path: Path, scope: str | None) -> dict:
    """HEAD, et l'empreinte de ce qui n'est pas commité, bornée à `scope`."""
    spec = ['--', scope] if scope else []
    head = git(path, 'rev-parse', 'HEAD').decode().strip()
    digest = hashlib.sha256()
    digest.update(git(path, 'diff', 'HEAD', '--binary', *spec))
    untracked = git(path, 'ls-files', '--others', '--exclude-standard', '-z', *spec).split(b'\0')
    for name in sorted(n for n in untracked if n):
        digest.update(name + b'\0')
        file = path / name.decode('utf-8', 'surrogateescape')
        if file.is_file():
            digest.update(hashlib.sha256(file.read_bytes()).digest())
    dirty = digest.hexdigest()
    clean = hashlib.sha256().hexdigest()
    return {'head': head, 'dirty': None if dirty == clean else dirty[:16]}


def fingerprint(lane: str, root: Path | None = None) -> dict:
    """L'état des dépôts couverts par la voie, et son condensé."""
    root = root or ROOT
    repos = {name: repo_state(root / path, scope) for name, path, scope in LANES[lane]['repos']}
    key = hashlib.sha256(json.dumps(repos, sort_keys=True).encode()).hexdigest()[:20]
    return {'lane': lane, 'key': key, 'repos': repos}


def record_path(lane: str, cache: Path | None = None) -> Path:
    return (cache or CACHE) / f'{lane}.json'


def lookup(lane: str, fp: dict, cache: Path | None = None) -> dict | None:
    """Le dernier passage vert de la voie, s'il a la même empreinte et que son rapport existe."""
    cache = cache or CACHE
    path = record_path(lane, cache)
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding='utf-8'))
    report = cache / record.get('report', '')
    if record.get('key') != fp['key'] or not report.is_file():
        return None
    return record


def remember(lane: str, fp: dict, report: Path, task: str, cache: Path | None = None) -> None:
    """Enregistre un passage vert : son empreinte et une copie de son rapport."""
    cache = cache or CACHE
    cache.mkdir(parents=True, exist_ok=True)
    kept = f'{lane}-{fp["key"]}.json'
    shutil.copyfile(report, cache / kept)
    for old in cache.glob(f'{lane}-*.json'):
        if old.name != kept:
            old.unlink()
    record = {**fp, 'task': task, 'report': kept,
              'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    record_path(lane, cache).write_text(json.dumps(record, indent=2), encoding='utf-8')


def git_bash() -> str:
    """Le bash de Git, jamais celui de WSL.

    Sous Windows, un processus lancé sans chemin cherche dans System32 AVANT le PATH : `bash` y est
    le bash de WSL, qui lit les scripts du poste avec leurs fins de ligne CRLF et des chemins
    /mnt/d/… (constaté au premier essai réel : « $'\\r': command not found », code 2).
    """
    candidates = [shutil.which('bash'), r'C:\Program Files\Git\bin\bash.exe',
                  r'C:\Program Files\Git\usr\bin\bash.exe']
    for candidate in candidates:
        lowered = (candidate or '').lower()
        if candidate and os.path.isfile(candidate) and 'system32' not in lowered and 'windowsapps' not in lowered:
            return candidate
    return 'bash'


def measure(task: str, lane: str, label: str, command: list[str], cwd: str, env: dict) -> int:
    """Une commande enveloppée par Tools/timing/measure.sh (sortie et code inchangés)."""
    conf = LANES[lane]
    # Chemin RELATIF, résolu depuis ROOT : bash (Git Bash) mutile un chemin Windows absolu à
    # antislashs (« D:TechWatch… », code 127, voie jamais lancée — constaté au premier essai réel).
    args = [git_bash(), 'Tools/timing/measure.sh', '--task', task, '--step', 'e2e',
            '--repo', conf['repo'], '--cwd', cwd, '--kind', 'e2e', '--label', label, '--', *command]
    code = subprocess.run(args, cwd=ROOT, env={**os.environ, **env}).returncode
    # Toute sortie autre que 0 (vert) ou 1 (rouge) est une panne d'outillage : la porte ne connaît que
    # 0, 1 et 2, et un 127 (commande introuvable) ne prouve rien.
    return code if code in (0, 1) else 2


def play(task: str, lane: str, out: Path, command: list[str] | None = None) -> int:
    """Joue la voie (au plus deux fois sur un code 2) et copie son rapport dans `out`."""
    conf = LANES[lane]
    report = ROOT / conf['report']
    code = 2
    for attempt in (1, 2):
        report.unlink(missing_ok=True)
        code = measure(task, lane, lane, command or conf['command'], conf['cwd'], conf['env'])
        if report.is_file():
            shutil.copyfile(report, out / f'{lane}-report.json')
        if code != 2:
            break
        if attempt == 1:
            print(f'[lane-cache] voie {lane} : code 2 (outillage), rejouée une fois', flush=True)
    return code


def run(task: str, lane: str, out: Path, command: list[str] | None = None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{lane}-report.json').unlink(missing_ok=True)
    before = fingerprint(lane)
    known = lookup(lane, before)
    if known is not None:
        shutil.copyfile(CACHE / known['report'], out / f'{lane}-report.json')
        measure(task, lane, f'{lane}-reused', ['true'], '.', {})
        print(f'[lane-cache] voie {lane} RÉUTILISÉE : verte sur la même empreinte {before["key"]} '
              f'({known["task"]}, {known["at"]})', flush=True)
        write_state(out, lane, before, 'reused', known)
        return 0

    code = play(task, lane, out, command)
    after = fingerprint(lane)
    if code == 0 and after['key'] == before['key'] and (out / f'{lane}-report.json').is_file():
        remember(lane, before, out / f'{lane}-report.json', task)
    elif code == 0:
        print(f'[lane-cache] voie {lane} verte, NON mémorisée : le code a changé pendant la voie', flush=True)
    write_state(out, lane, before, 'played', {'code': code})
    return code


def write_state(out: Path, lane: str, fp: dict, how: str, detail: dict) -> None:
    """Ce que le ## E2E log cite : la voie, jouée ou réutilisée, et les HEAD des dépôts couverts."""
    state = {'lane': lane, 'how': how, 'key': fp['key'], 'repos': fp['repos'], **detail}
    (out / f'{lane}-lane.json').write_text(json.dumps(state, indent=2), encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_run = sub.add_parser('run')
    p_run.add_argument('--task', required=True)
    p_run.add_argument('--lane', required=True, choices=LANES)
    p_run.add_argument('--out', required=True, type=Path)
    p_fp = sub.add_parser('fingerprint')
    p_fp.add_argument('--lane', required=True, choices=LANES)
    sub.add_parser('status')
    p_forget = sub.add_parser('forget')
    p_forget.add_argument('--lane', choices=LANES)
    args = parser.parse_args()

    if args.cmd == 'run':
        return run(args.task, args.lane, args.out)
    if args.cmd == 'fingerprint':
        print(json.dumps(fingerprint(args.lane), indent=2))
        return 0
    if args.cmd == 'status':
        for lane in LANES:
            path = record_path(lane)
            known = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
            current = fingerprint(lane)['key']
            if known is None:
                print(f'{lane}: aucun passage vert mémorisé (empreinte actuelle {current})')
            else:
                same = 'IDENTIQUE — sera réutilisée' if known['key'] == current else 'différente — sera rejouée'
                print(f'{lane}: vert {known["task"]} {known["at"]} ; empreinte {same}')
        return 0
    for lane in [args.lane] if args.lane else LANES:
        record_path(lane).unlink(missing_ok=True)
        for old in CACHE.glob(f'{lane}-*.json'):
            old.unlink()
    return 0


if __name__ == '__main__':
    sys.exit(main())
