"""Main Graphical User Interface (GUI) Module for xgamma GUI Tool.

This module implements the primary PyQt5 interface, including gamma sliders,
a reference image display, and various control buttons. It orchestrates
user interactions with the `GammaCore` and `ConfigManager` to provide
a seamless gamma adjustment experience.
"""

import html
import logging

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QPushButton, QLineEdit, QStatusBar,
    QSizePolicy, QApplication, QDialog,
    QDialogButtonBox, QFrame
)
from PyQt5.QtCore import Qt, QEvent, QSize, QTimer, QRectF, QCoreApplication
from PyQt5.QtGui import (
    QPixmap, QFontMetrics, QPainter, QPen, QBrush,
    QColor, QIcon, QDoubleValidator
)
from .gamma_core import GammaCore
from .environment_checks import collect_environment_warnings
from .reference_image import ReferenceImageGenerator
from .config_manager import ConfigManager
from .version_info import __version__ as APP_VERSION
from PyQt5.QtCore import QThread, pyqtSignal

_logger = logging.getLogger(__name__)


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
        warningMessages = collect_environment_warnings()

        self.finished.emit({
            'gamma': currentGamma,
            'warnings': warningMessages,
            'gamma_read_source': self.gammaCore.getLastGammaReadSource(),
        })


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


