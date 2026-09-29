"""The web app's permission table (`apps/web/lib/permissions.ts`) mirrors `MATRIX` exactly.

The web uses it to hide nav items and pages a role can't use (DASH-001); the API enforces the same
table with `require(action)`. If they drift, the UI would show links the API refuses, or hide
pages a role may use.
"""

import re
from pathlib import Path

from app.core.context import Role
from app.core.permissions import MATRIX, Access, Action

WEB_PERMISSIONS = Path(__file__).resolve().parents[4] / "apps" / "web" / "lib" / "permissions.ts"
SHORT = {"A": Access.WORKSPACE, "D": Access.DEPARTMENTS, "S": Access.SHORTLIST}


def web_matrix() -> dict[str, dict[str, Access]]:
    source = WEB_PERMISSIONS.read_text()
    block = source.split("export const MATRIX", 1)[1].split("};", 1)[0]
    rows = re.findall(r"^\s*(\w+): \{([^}]*)\},?$", block, flags=re.MULTILINE)
    return {
        action: {role: SHORT[short] for role, short in re.findall(r"(\w+): ([ADS])\b", entries)}
        for action, entries in rows
    }


def test_web_permissions_mirror_the_api_matrix() -> None:
    expected = {
        action.value: {role.value: access for role, access in by_role.items()}
        for action, by_role in MATRIX.items()
    }
    assert web_matrix() == expected


def test_every_action_and_role_is_known_to_the_web() -> None:
    source = WEB_PERMISSIONS.read_text()
    for action in Action:
        assert f'"{action.value}"' in source
    for role in Role:
        assert f'"{role.value}"' in source
