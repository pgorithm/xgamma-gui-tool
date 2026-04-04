"""SEC-012: ReDoS / regex cost on very long stdout (xgamma / xrandr parsing)."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gamma_core import GammaCore  # noqa: E402

# Production patterns (gamma_core._parseGammaFromString / _readGammaFromXrandr) use
# fixed literals plus \\s+, \\s*, and a linear float token — no nested quantifiers
# like (a+)+b that typically trigger catastrophic backtracking. These tests bound
# wall time on large buffers to catch accidental introduction of dangerous patterns.

_PARSE_BUDGET_SEC = 2.0
_XRANDR_BUDGET_SEC = 2.0


def _bare_core() -> GammaCore:
    core = GammaCore.__new__(GammaCore)
    core.xgammaPath = "/usr/bin/xgamma"
    core.lastRawOutput = ""
    core.lastApplyRawOutput = ""
    core.lastGammaReadSource = "default"
    core.lastGammaReadClamped = False
    return core


@pytest.mark.security
def test_sec012_parse_gamma_long_stdout_no_match_bounded_time() -> None:
    core = _bare_core()
    text = "Z" * 400_000
    start = time.perf_counter()
    assert core._parseGammaFromString(text) is None
    assert time.perf_counter() - start < _PARSE_BUDGET_SEC


@pytest.mark.security
def test_sec012_parse_gamma_long_prefix_before_triplet_bounded_time() -> None:
    core = _bare_core()
    tail = "Red 1.0, Green 1.0, Blue 1.0"
    text = "P" * 300_000 + tail
    start = time.perf_counter()
    g = core._parseGammaFromString(text)
    elapsed = time.perf_counter() - start
    assert g is not None
    assert g["red"] == g["green"] == g["blue"] == 1.0
    assert elapsed < _PARSE_BUDGET_SEC


@pytest.mark.security
def test_sec012_xrandr_regex_long_stdout_no_gamma_bounded_time() -> None:
    core = _bare_core()
    huge = "noise-line\n" * 40_000

    def _run(_cmd, **_kwargs):
        return MagicMock(returncode=0, stdout=huge, stderr="")

    with patch.object(subprocess, "run", side_effect=_run):
        start = time.perf_counter()
        assert core._readGammaFromXrandr() == (None, False)
        assert time.perf_counter() - start < _XRANDR_BUDGET_SEC


@pytest.mark.security
def test_sec012_xrandr_regex_long_prefix_then_gamma_bounded_time() -> None:
    core = _bare_core()
    huge = ("n" * 20 + "\n") * 15_000 + "Gamma: 1.0:1.0:1.0\n"

    def _run(_cmd, **_kwargs):
        return MagicMock(returncode=0, stdout=huge, stderr="")

    with patch.object(subprocess, "run", side_effect=_run):
        start = time.perf_counter()
        g, clamped = core._readGammaFromXrandr()
        elapsed = time.perf_counter() - start
    assert g == {"red": 1.0, "green": 1.0, "blue": 1.0}
    assert clamped is False
    assert elapsed < _XRANDR_BUDGET_SEC