class AboutDialog(QDialog):
    """Modal about box: app name, version from version_info, project link."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr('About xgamma GUI Tool'))
        self.setModal(True)

        layout = QVBoxLayout(self)
        title = QLabel(
            '<h3 style="margin:0">{}</h3>'.format(html.escape(self.tr('xgamma GUI Tool')))
        )
        layout.addWidget(title)
        ver = QLabel(
            '<b>{}</b> {}'.format(
                html.escape(self.tr('Version:')),
                html.escape(APP_VERSION),
            )
        )
        layout.addWidget(ver)
        gh_url = 'https://github.com/pgorithm/xgamma_gui_tool'
        link = QLabel(
            '<a href="{}">{}</a>'.format(
                html.escape(gh_url),
                html.escape(self.tr('Project on GitHub')),
            )
        )
        link.setOpenExternalLinks(True)
        layout.addWidget(link)
        layout.addWidget(QLabel(self.tr('Author: pgorithm')))

        tips_heading = QLabel(self.tr('Calibration tips'))
        tips_font = tips_heading.font()
        tips_font.setBold(True)
        tips_heading.setFont(tips_font)
        layout.addWidget(tips_heading)
        tips_body = QLabel(
            self.tr(
                'A gamma of 1.0 on a channel is neutral—it does not brighten or darken that primary. '
                'Adjust Red, Green, and Blue when you need to fix a color cast or balance white; '
                'use All when you want one factor applied to every channel. '
                'Small moves and the preview pattern are safer than pushing sliders to extremes.'
            )
        )
        tips_body.setWordWrap(True)
        layout.addWidget(tips_body)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class SettingsDialog(QDialog):
    """Модальное окно настроек."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr('Settings'))
        self.setModal(True)
        # Минимальный размер окна настроек
        self.setMinimumSize(150, 150)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(15)

        about_button = QPushButton(_create_info_icon(), self.tr('About'), self)
        about_button.setIconSize(QSize(22, 22))
        about_button.setToolTip(self.tr('Open version and project information'))
        about_button.clicked.connect(lambda: AboutDialog(self).exec_())
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
        self._channelLabels = {}
        self.warningMessages = []
        self._environmentBannerDismissed = False
        self.currentGamma = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        self._gammaControlsReady = False
        
        self.imageUpdateTimer = QTimer()
        self.imageUpdateTimer.setSingleShot(True)
        self.imageUpdateTimer.timeout.connect(self._updateReferenceImage)
        # Таймер `imageUpdateTimer` используется для отложенного обновления эталонного изображения,
        # чтобы избежать частых перерисовок и улучшить производительность GUI при быстрых изменениях гаммы.

        self._referencePixmapFull = None
        self._referenceResizeTimer = QTimer()
        self._referenceResizeTimer.setSingleShot(True)
        self._referenceResizeTimer.timeout.connect(self._fitReferencePixmapToLabel)
    
        self.gammaApplyTimer = QTimer()
        self.gammaApplyTimer.setSingleShot(True)
        self.gammaApplyTimer.timeout.connect(self._applyPendingGamma)
        # Таймер `gammaApplyTimer` используется для отложенного применения гаммы к системе,
        # чтобы предотвратить избыточные вызовы xgamma при каждом движении ползунка и уменьшить нагрузку на систему.
        self.pendingGamma = None
        # `pendingGamma` хранит значения гаммы, которые ожидают применения таймером,
        # позволяя накапливать изменения перед их фактическим использованием.
          
        self.setWindowTitle(self.tr('xgamma GUI Tool'))
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
            self.tr('Settings'),
            self._openSettingsDialog
        )
        self.warningIconLabel = QLabel()
        self.warningIconLabel.setVisible(False)
        self.warningIconLabel.setAlignment(Qt.AlignCenter)
        self.warningIconLabel.setFixedSize(32, 32)
        topPanel.addWidget(self.warningIconLabel)
        topPanel.addWidget(self.settingsButton)
        mainLayout.addLayout(topPanel)

        # PRD 3.11.5 / 3.8: visible environment notice (VM/HDR), not only corner icon.
        self._environmentBannerFrame = QFrame()
        self._environmentBannerFrame.setObjectName('environmentWarningBanner')
        self._environmentBannerFrame.setFrameShape(QFrame.StyledPanel)
        self._environmentBannerFrame.setVisible(False)
        self._environmentBannerFrame.setStyleSheet(
            'QFrame#environmentWarningBanner {'
            ' background-color: #fff8e1;'
            ' border: 1px solid #d4a017;'
            ' border-radius: 6px;'
            ' padding: 2px;'
            '}'
        )
        bannerLayout = QHBoxLayout(self._environmentBannerFrame)
        bannerLayout.setContentsMargins(10, 8, 8, 8)
        bannerLayout.setSpacing(10)
        bannerIcon = QLabel()
        bannerIcon.setPixmap(self._createWarningIcon())
        bannerIcon.setFixedSize(28, 28)
        bannerIcon.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        bannerLayout.addWidget(bannerIcon, 0, Qt.AlignTop)
        self._environmentBannerLabel = QLabel()
        self._environmentBannerLabel.setTextFormat(Qt.RichText)
        self._environmentBannerLabel.setWordWrap(True)
        self._environmentBannerLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._environmentBannerLabel.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Minimum,
        )
        bannerLayout.addWidget(self._environmentBannerLabel, 1)
        self._bannerDismissButton = QPushButton(self.tr('Dismiss'))
        self._bannerDismissButton.setFlat(True)
        self._bannerDismissButton.setCursor(Qt.PointingHandCursor)
        self._bannerDismissButton.setToolTip(
            self.tr('Hide this notice. The warning icon stays for details.')
        )
        self._bannerDismissButton.clicked.connect(self._dismissEnvironmentBanner)
        bannerLayout.addWidget(self._bannerDismissButton, 0, Qt.AlignTop)
        mainLayout.addWidget(self._environmentBannerFrame)
        
        # Инициализируем генератор эталонного изображения, который будет использоваться для визуализации текущих значений гаммы.
        self.imageGenerator = ReferenceImageGenerator(600)
        self.referenceLabel = QLabel()
        self.referenceLabel.setAlignment(Qt.AlignCenter)
        self.referenceLabel.setMinimumHeight(self.imageGenerator.calculatedHeight - 10)
        self.referenceLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.referenceLabel.setFocusPolicy(Qt.NoFocus)
        self.referenceLabel.setText(self.tr('Reading display gamma…'))
        mainLayout.addWidget(self.referenceLabel)
        
        # Инициализируем ползунки и поля ввода значений для каждого цветового канала, чтобы пользователь мог интерактивно управлять гаммой.
        self.sliders = {}
        self.valueInputs = {}
        
        channels = [
            ('red', self.tr('Red')),
            ('green', self.tr('Green')),
            ('blue', self.tr('Blue')),
            ('all', self.tr('All')),
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
            # PRD 3.11.7 / 3.5: visible focus on a row (Tab/click label), not only the slider track.
            channelLabel.setFocusPolicy(Qt.TabFocus | Qt.ClickFocus)
            self._channelLabels[channel] = channelLabel
            self.widgetChannel[channelLabel] = channel
            sliderLayout.addWidget(channelLabel)
            
            # Вставляем ползунок, который позволяет пользователю изменять значение гаммы для соответствующего канала.
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(1)  # 0.01 * 100
            slider.setMaximum(500)  # 5.0 * 100
            slider.setValue(100)  # 1.0 * 100
            slider.setTickPosition(QSlider.NoTicks)
            slider.setEnabled(False)
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
            valueInput.setText('')
            valueInput.setPlaceholderText('…')
            valueInput.setEnabled(False)
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

            if channel in ('red', 'green', 'blue'):
                # PRD 3.11.10: channel hygiene + keyboard (3.11.7 / 3.5)
                _rgb_tip = self.tr(
                    '1.0 means no change for this channel. '
                    'Use Red, Green, and Blue to correct tint and white balance; use All to apply '
                    'the same factor to every channel. '
                    'Focus this row (Tab or click the label), then use ←/→ to adjust gamma; '
                    'hold Shift for larger steps.'
                )
                _rgb_status = self.tr(
                    '1.0 neutral; R/G/B for cast, All to scale all channels.'
                )
                channelLabel.setToolTip(_rgb_tip)
                channelLabel.setStatusTip(_rgb_status)
                slider.setToolTip(_rgb_tip)
                slider.setStatusTip(_rgb_status)
                valueInput.setToolTip(_rgb_tip)
                valueInput.setStatusTip(_rgb_status)
            elif channel == 'all':
                # PRD 3.11.4 / 5.1: All row mean vs equalize; 3.11.10 / 3.11.7
                _all_tip = self.tr(
                    'When Red, Green, and Blue match, 1.0 is neutral for all. '
                    'While they differ, this row shows their arithmetic average. '
                    'Moving the All slider sets all three channels to the same gamma value. '
                    'Focus this row (Tab or click the label), then use ←/→; hold Shift for larger steps.'
                )
                _all_status = self.tr(
                    '1.0 when matched; average when R/G/B differ; All drag equalizes channels.'
                )
                channelLabel.setToolTip(_all_tip)
                channelLabel.setStatusTip(_all_status)
                slider.setToolTip(_all_tip)
                slider.setStatusTip(_all_status)
                valueInput.setToolTip(_all_tip)
                valueInput.setStatusTip(_all_status)
            
            mainLayout.addLayout(sliderLayout)
        
        # Создаем кнопки управления (Reset, Apply), чтобы предоставить пользователю функционал для сброса настроек и сохранения изменений.
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        
        self.resetButton = QPushButton(self.tr('Reset'))
        self.resetButton.setEnabled(False)
        self.resetButton.clicked.connect(self._onResetClicked)
        buttonLayout.addWidget(self.resetButton)
        
        buttonLayout.addStretch()
        
        self.saveButton = QPushButton(self.tr('Apply'))
        self.saveButton.setEnabled(False)
        self.saveButton.clicked.connect(self._onSaveClicked)
        buttonLayout.addWidget(self.saveButton)
        
        buttonLayout.addStretch()
        
        mainLayout.addLayout(buttonLayout)
        
        # Инициализируем строку состояния для отображения информации о текущем статусе приложения
        # и возможных предупреждениях.
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(self.tr('Loading initial settings…'))

        self.worker = InitializationWorker(self.gammaCore)
        self.worker.finished.connect(self._onInitializationComplete)
        self.worker.start()

        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
            app.focusChanged.connect(self._onApplicationFocusChanged)

        self._init_read_source = None

    def retranslateUi(self):
        """Refresh all user-visible strings after QTranslator change (PRD 3.11.12 / TASK-016)."""
        self.setWindowTitle(self.tr('xgamma GUI Tool'))
        self.settingsButton.setToolTip(self.tr('Settings'))
        self._bannerDismissButton.setText(self.tr('Dismiss'))
        self._bannerDismissButton.setToolTip(
            self.tr('Hide this notice. The warning icon stays for details.')
        )

        if not self._gammaControlsReady:
            self.referenceLabel.setText(self.tr('Reading display gamma…'))
            self.statusBar.showMessage(self.tr('Loading initial settings…'))
        else:
            if self._init_read_source is not None:
                self._showPostInitStatusBarMessage()

        channels = [
            ('red', self.tr('Red')),
            ('green', self.tr('Green')),
            ('blue', self.tr('Blue')),
            ('all', self.tr('All')),
        ]
        font_metrics = QFontMetrics(self.font())
        max_label_width = max(font_metrics.width(f'{label}:') for _, label in channels) + 10
        for channel, label in channels:
            lbl = self._channelLabels[channel]
            lbl.setText(f'{label}:')
            lbl.setFixedWidth(max_label_width)

        _rgb_tip = self.tr(
            '1.0 means no change for this channel. '
            'Use Red, Green, and Blue to correct tint and white balance; use All to apply '
            'the same factor to every channel. '
            'Focus this row (Tab or click the label), then use ←/→ to adjust gamma; '
            'hold Shift for larger steps.'
        )
        _rgb_status = self.tr(
            '1.0 neutral; R/G/B for cast, All to scale all channels.'
        )
        for ch in ('red', 'green', 'blue'):
            for w in (
                self._channelLabels[ch],
                self.sliders[ch],
                self.valueInputs[ch],
            ):
                w.setToolTip(_rgb_tip)
                w.setStatusTip(_rgb_status)

        _all_tip = self.tr(
            'When Red, Green, and Blue match, 1.0 is neutral for all. '
            'While they differ, this row shows their arithmetic average. '
            'Moving the All slider sets all three channels to the same gamma value. '
            'Focus this row (Tab or click the label), then use ←/→; hold Shift for larger steps.'
        )
        _all_status = self.tr(
            '1.0 when matched; average when R/G/B differ; All drag equalizes channels.'
        )
        for w in (
            self._channelLabels['all'],
            self.sliders['all'],
            self.valueInputs['all'],
        ):
            w.setToolTip(_all_tip)
            w.setStatusTip(_all_status)

        self.resetButton.setText(self.tr('Reset'))
        self.saveButton.setText(self.tr('Apply'))

        self._updateWarningIndicator()
        if self.warningMessages and not self._environmentBannerDismissed:
            self._updateEnvironmentBanner()

    def _onApplicationFocusChanged(self, old, new):
        """Keep activeChannel aligned with keyboard focus (PRD 3.5, 3.11.7)."""
        if not self._gammaControlsReady:
            return
        if new is None or not self.isAncestorOf(new):
            return
        ch = self.widgetChannel.get(new)
        if ch:
            self._setActiveChannel(ch)
        elif self._focusClearsKeyboardChannel(new):
            self._clearActiveChannel()

    def _focusClearsKeyboardChannel(self, w):
        """Focus on chrome controls: arrows should not move gamma via the global filter."""
        if w in (self.resetButton, self.saveButton, self.settingsButton):
            return True
        if w is self.warningIconLabel:
            return True
        if w is self._bannerDismissButton:
            return True
        return self._environmentBannerFrame.isAncestorOf(w)

    def _updateKeyboardChannelHighlight(self):
        """Show which row matches activeChannel for keyboard adjustment."""
        for ch, lbl in self._channelLabels.items():
            if self.activeChannel == ch:
                lbl.setStyleSheet('font-weight: bold;')
            else:
                lbl.setStyleSheet('')

    def _onInitializationComplete(self, results):
        """
        Slot to receive results from InitializationWorker and update the GUI.
        """
        current = results['gamma']
        self.warningMessages = results['warnings']
        read_source = results.get('gamma_read_source', 'default')
        self._init_read_source = read_source

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

        for slider in self.sliders.values():
            slider.blockSignals(False)

        self.referenceLabel.setText('')
        for vi in self.valueInputs.values():
            vi.setPlaceholderText('')
            vi.setEnabled(True)
        for s in self.sliders.values():
            s.setEnabled(True)
        self.resetButton.setEnabled(True)
        self.saveButton.setEnabled(True)
        self._gammaControlsReady = True

        self._updateReferenceImage(self.currentGamma)

        self._updateWarningIndicator()
        self._updateEnvironmentBanner()
        raw_diag = self.gammaCore.getLastRawOutput().strip()
        if read_source == 'xgamma':
            if raw_diag:
                _logger.info(
                    'xgamma diagnostic (truncated): %s',
                    raw_diag[:500] + ('...' if len(raw_diag) > 500 else ''),
                )
        elif read_source == 'xrandr':
            if raw_diag:
                _logger.info(
                    'xgamma diagnostic (truncated): %s',
                    raw_diag[:500] + ('...' if len(raw_diag) > 500 else ''),
                )
        elif raw_diag:
            _logger.warning(
                'Gamma read failed; diagnostic (truncated): %s',
                raw_diag[:500] + ('...' if len(raw_diag) > 500 else ''),
            )

        self._showPostInitStatusBarMessage()

        self.isUpdating = False

    def _showPostInitStatusBarMessage(self):
        """Steady status after init; also used when UI language changes (TASK-016)."""
        read_source = self._init_read_source
        if read_source is None:
            return
        env_hint = (
            self.tr(' Environment may limit gamma — see the notice above.')
            if self.warningMessages
            else ''
        )
        if read_source == 'xgamma':
            self.statusBar.showMessage(
                self.tr('Ready') + env_hint,
                8000 if env_hint else 3000,
            )
        elif read_source == 'xrandr':
            self.statusBar.showMessage(
                self.tr('Gamma from xrandr (xgamma output was not recognized).') + env_hint,
                12000 if env_hint else 8000,
            )
        else:
            self.statusBar.showMessage(
                self.tr(
                    'Could not read display gamma; defaults (1.0) shown. '
                    'Check DISPLAY and xgamma.'
                )
                + env_hint,
                14000 if env_hint else 10000,
            )

    def _updateReferenceImage(self, gammaValues=None):
        """Update the reference image with the current gamma values.

        Args:
            gammaValues: Optional dict with 'red', 'green', and 'blue'. If
                None, self.currentGamma is used.
        """
        if gammaValues is None:
            gammaValues = self.currentGamma
        self._referencePixmapFull = self.imageGenerator.generateImage(gammaValues)
        self._fitReferencePixmapToLabel()

    def _scheduleReferencePixmapFit(self):
        self._referenceResizeTimer.stop()
        self._referenceResizeTimer.start(50)

    def _fitReferencePixmapToLabel(self):
        if self._referencePixmapFull is None or self._referencePixmapFull.isNull():
            return
        cr = self.referenceLabel.contentsRect()
        w = max(1, cr.width())
        h = max(1, cr.height())
        scaled = self._referencePixmapFull.scaled(
            w,
            h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.referenceLabel.setPixmap(scaled)

    def _showGammaApplyFailure(self):
        """User-visible status when xgamma apply fails; full output kept in GammaCore."""
        detail = self.gammaCore.getLastApplyRawOutput().strip()
        base = self.tr('Could not apply gamma to the display.')
        if detail:
            one_line = ' '.join(detail.split())
            if len(one_line) > 180:
                one_line = one_line[:177] + '...'
            self.statusBar.showMessage('{} {}'.format(base, one_line), 10000)
        else:
            self.statusBar.showMessage(base, 8000)

    def _applyPendingGamma(self):
        """Apply pending gamma to the display via GammaCore.

        Called from a QTimer after a short delay to avoid excessive xgamma
        invocations while sliders or value fields change.
        """
        if not self._gammaControlsReady:
            return
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
        self._updateKeyboardChannelHighlight()
    
    def _clearActiveChannel(self):
        """Reset keyboard-controlled channel."""
        self.activeChannel = None
        self._updateKeyboardChannelHighlight()
    
    def _adjustChannelSlider(self, channel, delta):
        """Adjust the given channel slider by delta ticks (1 tick = 0.001 gamma)."""
        if not self._gammaControlsReady or not channel:
            return
        slider = self.sliders[channel]
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
        if not self._gammaControlsReady:
            return
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
            
            # Синхронизируем ползунок All со средним арифметическим RGB (см. tooltip на строке All).
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
            tooltip = '\n'.join(
                QCoreApplication.translate('environment', m) for m in self.warningMessages
            )
            self.warningIconLabel.setToolTip(tooltip)
        else:
            self.warningIconLabel.setToolTip('')

    def _updateEnvironmentBanner(self):
        """Show session banner with full VM/HDR text until dismissed (PRD 3.11.5)."""
        if not self.warningMessages or self._environmentBannerDismissed:
            self._environmentBannerFrame.setVisible(False)
            return
        body = '<br/>'.join(
            html.escape(QCoreApplication.translate('environment', m))
            for m in self.warningMessages
        )
        self._environmentBannerLabel.setText(
            '<b>{}</b><br/>{}'.format(html.escape(self.tr('Display environment')), body)
        )
        self._environmentBannerFrame.setVisible(True)

    def _dismissEnvironmentBanner(self):
        self._environmentBannerDismissed = True
        self._environmentBannerFrame.setVisible(False)

    def _onValueInputChanged(self, channel):
        """
        Handle value input field change.
        
        Args:
            channel (str): Channel name
        """
        if not self._gammaControlsReady:
            return
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
        if not self._gammaControlsReady:
            return
        self.isUpdating = True

        # Блокируем сигналы от ползунков, чтобы избежать нежелательных
        # обновлений GUI во время операции сброса.
        for slider in self.sliders.values():
            slider.blockSignals(True)

        # Сбрасываем ползунки и поля ввода к 1.000 для быстрого возврата к умолчанию.
        for channel in ['red', 'green', 'blue', 'all']:
            self.sliders[channel].setValue(100)  # 1.0 * 100
            self.valueInputs[channel].setText('1.000')

        # Снимаем блокировку сигналов.
        for slider in self.sliders.values():
            slider.blockSignals(False)

        # Применяем гамму по умолчанию сразу, чтобы результат сброса был виден.
        self.currentGamma = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        # Отменяем отложенное применение гаммы — сброс должен быть немедленным.
        self.gammaApplyTimer.stop()
        self.pendingGamma = None
        apply_ok = self.gammaCore.applyGamma(overall=1.0)

        remove_res = self.configManager.removeFromAutostart()
        if not apply_ok:
            self._showGammaApplyFailure()
        if not remove_res.ok:
            tip = self.statusBar.currentMessage()
            suffix = self.tr(' — Autostart: {}.').format(remove_res.error_message)
            self.statusBar.showMessage(
                (tip + suffix)
                if tip
                else self.tr('Could not remove autostart ({}).').format(
                    remove_res.error_message
                ),
                12000,
            )
        elif apply_ok:
            if remove_res.removed:
                self.statusBar.showMessage(
                    self.tr('Reset to defaults and removed from autostart'),
                    3000,
                )
            else:
                self.statusBar.showMessage(self.tr('Reset to defaults'), 3000)

        self._updateReferenceImage(self.currentGamma)
        self.isUpdating = False

    def _onSaveClicked(self):
        """Handle save button click."""
        if not self._gammaControlsReady:
            return
        # Получаем текущие значения гаммы из ползунков, чтобы сформировать команду xgamma для сохранения в автозапуск.
        red = self._sliderValueToGamma(self.sliders['red'].value())
        green = self._sliderValueToGamma(self.sliders['green'].value())
        blue = self._sliderValueToGamma(self.sliders['blue'].value())
        
        # Формируем полную команду xgamma на основе текущих настроек, которая будет использоваться для автозапуска.
        command = self.gammaCore.buildXgammaCommand(red=red, green=green, blue=blue)
        
        if not command:
            self.statusBar.showMessage(self.tr('Error: xgamma not available'), 3000)
            return
        
        # Сохраняем команду xgamma в автозапуск, чтобы настройки гаммы применялись автоматически при старте системы.
        save_res = self.configManager.saveToAutostart(command)
        if save_res.ok:
            self.statusBar.showMessage(
                self.tr('Settings applied and saved to autostart'),
                3000,
            )
        else:
            self.statusBar.showMessage(
                self.tr('Could not save to autostart ({}). See log for details.').format(
                    save_res.error_message
                ),
                8000,
            )

        self._updateReferenceImage(self.currentGamma)
        self.isUpdating = False

    def eventFilter(self, obj, event):
        """Handle global mouse and keyboard events for slider control."""
        if obj is self.referenceLabel and event.type() == QEvent.Resize:
            self._scheduleReferencePixmapFit()
        elif event.type() == QEvent.MouseButtonPress:
            channel = self.widgetChannel.get(obj)
            if channel:
                self._setActiveChannel(channel)
            else:
                self._clearActiveChannel()
        elif event.type() == QEvent.KeyPress:
            if event.key() not in (Qt.Key_Left, Qt.Key_Right):
                return super().eventFilter(obj, event)
            if not self._gammaControlsReady:
                return super().eventFilter(obj, event)
            ch = self.widgetChannel.get(obj)
            if ch is None or self.activeChannel != ch:
                # Let QSlider/QLineEdit handle keys, or ignore if focus is elsewhere.
                return super().eventFilter(obj, event)
            step = 10 if (event.modifiers() & Qt.ShiftModifier) else 1
            delta = step if event.key() == Qt.Key_Right else -step
            self._adjustChannelSlider(ch, delta)
            return True
        return super().eventFilter(obj, event)