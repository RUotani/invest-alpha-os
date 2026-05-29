from __future__ import annotations

from invis_alpha_os.security.dependency_security_audit import build_dependency_security_audit


def test_dependency_security_audit_inventory() -> None:
    result = build_dependency_security_audit()
    assert result.json_payload["no_new_dependencies"] is True
    assert result.json_payload["secrets_printed"] is False
    assert "installed_package_count" in result.json_payload
