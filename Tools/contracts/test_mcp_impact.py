"""Tests de Tools/contracts/mcp_impact.py — sur des dépôts git temporaires, avec les vrais fichiers.

Les dépôts temporaires reprennent les fichiers réels d'api-mcp, et ceux d'api-mail et de dtos-mss tels
qu'ils sont sur origin/develop : un analyseur qui ne comprendrait plus le code réel échoue ici.

    python -m unittest Tools/contracts/test_mcp_impact.py
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcp_impact  # noqa: E402

WORKSPACE = mcp_impact.ROOT
DTO_FILES = ['MailboxDto.cs', 'FolderDto.cs', 'MailDto.cs', 'MailAddressDto.cs', 'SearchRequestDto.cs', 'SearchResultDto.cs']
CONTROLLERS = 'src/Api/Controllers/V1'
CONTROLLER_FILES = ['AccountController.cs', 'MailController.cs', 'SearchController.cs']
PROGRAM = 'src/Api/Program.cs'


def sh(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def real(repo: str, path: str) -> str:
    return subprocess.run(['git', '-C', str(WORKSPACE / repo), 'show', f'origin/develop:{path}'],
                          check=True, capture_output=True, text=True, encoding='utf-8').stdout


def make_repo(path: Path, files: dict[str, str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    sh(path, 'git', 'init', '-q')
    sh(path, 'git', 'config', 'user.email', 't@t')
    sh(path, 'git', 'config', 'user.name', 't')
    for name, content in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(content, encoding='utf-8')
    sh(path, 'git', 'add', '.')
    sh(path, 'git', 'commit', '-q', '-m', 'develop')
    sh(path, 'git', 'update-ref', 'refs/remotes/origin/develop', 'HEAD')


class Workspace:
    """Un espace de travail temporaire : api-mcp réel, api-mail et dtos-mss de origin/develop."""

    def __init__(self, root: Path):
        self.root = root
        mcp = root / mcp_impact.MCP_API_MAIL
        mcp.mkdir(parents=True)
        for name in ('ApiMailContracts.cs', 'ApiMailRoutes.cs'):
            shutil.copy(WORKSPACE / mcp_impact.MCP_API_MAIL / name, mcp / name)
        self.dtos = root / 'Dtos'
        make_repo(self.dtos, {f: real('Dtos', f) for f in DTO_FILES})
        self.api = root / 'Api/Mail'
        files = {f'{CONTROLLERS}/{f}': real('Api/Mail', f'{CONTROLLERS}/{f}') for f in CONTROLLER_FILES}
        files[PROGRAM] = real('Api/Mail', PROGRAM)
        make_repo(self.api, files)

    def edit(self, repo: Path, path: str, old: str, new: str) -> None:
        file = repo / path
        text = file.read_text(encoding='utf-8')
        assert old in text, f'motif absent de {path} : {old}'
        file.write_text(text.replace(old, new, 1), encoding='utf-8')

    def check(self) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = mcp_impact.check(self.root)
        return code, out.getvalue()


class SurfaceTests(unittest.TestCase):
    def test_surface_is_derived_from_the_real_api_mcp(self):
        surface = mcp_impact.derive_surface(WORKSPACE)

        self.assertIn('email', surface.fields['MailboxDto'])
        self.assertIn('unreadcount', surface.fields['FolderDto'])
        self.assertIn(('POST', 'api/v1/search/semantic'), surface.routes)
        self.assertIn(('GET', 'api/v1/mail/folders/{}/emails/{}'), surface.routes)
        self.assertIn('MAILBOX_ACCESS_REFUSED', surface.error_codes)

    def test_a_record_without_declared_dto_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            mcp = Path(tmp) / mcp_impact.MCP_API_MAIL
            mcp.mkdir(parents=True)
            source = (WORKSPACE / mcp_impact.MCP_API_MAIL / 'ApiMailContracts.cs').read_text(encoding='utf-8')
            (mcp / 'ApiMailContracts.cs').write_text(source + '\ninternal sealed record ApiPatient(string Ins);\n', encoding='utf-8')
            shutil.copy(WORKSPACE / mcp_impact.MCP_API_MAIL / 'ApiMailRoutes.cs', mcp / 'ApiMailRoutes.cs')

            with self.assertRaisesRegex(LookupError, 'ApiPatient'):
                mcp_impact.derive_surface(Path(tmp))


class CheckTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def assert_impact(self, expected: str):
        code, out = self.ws.check()
        self.assertEqual(1, code, out)
        self.assertIn(expected, out)

    def test_nothing_changed_means_no_impact(self):
        code, out = self.ws.check()
        self.assertEqual(0, code, out)

    def test_adding_a_field_is_not_an_impact(self):
        self.ws.edit(self.ws.dtos, 'MailboxDto.cs', 'public string Email { get; set; }',
                     'public string Email { get; set; }\n    public string? Nouveau { get; set; }')
        code, out = self.ws.check()
        self.assertEqual(0, code, out)

    def test_removing_a_read_field_is_an_impact(self):
        self.ws.edit(self.ws.dtos, 'MailboxDto.cs', 'public string Email { get; set; }', 'public string Adresse { get; set; }')
        self.assert_impact('MailboxDto.email disparaît')

    def test_changing_the_type_of_a_read_field_is_an_impact(self):
        self.ws.edit(self.ws.dtos, 'FolderDto.cs', 'public int UnreadCount { get; set; }', 'public long UnreadCount { get; set; }')
        self.assert_impact('FolderDto.unreadcount change de type')

    def test_reordering_an_enum_decoded_by_rank_is_an_impact(self):
        self.ws.edit(self.ws.dtos, 'FolderDto.cs', 'Inbox,\n    Sent,', 'Sent,\n    Inbox,')
        self.assert_impact('énumération FolderType modifiée')

    def test_removing_a_called_route_is_an_impact(self):
        self.ws.edit(self.ws.api, f'{CONTROLLERS}/SearchController.cs', '[HttpPost("semantic")]', '[HttpPost("semantique")]')
        self.assert_impact('route POST api/v1/search/semantic disparaît')

    def test_removing_a_translated_error_code_is_an_impact(self):
        self.ws.edit(self.ws.dtos, 'MailboxDto.cs', '"MAILBOX_ACCESS_REFUSED"', '"MAILBOX_OPERATOR_REFUSED"')
        self.assert_impact('MAILBOX_ACCESS_REFUSED')

    def test_changing_the_json_shape_is_an_impact(self):
        self.ws.edit(self.ws.api, PROGRAM, 'JsonNamingPolicy.CamelCase', 'JsonNamingPolicy.SnakeCaseLower')
        self.assert_impact('forme du JSON modifiée')

    def test_a_class_missing_on_develop_is_a_tool_error_not_a_silent_pass(self):
        self.ws.edit(self.ws.dtos, 'SearchResultDto.cs', 'class SearchHitDto', 'class SearchMatchDto')
        sh(self.ws.dtos, 'git', 'commit', '-q', '-am', 'renommage sur develop')
        sh(self.ws.dtos, 'git', 'update-ref', 'refs/remotes/origin/develop', 'HEAD')

        code, out = self.ws.check()

        self.assertEqual(2, code, out)
        self.assertIn('classe SearchHitDto', out)


class ParserTests(unittest.TestCase):
    def test_json_property_name_is_the_read_name(self):
        members = mcp_impact.class_members('public class X {\n [JsonPropertyName("proxy_session_id")]\n public string? Id { get; set; }\n}')
        self.assertIn('proxy_session_id', members['X'])

    def test_controller_routes_resolve_the_controller_token(self):
        routes = mcp_impact.controller_routes(
            '[Route("api/v{version:apiVersion}/[controller]")]\npublic class MailController {\n [HttpGet("folders/{foldername}")]\n}')
        self.assertEqual({('GET', 'api/v1/mail/folders/{}')}, routes)


if __name__ == '__main__':
    unittest.main()
