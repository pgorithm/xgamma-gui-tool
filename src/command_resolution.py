"""Resolve external command paths (SEC-001 / PRD §7.1).

`shutil.which` uses the first executable match on PATH. A writable earlier
directory can shadow distro tools. By default we keep that behavior; set
`XGAMMA_GUI_TOOL_TRUSTED_PREFIXES` to a PATH-style list of directory prefixes
(see os.pathsep) so only executables whose realpath lies under one of those
directories are used. If no such executable exists, resolution returns None.
"""

import os
import shutil


def _trusted_prefixes():
    raw = os.environ.get('XGAMMA_GUI_TOOL_TRUSTED_PREFIXES', '').strip()
    if not raw:
        return None
    return [os.path.normpath(p) for p in raw.split(os.pathsep) if p.strip()]


def _under_trusted_prefix(resolved_path, prefixes):
    try:
        real = os.path.realpath(resolved_path)
    except OSError:
        return False
    for prefix in prefixes:
        try:
            pref_real = os.path.realpath(prefix)
        except OSError:
            continue
        if real == pref_real or real.startswith(pref_real + os.sep):
            return True
    return False


def _first_trusted_in_path(name, prefixes):
    path_env = os.environ.get('PATH', '') or os.defpath
    for directory in path_env.split(os.pathsep):
        directory = directory or os.curdir
        candidate = os.path.join(directory, name)
        if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
            continue
        if _under_trusted_prefix(candidate, prefixes):
            return candidate
    return None


def resolve_command(name):
    """
    Locate an executable by basename, optionally restricted to trusted prefixes.

    Returns:
        str path, or None if not found or (when prefixes set) no trusted match.
    """
    prefixes = _trusted_prefixes()
    if not prefixes:
        return shutil.which(name)
    return _first_trusted_in_path(name, prefixes)
