"""SEC-016: requirements.txt dependency CVE posture (pip-audit / advisory DB)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = REPO_ROOT / "requirements.txt"


def _pip_audit_importable() -> bool:
    try:
        import pip_audit  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.security
def test_sec016_requirements_lists_pyqt5() -> None:
    assert REQUIREMENTS.is_file()
    lines = [
        ln.strip()
        for ln in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert any(ln.upper().startswith("PYQT5") for ln in lines), "expected PyQt5 dependency line"


@pytest.mark.security
@pytest.mark.skipif(not _pip_audit_importable(), reason="install pip-audit: python -m pip install pip-audit")
def test_sec016_pip_audit_no_known_vulnerabilities() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            str(REQUIREMENTS),
            "--format",
            "json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    data = json.loads(proc.stdout)
    for dep in data.get("dependencies", []):
        vulns = dep.get("vulns") or []
        assert not vulns, f"{dep.get('name')}@{dep.get('version')}: {vulns}"
