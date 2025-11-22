"""
Core module for gamma management using xgamma command.
Handles xgamma availability check, command execution, and current values reading.
"""

import subprocess
import shutil
import re


class GammaCore:
    """Core class for managing gamma settings via xgamma command."""
    
    DEFAULT_GAMMA = 1.0
    MIN_GAMMA = 0.01
    MAX_GAMMA = 5.0
    
    def __init__(self):
        """Initialize GammaCore and check xgamma availability."""
        self.xgammaPath = self._findXgamma()
    
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
            return {
                'red': self.DEFAULT_GAMMA,
                'green': self.DEFAULT_GAMMA,
                'blue': self.DEFAULT_GAMMA
            }
        
        try:
            # Run xgamma without parameters to get current values
            result = subprocess.run(
                [self.xgammaPath],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Parse output like: "-> Red  1.000, Green  1.000, Blue  1.000"
            output = result.stdout
            redMatch = re.search(r'Red\s+([\d.]+)', output)
            greenMatch = re.search(r'Green\s+([\d.]+)', output)
            blueMatch = re.search(r'Blue\s+([\d.]+)', output)
            
            red = float(redMatch.group(1)) if redMatch else self.DEFAULT_GAMMA
            green = float(greenMatch.group(1)) if greenMatch else self.DEFAULT_GAMMA
            blue = float(blueMatch.group(1)) if blueMatch else self.DEFAULT_GAMMA
            
            return {
                'red': red,
                'green': green,
                'blue': blue
            }
        except (subprocess.TimeoutExpired, ValueError, AttributeError, Exception):
            # Return default values on any error
            return {
                'red': self.DEFAULT_GAMMA,
                'green': self.DEFAULT_GAMMA,
                'blue': self.DEFAULT_GAMMA
            }
    
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
            return False
        
        # Build command arguments
        args = [self.xgammaPath]
        
        if overall is not None:
            # Apply overall gamma to all channels
            args.extend(['-gamma', str(overall)])
        else:
            # Apply individual channel values
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
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
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