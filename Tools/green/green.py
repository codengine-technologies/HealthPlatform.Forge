#!/usr/bin/env python
"""Marqueur vert partagé : ne pas rejouer build + tests sur un code déjà prouvé vert.

Une étape de la chaîne qui vient de jouer le build ET la suite de tests complète d'un dépôt, au
vert, **marque** son empreinte (HEAD, diff de l'arbre de travail, contenu des fichiers non suivis
— la même que celle des voies e2e, `Tools/e2e/lane_cache.py`). Une étape suivante qui devrait
rejouer la même validation **vérifie** d'abord : même empreinte → la preuve existe pour ce code
exact, elle n'est pas rejouée ; empreinte différente, marqueur absent ou outil en panne → elle
rejoue (jamais l'inverse : le doute coûte un build, pas une régression).

    python Tools/green/green.py mark  --task task-449 --repo api-mail --by develop
    python Tools/green/green.py check --task task-449 --repo api-mail
    python Tools/green/green.py forget --task task-449

Codes de `check` : 0 vert (même code, déjà validé), 1 à rejouer (avec la raison sur stdout).
`mark` et `forget` sortent toujours en 0 (best-effort, comme le timing). Voir CLAUDE.md,
« Revue anticipée et marqueur vert ».
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'e2e'))
from lane_cache import repo_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'metrics' / '.state' / 'green'

# Les dépôts validés par la chaîne : chemin, et sous-dossier borné (client-angular : seul front/
# est construit et testé par la forge).
REPOS = {
    'api-mail': ('Api/Mail', None),
    'client-blazor': ('Client/Blazor', None),
    'client-angular': ('Client/Angular', 'front'),
    'client-mobile': ('Client/Mobile', None),
    'dtos-mss': ('Dtos', None),
    'sdk': ('Sdk', None),
    'interop-cda': ('interop', None),
}


def state_of(repo: str, root: Path) -> dict:
    path, scope = REPOS[repo]
    return repo_state(root / path, scope)


def marker(task: str, repo: str, state: Path) -> Path:
    return state / task / f'{repo}.json'


def mark(task: str, repo: str, by: str, root: Path = ROOT, state: Path = STATE) -> int:
    try:
        target = marker(task, repo, state)
        target.parent.mkdir(parents=True, exist_ok=True)
        record = {
            'repo': repo,
            'state': state_of(repo, root),
            'by': by,
            'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        }
        target.write_text(json.dumps(record, indent=2), encoding='utf-8')
        print(f"vert marqué : {repo} {record['state']['head'][:8]}"
              f"{' + arbre modifié' if record['state']['dirty'] else ''} ({by})")
    except Exception as error:  # best-effort : un marqueur manquant fait seulement rejouer
        print(f'marqueur non écrit ({error}) : la validation sera rejouée')
    return 0


def check(task: str, repo: str, root: Path = ROOT, state: Path = STATE) -> int:
    try:
        target = marker(task, repo, state)
        if not target.is_file():
            print(f'à rejouer : aucun vert marqué pour {repo}')
            return 1
        record = json.loads(target.read_text(encoding='utf-8'))
        current = state_of(repo, root)
        if record.get('state') != current:
            print(f"à rejouer : {repo} a changé depuis le vert de /{record.get('by')} "
                  f"({record['state']['head'][:8]} → {current['head'][:8]})")
            return 1
        print(f"vert : {repo} {current['head'][:8]} validé par /{record.get('by')} à {record.get('at')}")
        return 0
    except Exception as error:
        print(f'à rejouer : marqueur illisible ({error})')
        return 1


def forget(task: str, state: Path = STATE) -> int:
    try:
        for file in (state / task).glob('*.json'):
            file.unlink()
    except Exception:
        pass
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('mark', 'check'):
        p = sub.add_parser(name)
        p.add_argument('--task', required=True)
        p.add_argument('--repo', required=True, choices=sorted(REPOS))
        if name == 'mark':
            p.add_argument('--by', required=True, help="l'étape qui vient de valider (develop, sonar, lint-mobile…)")
    p_forget = sub.add_parser('forget')
    p_forget.add_argument('--task', required=True)
    args = parser.parse_args()
    if args.cmd == 'mark':
        return mark(args.task, args.repo, args.by)
    if args.cmd == 'check':
        return check(args.task, args.repo)
    return forget(args.task)


if __name__ == '__main__':
    sys.exit(main())
