"""SEC-011: parse xgamma/xrandr read path — finite-only, clamp to product range."""

import pytest

from src.gamma_core import GammaCore


@pytest.fixture
def core():
    return GammaCore()


def test_parse_typical_xgamma_line_in_range(core):
    text = '-> Red  1.000, Green  1.000, Blue  1.000'
    raw = core._parseGammaFromString(text)
    out, clamped = core._finalize_read_gamma_dict(raw)
    assert out == {'red': 1.0, 'green': 1.0, 'blue': 1.0}
    assert clamped is False


def test_parse_clamps_high_channel(core):
    text = '-> Red  9.500, Green  1.000, Blue  1.000'
    raw = core._parseGammaFromString(text)
    out, clamped = core._finalize_read_gamma_dict(raw)
    assert out['red'] == pytest.approx(5.0)
    assert out['green'] == pytest.approx(1.0)
    assert out['blue'] == pytest.approx(1.0)
    assert clamped is True


def test_parse_clamps_low_channel(core):
    text = 'Red 0.001, Green 1.0, Blue 1.0'
    raw = core._parseGammaFromString(text)
    out, clamped = core._finalize_read_gamma_dict(raw)
    assert out['red'] == pytest.approx(0.01)
    assert clamped is True


def test_parse_scientific_notation(core):
    text = 'Red 2e0, Green 1.0, Blue 1.0'
    raw = core._parseGammaFromString(text)
    out, clamped = core._finalize_read_gamma_dict(raw)
    assert out['red'] == pytest.approx(2.0)
    assert clamped is False


def test_finalize_rejects_non_finite(core):
    out, clamped = core._finalize_read_gamma_dict(
        {'red': float('nan'), 'green': 1.0, 'blue': 1.0}
    )
    assert out is None
    assert clamped is False

    out2, _ = core._finalize_read_gamma_dict(
        {'red': float('inf'), 'green': 1.0, 'blue': 1.0}
    )
    assert out2 is None


def test_parse_malformed_returns_none(core):
    assert core._parseGammaFromString('no gamma here') is None
    assert core._parseGammaFromString('Red 1.0, Green 2.0') is None


def test_read_gamma_from_xrandr_line_via_finalize(core):
    # Simulated snippet (no subprocess): same regex as _readGammaFromXrandr stdout scan.
    stdout = '  Gamma: 0.5:1.0:2.0\n'
    t = GammaCore._FLOAT_TOKEN
    import re

    match = re.search(
        r'Gamma:\s*({t}):({t}):({t})'.format(t=t),
        stdout,
    )
    assert match
    raw = {
        'red': float(match.group(1)),
        'green': float(match.group(2)),
        'blue': float(match.group(3)),
    }
    out, clamped = core._finalize_read_gamma_dict(raw)
    assert out['red'] == pytest.approx(0.5)
    assert out['green'] == pytest.approx(1.0)
    assert out['blue'] == pytest.approx(2.0)
    assert clamped is False
