"""
Main entry point for xgamma GUI Tool application.
Handles dependency checks and application initialization.
"""

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from .gamma_core import GammaCore
from .config_manager import ConfigManager
from .gui import GammaMainWindow


def checkDependencies():
    """
    Check if all required dependencies are available.
    
    Returns:
        tuple: (bool, str) - (is_available, error_message)
    """
    gammaCore = GammaCore()
    
    if not gammaCore.isXgammaAvailable():
        return False, (
            "xgamma is not installed or not found in PATH.\n\n"
            "Please install xgamma using one of the following commands:\n\n"
            "Ubuntu/Debian: sudo apt-get install x11-xserver-utils\n"
            "Fedora: sudo dnf install xorg-x11-server-utils\n"
            "Arch Linux: sudo pacman -S xorg-xgamma\n\n"
            "After installation, please restart the application."
        )
    
    return True, ""


def main():
    """Main application entry point."""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName('xgamma GUI Tool')
    
    # Check dependencies
    isAvailable, errorMessage = checkDependencies()
    if not isAvailable:
        # Show error message and exit
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle('xgamma GUI Tool - Missing Dependency')
        msgBox.setText('xgamma Not Found')
        msgBox.setInformativeText(errorMessage)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()
        sys.exit(1)
    
    # Initialize core components
    gammaCore = GammaCore()
    configManager = ConfigManager()
    
    # Create and show main window
    mainWindow = GammaMainWindow(gammaCore, configManager)
    mainWindow.show()
    
    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

