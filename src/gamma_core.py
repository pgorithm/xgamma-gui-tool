"""Gamma Core Module.

This module provides the core functionality for managing display gamma settings
using the `xgamma` command-line utility. It handles checking for `xgamma`
availability, executing gamma correction commands, and parsing current
gamma values from the system.
"""

import subprocess
import shutil
import re


class GammaCore:
    """Core class for managing gamma settings via xgamma command."""
    
    DEFAULT_GAMMA = 1.000
    MIN_GAMMA = 0.010
    MAX_GAMMA = 5.000
    
    def __init__(self):
        """Initialize GammaCore and check xgamma availability."""
        self.xgammaPath = self._findXgamma()
        self.lastRawOutput = ''  # Последний stdout от xgamma, для отладки
        self.lastApplyRawOutput = ''  # Вывод последнего вызова xgamma при apply (успех или сбой)
    
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
                return parsedGamma
            
            # Пробуем получить данные через xrandr как запасной вариант
            fallbackGamma = self._readGammaFromXrandr()
            if fallbackGamma:
                self.lastRawOutput = 'xrandr fallback: {}'.format(fallbackGamma)
                return fallbackGamma
            
            return self._defaultGammaValues()
        except (subprocess.TimeoutExpired, ValueError, AttributeError, Exception) as error:
            # При любой ошибке пробуем fallback, иначе значения по умолчанию
            self.lastRawOutput = str(error)
            fallbackGamma = self._readGammaFromXrandr()
            if fallbackGamma:
                self.lastRawOutput = 'xrandr fallback after error: {}'.format(fallbackGamma)
                return fallbackGamma
            return self._defaultGammaValues()

    def getLastRawOutput(self):
        """Return raw stdout from latest xgamma call."""
        return self.lastRawOutput

    def getLastApplyRawOutput(self):
        """Return captured stdout/stderr from the latest applyGamma run."""
        return self.lastApplyRawOutput
    
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
            # Если указано общее значение гаммы, применяем его ко всем цветовым каналам для равномерной коррекции.
            args.extend(['-gamma', str(overall)])
        else:
            # Если общее значение не указано, применяем индивидуальные значения гаммы для каждого запрошенного цветового канала.
            if red is not None:
                args.extend(['-rgamma', str(red)])
            if green is not None:
                args.extend(['-ggamma', str(green)])
            if blue is not None:
                args.extend(['-bgamma', str(blue)])
        
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
            parts.extend(['-gamma', str(overall)])
        else:
            if red is not None:
                parts.extend(['-rgamma', str(red)])
            if green is not None:
                parts.extend(['-ggamma', str(green)])
            if blue is not None:
                parts.extend(['-bgamma', str(blue)])
        
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