"""Impact d'une task sur les consommateurs du contrat d'api-mail : api-mcp, client-mobile, client-angular.

Aucun de ces trois consommateurs ne dépend d'un paquet NuGet d'api-mail ou de dtos-mss :
- api-mcp lit api-mail en HTTP par des contrats locaux minimaux (records C#) ;
- client-mobile et client-angular recopient à la main les contrats dans leurs modèles TypeScript.
Un changement d'api-mail ou de dtos-mss ne les casse donc pas à la compilation. Il peut pourtant leur
faire perdre un champ, une route, une valeur d'énumération ou un code d'erreur : l'écran affiche alors un
vide, sans rouge. Cet outil déduit la surface lue **du code de chaque consommateur**, puis la compare à ce
que la branche courante change dans api-mail et dtos-mss, par rapport à origin/develop.

    python Tools/contracts/contract_impact.py check                         # verdict par consommateur
    python Tools/contracts/contract_impact.py surface --consumer client-mobile

Codes de sortie de check : 0 aucun consommateur touché ; 1 au moins un impact (raisons listées) ;
2 erreur d'outil (surface introuvable sur origin/develop : un analyseur ou une déclaration est périmé,
jamais un feu vert silencieux).

Tests : python -m unittest Tools/contracts/test_contract_impact.py Tools/contracts/test_mcp_impact.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
BASE = 'origin/develop'
BACKSLASH = chr(92)

REPOS = {'api-mail': Path('Api/Mail'), 'dtos-mss': Path('Dtos')}

# Toute modification d'une ligne qui porte l'un de ces jetons change la forme du JSON lu par TOUS les
# consommateurs.
JSON_SHAPE_TOKENS = ('PropertyNamingPolicy', 'JsonStringEnumConverter', 'DefaultIgnoreCondition', 'JsonNamingPolicy')


@dataclass
class Surface:
    fields: dict[str, set[str]]                 # classe dtos-mss -> champs lus (minuscules)
    routes: set[tuple[str, str]]                # (verbe, gabarit normalisé) ; verbe « * » s'il n'est pas lisible
    error_codes: set[str] = field(default_factory=set)
    enums: tuple[str, ...] = ()                 # énumérations décodées par rang
    sent_tokens: tuple[str, ...] = ()
    readers: dict[str, str] = field(default_factory=dict)   # classe -> fichier du consommateur qui la lit
    local_models: dict[str, str] = field(default_factory=dict)  # modèle de vue local -> fichier
    outside_dtos: dict[str, str] = field(default_factory=dict)  # *Dto sans classe dtos-mss -> raison
    codes_must_exist: bool = True               # api-mcp : un code introuvable est une erreur d'outil


@dataclass
class Report:
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Consumer:
    name: str
    git_mode: str                               # « pushable » ou « code-only »
    derive: Callable[[Path], Surface]
    source: Path                                # dossier dont la présence est exigée


# --- Lecture d'api-mcp -------------------------------------------------------------------------

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


def derive_mcp_surface(root: Path = ROOT) -> Surface:
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
    return Surface(fields=fields, routes=routes, error_codes=codes, enums=ENUMS_BY_RANK,
                   sent_tokens=SENT_TOKENS, readers={dto: 'api-mcp' for dto in fields})


# --- Lecture des clients TypeScript -------------------------------------------------------------

# Modèles client dont le nom diffère de leur classe dtos-mss. Un modèle en *Dto qui n'est ni ici, ni le
# nom d'une classe de dtos-mss, ni dans CLIENT_OUTSIDE_DTOS fait échouer l'outil (code 2) : son contrat
# a été renommé ou supprimé, et l'oublier serait un feu vert silencieux.
CLIENT_ALIASES = {
    'Mailbox': 'MailboxDto',
    'DirectoryMailbox': 'DirectoryMailboxDto',
    'DirectorySearchQuery': 'PractitionerSearchQueryDto',
    'ContactSearchFilter': 'ContactSearchFilterDto',
    'SignatureDto': 'MailSignatureDto',
    'CreateSignatureDto': 'CreateMailSignatureDto',
    'UpdateSignatureDto': 'UpdateMailSignatureDto',
    'SseActionDto': 'AiActionDto',
    'SseDataDto': 'AiStreamEventDto',
    'OutgoingMailDto': 'MailDto',
    'AuditTraceDto': 'MssAuditTraceDto',
    'DetectPlaceholdersResponse': 'DetectPlaceholdersResponseDto',
    'ImproveTextResponse': 'ImproveTextResponseDto',
    'GenerateTemplateResponse': 'GenerateTemplateResponseDto',
    'MssProbeErrorResponse': 'MssImapTestErrorResponse',
}

# Modèles client en *Dto qu'aucune classe de dtos-mss ne décrit (relevé du 2026-11-20). Ils restent hors
# surface, listés à part par « surface ».
CLIENT_OUTSIDE_DTOS = {
    'SendMailResultDto': 'réponse de l\'envoi, sans classe dans dtos-mss ni api-mail',
    'PendingEmailSendResultDto': 'réponse de l\'envoi d\'un message en attente, sans classe dans dtos-mss ni api-mail',
    'ConfirmPendingEmailResultDto': 'réponse de l\'envoi d\'un message en attente, sans classe dans dtos-mss ni api-mail',
    'SpecialtyDto': 'référentiel de l\'Annuaire Santé relayé tel quel, sans classe dans dtos-mss ni api-mail',
}

CLIENT_MOBILE_MODELS = Path('Client/Mobile/src/app/core/models')
CLIENT_MOBILE_SOURCES = Path('Client/Mobile/src')
CLIENT_ANGULAR_MODELS = Path('Client/Angular/front/libs/mss/src/core/models')
CLIENT_ANGULAR_SOURCES = Path('Client/Angular/front/libs/mss/src')

HTTP_CALL = re.compile(r'\.(get|post|put|delete|patch)\s*(?:<[^()]*?>)?\s*\(\s*$', re.I)
ERROR_CODE = re.compile(r'^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$')


def ts_literals(src: str) -> list[tuple[int, str]]:
    """Les chaînes et gabarits d'un fichier TypeScript : (position, texte). Les commentaires sont sautés,
    et un gabarit garde ses ${…} tels quels. Un vrai lexeur plutôt qu'une expression régulière : un accent
    grave fermant pris pour une ouverture fait déborder le motif d'un littéral au suivant."""
    out: list[tuple[int, str]] = []
    n = len(src)

    def template(i: int) -> int:
        while i < n:
            c = src[i]
            if c == BACKSLASH:
                i += 2
                continue
            if c == '`':
                return i + 1
            if c == '$' and i + 1 < n and src[i + 1] == '{':
                i = code(i + 2, '}')
                continue
            i += 1
        return n

    def code(i: int, stop: str | None) -> int:
        depth = 0
        while i < n:
            c = src[i]
            if src.startswith('//', i):
                j = src.find('\n', i)
                i = n if j < 0 else j
                continue
            if src.startswith('/*', i):
                j = src.find('*/', i)
                i = n if j < 0 else j + 2
                continue
            if c in '\'"':
                j = i + 1
                while j < n and src[j] != c and src[j] != '\n':
                    j += 2 if src[j] == BACKSLASH else 1
                out.append((i, src[i + 1:j]))
                i = j + 1
                continue
            if c == '`':
                j = template(i + 1)
                out.append((i, src[i + 1:j - 1]))
                i = j
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                if depth == 0 and stop == '}':
                    return i + 1
                depth -= 1
            i += 1
        return n

    code(0, None)
    return out


