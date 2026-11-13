"""Impact d'une task sur api-mcp, le serveur MCP de la messagerie.

api-mcp lit api-mail en HTTP, par des contrats locaux minimaux (tolerant reader). Il ne
dépend d'aucun paquet NuGet : un changement d'api-mail ou de dtos-mss ne le casse pas à la
compilation. Il peut pourtant lui faire perdre un champ, une route ou un code d'erreur. Cet
outil déduit la surface consommée **du code d'api-mcp lui-même**, puis la compare à ce que la
branche courante change dans api-mail et dtos-mss, par rapport à origin/develop.

    python Tools/contracts/mcp_impact.py surface    # ce qu'api-mcp consomme
    python Tools/contracts/mcp_impact.py check      # 0 : aucun impact ; 1 : impact (raisons listées) ; 2 : erreur

Tests : python -m unittest Tools/contracts/test_mcp_impact.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 'origin/develop'

MCP_API_MAIL = Path('Api/Mcp/src/HealthPlatform.Api.Mcp/ApiMail')

# Chaque contrat local d'api-mcp et la classe de dtos-mss qu'il lit. Un contrat absent de cette
# table fait échouer l'outil : un nouveau contrat dans api-mcp doit y être déclaré.
RECORD_TO_DTO = {
    'ApiMailbox': 'MailboxDto',
    'ApiFolder': 'FolderDto',
    'ApiAddress': 'MailAddressDto',
    'ApiMailHeader': 'MailDto',
    'ApiSearchRequest': 'SearchRequestDto',
    'ApiSearchResponse': 'SearchResponseDto',
    'ApiSearchHit': 'SearchHitDto',
}

# Énumérations qu'api-mcp décode par leur rang (api-mail les sérialise en nombres).
ENUMS_BY_RANK = ('FolderType', 'FolderSource')

# Routes construites par ApiMailRoutes.Folder() et ApiMailRoutes.Headers() : les deux méthodes
# doivent exister, sinon cette déclaration est périmée.
BUILT_ROUTES = {
    'Folder': ('GET', 'api/v1/mail/folders/{}'),
    'Headers': ('GET', 'api/v1/mail/folders/{}/emails/{}'),
}

# Ce qu'api-mcp envoie à api-mail : la disparition de l'un de ces jetons le prive d'un réglage.
SENT_TOKENS = ('Client-Email', 'Client-Session-Id', 'X-Correlation-Id', 'proxy_session_id', 'includeThreadCounts')

# Toute modification d'une ligne qui porte l'un de ces jetons change la forme du JSON lu.
JSON_SHAPE_TOKENS = ('PropertyNamingPolicy', 'JsonStringEnumConverter', 'DefaultIgnoreCondition', 'JsonNamingPolicy')

REPOS = {'api-mail': Path('Api/Mail'), 'dtos-mss': Path('Dtos')}


@dataclass
class Surface:
    fields: dict[str, set[str]]                 # classe dtos-mss -> champs lus (minuscules)
    routes: set[tuple[str, str]]                # (verbe, gabarit normalisé)
    error_codes: set[str]
    enums: tuple[str, ...] = ENUMS_BY_RANK
    sent_tokens: tuple[str, ...] = SENT_TOKENS


@dataclass
class Report:
    reasons: list[str] = field(default_factory=list)


# --- Lecture d'api-mcp -------------------------------------------------------------------------

def split_top_level(text: str) -> list[str]:
    parts, depth, current = [], 0, []
    for ch in text:
        if ch in '<([':
            depth += 1
        elif ch in '>)]':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if ''.join(current).strip():
        parts.append(''.join(current))
    return parts


def parse_records(source: str) -> dict[str, list[str]]:
    """Les records positionnels du fichier, avec le nom de leurs paramètres."""
    records = {}
    for match in re.finditer(r'record\s+(\w+)\s*\((.*?)\);', source, re.S):
        names = []
        for part in split_top_level(match.group(2)):
            declaration = part.split('=')[0].strip()
            if declaration:
                names.append(declaration.split()[-1])
        records[match.group(1)] = names
    return records


def parse_string_constants(source: str, owner: str) -> dict[str, str]:
    """Les constantes chaîne d'une classe statique."""
    block = re.search(r'class\s+' + owner + r'\b.*?\{(.*?)\n\}', source, re.S)
    if not block:
        return {}
    return dict(re.findall(r'const\s+string\s+(\w+)\s*=\s*"([^"]*)"', block.group(1)))


def normalize_route(route: str) -> str:
    route = route.split('?')[0].strip('/').lower()
    route = re.sub(r'\{[^}]*\}', '{}', route)
    return route.replace('api/v{}', 'api/v1')


