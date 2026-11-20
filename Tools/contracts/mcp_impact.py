"""Alias historique de contract_impact.py (task-484, 2026-11-20).

L'outil couvrait d'abord le seul api-mcp. Il suit désormais les trois consommateurs du contrat d'api-mail
(api-mcp, client-mobile, client-angular) : voir contract_impact.py. Ce module garde la ligne de commande
et l'API Python d'origine, pour les playbooks et les tests qui les citent.

    python Tools/contracts/mcp_impact.py check                      # = contract_impact.py check (tous)
    python Tools/contracts/mcp_impact.py surface --consumer client-mobile

En Python, check(root) et derive_surface(root) restent ceux d'api-mcp.

Tests : python -m unittest Tools/contracts/test_mcp_impact.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_impact import (  # noqa: E402,F401  (réexportés pour les tests et les appelants)
    BASE, BUILT_ROUTES, ENUMS_BY_RANK, JSON_SHAPE_TOKENS, MCP_API_MAIL, RECORD_TO_DTO, REPOS, ROOT, SENT_TOKENS,
    Report, Surface, class_members, compare, controller_routes, enum_members, main, missing_from_base,
    normalize_route, parse_records, parse_string_constants, split_top_level,
)
from contract_impact import check as _check_all  # noqa: E402
from contract_impact import derive_mcp_surface as derive_surface  # noqa: E402,F401


def check(root: Path = ROOT) -> int:
    """Le verdict d'api-mcp seul, comme avant task-484."""
    return _check_all(root, only=('api-mcp',))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