def client_route(literal: str) -> str:
    """Le gabarit normalisé d'une URL client : `${base}/api/v1/mail/folders/${f}${query}` -> api/v1/mail/folders/{}."""
    route = literal[literal.index('/api/v1/') + 1:]
    route = re.sub(r'/\$\{[^}]*\}', '/{}', route)
    route = re.sub(r'\$\{[^}]*\}', '', route)
    return normalize_route(route)


def ts_sources(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob('*.ts') if not p.name.endswith('.spec.ts'))


def strip_ts_comments(source: str) -> str:
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', '', source)


def block_after(source: str, start: int) -> str:
    """Le corps entre l'accolade ouvrante à l'indice start et sa fermante."""
    depth = 0
    for j in range(start, len(source)):
        if source[j] == '{':
            depth += 1
        elif source[j] == '}':
            depth -= 1
            if depth == 0:
                return source[start + 1:j]
    return source[start + 1:]


def top_level_fields(body: str) -> set[str]:
    """Les champs de premier niveau d'un corps d'interface ou de type objet (minuscules)."""
    fields, depth = set(), 0
    for line in body.splitlines():
        if depth == 0:
            match = re.match(r"\s*(?:readonly\s+)?['\"]?(\w+)['\"]?\??\s*:", line)
            if match:
                fields.add(match.group(1).lower())
        depth += sum(line.count(c) for c in '{([') - sum(line.count(c) for c in '})]')
    return fields