def derive_surface(root: Path = ROOT) -> Surface:
    contracts = (root / MCP_API_MAIL / 'ApiMailContracts.cs').read_text(encoding='utf-8')
    routes_source = (root / MCP_API_MAIL / 'ApiMailRoutes.cs').read_text(encoding='utf-8')

    fields: dict[str, set[str]] = {}
    for record, params in parse_records(contracts).items():
        if record not in RECORD_TO_DTO:
            raise LookupError(f'contrat api-mcp « {record} » sans classe dtos-mss déclarée dans RECORD_TO_DTO')
        fields.setdefault(RECORD_TO_DTO[record], set()).update(p.lower() for p in params)

    constants = parse_string_constants(routes_source, 'ApiMailRoutes')
    routes = {('GET', normalize_route(constants['Mailboxes'])),
              ('GET', normalize_route(constants['Folders'])),
              ('POST', normalize_route(constants['Search']))}
    for method, (verb, template) in BUILT_ROUTES.items():
        if not re.search(r'static\s+string\s+' + method + r'\s*\(', routes_source):
            raise LookupError(f'ApiMailRoutes.{method}() introuvable : BUILT_ROUTES est périmé')
        routes.add((verb, template))

    codes = set(parse_string_constants(contracts, 'ApiMailErrorCodes').values())
    return Surface(fields=fields, routes=routes, error_codes=codes)


# --- Lecture d'api-mail et de dtos-mss --------------------------------------------------------

def class_members(source: str) -> dict[str, dict[str, str]]:
    """Classe -> {champ JSON (minuscules) -> type}, pour les classes et records d'un fichier C#."""
    result: dict[str, dict[str, str]] = {}
    declarations = list(re.finditer(r'\b(?:class|record)\s+(\w+)', source))
    for i, declaration in enumerate(declarations):
        end = declarations[i + 1].start() if i + 1 < len(declarations) else len(source)
        body = source[declaration.end():end]
        members: dict[str, str] = {}
        for prop in re.finditer(
                r'(?:\[JsonPropertyName\("(?P<json>[^"]+)"\)\]\s*)?public\s+(?P<type>[\w<>\[\]?.,\s]+?)\s+(?P<name>\w+)\s*\{\s*get',
                body):
            name = (prop.group('json') or prop.group('name')).lower()
            members[name] = re.sub(r'\s+', '', prop.group('type'))
        result.setdefault(declaration.group(1), {}).update(members)
    return result


def enum_members(source: str) -> dict[str, list[str]]:
    return {m.group(1): [x.split('=')[0].strip() for x in re.sub(r'//.*', '', m.group(2)).split(',') if x.strip()]
            for m in re.finditer(r'\benum\s+(\w+)\s*\{([^}]*)\}', source)}


def controller_routes(source: str) -> set[tuple[str, str]]:
    """Les routes (verbe, gabarit normalisé) déclarées par les contrôleurs d'un fichier."""
    routes = set()
    for cls in re.finditer(r'\[Route\("([^"]+)"\)\][^{]*?class\s+(\w+)Controller\b(.*?)(?=\[Route\(|\Z)', source, re.S):
        prefix = cls.group(1).replace('[controller]', cls.group(2))
        for action in re.finditer(r'\[Http(Get|Post|Put|Delete|Patch)(?:\("([^"]*)"\))?\]', cls.group(3)):
            template = prefix + ('/' + action.group(2) if action.group(2) else '')
            routes.add((action.group(1).upper(), normalize_route(template)))
    return routes


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, encoding='utf-8')
    if done.returncode != 0:
        raise RuntimeError(f'git {" ".join(args)} ({repo}) : {done.stderr.strip()}')
    return done.stdout


def changed_files(repo: Path) -> list[str]:
    """Fichiers .cs modifiés par rapport à origin/develop, travail en cours et fichiers non suivis compris."""
    tracked = git(repo, 'diff', '--name-only', BASE, '--', '*.cs').split()
    untracked = git(repo, 'ls-files', '--others', '--exclude-standard', '--', '*.cs').split()
    return sorted(set(tracked) | set(untracked))


def old_content(repo: Path, path: str) -> str:
    try:
        return git(repo, 'show', f'{BASE}:{path}')
    except RuntimeError:
        return ''


def new_content(repo: Path, path: str) -> str:
    file = repo / path
    return file.read_text(encoding='utf-8-sig') if file.exists() else ''


# --- Comparaison --------------------------------------------------------------------------------

