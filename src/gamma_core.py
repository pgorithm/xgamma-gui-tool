"""Gamma Core Module.

This module provides the core functionality for managing display gamma settings
using the `xgamma` command-line utility. It handles checking for `xgamma`
availability, executing gamma correction commands, and parsing current
gamma values from the system.
"""

import math
import re
import shutil
import subprocess


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
    
    def _findXgamma(self):
        """
        Find xgamma executable in system PATH.
        
        Returns:
            str: Path to xgamma executable or None if not found
        """
        return shutil.which('xgamma')
    
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
            return self._defaultGammaValues()
        
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
            if parsedGamma:
                self.lastGammaReadSource = 'xgamma'
                return parsedGamma
            
            # Пробуем получить данные через xrandr как запасной вариант
            fallbackGamma = self._readGammaFromXrandr()
            if fallbackGamma:
                self.lastRawOutput = 'xrandr fallback: {}'.format(fallbackGamma)
                self.lastGammaReadSource = 'xrandr'
                return fallbackGamma
            
            self.lastGammaReadSource = 'default'
            return self._defaultGammaValues()
        except (subprocess.TimeoutExpired, ValueError, AttributeError, Exception) as error:
            # При любой ошибке пробуем fallback, иначе значения по умолчанию
            self.lastRawOutput = str(error)
            fallbackGamma = self._readGammaFromXrandr()
            if fallbackGamma:
                self.lastRawOutput = 'xrandr fallback after error: {}'.format(fallbackGamma)
                self.lastGammaReadSource = 'xrandr'
                return fallbackGamma
            self.lastGammaReadSource = 'default'
            return self._defaultGammaValues()

    def getLastRawOutput(self):
        """Return raw stdout from latest xgamma call."""
        return self.lastRawOutput

    def getLastGammaReadSource(self):
        """How current gamma values were obtained: xgamma, xrandr, or default."""
        return self.lastGammaReadSource

    def getLastApplyRawOutput(self):
        """Return captured stdout/stderr from the latest applyGamma run."""
        return self.lastApplyRawOutput

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
    
    def buildXgammaCommand(self, red=None, green=None, blue=None, overall=None):
        """
        Build xgamma command string for autostart.
        
        Args:
            red (float, optional): Red channel gamma value
            green (float, optional): Green channel gamma value
            blue (float, optional): Blue channel gamma value
            overall (float, optional): Overall gamma value
        
        Returns:
            str: Command string ready for autostart file
        """
        if not self.isXgammaAvailable():
            return ""
        
        parts = [self.xgammaPath]
        
        if overall is not None:
            prepared = self._prepare_gamma_scalar(overall)
            if prepared is None:
                return ""
            parts.extend(['-gamma', str(prepared)])
        else:
            if red is not None:
                prepared = self._prepare_gamma_scalar(red)
                if prepared is None:
                    return ""
                parts.extend(['-rgamma', str(prepared)])
            if green is not None:
                prepared = self._prepare_gamma_scalar(green)
                if prepared is None:
                    return ""
                parts.extend(['-ggamma', str(prepared)])
            if blue is not None:
                prepared = self._prepare_gamma_scalar(blue)
                if prepared is None:
                    return ""
                parts.extend(['-bgamma', str(prepared)])
        
        return ' '.join(parts)

    def _defaultGammaValues(self):
        """Return fallback gamma values."""
        return {
            'red': self.DEFAULT_GAMMA,
            'green': self.DEFAULT_GAMMA,
            'blue': self.DEFAULT_GAMMA
        }

    def _parseGammaFromString(self, text):
        """Parse gamma triplet from xgamma stdout/stderr."""
        if not text:
            return None
        redMatch = re.search(r'Red\s+([\d.]+)', text)
        greenMatch = re.search(r'Green\s+([\d.]+)', text)
        blueMatch = re.search(r'Blue\s+([\d.]+)', text)
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
        try:
            result = subprocess.run(
                ['xrandr', '--verbose'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return None
        
        match = re.search(r'Gamma:\s*([\d.]+):([\d.]+):([\d.]+)', result.stdout)
        if not match:
            return None
        try:
            return {
                'red': float(match.group(1)),
                'green': float(match.group(2)),
                'blue': float(match.group(3))
            }
        except ValueError:
            return None