def ts_models(root: Path, folder: Path) -> tuple[dict[str, tuple[set[str], str]], dict[str, str]]:
    """(modèles à corps : nom -> (champs, fichier), déclarations nommées : nom -> fichier), chemins
    relatifs à la racine de l'espace de travail."""
    models: dict[str, tuple[set[str], str]] = {}
    declared: dict[str, str] = {}
    for path in ts_sources(root / folder):
        source = strip_ts_comments(path.read_text(encoding='utf-8'))
        relative = path.relative_to(root).as_posix()
        for match in re.finditer(r'export\s+(?:const\s+)?(?:interface|type|enum|const)\s+(\w+)', source):
            declared.setdefault(match.group(1), relative)
        for match in re.finditer(r'export\s+interface\s+(\w+)[^{]*\{|export\s+type\s+(\w+)(?:<[^=]*>)?\s*=\s*\{', source):
            name = match.group(1) or match.group(2)
            models[name] = (top_level_fields(block_after(source, match.end() - 1)), relative)
    return models, declared


def client_surface(root: Path, models_folder: Path, sources_folder: Path, dto_classes: set[str],
                   dto_enums: set[str]) -> Surface:
    if not (root / models_folder).is_dir():
        raise LookupError(f'dossier de modèles introuvable : {models_folder}')
    models, declared = ts_models(root, models_folder)

    fields: dict[str, set[str]] = {}
    readers: dict[str, str] = {}
    local: dict[str, str] = {}
    outside: dict[str, str] = {}
    for name, (read, reader) in sorted(models.items()):
        if name in CLIENT_OUTSIDE_DTOS:
            outside[name] = CLIENT_OUTSIDE_DTOS[name]
            continue
        dto = CLIENT_ALIASES.get(name) or (name if name.endswith('Dto') or name in dto_classes else None)
        if dto is None:
            local[name] = reader
            continue
        fields.setdefault(dto, set()).update(read)
        readers.setdefault(dto, reader)

    enums = tuple(sorted(name for name in declared if name in dto_enums))

    routes: set[tuple[str, str]] = set()
    codes: set[str] = set()
    for path in ts_sources(root / sources_folder):
        source = path.read_text(encoding='utf-8')
        for position, text in ts_literals(source):
            if ERROR_CODE.match(text):
                codes.add(text)
            if '/api/v1/' not in text:
                continue
            call = HTTP_CALL.search(source[max(0, position - 200):position])
            routes.add((call.group(1).upper() if call else '*', client_route(text)))

    return Surface(fields=fields, routes=routes, error_codes=codes, enums=enums, readers=readers,
                   local_models=local, outside_dtos=outside, codes_must_exist=False)


# --- Lecture d'api-mail et de dtos-mss --------------------------------------------------------

def strip_cs_comments(source: str) -> str:
    """Retire les blocs /* */ et les lignes de commentaire. Une documentation XML qui écrit « record » ou
    « class » (« …record or filter on the patient… ») était lue comme une déclaration : la classe était
    coupée en deux, et ses champs suivants disparaissaient de l'analyse."""
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', '', source)