def compare(surface: Surface, old: dict[str, str], new: dict[str, str]) -> Report:
    """Compare l'avant et l'après des fichiers modifiés d'un dépôt ({chemin: contenu})."""
    report = Report()
    old_all, new_all = '\n'.join(old.values()), '\n'.join(new.values())

    old_members, new_members = class_members(old_all), class_members(new_all)
    for dto, read in sorted(surface.fields.items()):
        if dto not in old_members:
            continue
        for name in sorted(read):
            before, after = old_members[dto].get(name), new_members.get(dto, {}).get(name)
            if before is None:
                continue
            if after is None:
                report.reasons.append(f'{dto}.{name} disparaît (lu par api-mcp)')
            elif after != before:
                report.reasons.append(f'{dto}.{name} change de type : {before} -> {after} (lu par api-mcp)')

    old_enums, new_enums = enum_members(old_all), enum_members(new_all)
    for enum in surface.enums:
        if enum in old_enums and old_enums[enum] != new_enums.get(enum):
            report.reasons.append(f'énumération {enum} modifiée : api-mcp la décode par rang')

    old_routes, new_routes = controller_routes(old_all), controller_routes(new_all)
    for route in sorted(surface.routes & old_routes - new_routes):
        report.reasons.append(f'route {route[0]} {route[1]} disparaît (appelée par api-mcp)')

    for path in sorted(set(old) | set(new)):
        removed = token_lines(old.get(path, ''), new.get(path, ''))
        for token in [*surface.error_codes, *surface.sent_tokens]:
            if any(token in line for line in removed[0]) and not any(token in line for line in removed[1]):
                report.reasons.append(f'« {token} » retiré de {path} (utilisé par api-mcp)')
        for token in JSON_SHAPE_TOKENS:
            if any(token in line for line in removed[0] + removed[1]):
                report.reasons.append(f'forme du JSON modifiée dans {path} (« {token} »)')
                break
    return report


def token_lines(old: str, new: str) -> tuple[list[str], list[str]]:
    """Lignes présentes seulement avant, puis seulement après (multiensemble)."""
    old_lines, new_lines = old.splitlines(), new.splitlines()
    remaining = list(new_lines)
    only_old = []
    for line in old_lines:
        if line in remaining:
            remaining.remove(line)
        else:
            only_old.append(line)
    return only_old, remaining


def base_sources(repo: Path, prefix: str) -> str:
    """Les sources .cs d'un dossier du dépôt, telles qu'elles sont sur origin/develop."""
    paths = [p for p in git(repo, 'ls-tree', '-r', '--name-only', BASE, '--', prefix).split() if p.endswith('.cs')]
    return chr(10).join(old_content(repo, p) for p in paths)


def missing_from_base(surface: Surface, dtos: str, controllers: str) -> tuple[list[str], list[str]]:
    """
    Ce que la surface déclare et que origin/develop ne contient pas, en (erreurs, avertissements).
    Erreur : une classe, une énumération, une route ou un code introuvable. Un analyseur ou une
    déclaration est alors périmé, et « aucun impact » ne voudrait rien dire.
    Avertissement : un champ isolé absent. api-mcp le lit en lecteur tolérant (par exemple un champ
    ajouté par une task pas encore mergée) : son absence ne casse rien.
    """
    errors, warnings = [], []
    members = class_members(dtos)
    for dto, read in sorted(surface.fields.items()):
        if dto not in members:
            errors.append(f'classe {dto}')
            continue
        warnings += [f'champ {dto}.{name}' for name in sorted(read - set(members[dto]))]
    enums = enum_members(dtos)
    errors += [f'énumération {e}' for e in surface.enums if e not in enums]
    routes = controller_routes(controllers)
    errors += [f'route {v} {r}' for v, r in sorted(surface.routes - routes)]
    errors += [f'code {c}' for c in sorted(surface.error_codes) if f'"{c}"' not in dtos]
    return errors, warnings


def check(root: Path = ROOT) -> int:
    try:
        surface = derive_surface(root)
        errors, warnings = missing_from_base(surface,
                                             base_sources(root / REPOS['dtos-mss'], '.'),
                                             base_sources(root / REPOS['api-mail'], 'src/Api/Controllers'))
        if errors:
            print('mcp_impact : erreur — surface introuvable sur origin/develop (analyseur ou déclaration périmé) :')
            for item in errors:
                print(f'  - {item}')
            return 2
        for item in warnings:
            print(f'mcp_impact : avertissement — {item} absent de origin/develop (lecture tolérante, sans effet)')
        reasons = []
        for name, repo_path in REPOS.items():
            repo = root / repo_path
            files = changed_files(repo)
            report = compare(surface,
                             {f: old_content(repo, f) for f in files},
                             {f: new_content(repo, f) for f in files})
            reasons += [f'{name} : {reason}' for reason in report.reasons]
    except (LookupError, RuntimeError, OSError) as error:
        print(f'mcp_impact : erreur — {error}')
        return 2

    if not reasons:
        print('api-mcp : aucun impact.')
        return 0
    print('api-mcp : IMPACT — la task doit adapter api-mcp (contrats locaux, simulations, tests) :')
    for reason in reasons:
        print(f'  - {reason}')
    return 1


def show_surface(root: Path = ROOT) -> int:
    surface = derive_surface(root)
    print('Champs lus :')
    for dto, read in sorted(surface.fields.items()):
        print(f'  {dto} : {", ".join(sorted(read))}')
    print('Routes appelées :')
    for verb, route in sorted(surface.routes):
        print(f'  {verb} {route}')
    print(f'Codes d\'erreur traduits : {", ".join(sorted(surface.error_codes))}')
    print(f'Énumérations décodées par rang : {", ".join(surface.enums)}')
    print(f'En-têtes, cookie et paramètres envoyés : {", ".join(surface.sent_tokens)}')
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'check':
        return check()
    if command == 'surface':
        return show_surface()
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
