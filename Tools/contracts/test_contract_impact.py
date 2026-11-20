"""Tests de Tools/contracts/contract_impact.py côté clients (task-484) — sur des dépôts git temporaires.

Les dépôts temporaires reprennent les vrais fichiers : dtos-mss et les contrôleurs d'api-mail tels qu'ils
sont sur le disque (fichiers suivis), les modèles et services TypeScript de client-mobile et client-angular tels qu'ils
sont sur le disque, et les contrats d'api-mcp. Un analyseur qui ne comprendrait plus le code réel échoue ici.

    python -m unittest Tools/contracts/test_contract_impact.py
"""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_impact as ci  # noqa: E402

WORKSPACE = ci.ROOT
CONTROLLERS = 'src/Api/Controllers'
PROGRAM = 'src/Api/Program.cs'


def sh(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


@lru_cache(maxsize=None)
def develop_files(repo: str, prefix: str) -> dict[str, str]:
    """
    Les fichiers .cs d'un dossier d'un dépôt (suivis ou nouveaux), tels qu'ils sont sur le disque (lus une fois).

    Le disque, et non origin/develop : les modèles des clients sont copiés du disque, et une task en cours y fait lire
    un contrat qu'elle ajoute (task-462). Lire dtos-mss et api-mail ailleurs que là où sont lus les clients ferait
    échouer ces tests à chaque task qui touche le contrat.
    """
    root = WORKSPACE / repo
    paths = [p for p in ci.git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', prefix).split()
             if p.endswith('.cs')]
    return {p: ci.new_content(root, p) for p in paths}


def make_repo(path: Path, files: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    sh(path, 'git', 'init', '-q')
    sh(path, 'git', 'config', 'user.email', 't@t')
    sh(path, 'git', 'config', 'user.name', 't')
    sh(path, 'git', 'config', 'core.autocrlf', 'false')
    for name, content in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(content, encoding='utf-8', newline='')
    sh(path, 'git', 'add', '.')
    sh(path, 'git', 'commit', '-q', '-m', 'develop')
    sh(path, 'git', 'update-ref', 'refs/remotes/origin/develop', 'HEAD')


def copy_typescript(source: Path, target: Path) -> None:
    for path in ci.ts_sources(WORKSPACE / source):
        destination = target / path.relative_to(WORKSPACE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, destination)


class Workspace:
    """Un espace de travail temporaire : les trois consommateurs réels, dtos-mss et api-mail du disque."""

    def __init__(self, root: Path):
        self.root = root
        mcp = root / ci.MCP_API_MAIL
        mcp.mkdir(parents=True)
        for name in ('ApiMailContracts.cs', 'ApiMailRoutes.cs'):
            shutil.copy(WORKSPACE / ci.MCP_API_MAIL / name, mcp / name)
        copy_typescript(ci.CLIENT_MOBILE_SOURCES, root)
        copy_typescript(ci.CLIENT_ANGULAR_SOURCES, root)
        self.dtos = root / 'Dtos'
        make_repo(self.dtos, develop_files('Dtos', '.'))
        self.api = root / 'Api/Mail'
        files = dict(develop_files('Api/Mail', CONTROLLERS))
        files[PROGRAM] = develop_files('Api/Mail', 'src/Api')[PROGRAM]
        make_repo(self.api, files)

    def edit(self, repo: Path, path: str, old: str, new: str) -> None:
        file = repo / path
        text = file.read_text(encoding='utf-8')
        assert old in text, f'motif absent de {path} : {old}'
        file.write_text(text.replace(old, new, 1), encoding='utf-8', newline='')

    def file_declaring(self, repo: Path, pattern: str) -> str:
        """Le fichier du dépôt dont le contenu porte ce motif (expression régulière)."""
        for path in sorted(p for p in repo.rglob('*.cs') if '.git' not in p.parts):
            if re.search(pattern, path.read_text(encoding='utf-8')):
                return path.relative_to(repo).as_posix()
        raise AssertionError(f'aucun fichier ne porte {pattern}')

    def check(self) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = ci.check(self.root)
        return code, out.getvalue()


def verdict(out: str, consumer: str) -> str:
    """La ligne de verdict d'un consommateur et ses raisons."""
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(consumer) and ' : avertissement' not in line)
    block = [lines[start]]
    for line in lines[start + 1:]:
        if not line.startswith('  - '):
            break
        block.append(line)
    return '\n'.join(block)


class SurfaceTests(unittest.TestCase):
    """Les surfaces se déduisent des vrais fichiers des clients."""

    @classmethod
    def setUpClass(cls):
        # La même base que les clients copiés : le disque (voir develop_files).
        cls.base = ci.Base(dtos=chr(10).join(develop_files('Dtos', '.').values()),
                           controllers=chr(10).join(develop_files('Api/Mail', CONTROLLERS).values()))
        cls.surfaces = {c.name: c.derive(WORKSPACE) for c in ci.consumers(cls.base)}

    def test_the_mobile_surface_holds_its_contract_models_and_the_mailboxes_route(self):
        mobile = self.surfaces['client-mobile']

        self.assertIn('unreadcount', mobile.fields['FolderDto'])
        self.assertEqual({'address', 'name'}, mobile.fields['MailAddressDto'] & {'address', 'name'})
        self.assertIn('email', mobile.fields['MailboxDto'], 'Mailbox est rattaché à MailboxDto par la table')
        self.assertIn(('GET', 'api/v1/account/mailboxes'), mobile.routes)
        self.assertIn('FolderType', mobile.enums)

    def test_an_angular_interface_is_bound_to_its_csharp_class(self):
        angular = self.surfaces['client-angular']

        self.assertIn('unreadcount', angular.fields['FolderDto'])
        self.assertTrue(angular.readers['FolderDto'].startswith(ci.CLIENT_ANGULAR_MODELS.as_posix()))
        self.assertIn('FolderType', angular.enums, 'const + type homonymes de l\'énumération C#')

    def test_every_route_a_client_calls_exists_in_api_mail(self):
        for name in ('client-mobile', 'client-angular'):
            errors, _ = ci.missing_from_base(self.surfaces[name], self.base.dtos, self.base.controllers)
            self.assertEqual([], errors, name)

    def test_view_models_and_dto_without_class_stay_out_of_the_surface(self):
        mobile = self.surfaces['client-mobile']

        self.assertIn('EditableContact', mobile.local_models)
        self.assertNotIn('EditableContact', mobile.fields)
        self.assertIn('SendMailResultDto', mobile.outside_dtos)


class CheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_nothing_changed_means_no_impact_on_any_consumer(self):
        code, out = self.ws.check()

        self.assertEqual(0, code, out)
        for consumer in ci.CONSUMER_NAMES:
            self.assertIn('aucun impact', verdict(out, consumer))

    def test_a_field_read_by_the_mobile_only_is_an_impact_on_the_mobile_only(self):
        self.ws.edit(self.ws.dtos, 'MailDto.cs', 'public uint? CancelAndReplaceUid { get; set; }', '')

        code, out = self.ws.check()

        self.assertEqual(1, code, out)
        mobile = verdict(out, 'client-mobile')
        self.assertIn('IMPACT', mobile)
        self.assertIn('MailDto.cancelandreplaceuid disparaît (lu par Client/Mobile/src/app/core/models/', mobile)
        self.assertIn('aucun impact', verdict(out, 'client-angular'))
        self.assertIn('aucun impact', verdict(out, 'api-mcp'))

    def test_a_field_read_by_angular_only_is_an_impact_on_angular_only(self):
        self.ws.edit(self.ws.dtos, 'AttachmentDto.cs', 'public IheXdmPackagingDto? Packaging { get; set; }', '')

        code, out = self.ws.check()

        self.assertEqual(1, code, out)
        angular = verdict(out, 'client-angular')
        self.assertIn('IMPACT', angular)
        self.assertIn('AttachmentDto.packaging disparaît', angular)
        self.assertIn('code seul', angular, 'le verdict rappelle que l\'humain commite client-angular')
        self.assertIn('aucun impact', verdict(out, 'client-mobile'))

    def test_a_route_called_by_the_clients_disappearing_is_an_impact(self):
        controller = self.ws.file_declaring(self.ws.api, r'\[HttpDelete\("groups/\{')
        text = (self.ws.api / controller).read_text(encoding='utf-8')
        attribute = re.search(r'\[HttpDelete\("groups/\{[^"]*"\)\]', text).group(0)
        self.ws.edit(self.ws.api, controller, attribute, '[HttpDelete("groupes/{id}")]')

        code, out = self.ws.check()

        self.assertEqual(1, code, out)
        for consumer in ('client-mobile', 'client-angular'):
            self.assertIn('route DELETE api/v1/contact/groups/{} disparaît', verdict(out, consumer))
        self.assertIn('aucun impact', verdict(out, 'api-mcp'))

    def test_adding_a_field_is_not_an_impact(self):
        self.ws.edit(self.ws.dtos, 'MailDto.cs', 'public uint? CancelAndReplaceUid { get; set; }',
                     'public uint? CancelAndReplaceUid { get; set; }\n    public string? Nouveau { get; set; }')

        code, out = self.ws.check()

        self.assertEqual(0, code, out)

    def test_a_view_model_added_to_a_client_stays_out_of_the_surface(self):
        models = self.ws.root / ci.CLIENT_MOBILE_MODELS
        (models / 'vue-locale.model.ts').write_text(
            'export interface CarteDePatientVue {\n  titre: string;\n  badge?: number;\n}\n', encoding='utf-8')

        surface = next(c for c in ci.consumers() if c.name == 'client-mobile').derive(self.ws.root)
        code, out = self.ws.check()

        self.assertIn('CarteDePatientVue', surface.local_models)
        self.assertNotIn('CarteDePatientVue', surface.fields)
        self.assertEqual(0, code, out)

    def test_a_client_model_bound_to_a_class_missing_on_develop_is_a_tool_error(self):
        path = self.ws.file_declaring(self.ws.dtos, r'class ContactGroupDto\b')
        self.ws.edit(self.ws.dtos, path, 'class ContactGroupDto', 'class ContactTeamDto')
        sh(self.ws.dtos, 'git', 'commit', '-q', '-am', 'renommage sur develop')
        sh(self.ws.dtos, 'git', 'update-ref', 'refs/remotes/origin/develop', 'HEAD')

        code, out = self.ws.check()

        self.assertEqual(2, code, out)
        self.assertIn('ERREUR', verdict(out, 'client-mobile'))
        self.assertIn('classe ContactGroupDto', out)

    def test_a_contract_the_branch_adds_and_a_client_reads_is_not_a_tool_error(self):
        # task-462 : le contrat (classe et route) naît sur la branche, et le client le lit dans le même cycle.
        (self.ws.dtos / 'RappelNeufDto.cs').write_text(
            'namespace HealthPlatform.Dtos.Mss;\npublic class RappelNeufDto\n{\n    public string Echeance { get; set; } = "";\n}\n',
            encoding='utf-8')
        controller = self.ws.file_declaring(self.ws.api, r'\[HttpDelete\("groups/\{')
        self.ws.edit(self.ws.api, controller, '[HttpDelete("groups/', '[HttpGet("rappels-neufs")]\n    [HttpDelete("groups/')
        models = self.ws.root / ci.CLIENT_MOBILE_MODELS
        (models / 'rappel-neuf.model.ts').write_text('export interface RappelNeufDto {\n  echeance: string;\n}\n', encoding='utf-8')
        (self.ws.root / ci.CLIENT_MOBILE_SOURCES / 'rappel-neuf.service.ts').write_text(
            'export const call = (http: any, base: string) => http.get<unknown>(`${base}/api/v1/contact/rappels-neufs`);\n',
            encoding='utf-8')

        code, out = self.ws.check()

        self.assertNotEqual(2, code, out)
        self.assertNotIn('ERREUR', verdict(out, 'client-mobile'))

    def test_an_unknown_consumer_is_a_tool_error(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = ci.check(self.ws.root, only=('client-blazor',))

        self.assertEqual(2, code, out.getvalue())


class ParserTests(unittest.TestCase):
    def test_a_positional_record_exposes_its_parameters_as_fields(self):
        members = ci.class_members('public record SyncStatusDto(\n    SyncStatus Status,\n    SyncProgressDto? Progress = null\n);')

        self.assertEqual({'status': 'SyncStatus', 'progress': 'SyncProgressDto?'}, members['SyncStatusDto'])

    def test_a_doc_comment_saying_record_does_not_cut_the_class(self):
        members = ci.class_members(
            'public record SearchFoundPatientDto\n{\n'
            '    /// <summary>To open the patient record or filter on the patient.</summary>\n'
            '    public Guid Id { get; init; }\n'
            '    public string LastName { get; init; }\n}')

        self.assertEqual({'id', 'lastname'}, set(members['SearchFoundPatientDto']))
        self.assertNotIn('or', members)

    def test_a_template_url_is_normalized_and_its_verb_read(self):
        source = ('return this.http.get<FolderDto[]>(`${this.baseUrl}/api/v1/mail/folders/${encoded}/emails${query}`);\n'
                  'const stream = `${base}/api/v1/mail/events/stream` + `?folder=${f}`;\n')

        literals = [text for _, text in ci.ts_literals(source) if '/api/v1/' in text]

        self.assertEqual(['api/v1/mail/folders/{}/emails', 'api/v1/mail/events/stream'],
                         [ci.client_route(t) for t in literals])
        position = source.index('`')
        self.assertEqual('get', ci.HTTP_CALL.search(source[:position]).group(1))

    def test_a_route_without_readable_verb_matches_on_its_template(self):
        routes = {('GET', 'api/v1/mail/events/stream')}

        self.assertTrue(ci.route_present(('*', 'api/v1/mail/events/stream'), routes))
        self.assertFalse(ci.route_present(('POST', 'api/v1/mail/events/stream'), routes))


if __name__ == '__main__':
    unittest.main()