def positional_parameters(body: str) -> dict[str, str]:
    """Les paramètres d'un record positionnel (`record X(int A, string? B = null)`), en {champ JSON : type}."""
    opening = re.match(r'\s*(?:<[^>]*>)?\s*\(', body)
    if not opening:
        return {}
    depth, start = 0, opening.end() - 1
    for j in range(start, len(body)):
        depth += {'(': 1, ')': -1}.get(body[j], 0)
        if depth == 0:
            break
    members = {}
    for part in split_top_level(body[start + 1:j]):
        json = re.search(r'JsonPropertyName\("([^"]+)"\)', part)
        declaration = re.sub(r'\[[^\]]*\]', '', part).split('=')[0].split()
        if len(declaration) >= 2:
            members[(json.group(1) if json else declaration[-1]).lower()] = ''.join(declaration[:-1])
    return members


def class_members(source: str) -> dict[str, dict[str, str]]:
    """Classe -> {champ JSON (minuscules) -> type}, pour les classes et records d'un fichier C#."""
    source = strip_cs_comments(source)
    result: dict[str, dict[str, str]] = {}
    declarations = list(re.finditer(r'\b(?:class|record)\s+(\w+)', source))
    for i, declaration in enumerate(declarations):
        end = declarations[i + 1].start() if i + 1 < len(declarations) else len(source)
        body = source[declaration.end():end]
        members = positional_parameters(body)
        for prop in re.finditer(
                r'(?:\[JsonPropertyName\("(?P<json>[^"]+)"\)\]\s*)?public\s+(?P<type>[\w<>\[\]?.,\s]+?)\s+(?P<name>\w+)\s*\{\s*get',
                body):
            name = (prop.group('json') or prop.group('name')).lower()
            members[name] = re.sub(r'\s+', '', prop.group('type'))
        result.setdefault(declaration.group(1), {}).update(members)
    return result


def enum_members(source: str) -> dict[str, list[str]]:
    source = strip_cs_comments(source)
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


def base_sources(repo: Path, prefix: str) -> str:
    """Les sources .cs d'un dossier du dépôt, telles qu'elles sont sur origin/develop."""
    paths = [p for p in git(repo, 'ls-tree', '-r', '--name-only', BASE, '--', prefix).split() if p.endswith('.cs')]
    return chr(10).join(old_content(repo, p) for p in paths)


# --- Comparaison --------------------------------------------------------------------------------

def route_present(route: tuple[str, str], routes: set[tuple[str, str]]) -> bool:
    """Un verbe « * » (URL dont l'appel n'est pas lisible, comme un flux SSE) se contente du gabarit."""
    verb, template = route
    if verb == '*':
        return any(t == template for _, t in routes)
    return route in routes


def compare(surface: Surface, old: dict[str, str], new: dict[str, str], consumer: str = 'api-mcp') -> Report:
    """Compare l'avant et l'après des fichiers modifiés d'un dépôt ({chemin: contenu})."""
    report = Report()
    old_all, new_all = '\n'.join(old.values()), '\n'.join(new.values())

    old_members, new_members = class_members(old_all), class_members(new_all)
    for dto, read in sorted(surface.fields.items()):
        if dto not in old_members:
            continue
        reader = surface.readers.get(dto, consumer)
        for name in sorted(read):
            before, after = old_members[dto].get(name), new_members.get(dto, {}).get(name)
            if before is None:
                continue
            if after is None:
                report.reasons.append(f'{dto}.{name} disparaît (lu par {reader})')
            elif after != before:
                report.reasons.append(f'{dto}.{name} change de type : {before} -> {after} (lu par {reader})')

    old_enums, new_enums = enum_members(old_all), enum_members(new_all)
    for enum in surface.enums:
        if enum in old_enums and old_enums[enum] != new_enums.get(enum):
            report.reasons.append(f'énumération {enum} modifiée : {consumer} la décode par rang')

    old_routes, new_routes = controller_routes(old_all), controller_routes(new_all)
    for route in sorted(surface.routes):
        if route_present(route, old_routes) and not route_present(route, new_routes):
            report.reasons.append(f'route {route[0]} {route[1]} disparaît (appelée par {consumer})')

    for path in sorted(set(old) | set(new)):
        removed = token_lines(old.get(path, ''), new.get(path, ''))
        for token in sorted({*surface.error_codes, *surface.sent_tokens}):
            if any(token in line for line in removed[0]) and not any(token in line for line in removed[1]):
                report.reasons.append(f'« {token} » retiré de {path} (utilisé par {consumer})')
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


