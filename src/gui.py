"""
Main GUI module for xgamma GUI Tool.
Implements PyQt5 interface with sliders, reference image, and control buttons.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QPushButton, QLineEdit, QStatusBar,
    QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from .gamma_core import GammaCore
from .reference_image import ReferenceImageGenerator
from .config_manager import ConfigManager


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
        self.isUpdating = False  # Flag to prevent circular updates
        
        self.setWindowTitle('xgamma GUI Tool')
        self.setMinimumSize(600, 500)
        
        # Create central widget and layout
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)
        mainLayout.setSpacing(15)
        mainLayout.setContentsMargins(15, 15, 15, 15)
        
        # Create reference image
        self.imageGenerator = ReferenceImageGenerator(600, 300)
        self.referenceLabel = QLabel()
        self.referenceLabel.setAlignment(Qt.AlignCenter)
        self.referenceLabel.setMinimumHeight(300)
        self.referenceLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.referenceLabel.setScaledContents(True)
        self._updateReferenceImage()
        mainLayout.addWidget(self.referenceLabel)
        
        # Create sliders and value inputs
        self.sliders = {}
        self.valueInputs = {}
        
        channels = [
            ('red', 'Red'),
            ('green', 'Green'),
            ('blue', 'Blue'),
            ('all', 'All')
        ]
        
        for channel, label in channels:
            sliderLayout = QHBoxLayout()
            
            # Label
            channelLabel = QLabel(f'{label}:')
            channelLabel.setMinimumWidth(60)
            sliderLayout.addWidget(channelLabel)
            
            # Slider
            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(1)  # 0.01 * 100
            slider.setMaximum(500)  # 5.0 * 100
            slider.setValue(100)  # 1.0 * 100
            slider.setTickPosition(QSlider.NoTicks)
            slider.valueChanged.connect(
                lambda value, ch=channel: self._onSliderChanged(ch, value)
            )
            self.sliders[channel] = slider
            sliderLayout.addWidget(slider)
            
            # Value input
            valueInput = QLineEdit()
            valueInput.setMinimumWidth(60)
            valueInput.setMaximumWidth(60)
            valueInput.setText('1.00')
            valueInput.setAlignment(Qt.AlignCenter)
            valueInput.editingFinished.connect(
                lambda ch=channel: self._onValueInputChanged(ch)
            )
            self.valueInputs[channel] = valueInput
            sliderLayout.addWidget(valueInput)
            
            mainLayout.addLayout(sliderLayout)
        
        # Create control buttons
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        
        self.resetButton = QPushButton('Reset')
        self.resetButton.clicked.connect(self._onResetClicked)
        buttonLayout.addWidget(self.resetButton)
        
        buttonLayout.addStretch()
        
        self.saveButton = QPushButton('Save to Autostart')
        self.saveButton.clicked.connect(self._onSaveClicked)
        buttonLayout.addWidget(self.saveButton)
        
        buttonLayout.addStretch()
        
        mainLayout.addLayout(buttonLayout)
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('Ready')
        
        # Load current gamma values from system
        self._loadCurrentGamma()
    
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
            # Set all RGB sliders to the same value (block signals to prevent recursion)
            self.sliders['red'].blockSignals(True)
            self.sliders['green'].blockSignals(True)
            self.sliders['blue'].blockSignals(True)
            
            self.sliders['red'].setValue(value)
            self.sliders['green'].setValue(value)
            self.sliders['blue'].setValue(value)
            
            self.sliders['red'].blockSignals(False)
            self.sliders['green'].blockSignals(False)
            self.sliders['blue'].blockSignals(False)
            
            # Update value inputs
            self.valueInputs['red'].setText(f'{gamma:.2f}')
            self.valueInputs['green'].setText(f'{gamma:.2f}')
            self.valueInputs['blue'].setText(f'{gamma:.2f}')
            self.valueInputs['all'].setText(f'{gamma:.2f}')
            
            # Apply gamma
            self.gammaCore.applyGamma(overall=gamma)
        else:
            # Update individual channel
            self.valueInputs[channel].setText(f'{gamma:.2f}')
            
            # Update 'all' slider to average of RGB (block signals to prevent recursion)
            redGamma = self._sliderValueToGamma(self.sliders['red'].value())
            greenGamma = self._sliderValueToGamma(self.sliders['green'].value())
            blueGamma = self._sliderValueToGamma(self.sliders['blue'].value())
            avgGamma = (redGamma + greenGamma + blueGamma) / 3.0
            avgSliderValue = self._gammaToSliderValue(avgGamma)
            
            self.sliders['all'].blockSignals(True)
            self.sliders['all'].setValue(avgSliderValue)
            self.sliders['all'].blockSignals(False)
            self.valueInputs['all'].setText(f'{avgGamma:.2f}')
            
            # Apply gamma
            red = self._sliderValueToGamma(self.sliders['red'].value())
            green = self._sliderValueToGamma(self.sliders['green'].value())
            blue = self._sliderValueToGamma(self.sliders['blue'].value())
            self.gammaCore.applyGamma(red=red, green=green, blue=blue)
        
        self._updateReferenceImage()
        self.isUpdating = False
    
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
            
            # Validate range
            if gamma < GammaCore.MIN_GAMMA:
                gamma = GammaCore.MIN_GAMMA
            elif gamma > GammaCore.MAX_GAMMA:
                gamma = GammaCore.MAX_GAMMA
            
            # Update slider
            sliderValue = self._gammaToSliderValue(gamma)
            self.sliders[channel].setValue(sliderValue)
            
            # Trigger slider change handler
            self._onSliderChanged(channel, sliderValue)
        except ValueError:
            # Invalid input, restore previous value
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
        
        # Block signals to prevent triggering updates during reset
        for slider in self.sliders.values():
            slider.blockSignals(True)
        
        # Reset all sliders to 1.0
        for channel in ['red', 'green', 'blue', 'all']:
            self.sliders[channel].setValue(100)  # 1.0 * 100
            self.valueInputs[channel].setText('1.00')
        
        # Unblock signals
        for slider in self.sliders.values():
            slider.blockSignals(False)
        
        # Apply default gamma
        self.gammaCore.applyGamma(overall=1.0)
        
        # Remove from autostart
        if self.configManager.removeFromAutostart():
            self.statusBar.showMessage('Reset to defaults and removed from autostart', 3000)
        else:
            self.statusBar.showMessage('Reset to defaults', 3000)
        
        self._updateReferenceImage()
        self.isUpdating = False
    
    def _onSaveClicked(self):
        """Handle save button click."""
        # Get current gamma values
        red = self._sliderValueToGamma(self.sliders['red'].value())
        green = self._sliderValueToGamma(self.sliders['green'].value())
        blue = self._sliderValueToGamma(self.sliders['blue'].value())
        
        # Build xgamma command
        command = self.gammaCore.buildXgammaCommand(red=red, green=green, blue=blue)
        
        if not command:
            self.statusBar.showMessage('Error: xgamma not available', 3000)
            return
        
        # Save to autostart
        if self.configManager.saveToAutostart(command):
            self.statusBar.showMessage('Settings saved to autostart', 3000)
        else:
            self.statusBar.showMessage('Error: Failed to save to autostart', 3000)
    
    def _loadCurrentGamma(self):
        """Load current gamma values from system."""
        current = self.gammaCore.getCurrentGamma()
        
        self.isUpdating = True
        
        # Block signals to prevent triggering updates during initialization
        for slider in self.sliders.values():
            slider.blockSignals(True)
        
        # Set sliders and inputs
        self.sliders['red'].setValue(self._gammaToSliderValue(current['red']))
        self.sliders['green'].setValue(self._gammaToSliderValue(current['green']))
        self.sliders['blue'].setValue(self._gammaToSliderValue(current['blue']))
        
        self.valueInputs['red'].setText(f"{current['red']:.2f}")
        self.valueInputs['green'].setText(f"{current['green']:.2f}")
        self.valueInputs['blue'].setText(f"{current['blue']:.2f}")
        
        # Calculate and set 'all' value
        avgGamma = (current['red'] + current['green'] + current['blue']) / 3.0
        self.sliders['all'].setValue(self._gammaToSliderValue(avgGamma))
        self.valueInputs['all'].setText(f'{avgGamma:.2f}')
        
        # Unblock signals
        for slider in self.sliders.values():
            slider.blockSignals(False)
        
        self.isUpdating = False