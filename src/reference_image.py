"""
Module for generating reference test pattern image for gamma calibration.
Creates an image with gradients and color blocks in RGB range.
"""

from PyQt5.QtGui import QPixmap, QPainter, QColor, QImage
from PyQt5.QtCore import Qt


class ReferenceImageGenerator:
    """Generator for reference test pattern image."""
    
    def __init__(self, width=600, height=400):
        """
        Initialize image generator.
        
        Args:
            width (int): Image width in pixels
            height (int): Image height in pixels
        """
        self.width = width
        self.height = height
    
    def generateImage(self, gammaValues=None):
        """
        Generate reference test pattern image with gradients and color blocks.
        
        Returns:
            QPixmap: Generated reference image
        """
        if gammaValues is None:
            gammaValues = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        
        # Создаем QImage для отрисовки
        image = QImage(self.width, self.height, QImage.Format_RGB32)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Заполняем фон нейтральным серым
        painter.fillRect(0, 0, self.width, self.height, QColor(128, 128, 128))
        
        # Рисуем горизонтальные градиентные полосы для каждого канала
        barHeight = self.height // 4
        margin = 10
        
        # Градиент для красного канала
        self._drawGradientBar(
            painter,
            0, margin,
            self.width, barHeight - margin * 2,
            QColor(0, 0, 0),
            QColor(255, 0, 0),
            Qt.Horizontal
        )
        
        # Градиент для зеленого канала
        self._drawGradientBar(
            painter,
            0, barHeight + margin,
            self.width, barHeight - margin * 2,
            QColor(0, 0, 0),
            QColor(0, 255, 0),
            Qt.Horizontal
        )
        
        # Градиент для синего канала
        self._drawGradientBar(
            painter,
            0, barHeight * 2 + margin,
            self.width, barHeight - margin * 2,
            QColor(0, 0, 0),
            QColor(0, 0, 255),
            Qt.Horizontal
        )
        
        # Блок цветовых образцов внизу
        blockY = barHeight * 3
        blockHeight = barHeight - margin * 2
        blockWidth = self.width // 8
        
        # Отрисовываем блоки: красный, зеленый, синий, желтый, циан, магента (маджента?), белый, черный
        colors = [
            QColor(255, 0, 0),      # Красный
            QColor(0, 255, 0),      # Зеленый
            QColor(0, 0, 255),      # Синий
            QColor(255, 255, 0),    # Желтый
            QColor(0, 255, 255),    # Циан
            QColor(255, 0, 255),    # Маджента
            QColor(255, 255, 255),  # Белый
            QColor(0, 0, 0)         # Черный
        ]
        
        for i, color in enumerate(colors):
            x = i * blockWidth + margin
            painter.fillRect(
                x, blockY + margin,
                blockWidth - margin * 2, blockHeight,
                color
            )
        
        painter.end()
        
        # Применяем гамма-коррекцию к готовому паттерну
        self._applyGammaToImage(image, gammaValues)
        
        # Конвертируем в QPixmap
        return QPixmap.fromImage(image)
    
    def _drawGradientBar(self, painter, x, y, width, height, startColor, endColor, orientation):
        """
        Draw a gradient bar.
        
        Args:
            painter (QPainter): Painter object
            x (int): X position
            y (int): Y position
            width (int): Bar width
            height (int): Bar height
            startColor (QColor): Start color
            endColor (QColor): End color
            orientation (Qt.Orientation): Gradient orientation
        """
        from PyQt5.QtGui import QLinearGradient
        
        gradient = QLinearGradient(x, y, x + width if orientation == Qt.Horizontal else x, y + height)
        gradient.setColorAt(0, startColor)
        gradient.setColorAt(1, endColor)
        
        painter.fillRect(x, y, width, height, gradient)

    def _applyGammaToImage(self, image, gammaValues):
        """Корректируем изображение согласно текущей гамме."""
        redGamma = max(gammaValues.get('red', 1.0), 0.001)
        greenGamma = max(gammaValues.get('green', 1.0), 0.001)
        blueGamma = max(gammaValues.get('blue', 1.0), 0.001)
        
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixel(x, y))
                r = self._applyGammaChannel(color.red(), redGamma)
                g = self._applyGammaChannel(color.green(), greenGamma)
                b = self._applyGammaChannel(color.blue(), blueGamma)
                image.setPixelColor(x, y, QColor(r, g, b))

    def _applyGammaChannel(self, value, gamma):
        """Применяем гамму к конкретному каналу."""
        normalized = (value / 255.0) or 0.0
        adjusted = pow(normalized, 1.0 / gamma) if normalized > 0 else 0.0
        return int(max(0, min(255, round(adjusted * 255))))