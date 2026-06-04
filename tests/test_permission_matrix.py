import json
from pathlib import Path


def test_roles_file_exists():
    path = Path("config/roles.json")
    assert path.exists(), "config/roles.json must exist"


def test_roles_have_permissions():
    data = json.loads(Path("config/roles.json").read_text())
    assert isinstance(data, dict)
    for role, info in data.items():
        assert "permissions" in info and isinstance(info["permissions"], list), f"Role {role} must declare permissions"


def test_no_unbounded_service_roles():
    data = json.loads(Path("config/roles.json").read_text())
    # Ensure non-admin roles do not have wildcard '*' permission
    for role, info in data.items():
        if role != "admin":
            perms = info.get("permissions", [])
            assert "*" not in perms, f"Non-admin role {role} must not have wildcard permissions"
