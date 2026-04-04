"""
Desktop Entry Exec= value formatting (freedesktop.org Desktop Entry Spec, SEC-008).

Joins argv-like tokens into a single Exec key value: space-separated, with double-quoted
segments and escapes where required.
"""

from __future__ import annotations

import re
from typing import Sequence

# Unquoted tokens: alnum, common path chars, flags. Chars like space or ";|&" force quoting.
_SAFE_UNQUOTED = re.compile(r'^[-A-Za-z0-9_./:@+=]+$')


def _needs_quoting(arg: str) -> bool:
    if arg == '':
        return True
    return _SAFE_UNQUOTED.match(arg) is None


def _escape_inside_double_quotes(arg: str) -> str:
    """Escape characters that are special inside Desktop Entry double quotes."""
    out: list[str] = []
    for c in arg:
        if c == '\\':
            out.append('\\\\')
        elif c == '"':
            out.append('\\"')
        elif c == '`':
            out.append('\\`')
        elif c == '$':
            out.append('\\$')
        elif c == '\n':
            out.append('\\n')
        elif c == '\r':
            out.append('\\r')
        elif c == '\t':
            out.append('\\t')
        else:
            out.append(c)
    return ''.join(out)


def format_desktop_exec_line(argv: Sequence[str]) -> str:
    """
    Build the value for Exec= from a list of arguments (argv[0] = executable path).

    >>> format_desktop_exec_line(['/usr/bin/xgamma', '-rgamma', '1.0'])
    '/usr/bin/xgamma -rgamma 1.0'
    >>> format_desktop_exec_line(['/opt/my tools/xgamma', '-rgamma', '1.0'])
    '"/opt/my tools/xgamma" -rgamma 1.0'
    >>> format_desktop_exec_line(['/bin/sh', 'a"b'])
    '/bin/sh "a\\\\"b"'
    """
    parts: list[str] = []
    for a in argv:
        if _needs_quoting(a):
            parts.append('"' + _escape_inside_double_quotes(a) + '"')
        else:
            parts.append(a)
    return ' '.join(parts)
