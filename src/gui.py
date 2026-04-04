"""Main Graphical User Interface (GUI) Module for xgamma GUI Tool.

This module implements the primary PyQt5 interface, including gamma sliders,
a reference image display, and various control buttons. It orchestrates
user interactions with the `GammaCore` and `ConfigManager` to provide
a seamless gamma adjustment experience.
"""

import subprocess

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QPushButton, QLineEdit, QStatusBar,
    QSizePolicy, QApplication, QDialog,
    QDialogButtonBox, QCheckBox
)
from PyQt5.QtCore import Qt, QEvent, QSize, QTimer, QRectF
from PyQt5.QtGui import (
    QPixmap, QFontMetrics, QPainter, QPen, QBrush,
    QColor, QIcon, QDoubleValidator
)
from .gamma_core import GammaCore
from .reference_image import ReferenceImageGenerator
from .config_manager import ConfigManager
from PyQt5.QtCore import QThread, pyqtSignal


class InitializationWorker(QThread):
    """
    Worker thread for performing initial blocking operations (gamma detection,
    environment checks) without freezing the GUI.
    """
    finished = pyqtSignal(dict)

    def __init__(self, gammaCore, parent=None):
        super().__init__(parent)
        self.gammaCore = gammaCore

    def run(self):
        """
        Perform blocking gamma detection and environment checks.
        Emit results via the 'finished' signal.
        """
        currentGamma = self.gammaCore.getCurrentGamma()

        # Temporarily create a dummy MainWindow instance to call private methods
        # for environment warnings without instantiating the full GUI.
        # This is a workaround as these methods are currently coupled to MainWindow.
        # In a more extensive refactor, these checks would be moved to GammaCore.
        class DummyMainWindow:
            def __init__(self, gamma_core_instance):
                self.gammaCore = gamma_core_instance
                self._is_vm_cached = None
                self._is_hdr_cached = None

            def _readSystemHint(self, path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                        return file.readline().strip()
                except (FileNotFoundError, PermissionError, OSError):
                    return ''

            def _isVirtualMachine(self):
                if self._is_vm_cached is not None:
                    return self._is_vm_cached
                
                keywords = ['virtualbox', 'vmware', 'kvm', 'qemu', 'hyper-v', 'parallels']
                hints = [
                    self._readSystemHint('/sys/class/dmi/id/product_name'),
                    self._readSystemHint('/sys/class/dmi/id/sys_vendor')
                ]
                for hint in hints:
                    lowered = hint.lower()
                    if lowered and any(word in lowered for word in keywords):
                        self._is_vm_cached = True
                        return True
                try:
                    result = subprocess.run(
                        ['systemd-detect-virt'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    vm_result = result.returncode == 0 and result.stdout.strip() not in ('none', '')
                    self._is_vm_cached = vm_result
                    return vm_result
                except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
                    self._is_vm_cached = False
                    return False

            def _isHdrPipelineActive(self):
                if self._is_hdr_cached is not None:
                    return self._is_hdr_cached
                
                try:
                    result = subprocess.run(
                        ['xrandr', '--verbose'],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
                    self._is_hdr_cached = False
                    return False
                text = result.stdout.lower()
                hdrTokens = ['hdr', '10 bpc', '10-bit', 'deep color']
                hdr_result = any(token in text for token in hdrTokens)
                self._is_hdr_cached = hdr_result
                return hdr_result

            def _collectEnvironmentWarnings(self):
                messages = []
                if self._isVirtualMachine():
                    messages.append('VM environment may limit gamma adjustment.')
                if self._isHdrPipelineActive():
                    messages.append('HDR or 10-bit mode may disable manual gamma adjustment.')
                return messages

        dummy_main_window = DummyMainWindow(self.gammaCore)
        warningMessages = dummy_main_window._collectEnvironmentWarnings()

        self.finished.emit({
            'gamma': currentGamma,
            'warnings': warningMessages,
            'raw_output': self.gammaCore.getLastRawOutput()
        })


class SettingsButton(QWidget):
    """Кнопка с иконкой и текстом."""
    def __init__(self, icon, text, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.iconLabel = QLabel()
        if icon:
            self.iconLabel.setPixmap(icon.pixmap(22, 22))
        self.label = QLabel(text)
        
        layout.addWidget(self.iconLabel)
        layout.addWidget(self.label)
        layout.addStretch()

class SettingsBoolean(QWidget):
    """Галочка с подписью."""
    def __init__(self, text, checked=False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.checkbox = QCheckBox(text)
        self.checkbox.setChecked(checked)
        layout.addWidget(self.checkbox)

class SettingsTextbox(QWidget):
    """Подпись и поле для ввода текста."""
    def __init__(self, text, value="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(text)
        self.textbox = QLineEdit(value)
        layout.addWidget(self.label)
        layout.addWidget(self.textbox)

class SettingsBooleanTextbox(QWidget):
    """Комбинация галочки, подписи и поля для ввода."""
    def __init__(self, checkbox_text, checked=False, textbox_value="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.checkbox = QCheckBox(checkbox_text)
        self.checkbox.setChecked(checked)
        self.textbox = QLineEdit(textbox_value)
        self.textbox.setEnabled(checked)
        self.checkbox.toggled.connect(self.textbox.setEnabled)
        
        layout.addWidget(self.checkbox)
        layout.addStretch()
        layout.addWidget(self.textbox)

class SettingsSlider(QWidget):
    """Слайдер с подписью и полем для значения."""
    def __init__(self, text, value=0, min_val=0, max_val=100, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        top_layout = QHBoxLayout()
        self.label = QLabel(text)
        self.value_label = QLabel(str(value))
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        top_layout.addWidget(self.value_label)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(lambda v: self.value_label.setText(str(v)))
        
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.slider)

def _create_info_icon():
    """Создает иконку 'i' в синем круге."""
    size = 24
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Синий круг
    painter.setBrush(QBrush(QColor('#0078d4')))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    
    # Буква 'i'
    painter.setPen(QPen(Qt.white, 2))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(16)
    painter.setFont(font)
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, 'i')
    
    painter.end()
    return QIcon(pixmap)

class SettingsDialog(QDialog):
    """Модальное окно настроек."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.setModal(True)
        # Минимальный размер окна настроек
        self.setMinimumSize(150, 150)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(15)

        about_button = SettingsButton(
            icon=_create_info_icon(),
            text="About"
        )
        about_button.setToolTip(
            "Version: dev\n"
            "Author: pgorithm\n"
            "GitHub: https://github.com/pgorithm/xgamma_gui_tool\n"
            "hello, world!"
        )
        mainLayout.addWidget(about_button)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(buttonBox)


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
        self.isUpdating = False 
        # Флаг `isUpdating` используется для предотвращения циклических обновлений, когда изменения одного виджета
        # (например, ползунка) вызывают нежелательные обновления других связанных виджетов.
        self.activeChannel = None 
        # `activeChannel` отслеживает, какой ползунок активно управляется с клавиатуры, 
        # что позволяет направленно изменять значения гаммы.
        self.widgetChannel = {}
        self.warningMessages = []
        self.currentGamma = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        
        self.imageUpdateTimer = QTimer()
        self.imageUpdateTimer.setSingleShot(True)
        self.imageUpdateTimer.timeout.connect(self._updateReferenceImage)
        # Таймер `imageUpdateTimer` используется для отложенного обновления эталонного изображения,
        # чтобы избежать частых перерисовок и улучшить производительность GUI при быстрых изменениях гаммы.
        
    
        self.gammaApplyTimer = QTimer()
        self.gammaApplyTimer.setSingleShot(True)
        self.gammaApplyTimer.timeout.connect(self._applyPendingGamma)
        # Таймер `gammaApplyTimer` используется для отложенного применения гаммы к системе,
        # чтобы предотвратить избыточные вызовы xgamma при каждом движении ползунка и уменьшить нагрузку на систему.
        self.pendingGamma = None
        # `pendingGamma` хранит значения гаммы, которые ожидают применения таймером,
        # позволяя накапливать изменения перед их фактическим использованием.
          
        self.setWindowTitle('xgamma GUI Tool')
        self.setMinimumSize(600, 650)
        
        # Создаем центральный виджет и компоновку, чтобы организовать основные элементы интерфейса в едином окне.
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.setSpacing(15)
        mainLayout.setContentsMargins(15, 15, 15, 15)
        
        # Размещаем верхнюю панель с иконками действий для доступа к настройкам и отображению предупреждений.
        topPanel = QHBoxLayout()
        topPanel.addStretch()
        self.settingsButton = self._buildIconButton(
            self._createGearIcon(),
            'Settings',
            self._openSettingsDialog
        )
        self.warningIconLabel = QLabel()
        self.warningIconLabel.setVisible(False)
        self.warningIconLabel.setAlignment(Qt.AlignCenter)
        self.warningIconLabel.setFixedSize(32, 32)
        topPanel.addWidget(self.warningIconLabel)
        topPanel.addWidget(self.settingsButton)
        mainLayout.addLayout(topPanel)
        
        # Инициализируем генератор эталонного изображения, который будет использоваться для визуализации текущих значений гаммы.
        self.imageGenerator = ReferenceImageGenerator(600)
        self.referenceLabel = QLabel()
        self.referenceLabel.setAlignment(Qt.AlignCenter)
        self.referenceLabel.setMinimumHeight(self.imageGenerator.calculatedHeight - 10)
        self.referenceLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.referenceLabel.setScaledContents(True)
        self._updateReferenceImage(self.currentGamma)
        mainLayout.addWidget(self.referenceLabel)
        
        # Инициализируем ползунки и поля ввода значений для каждого цветового канала, чтобы пользователь мог интерактивно управлять гаммой.
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
        
        # Вычисляем оптимальную ширину поля ввода на основе максимального значения гаммы,
        # чтобы обеспечить адекватное отображение всех возможных значений.
        # Формат: "5.000" (текущее максимальное значение) = 5 символов
        maxGammaStr = f'{GammaCore.MAX_GAMMA:.3f}'
        inputFieldWidth = fontMetrics.width(maxGammaStr) + 20  # Добавляем отступы
        
        for channel, label in channels:
            sliderLayout = QHBoxLayout()
            
            # Добавляем текстовую подпись для каждого ползунка, чтобы ясно обозначить, какой цветовой канал он контролирует.
            channelLabel = QLabel(f'{label}:')
            channelLabel.setFixedWidth(maxLabelWidth)
            channelLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sliderLayout.addWidget(channelLabel)
            
            # Вставляем ползунок, который позволяет пользователю изменять значение гаммы для соответствующего канала.
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
            
            # Добавляем поле ввода значения, чтобы пользователь мог вводить точные значения гаммы или просматривать текущие.
            valueInput = QLineEdit()
            valueInput.setMinimumWidth(inputFieldWidth)
            valueInput.setMaximumWidth(inputFieldWidth)
            valueInput.setText('1.000')
            valueInput.setAlignment(Qt.AlignCenter)
            # Ограничиваем ввод в поле только числами с заданной точностью, чтобы предотвратить некорректные значения и обеспечить целостность данных.
            validator = QDoubleValidator(
                GammaCore.MIN_GAMMA,
                GammaCore.MAX_GAMMA,
                3,
                valueInput
            )
            validator.setNotation(QDoubleValidator.StandardNotation)
            valueInput.setValidator(validator)
            # Обрабатываем завершение редактирования поля ввода (потерю фокуса или нажатие Enter), чтобы применить изменения, введенные пользователем.
            valueInput.editingFinished.connect(
                lambda ch=channel: self._onValueInputChanged(ch)
            )
            # Обрабатываем нажатие Enter в поле ввода для немедленного обновления значений, обеспечивая быстрый отклик на действия пользователя.
            valueInput.returnPressed.connect(
                lambda ch=channel: self._onValueInputChanged(ch)
            )
            self.widgetChannel[valueInput] = channel
            self.valueInputs[channel] = valueInput
            sliderLayout.addWidget(valueInput)
            
            mainLayout.addLayout(sliderLayout)
        
        # Создаем кнопки управления (Reset, Apply), чтобы предоставить пользователю функционал для сброса настроек и сохранения изменений.
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
        
        # Инициализируем строку состояния для отображения информации о текущем статусе приложения
        # и возможных предупреждениях.
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')
        
        self.statusBar.showMessage('Loading initial settings...')

        self.worker = InitializationWorker(self.gammaCore)
        self.worker.finished.connect(self._onInitializationComplete)
        self.worker.start()

        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

    def _onInitializationComplete(self, results):
        """
        Slot to receive results from InitializationWorker and update the GUI.
        """
        current = results['gamma']
        self.warningMessages = results['warnings']
        rawOutput = results['raw_output']

        self.isUpdating = True

        for slider in self.sliders.values():
            slider.blockSignals(True)

        self.sliders['red'].setValue(self._gammaToSliderValue(current['red']))
        self.sliders['green'].setValue(self._gammaToSliderValue(current['green']))
        self.sliders['blue'].setValue(self._gammaToSliderValue(current['blue']))

        self.valueInputs['red'].setText(f"{current['red']:.3f}")
        self.valueInputs['green'].setText(f"{current['green']:.3f}")
        self.valueInputs['blue'].setText(f"{current['blue']:.3f}")

        avgGamma = (current['red'] + current['green'] + current['blue']) / 3.0
        self.sliders['all'].setValue(self._gammaToSliderValue(avgGamma))
        self.valueInputs['all'].setText(f'{avgGamma:.3f}')
        self.currentGamma = {
            'red': current['red'],
            'green': current['green'],
            'blue': current['blue']
        }
        self._updateReferenceImage(self.currentGamma)

        for slider in self.sliders.values():
            slider.blockSignals(False)

        self._updateWarningIndicator()
        if rawOutput:
            self.statusBar.showMessage(rawOutput, 3000)
        else:
            self.statusBar.showMessage('Ready', 3000)
        
        self.isUpdating = False

    def _updateReferenceImage(self, gammaValues=None):
        """Updates the reference image display with the current gamma values.

    Args:
        gammaValues (dict, optional): A dictionary containing 'red', 'green', and 'blue'
            gamma values. If None, self.currentGamma is used.
    """
        if gammaValues is None:
            gammaValues = self.currentGamma
        pixmap = self.imageGenerator.generateImage(gammaValues)
        self.referenceLabel.setPixmap(pixmap)

    def _showGammaApplyFailure(self):
        """User-visible status when xgamma apply fails; full output kept in GammaCore."""
        detail = self.gammaCore.getLastApplyRawOutput().strip()
        base = 'Could not apply gamma to the display.'
        if detail:
            one_line = ' '.join(detail.split())
            if len(one_line) > 180:
                one_line = one_line[:177] + '...'
            self.statusBar.showMessage('{} {}'.format(base, one_line), 10000)
        else:
            self.statusBar.showMessage(base, 8000)

    def _applyPendingGamma(self):
        """Applies the accumulated pending gamma values to the system.

    This method is typically called by a QTimer to apply gamma corrections
    after a short delay, preventing excessive `xgamma` calls during slider
    or input field adjustments.
    """
        if self.pendingGamma is None:
            return
        
        if 'overall' in self.pendingGamma:
            ok = self.gammaCore.applyGamma(overall=self.pendingGamma['overall'])
        else:
            ok = self.gammaCore.applyGamma(
                red=self.pendingGamma.get('red'),
                green=self.pendingGamma.get('green'),
                blue=self.pendingGamma.get('blue')
            )
        if not ok:
            self._showGammaApplyFailure()
        self.pendingGamma = None
    
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
            # Выравниваем все RGB-ползунки, блокируя сигналы, чтобы избежать рекурсивных обновлений при программном изменении значений.
            self.sliders['red'].blockSignals(True)
            self.sliders['green'].blockSignals(True)
            self.sliders['blue'].blockSignals(True)
            
            self.sliders['red'].setValue(value)
            self.sliders['green'].setValue(value)
            self.sliders['blue'].setValue(value)
            
            self.sliders['red'].blockSignals(False)
            self.sliders['green'].blockSignals(False)
            self.sliders['blue'].blockSignals(False)
            
            # Обновляем поля значений, чтобы они отображали актуальные значения гаммы после изменения ползунка или загрузки из системы.
            self.valueInputs['red'].setText(f'{gamma:.3f}')
            self.valueInputs['green'].setText(f'{gamma:.3f}')
            self.valueInputs['blue'].setText(f'{gamma:.3f}')
            self.valueInputs['all'].setText(f'{gamma:.3f}')
            
            # Сохраняем значения гаммы для отложенного применения, чтобы агрегировать изменения перед отправкой в систему.
            self.currentGamma = {'red': gamma, 'green': gamma, 'blue': gamma}
            self.pendingGamma = {'overall': gamma}
            self.gammaApplyTimer.stop()
            self.gammaApplyTimer.start(50)  # Запускаем таймер применения гаммы с задержкой в 50 мс, чтобы дать пользователю возможность быстро изменить значения, прежде чем они будут применены.
        else:
            # Обновляем конкретный канал гаммы, когда пользователь изменяет его ползунок или поле ввода, фокусируясь на индивидуальной настройке.
            self.valueInputs[channel].setText(f'{gamma:.3f}')
            
            # Синхронизируем ползунок "all" со средним по RGB, блокируя сигналы, чтобы избежать рекурсивных обновлений. (Примечание: возможно, этот элемент будет удален в будущем, если его полезность будет сомнительна).
            redGamma = self._sliderValueToGamma(self.sliders['red'].value())
            greenGamma = self._sliderValueToGamma(self.sliders['green'].value())
            blueGamma = self._sliderValueToGamma(self.sliders['blue'].value())
            avgGamma = (redGamma + greenGamma + blueGamma) / 3.0
            avgSliderValue = self._gammaToSliderValue(avgGamma)
            
            self.sliders['all'].blockSignals(True)
            self.sliders['all'].setValue(avgSliderValue)
            self.sliders['all'].blockSignals(False)
            self.valueInputs['all'].setText(f'{avgGamma:.3f}')
            
            # Сохраняем значения гаммы для отложенного применения, чтобы агрегировать изменения перед отправкой в систему.
            red = self._sliderValueToGamma(self.sliders['red'].value())
            green = self._sliderValueToGamma(self.sliders['green'].value())
            blue = self._sliderValueToGamma(self.sliders['blue'].value())
            self.currentGamma = {'red': red, 'green': green, 'blue': blue}
            self.pendingGamma = {'red': red, 'green': green, 'blue': blue}
            self.gammaApplyTimer.stop()
            self.gammaApplyTimer.start(50)  # Запускаем таймер применения гаммы с задержкой 50 мс, чтобы предотвратить слишком частые вызовы xgamma при интерактивном изменении.
        
        # Отложенное обновление изображения для улучшения производительности. Обновление произойдет через 100 мс после последнего изменения ползунка, что уменьшает нагрузку на процессор.
        self.imageUpdateTimer.stop()
        self.imageUpdateTimer.start(100)
        
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
        center = size // 2  # центр иконки для целочисленных координат
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor('#f6c343')))
        painter.setPen(QPen(QColor('#b8860b'), 1))
        painter.drawEllipse(1, 1, size - 2, size - 2)
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(center, 6, center, 14)
        painter.drawPoint(center, 18)
        painter.end()
        return QPixmap(pixmap)
    
    def _openSettingsDialog(self):
        """Show settings modal."""
        dialog = SettingsDialog(self)
        dialog.exec_()
    
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
            
            # Проверяем диапазон, чтобы убедиться, что введенное значение гаммы находится в допустимых пределах (MIN_GAMMA и MAX_GAMMA).
            if gamma < GammaCore.MIN_GAMMA:
                gamma = GammaCore.MIN_GAMMA
            elif gamma > GammaCore.MAX_GAMMA:
                gamma = GammaCore.MAX_GAMMA
            
            # Обновляем ползунок, чтобы его положение соответствовало введенному значению гаммы.
            sliderValue = self._gammaToSliderValue(gamma)
            self.sliders[channel].setValue(sliderValue)
            
            # Вызываем обработчик изменения ползунка, чтобы синхронизировать все связанные элементы интерфейса.
            self._onSliderChanged(channel, sliderValue)
        except ValueError:
            # Если введено некорректное значение, возвращаем предыдущее значение в поле ввода, чтобы избежать ошибок.
            if channel == 'all':
                avgGamma = (
                    self._sliderValueToGamma(self.sliders['red'].value()) +
                    self._sliderValueToGamma(self.sliders['green'].value()) +
                    self._sliderValueToGamma(self.sliders['blue'].value())
                ) / 3.0
                self.valueInputs[channel].setText(f'{avgGamma:.3f}')
            else:
                gamma = self._sliderValueToGamma(self.sliders[channel].value())
                self.valueInputs[channel].setText(f'{gamma:.3f}')

    def _onResetClicked(self):
        """Handle reset button click."""
        self.isUpdating = True

        # Блокируем сигналы от ползунков, чтобы избежать нежелательных обновлений GUI во время операции сброса.
        for slider in self.sliders.values():
            slider.blockSignals(True)
        
        # Сбрасываем все ползунки и поля ввода к значениям по умолчанию (1.000), чтобы пользователь мог быстро вернуться к исходным настройкам.
        for channel in ['red', 'green', 'blue', 'all']:
            self.sliders[channel].setValue(100)  # 1.0 * 100
            self.valueInputs[channel].setText('1.000')
        
        # Снимаем блокировку сигналов
        for slider in self.sliders.values():
            slider.blockSignals(False)
        
        # Применяем гамму по умолчанию немедленно, чтобы пользователь сразу видел результат сброса.
        self.currentGamma = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        self.gammaApplyTimer.stop()  # Отменяем любые отложенные задачи применения гаммы, чтобы гарантировать немедленный сброс значений.
        self.pendingGamma = None
        apply_ok = self.gammaCore.applyGamma(overall=1.0)

        remove_res = self.configManager.removeFromAutostart()
        if not apply_ok:
            self._showGammaApplyFailure()
        if not remove_res.ok:
            tip = self.statusBar.currentMessage()
            suffix = ' — Autostart: {}.'.format(remove_res.error_message)
            self.statusBar.showMessage(
                (tip + suffix) if tip else 'Could not remove autostart ({}).'.format(
                    remove_res.error_message
                ),
                12000,
            )
        elif apply_ok:
            if remove_res.removed:
                self.statusBar.showMessage(
                    'Reset to defaults and removed from autostart',
                    3000,
                )
            else:
                self.statusBar.showMessage('Reset to defaults', 3000)

        self._updateReferenceImage(self.currentGamma)
        self.isUpdating = False

    def _onSaveClicked(self):
        """Handle save button click."""
        # Получаем текущие значения гаммы из ползунков, чтобы сформировать команду xgamma для сохранения в автозапуск.
        red = self._sliderValueToGamma(self.sliders['red'].value())
        green = self._sliderValueToGamma(self.sliders['green'].value())
        blue = self._sliderValueToGamma(self.sliders['blue'].value())
        
        # Формируем полную команду xgamma на основе текущих настроек, которая будет использоваться для автозапуска.
        command = self.gammaCore.buildXgammaCommand(red=red, green=green, blue=blue)
        
        if not command:
            self.statusBar.showMessage('Error: xgamma not available', 3000)
            return
        
        # Сохраняем команду xgamma в автозапуск, чтобы настройки гаммы применялись автоматически при старте системы.
        save_res = self.configManager.saveToAutostart(command)
        if save_res.ok:
            self.statusBar.showMessage('Settings applied and saved to autostart', 3000)
        else:
            self.statusBar.showMessage(
                'Could not save to autostart ({}). See log for details.'.format(
                    save_res.error_message
                ),
                8000,
            )

        self._updateReferenceImage(self.currentGamma)
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