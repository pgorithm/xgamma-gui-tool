"""
Module for managing autostart configuration.
Handles adding and removing xgamma commands from ~/.config/autostart/
"""

import logging
import os
from pathlib import Path
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)


class AutostartSaveResult(NamedTuple):
    ok: bool
    error_message: Optional[str]


class AutostartRemoveResult(NamedTuple):
    ok: bool
    error_message: Optional[str]
    removed: bool


def _user_safe_fs_reason(exc: BaseException) -> str:
    """Brief reason for status bar; no full paths (PRD §7)."""
    if isinstance(exc, PermissionError):
        return 'permission denied'
    if isinstance(exc, OSError) and exc.strerror:
        return exc.strerror
    return type(exc).__name__


class ConfigManager:
    """Manager for autostart configuration files."""
    
    AUTOSTART_DIR = Path.home() / '.config' / 'autostart'
    DESKTOP_FILE = AUTOSTART_DIR / 'xgamma_gui_tool.desktop'
    COMMENT_PREFIX = '# Applied by xgamma GUI Tool'
    
    def __init__(self):
        """Initialize ConfigManager and ensure autostart directory exists."""
        self.autostartDir = self.AUTOSTART_DIR
        self.desktopFile = self.DESKTOP_FILE
        self._ensureAutostartDir()
    
    def _ensureAutostartDir(self):
        """Create autostart directory if it doesn't exist."""
        self.autostartDir.mkdir(parents=True, exist_ok=True)
    
    def saveToAutostart(self, xgammaCommand):
        """
        Save xgamma command to autostart.
        
        Args:
            xgammaCommand (str): xgamma command string to execute on startup
        
        Returns:
            AutostartSaveResult: ok and optional user-safe error_message
        """
        try:
            # Формируем содержимое desktop-файла
            desktopContent = f"""[Desktop Entry]
Type=Application
Name=xgamma Gamma Adjustment
Comment={self.COMMENT_PREFIX}
Exec={xgammaCommand}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
            
            # Записываем desktop-файл
            self.desktopFile.write_text(desktopContent, encoding='utf-8')
            
            # Делаем файл исполняемым
            os.chmod(self.desktopFile, 0o755)
            
            return AutostartSaveResult(True, None)
        except Exception as exc:
            logger.exception(
                'Failed to write autostart desktop file at %s',
                self.desktopFile,
            )
            return AutostartSaveResult(False, _user_safe_fs_reason(exc))
    
    def removeFromAutostart(self):
        """
        Remove this app's autostart desktop file only (PRD 3.6, §7).
        
        Returns:
            AutostartRemoveResult: ok, optional user-safe error_message, removed flag
        """
        if not self.desktopFile.exists():
            return AutostartRemoveResult(True, None, False)
        try:
            self.desktopFile.unlink()
            return AutostartRemoveResult(True, None, True)
        except Exception as exc:
            logger.exception(
                'Failed to remove autostart desktop file at %s',
                self.desktopFile,
            )
            return AutostartRemoveResult(
                False,
                _user_safe_fs_reason(exc),
                False,
            )
    
    def isInAutostart(self):
        """
        Check if xgamma is configured in autostart.
        
        Returns:
            bool: True if xgamma is in autostart, False otherwise
        """
        # Проверяем наш desktop-файл
        if self.desktopFile.exists():
            return True
        
        # Ищем xgamma в остальных desktop-файлах
        if self.autostartDir.exists():
            for desktopFile in self.autostartDir.glob('*.desktop'):
                try:
                    content = desktopFile.read_text(encoding='utf-8')
                    if 'xgamma' in content.lower():
                        return True
                except Exception:
                    continue
        
        return False