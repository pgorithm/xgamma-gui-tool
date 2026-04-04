"""Gamma Core Module.

This module provides the core functionality for managing display gamma settings
using the `xgamma` command-line utility. It handles checking for `xgamma`
availability, executing gamma correction commands, and parsing current
gamma values from the system.
"""

import math
import re
import subprocess

from .command_resolution import resolve_command
from .desktop_entry import format_desktop_exec_line


class GammaCore:
    """Core class for managing gamma settings via xgamma command."""
    
    DEFAULT_GAMMA = 1.000
    MIN_GAMMA = 0.010
    MAX_GAMMA = 5.000
    # nan/inf: refuse to build argv (no silent substitution); see _prepare_gamma_scalar.
    
    def __init__(self):
        """Initialize GammaCore and check xgamma availability."""
        self.xgammaPath = self._findXgamma()
        self.lastRawOutput = ''  # Последний stdout от xgamma, для отладки
        self.lastApplyRawOutput = ''  # Вывод последнего вызова xgamma при apply (успех или сбой)
        # Источник значений при последнем getCurrentGamma: xgamma | xrandr | default
        self.lastGammaReadSource = 'default'
        # True if last successful read had R/G/B outside [MIN_GAMMA, MAX_GAMMA] before clamp (SEC-011).
        self.lastGammaReadClamped = False
    
    def _findXgamma(self):
        """
        Find xgamma executable in system PATH (optional SEC-001 trusted prefixes).
        
        Returns:
            str: Path to xgamma executable or None if not found
        """
        return resolve_command('xgamma')
    
    def isXgammaAvailable(self):
        """
        Check if xgamma is available in the system.
        
        Returns:
            bool: True if xgamma is available, False otherwise
        """
        return self.xgammaPath is not None
    
    def getCurrentGamma(self):
        """
        Get current gamma values from xgamma.
        
        Returns:
            dict: Dictionary with 'red', 'green', 'blue' keys and float values.
                  Returns default values (1.0) if xgamma is not available or on error.
        """
        if not self.isXgammaAvailable():
            self.lastRawOutput = 'xgamma not available'  # Нет бинарника — нет вывода
            self.lastGammaReadSource = 'default'
            self.lastGammaReadClamped = False
            return self._defaultGammaValues()
        
        self.lastGammaReadClamped = False
        try:
            # Запускаем xgamma без параметров, чтобы получить текущие значения гаммы
            result = subprocess.run(
                [self.xgammaPath],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Парсим вывод xgamma, чтобы извлечь текущие значения гаммы для каждого канала (например, "-> Red  1.000, Green  1.000, Blue  1.000").
            rawOutput = (result.stdout or '').strip() or (result.stderr or '').strip()
            self.lastRawOutput = rawOutput  # Сохраняем сырой вывод для дальнейшего анализа
            parsedGamma = self._parseGammaFromString(rawOutput)
            finalized, clamped = self._finalize_read_gamma_dict(parsedGamma)
            if finalized:
                self.lastGammaReadClamped = clamped
                self.lastGammaReadSource = 'xgamma'
                return finalized
            
            # Пробуем получить данные через xrandr как запасной вариант
            fallbackGamma, fb_clamped = self._readGammaFromXrandr()
            if fallbackGamma:
                self.lastRawOutput = 'xrandr fallback: {}'.format(fallbackGamma)
                self.lastGammaReadSource = 'xrandr'
                self.lastGammaReadClamped = fb_clamped
                return fallbackGamma
            
            self.lastGammaReadSource = 'default'
            self.lastGammaReadClamped = False
            return self._defaultGammaValues()
        except (subprocess.TimeoutExpired, ValueError, AttributeError, Exception) as error:
            # При любой ошибке пробуем fallback, иначе значения по умолчанию
            self.lastRawOutput = str(error)
            fallbackGamma, fb_clamped = self._readGammaFromXrandr()
            if fallbackGamma:
                self.lastRawOutput = 'xrandr fallback after error: {}'.format(fallbackGamma)
                self.lastGammaReadSource = 'xrandr'
                self.lastGammaReadClamped = fb_clamped
                return fallbackGamma
            self.lastGammaReadSource = 'default'
            self.lastGammaReadClamped = False
            return self._defaultGammaValues()

    def getLastRawOutput(self):
        """Return raw stdout from latest xgamma call."""
        return self.lastRawOutput

    def getLastGammaReadSource(self):
        """How current gamma values were obtained: xgamma, xrandr, or default."""
        return self.lastGammaReadSource

    def getLastGammaReadClamped(self):
        """True if last read values were outside product range and clamped (SEC-011)."""
        return self.lastGammaReadClamped

    def getLastApplyRawOutput(self):
        """Return captured stdout/stderr from the latest applyGamma run."""
        return self.lastApplyRawOutput

    def set_last_apply_raw_output(self, text):
        """Sync last apply diagnostics on the GUI thread after async apply (SEC-004)."""
        self.lastApplyRawOutput = text if text is not None else ''

    def _prepare_gamma_scalar(self, value):
        """
        Map one user/API gamma to the product range [MIN_GAMMA, MAX_GAMMA].

        Finite out-of-range values are clamped. nan/inf and non-numeric inputs
        are rejected (return None) so they never reach xgamma argv.
        """
        try:
            x = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(x):
            return None
        return max(self.MIN_GAMMA, min(self.MAX_GAMMA, x))
    
    def applyGamma(self, red=None, green=None, blue=None, overall=None):
        """
        Apply gamma correction using xgamma command.
        
        Args:
            red (float, optional): Red channel gamma value
            green (float, optional): Green channel gamma value
            blue (float, optional): Blue channel gamma value
            overall (float, optional): Overall gamma value (applies to all channels)
        
        Returns:
            bool: True if command executed successfully, False otherwise
        """
        if not self.isXgammaAvailable():
            self.lastApplyRawOutput = 'xgamma not available'
            return False
        
        # Собираем аргументы для команды xgamma, чтобы применить коррекцию гаммы.
        args = [self.xgammaPath]
        
        if overall is not None:
            prepared = self._prepare_gamma_scalar(overall)
            if prepared is None:
                self.lastApplyRawOutput = 'invalid gamma value (non-finite or non-numeric)'
                return False
            args.extend(['-gamma', str(prepared)])
        else:
            # Если общее значение не указано, применяем индивидуальные значения гаммы для каждого запрошенного цветового канала.
            if red is not None:
                prepared = self._prepare_gamma_scalar(red)
                if prepared is None:
                    self.lastApplyRawOutput = 'invalid gamma value (non-finite or non-numeric)'
                    return False
                args.extend(['-rgamma', str(prepared)])
            if green is not None:
                prepared = self._prepare_gamma_scalar(green)
                if prepared is None:
                    self.lastApplyRawOutput = 'invalid gamma value (non-finite or non-numeric)'
                    return False
                args.extend(['-ggamma', str(prepared)])
            if blue is not None:
                prepared = self._prepare_gamma_scalar(blue)
                if prepared is None:
                    self.lastApplyRawOutput = 'invalid gamma value (non-finite or non-numeric)'
                    return False
                args.extend(['-bgamma', str(prepared)])
        
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=5
            )
            out = (result.stdout or '').strip()
            err = (result.stderr or '').strip()
            parts = [p for p in (out, err) if p]
            self.lastApplyRawOutput = '\n'.join(parts) if parts else '(no output)'
            return result.returncode == 0
        except subprocess.TimeoutExpired as error:
            self.lastApplyRawOutput = 'timeout: {}'.format(error)
            return False
        except Exception as error:
            self.lastApplyRawOutput = str(error)
            return False
    
    def buildXgammaArgv(self, red=None, green=None, blue=None, overall=None):
        """
        Build argv list for xgamma (executable path + flags/values).

        Returns:
            list[str]: Non-empty argv, or [] if xgamma is unavailable or values are invalid.
        """
        if not self.isXgammaAvailable():
            return []

        argv = [self.xgammaPath]

        if overall is not None:
            prepared = self._prepare_gamma_scalar(overall)
            if prepared is None:
                return []
            argv.extend(['-gamma', str(prepared)])
        else:
            if red is not None:
                prepared = self._prepare_gamma_scalar(red)
                if prepared is None:
                    return []
                argv.extend(['-rgamma', str(prepared)])
            if green is not None:
                prepared = self._prepare_gamma_scalar(green)
                if prepared is None:
                    return []
                argv.extend(['-ggamma', str(prepared)])
            if blue is not None:
                prepared = self._prepare_gamma_scalar(blue)
                if prepared is None:
                    return []
                argv.extend(['-bgamma', str(prepared)])

        return argv

    def buildXgammaCommand(self, red=None, green=None, blue=None, overall=None):
        """
        Build xgamma Exec= value for autostart (.desktop), with Desktop Entry quoting (SEC-008).

        Args:
            red (float, optional): Red channel gamma value
            green (float, optional): Green channel gamma value
            blue (float, optional): Blue channel gamma value
            overall (float, optional): Overall gamma value

        Returns:
            str: Exec line value (no ``Exec=`` prefix), or "" if unavailable/invalid
        """
        argv = self.buildXgammaArgv(
            red=red, green=green, blue=blue, overall=overall
        )
        if not argv:
            return ''
        return format_desktop_exec_line(argv)

    def _defaultGammaValues(self):
        """Return fallback gamma values."""
        return {
            'red': self.DEFAULT_GAMMA,
            'green': self.DEFAULT_GAMMA,
            'blue': self.DEFAULT_GAMMA
        }

    # Matches a float token as printed by typical xgamma/xrandr (incl. scientific notation).
    _FLOAT_TOKEN = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'

    def _finalize_read_gamma_dict(self, parsed):
        """
        Require finite R/G/B and clamp to product range. Non-finite → parse failure (None).
        Returns (dict | None, clamped_flag).
        """
        if not parsed:
            return None, False
        try:
            r = float(parsed['red'])
            g = float(parsed['green'])
            b = float(parsed['blue'])
        except (KeyError, TypeError, ValueError):
            return None, False
        if not all(math.isfinite(x) for x in (r, g, b)):
            return None, False
        out = {}
        clamped = False
        for key, v in (('red', r), ('green', g), ('blue', b)):
            c = max(self.MIN_GAMMA, min(self.MAX_GAMMA, v))
            if c != v:
                clamped = True
            out[key] = c
        return out, clamped

    def _parseGammaFromString(self, text):
        """Parse gamma triplet from xgamma stdout/stderr (raw floats, not yet clamped)."""
        if not text:
            return None
        t = self._FLOAT_TOKEN
        redMatch = re.search(r'Red\s+({})'.format(t), text)
        greenMatch = re.search(r'Green\s+({})'.format(t), text)
        blueMatch = re.search(r'Blue\s+({})'.format(t), text)
        if not (redMatch and greenMatch and blueMatch):
            return None
        try:
            return {
                'red': float(redMatch.group(1)),
                'green': float(greenMatch.group(1)),
                'blue': float(blueMatch.group(1))
            }
        except ValueError:
            return None

    def _readGammaFromXrandr(self):
        """Fallback gamma detection using xrandr --verbose output."""
        xrandr_path = resolve_command('xrandr')
        if not xrandr_path:
            return None, False
        try:
            result = subprocess.run(
                [xrandr_path, '--verbose'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return None, False
        
        t = self._FLOAT_TOKEN
        match = re.search(
            r'Gamma:\s*({t}):({t}):({t})'.format(t=t),
            result.stdout or '',
        )
        if not match:
            return None, False
        try:
            raw = {
                'red': float(match.group(1)),
                'green': float(match.group(2)),
                'blue': float(match.group(3))
            }
        except ValueError:
            return None, False
        return self._finalize_read_gamma_dict(raw)