"""
Main entry point for xgamma GUI Tool application.
Handles dependency checks and application initialization.
"""

import logging
import sys
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QApplication, QMessageBox
from .gamma_core import GammaCore
from .config_manager import ConfigManager
from .gui import GammaMainWindow
from .i18n import install_translators


def checkDependencies():
    """
    Check if all required dependencies are available.
    
    Returns:
        tuple: (bool, str) - (is_available, error_message)
    """
    gammaCore = GammaCore()
    
    if not gammaCore.isXgammaAvailable():
        return False, QCoreApplication.translate(
            "main",
            "xgamma is not installed or not found in PATH.\n\n"
            "Please install xgamma using one of the following commands:\n\n"
            "Ubuntu/Debian: sudo apt-get install x11-xserver-utils\n"
            "Fedora: sudo dnf install xorg-x11-server-utils\n"
            "Arch Linux: sudo pacman -S xorg-xgamma\n\n"
            "After installation, please restart the application.",
        )

    return True, QCoreApplication.translate("main", "Ok")


def main():
    """Main application entry point."""
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s %(name)s: %(message)s',
        )

    # Создаем QApplication
    app = QApplication(sys.argv)
    app.setApplicationName('xgamma GUI Tool')
    install_translators(app)

    # Проверяем зависимости (xgamma)
    isAvailable, errorMessage = checkDependencies()
    if not isAvailable:
        # Показываем сообщение об ошибке и выходим
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle(
            QCoreApplication.translate("main", "xgamma GUI Tool - Missing Dependency")
        )
        msgBox.setText(QCoreApplication.translate("main", "xgamma Not Found"))
        msgBox.setInformativeText(errorMessage)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()
        sys.exit(1)
    
    # Инициализируем основные компоненты
    gammaCore = GammaCore()
    configManager = ConfigManager()
    
    # Создаем и отображаем главное окно
    mainWindow = GammaMainWindow(gammaCore, configManager)
    mainWindow.show()
    
    # Запускаем приложение
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()