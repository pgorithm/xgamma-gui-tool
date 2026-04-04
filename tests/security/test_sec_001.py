"""SEC-001: PATH — first match for xgamma (which) and bare names for other utils."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gamma_core import GammaCore  # noqa: E402


@pytest.mark.security
def test_xgamma_executable_is_which_result() -> None:
    fake = "/tmp/sec001_mock_xgamma"
    with patch("src.gamma_core.shutil.which", return_value=fake):
        core = GammaCore()
    assert core.xgammaPath == fake


@pytest.mark.security
def test_apply_invokes_subprocess_with_which_path() -> None:
    fake = "/tmp/sec001_evil_xgamma"
    with patch("src.gamma_core.shutil.which", return_value=fake):
        core = GammaCore()
    captured: list[list[str]] = []

    def fake_run(args, **_kwargs):
        captured.append(list(args))
        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    with patch("src.gamma_core.subprocess.run", side_effect=fake_run):
        assert core.applyGamma(overall=1.0) is True
    assert captured and captured[0][0] == fake


class _FirstArgVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.argv_lists: list[list[str | None]] = []

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.args
        ):
            first = node.args[0]
            if isinstance(first, ast.List):
                elts: list[str | None] = []
                for elt in first.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        elts.append(elt.value)
                    else:
                        elts.append(None)
                self.argv_lists.append(elts)
        self.generic_visit(node)


def _subprocess_argv_lists(path: Path) -> list[list[str | None]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    v = _FirstArgVisitor()
    v.visit(tree)
    return v.argv_lists


@pytest.mark.security
def test_xrandr_and_systemd_invoked_without_absolute_path() -> None:
    """Bare names → resolved via PATH (same class of risk as hijacked xgamma)."""
    gamma_lists = _subprocess_argv_lists(REPO_ROOT / "src" / "gamma_core.py")
    env_lists = _subprocess_argv_lists(REPO_ROOT / "src" / "environment_checks.py")

    xrandr_heads = [lst[0] for lst in gamma_lists + env_lists if lst and lst[0]]
    assert "xrandr" in xrandr_heads
    for h in xrandr_heads:
        if h == "xrandr":
            assert not h.startswith("/")

    systemd_heads = [lst[0] for lst in env_lists if lst and lst[0] == "systemd-detect-virt"]
    assert systemd_heads == ["systemd-detect-virt"]