def missing_from_base(surface: Surface, dtos: str, controllers: str) -> tuple[list[str], list[str]]:
    """
    Ce que la surface déclare et que origin/develop ne contient pas, en (erreurs, avertissements).
    Erreur : une classe, une énumération, une route ou (pour api-mcp) un code introuvable. Un analyseur
    ou une déclaration est alors périmé, et « aucun impact » ne voudrait rien dire.
    Avertissement : un champ isolé absent. Le consommateur le lit en lecteur tolérant (un champ ajouté
    par une task pas encore mergée, un champ calculé côté client) : son absence ne casse rien.
    """
    errors, warnings = [], []
    members = class_members(dtos)
    for dto, read in sorted(surface.fields.items()):
        if dto not in members:
            errors.append(f'classe {dto} (lue par {surface.readers.get(dto, "?")})')
            continue
        warnings += [f'{dto}.{name}' for name in sorted(read - set(members[dto]))]
    enums = enum_members(dtos)
    errors += [f'énumération {e}' for e in surface.enums if e not in enums]
    routes = controller_routes(controllers)
    errors += [f'route {v} {r}' for v, r in sorted(surface.routes) if not route_present((v, r), routes)]
    if surface.codes_must_exist:
        errors += [f'code {c}' for c in sorted(surface.error_codes) if f'"{c}"' not in dtos]
    return errors, warnings


# --- Consommateurs ------------------------------------------------------------------------------

@dataclass
class Base:
    """Ce que origin/develop contient, lu une fois pour tous les consommateurs."""
    dtos: str
    controllers: str

    @property
    def dto_classes(self) -> set[str]:
        return set(class_members(self.dtos))

    @property
    def dto_enums(self) -> set[str]:
        return set(enum_members(self.dtos))


def read_base(root: Path) -> Base:
    return Base(dtos=base_sources(root / REPOS['dtos-mss'], '.'),
                controllers=base_sources(root / REPOS['api-mail'], 'src/Api/Controllers'))


def consumers(base: Base | None = None) -> list[Consumer]:
    def mobile(root: Path) -> Surface:
        b = base or read_base(root)
        surface = client_surface(root, CLIENT_MOBILE_MODELS, CLIENT_MOBILE_SOURCES, b.dto_classes, b.dto_enums)
        surface.error_codes = {c for c in surface.error_codes if f'"{c}"' in b.dtos}
        return surface

    def angular(root: Path) -> Surface:
        b = base or read_base(root)
        surface = client_surface(root, CLIENT_ANGULAR_MODELS, CLIENT_ANGULAR_SOURCES, b.dto_classes, b.dto_enums)
        surface.error_codes = {c for c in surface.error_codes if f'"{c}"' in b.dtos}
        return surface

    return [
        Consumer('api-mcp', 'pushable', derive_mcp_surface, MCP_API_MAIL),
        Consumer('client-mobile', 'pushable', mobile, CLIENT_MOBILE_MODELS),
        Consumer('client-angular', 'code-only', angular, CLIENT_ANGULAR_MODELS),
    ]


CONSUMER_NAMES = ('api-mcp', 'client-mobile', 'client-angular')

ADAPT = {
    'api-mcp': 'adapter api-mcp (contrats locaux, simulations, tests)',
    'client-mobile': 'adapter client-mobile (branche paresseuse, modèles, services, tests, scénario e2e)',
    'client-angular': 'adapter client-angular (modèles, services, tests ; code seul, fichiers listés pour l\'humain)',
}


