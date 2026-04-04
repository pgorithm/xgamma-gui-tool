"""SEC-008: .desktop Exec= is built from xgamma path + argv pieces; quoting/validation gaps."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gamma_core import GammaCore  # noqa: E402


def _core_with_xgamma(path: str) -> GammaCore:
    with patch("src.gamma_core.shutil.which", return_value=path):
        return GammaCore()


@pytest.mark.security
def test_build_xgamma_command_rgb_matches_subprocess_style_tokens() -> None:
    core = _core_with_xgamma("/usr/bin/xgamma")
    s = core.buildXgammaCommand(red=1.0, green=1.25, blue=2.5)
    assert s == "/usr/bin/xgamma -rgamma 1.0 -ggamma 1.25 -bgamma 2.5"


@pytest.mark.security
def test_build_xgamma_command_overall_branch() -> None:
    core = _core_with_xgamma("/bin/xgamma")
    assert core.buildXgammaCommand(overall=1.75) == "/bin/xgamma -gamma 1.75"


@pytest.mark.security
def test_path_with_space_splits_on_naive_tokenization() -> None:
    """Desktop Entry parsers tokenize Exec on spaces; path must be escaped (\\s or quotes)."""
    core = _core_with_xgamma("/opt/my tool/xgamma")
    s = core.buildXgammaCommand(overall=1.0)
    naive = s.split()
    assert naive[0] == "/opt/my"
    assert naive[1].startswith("tool/")


@pytest.mark.security
def test_gamma_numeric_tokens_have_no_shell_metacharacters_from_floats() -> None:
    core = _core_with_xgamma("/usr/bin/xgamma")
    s = core.buildXgammaCommand(red=0.01, green=5.0, blue=3.333)
    for tok in s.split()[1:]:
        if tok.startswith("-"):
            continue
        assert re.fullmatch(r"\d+(\.\d+)?", tok), f"unexpected token: {tok!r}"


@pytest.mark.security
def test_build_rejects_non_numeric_api_values() -> None:
    """Non-numeric gamma must not reach argv (SEC-003 / _prepare_gamma_scalar)."""
    core = _core_with_xgamma("/usr/bin/xgamma")
    s = core.buildXgammaCommand(red="1.0|evil")  # type: ignore[arg-type]
    assert s == ""


@pytest.mark.security
def test_save_to_autostart_desktop_template() -> None:
    """Exec= is the only interpolated line; name/comment are not taken from UI."""
    text = (REPO_ROOT / "src" / "config_manager.py").read_text(encoding="utf-8")
    assert "Exec={xgammaCommand}" in text
    assert "Name=xgamma Gamma Adjustment" in text
    assert "self.COMMENT_PREFIX" in text
