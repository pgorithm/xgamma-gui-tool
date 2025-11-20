"""
Module for managing autostart configuration.
Handles adding and removing xgamma commands from ~/.config/autostart/
"""

import os
import re
from pathlib import Path


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
            bool: True if saved successfully, False otherwise
        """
        try:
            # Create desktop file content
            desktopContent = f"""[Desktop Entry]
Type=Application
Name=xgamma Gamma Adjustment
Comment={self.COMMENT_PREFIX}
Exec={xgammaCommand}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
            
            # Write to desktop file
            self.desktopFile.write_text(desktopContent, encoding='utf-8')
            
            # Make file executable
            os.chmod(self.desktopFile, 0o755)
            
            return True
        except Exception:
            return False
    
    def removeFromAutostart(self):
        """
        Remove xgamma commands from autostart.
        Removes all xgamma-related entries from autostart directory.
        
        Returns:
            bool: True if removed successfully, False otherwise
        """
        try:
            removed = False
            
            # Remove our desktop file if it exists
            if self.desktopFile.exists():
                self.desktopFile.unlink()
                removed = True
            
            # Scan all desktop files in autostart directory
            # and remove any that contain xgamma commands
            if self.autostartDir.exists():
                for desktopFile in self.autostartDir.glob('*.desktop'):
                    try:
                        content = desktopFile.read_text(encoding='utf-8')
                        # Check if file contains xgamma command
                        if 'xgamma' in content.lower():
                            desktopFile.unlink()
                            removed = True
                    except Exception:
                        # Skip files that can't be read
                        continue
            
            return removed
        except Exception:
            return False
    
    def isInAutostart(self):
        """
        Check if xgamma is configured in autostart.
        
        Returns:
            bool: True if xgamma is in autostart, False otherwise
        """
        # Check our desktop file
        if self.desktopFile.exists():
            return True
        
        # Check other desktop files for xgamma
        if self.autostartDir.exists():
            for desktopFile in self.autostartDir.glob('*.desktop'):
                try:
                    content = desktopFile.read_text(encoding='utf-8')
                    if 'xgamma' in content.lower():
                        return True
                except Exception:
                    continue
        
        return False

