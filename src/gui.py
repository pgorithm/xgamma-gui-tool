"""
Main GUI module for xgamma GUI Tool.
Implements PyQt5 interface with sliders, reference image, and control buttons.
"""

import subprocess

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QPushButton, QLineEdit, QStatusBar,
    QSizePolicy, QApplication, QDialog,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QEvent, QSize
from PyQt5.QtGui import QPixmap, QFontMetrics, QPainter, QPen, QBrush, QColor, QIcon
from .gamma_core import GammaCore
from .reference_image import ReferenceImageGenerator
from .config_manager import ConfigManager


class SettingsDialog(QDialog):
    """Minimal modal settings placeholder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setModal(True)
        layout = QVBoxLayout(self)
        infoLabel = QLabel('WIP, sorry')
        infoLabel.setWordWrap(True)
        layout.addWidget(infoLabel)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)


class GammaMainWindow(QMainWindow):
    """Main application window for gamma adjustment."""
    
    def __init__(self, gammaCore, configManager):
        """
        Initialize main window.
        
        Args:
            gammaCore (GammaCore): Gamma core instance
            configManager (ConfigManager): Config manager instance
        """
        super().__init__()
        self.gammaCore = gammaCore
        self.configManager = configManager
        self.isUpdating = False  # Флаг, предотвращающий циклические обновления
        self.activeChannel = None  # Отслеживает ползунок, которым управляют с клавиатуры
        self.widgetChannel = {}
        self.warningMessages = []
        
        self.setWindowTitle('xgamma GUI Tool')
        self.setMinimumSize(600, 500)
        
        # Создаем центральный виджет и компоновку
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.setSpacing(15)
        mainLayout.setContentsMargins(15, 15, 15, 15)
        
        # Верхняя панель с иконками действий
        topPanel = QHBoxLayout()
        topPanel.addStretch()
        self.settingsButton = self._buildIconButton(
            self._createGearIcon(),
            'Settings',
            self._openSettingsDialog
        )
        topPanel.addWidget(self.settingsButton)
        self.warningIconLabel = QLabel()
        self.warningIconLabel.setVisible(False)
        self.warningIconLabel.setAlignment(Qt.AlignCenter)
        self.warningIconLabel.setFixedSize(32, 32)
        topPanel.addWidget(self.warningIconLabel)
        mainLayout.addLayout(topPanel)
        
        # В заголовке указываем, что эталонное изображение при изменении гаммы остается статичным
        self.referenceTitleLabel = QLabel('Static Reference')
        self.referenceTitleLabel.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(self.referenceTitleLabel)
        
        # Создаем эталонное изображение
        self.imageGenerator = ReferenceImageGenerator(600, 300)
        self.referenceLabel = QLabel()
        self.referenceLabel.setAlignment(Qt.AlignCenter)
        self.referenceLabel.setMinimumHeight(300)
        self.referenceLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.referenceLabel.setScaledContents(True)
        self._updateReferenceImage()
        mainLayout.addWidget(self.referenceLabel)
        
        # Создаем слайдеры и поля значений
        self.sliders = {}
        self.valueInputs = {}
        
        channels = [
            ('red', 'Red'),
            ('green', 'Green'),
            ('blue', 'Blue'),
            ('all', 'All')
        ]
        fontMetrics = QFontMetrics(self.font())
        maxLabelWidth = max(fontMetrics.width(f'{label}:') for _, label in channels) + 10
        
        for channel, label in channels:
            sliderLayout = QHBoxLayout()
            
            # Подпись
            channelLabel = QLabel(f'{label}:')
            channelLabel.setFixedWidth(maxLabelWidth)
            channelLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sliderLayout.addWidget(channelLabel)
            
            # Ползунок
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(1)  # 0.01 * 100
            slider.setMaximum(500)  # 5.0 * 100
            slider.setValue(100)  # 1.0 * 100
            slider.setTickPosition(QSlider.NoTicks)
            slider.valueChanged.connect(
                lambda value, ch=channel: self._onSliderChanged(ch, value)
            )
            self.widgetChannel[slider] = channel
            self.sliders[channel] = slider
            sliderLayout.addWidget(slider)
            
            # Поле ввода значения
            valueInput = QLineEdit()
            valueInput.setMinimumWidth(60)
            valueInput.setMaximumWidth(60)
            valueInput.setText('1.00')
            valueInput.setAlignment(Qt.AlignCenter)
            valueInput.editingFinished.connect(
                lambda ch=channel: self._onValueInputChanged(ch)
            )
            self.widgetChannel[valueInput] = channel
            self.valueInputs[channel] = valueInput
            sliderLayout.addWidget(valueInput)
            
            mainLayout.addLayout(sliderLayout)
        
        # Создаем кнопки управления
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        
        self.resetButton = QPushButton('Reset')
        self.resetButton.clicked.connect(self._onResetClicked)
        buttonLayout.addWidget(self.resetButton)
        
        buttonLayout.addStretch()
        
        self.saveButton = QPushButton('Apply')
        self.saveButton.clicked.connect(self._onSaveClicked)
        buttonLayout.addWidget(self.saveButton)
        
        buttonLayout.addStretch()
        
        mainLayout.addLayout(buttonLayout)
        
        # Создаем строку состояния
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')
        
        # Загружаем текущие значения гаммы из системы
        self._loadCurrentGamma()
        self._collectEnvironmentWarnings()
        
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
    
    def _updateReferenceImage(self):
        """Update reference image display."""
        pixmap = self.imageGenerator.generateImage()
        self.referenceLabel.setPixmap(pixmap)
    
    def _sliderValueToGamma(self, sliderValue):
        """
        Convert slider value to gamma value.
        
        Args:
            sliderValue (int): Slider value (1-500)
        
        Returns:
            float: Gamma value (0.01-5.0)
        """
        return sliderValue / 100.0
    
    def _gammaToSliderValue(self, gamma):
        """
        Convert gamma value to slider value.
        
        Args:
            gamma (float): Gamma value (0.01-5.0)
        
        Returns:
            int: Slider value (1-500)
        """
        return int(gamma * 100)
    
    def _setActiveChannel(self, channel):
        """Mark channel as keyboard-controlled."""
        self.activeChannel = channel
    
    def _clearActiveChannel(self):
        """Reset keyboard-controlled channel."""
        self.activeChannel = None
    
    def _adjustActiveSlider(self, delta):
        """Adjust active slider value by delta ticks."""
        if not self.activeChannel:
            return
        
        slider = self.sliders[self.activeChannel]
        newValue = max(slider.minimum(), min(slider.maximum(), slider.value() + delta))
        if newValue != slider.value():
            slider.setValue(newValue)
    
    def _onSliderChanged(self, channel, value):
        """
        Handle slider value change.
        
        Args:
            channel (str): Channel name ('red', 'green', 'blue', 'all')
            value (int): New slider value
        """
        if self.isUpdating:
            return
        
        self.isUpdating = True
        
        gamma = self._sliderValueToGamma(value)
        
        if channel == 'all':
            # Выравниваем все RGB-ползунки (блокируем сигналы, чтобы избежать рекурсии)
            self.sliders['red'].blockSignals(True)
            self.sliders['green'].blockSignals(True)
            self.sliders['blue'].blockSignals(True)
            
            self.sliders['red'].setValue(value)
            self.sliders['green'].setValue(value)
            self.sliders['blue'].setValue(value)
            
            self.sliders['red'].blockSignals(False)
            self.sliders['green'].blockSignals(False)
            self.sliders['blue'].blockSignals(False)
            
            # Обновляем поля значений
            self.valueInputs['red'].setText(f'{gamma:.2f}')
            self.valueInputs['green'].setText(f'{gamma:.2f}')
            self.valueInputs['blue'].setText(f'{gamma:.2f}')
            self.valueInputs['all'].setText(f'{gamma:.2f}')
            
            # Применяем гамму
            self.gammaCore.applyGamma(overall=gamma)
        else:
            # Обновляем конкретный канал
            self.valueInputs[channel].setText(f'{gamma:.2f}')
            
            # Синхронизируем ползунок "all" со средним по RGB (тоже блокируем сигналы)
            # Возможно, в будущем его нужно будет нахрен убрать
            redGamma = self._sliderValueToGamma(self.sliders['red'].value())
            greenGamma = self._sliderValueToGamma(self.sliders['green'].value())
            blueGamma = self._sliderValueToGamma(self.sliders['blue'].value())
            avgGamma = (redGamma + greenGamma + blueGamma) / 3.0
            avgSliderValue = self._gammaToSliderValue(avgGamma)
            
            self.sliders['all'].blockSignals(True)
            self.sliders['all'].setValue(avgSliderValue)
            self.sliders['all'].blockSignals(False)
            self.valueInputs['all'].setText(f'{avgGamma:.2f}')
            
            # Применяем гамму
            red = self._sliderValueToGamma(self.sliders['red'].value())
            green = self._sliderValueToGamma(self.sliders['green'].value())
            blue = self._sliderValueToGamma(self.sliders['blue'].value())
            self.gammaCore.applyGamma(red=red, green=green, blue=blue)
        
        self._updateReferenceImage()
        self.isUpdating = False
    
    def _buildIconButton(self, icon, tooltip, handler):
        """Create flat icon button."""
        button = QPushButton()
        button.setFlat(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setIcon(icon)
        button.setIconSize(QSize(22, 22))
        button.setToolTip(tooltip)
        button.clicked.connect(handler)
        button.setFixedSize(32, 32)
        return button
    
    def _createGearIcon(self):
        """Build gear icon pixmap."""
        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor('#2f2f2f'))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(6, 6, 12, 12)
        for angle in range(0, 360, 60):
            painter.save()
            painter.translate(size / 2, size / 2)
            painter.rotate(angle)
            painter.drawLine(0, -10, 0, -6)
            painter.restore()
        painter.end()
        return QIcon(pixmap)
    
    def _createWarningIcon(self):
        """Build warning icon pixmap."""
        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor('#f6c343')))
        painter.setPen(QPen(QColor('#b8860b'), 1))
        painter.drawEllipse(1, 1, size - 2, size - 2)
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(size / 2, 6, size / 2, 14)
        painter.drawPoint(size / 2, 18)
        painter.end()
        return QPixmap(pixmap)
    
    def _openSettingsDialog(self):
        """Show settings modal."""
        dialog = SettingsDialog(self)
        dialog.exec_()
    
    def _collectEnvironmentWarnings(self):
        """Gather warning messages and update indicator."""
        messages = []
        if self._isVirtualMachine():
            messages.append('VM environment may limit gamma adjustment.')
        if self._isHdrPipelineActive():
            messages.append('HDR or 10-bit mode may disable manual gamma adjustment.')
        self.warningMessages = messages
        self._updateWarningIndicator()
    
    def _updateWarningIndicator(self):
        """Show or hide warning icon with tooltip."""
        hasWarnings = bool(self.warningMessages)
        self.warningIconLabel.setVisible(hasWarnings)
        if hasWarnings:
            self.warningIconLabel.setPixmap(self._createWarningIcon())
            tooltip = '\n'.join(self.warningMessages)
            self.warningIconLabel.setToolTip(tooltip)
        else:
            self.warningIconLabel.setToolTip('')
    
    def _readSystemHint(self, path):
        """Read single line helper."""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.readline().strip()
        except (FileNotFoundError, PermissionError, OSError):
            return ''
    
    def _isVirtualMachine(self):
        """Best-effort VM detection."""
        keywords = ['virtualbox', 'vmware', 'kvm', 'qemu', 'hyper-v', 'parallels']
        hints = [
            self._readSystemHint('/sys/class/dmi/id/product_name'),
            self._readSystemHint('/sys/class/dmi/id/sys_vendor')
        ]
        for hint in hints:
            lowered = hint.lower()
            if lowered and any(word in lowered for word in keywords):
                return True
        try:
            result = subprocess.run(
                ['systemd-detect-virt'],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0 and result.stdout.strip() not in ('none', '')
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return False
    
    def _isHdrPipelineActive(self):
        """Detect HDR or 10-bit modes via xrandr output."""
        try:
            result = subprocess.run(
                ['xrandr', '--verbose'],
                capture_output=True,
                text=True,
                timeout=3
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return False
        text = result.stdout.lower()
        hdrTokens = ['hdr', '10 bpc', '10-bit', 'deep color']
        return any(token in text for token in hdrTokens)
    
    def _onValueInputChanged(self, channel):
        """
        Handle value input field change.
        
        Args:
            channel (str): Channel name
        """
        if self.isUpdating:
            return
        
        try:
            valueInput = self.valueInputs[channel]
            text = valueInput.text().strip()
            gamma = float(text)
            
            # Проверяем диапазон
            if gamma < GammaCore.MIN_GAMMA:
                gamma = GammaCore.MIN_GAMMA
            elif gamma > GammaCore.MAX_GAMMA:
                gamma = GammaCore.MAX_GAMMA
            
            # Обновляем ползунок
            sliderValue = self._gammaToSliderValue(gamma)
            self.sliders[channel].setValue(sliderValue)
            
            # Вызываем обработчик изменения ползунка
            self._onSliderChanged(channel, sliderValue)
        except ValueError:
            # Некорректное значение, возвращаем предыдущее
            if channel == 'all':
                avgGamma = (
                    self._sliderValueToGamma(self.sliders['red'].value()) +
                    self._sliderValueToGamma(self.sliders['green'].value()) +
                    self._sliderValueToGamma(self.sliders['blue'].value())
                ) / 3.0
                self.valueInputs[channel].setText(f'{avgGamma:.2f}')
            else:
                gamma = self._sliderValueToGamma(self.sliders[channel].value())
                self.valueInputs[channel].setText(f'{gamma:.2f}')
    
    def _onResetClicked(self):
        """Handle reset button click."""
        self.isUpdating = True
        
        # Блокируем сигналы, чтобы не запускать обновления во время сброса
        for slider in self.sliders.values():
            slider.blockSignals(True)
        
        # Сбрасываем все ползунки на 1.00
        for channel in ['red', 'green', 'blue', 'all']:
            self.sliders[channel].setValue(100)  # 1.0 * 100
            self.valueInputs[channel].setText('1.00')
        
        # Снимаем блокировку сигналов
        for slider in self.sliders.values():
            slider.blockSignals(False)
        
        # Применяем гамму по умолчанию
        self.gammaCore.applyGamma(overall=1.0)
        
        # Удаляем из автозапуска
        if self.configManager.removeFromAutostart():
            self.statusBar.showMessage('Reset to defaults and removed from autostart', 3000)
        else:
            self.statusBar.showMessage('Reset to defaults', 3000)
        
        self._updateReferenceImage()
        self.isUpdating = False
    
    def _onSaveClicked(self):
        """Handle save button click."""
        # Получаем текущие значения гаммы
        red = self._sliderValueToGamma(self.sliders['red'].value())
        green = self._sliderValueToGamma(self.sliders['green'].value())
        blue = self._sliderValueToGamma(self.sliders['blue'].value())
        
        # Формируем команду xgamma
        command = self.gammaCore.buildXgammaCommand(red=red, green=green, blue=blue)
        
        if not command:
            self.statusBar.showMessage('Error: xgamma not available', 3000)
            return
        
        # Сохраняем в автозапуск
        if self.configManager.saveToAutostart(command):
            self.statusBar.showMessage('Settings applied and saved to autostart', 3000)
        else:
            self.statusBar.showMessage('Error: Failed to apply and save to autostart', 3000)
    
    def _loadCurrentGamma(self):
        """Load current gamma values from system."""
        current = self.gammaCore.getCurrentGamma()
        
        self.isUpdating = True
        
        # Блокируем сигналы, чтобы исключить лишние обновления при инициализации
        for slider in self.sliders.values():
            slider.blockSignals(True)
        
        # Выставляем значения ползунков и полей
        self.sliders['red'].setValue(self._gammaToSliderValue(current['red']))
        self.sliders['green'].setValue(self._gammaToSliderValue(current['green']))
        self.sliders['blue'].setValue(self._gammaToSliderValue(current['blue']))
        
        self.valueInputs['red'].setText(f"{current['red']:.2f}")
        self.valueInputs['green'].setText(f"{current['green']:.2f}")
        self.valueInputs['blue'].setText(f"{current['blue']:.2f}")
        
        # Считаем и задаем значение для «all»
        avgGamma = (current['red'] + current['green'] + current['blue']) / 3.0
        self.sliders['all'].setValue(self._gammaToSliderValue(avgGamma))
        self.valueInputs['all'].setText(f'{avgGamma:.2f}')
        
        # Снимаем блокировку сигналов
        for slider in self.sliders.values():
            slider.blockSignals(False)
        
        self.isUpdating = False
    
    def eventFilter(self, obj, event):
        """Handle global mouse and keyboard events for slider control."""
        if event.type() == QEvent.MouseButtonPress:
            channel = self.widgetChannel.get(obj)
            if channel:
                self._setActiveChannel(channel)
            else:
                self._clearActiveChannel()
        elif event.type() == QEvent.KeyPress and self.activeChannel:
            if event.key() in (Qt.Key_Left, Qt.Key_Right):
                step = 10 if (event.modifiers() & Qt.ShiftModifier) else 1
                delta = step if event.key() == Qt.Key_Right else -step
                self._adjustActiveSlider(delta)
                return True
        return super().eventFilter(obj, event)