def check(root: Path = ROOT, only: tuple[str, ...] = CONSUMER_NAMES) -> int:
    """Verdict par consommateur. 0 : aucun touché ; 1 : au moins un impact ; 2 : erreur d'outil."""
    unknown = [name for name in only if name not in CONSUMER_NAMES]
    if unknown:
        print(f'contract_impact : erreur — consommateur inconnu : {", ".join(unknown)} '
              f'(attendu : {", ".join(CONSUMER_NAMES)})')
        return 2
    try:
        base = read_base(root)
        changes = {}
        for name, repo_path in REPOS.items():
            repo = root / repo_path
            files = changed_files(repo)
            changes[name] = ({f: old_content(repo, f) for f in files}, {f: new_content(repo, f) for f in files})
    except (RuntimeError, OSError) as error:
        print(f'contract_impact : erreur — {error}')
        return 2

    worst = 0
    width = max(len(n) for n in only)
    for consumer in consumers(base):
        if consumer.name not in only:
            continue
        label = consumer.name.ljust(width)
        try:
            surface = consumer.derive(root)
            errors, warnings = missing_from_base(surface, base.dtos, base.controllers)
        except (LookupError, RuntimeError, OSError, KeyError) as error:
            print(f'{label} : ERREUR — {error}')
            worst = 2
            continue
        if errors:
            print(f'{label} : ERREUR — surface introuvable sur origin/develop (analyseur ou déclaration périmé) :')
            for item in errors:
                print(f'  - {item}')
            worst = 2
            continue
        reasons = []
        for repo_name, (old, new) in changes.items():
            report = compare(surface, old, new, consumer.name)
            reasons += [f'{repo_name} : {reason}' for reason in report.reasons]
        if warnings:
            shown = ', '.join(warnings[:6]) + (f', … (+{len(warnings) - 6})' if len(warnings) > 6 else '')
            print(f'{label} : avertissement — {len(warnings)} champ(s) lu(s) absent(s) de origin/develop '
                  f'(lecture tolérante, sans effet) : {shown}')
        if not reasons:
            print(f'{label} : aucun impact')
            continue
        print(f'{label} : IMPACT — la task doit {ADAPT[consumer.name]} :')
        for reason in reasons:
            print(f'  - {reason}')
        worst = max(worst, 1)
    return worst


def show_surface(root: Path = ROOT, name: str = 'api-mcp') -> int:
    consumer = next((c for c in consumers() if c.name == name), None)
    if consumer is None:
        print(f'consommateur inconnu : {name} (attendu : {", ".join(CONSUMER_NAMES)})')
        return 2
    surface = consumer.derive(root)
    print(f'Surface de {name} ({consumer.git_mode}) :')
    print('Champs lus :')
    for dto, read in sorted(surface.fields.items()):
        reader = surface.readers.get(dto, name)
        print(f'  {dto} : {", ".join(sorted(read))}' + ('' if reader == name else f'  [{reader}]'))
    print('Routes appelées :')
    for verb, route in sorted(surface.routes, key=lambda r: (r[1], r[0])):
        print(f'  {verb} {route}')
    print(f'Codes d\'erreur lus : {", ".join(sorted(surface.error_codes)) or "aucun"}')
    print(f'Énumérations décodées par rang : {", ".join(surface.enums) or "aucune"}')
    if surface.sent_tokens:
        print(f'En-têtes, cookie et paramètres envoyés : {", ".join(surface.sent_tokens)}')
    if surface.outside_dtos:
        print('Modèles en *Dto sans classe dtos-mss (hors surface) :')
        for model, reason in sorted(surface.outside_dtos.items()):
            print(f'  {model} : {reason}')
    if surface.local_models:
        print('Modèles de vue locaux (hors surface) :')
        for model, path in sorted(surface.local_models.items()):
            print(f'  {model}  [{path}]')
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command = args[0] if args else ''
    consumer = args[args.index('--consumer') + 1] if '--consumer' in args and args.index('--consumer') + 1 < len(args) else None
    if command == 'check':
        return check(only=(consumer,) if consumer else CONSUMER_NAMES)
    if command == 'surface':
        return show_surface(name=consumer or 'api-mcp')
    print(__doc__)
    return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
