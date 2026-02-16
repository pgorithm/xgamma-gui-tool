from PyQt5.QtGui import QPixmap, QPainter, QColor, QImage, QLinearGradient
from PyQt5.QtCore import Qt

class ReferenceImageGenerator:
    """Generator for reference test pattern image."""

    def __init__(self, width=600):
        self.width = width
        self.barHeight = 30
        self.barMargin = 5
        self.blockHeight = 80
        self.blockMargin = 5
        self.numColorBlocks = 8
        self.numGradientBars = 3
        self.calculatedHeight = self._calculateImageHeight()

    def _calculateImageHeight(self):
        gradients_height = (self.barHeight * 2 + self.barMargin) * self.numGradientBars
        blocks_height = self.blockHeight + self.blockMargin * 2
        return gradients_height + self.barMargin + blocks_height

    def generateImage(self, gammaValues=None):
        if gammaValues is None:
            gammaValues = {'red': 1.0, 'green': 1.0, 'blue': 1.0}

        static_image = self._createReferenceSet()
        dynamic_image = self._createReferenceSet()
        
        self._applyGammaToImage(dynamic_image, gammaValues)
        
        return self._composeFinalImage(static_image, dynamic_image)

    def _createReferenceSet(self):
        image_height = self.barHeight * self.numGradientBars + self.blockHeight + self.barMargin * (self.numGradientBars + 1)
        image = QImage(self.width, image_height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        currentY = 0
        
        # Градиенты
        gradient_colors = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255)]
        for color in gradient_colors:
            self._drawGradientBar(painter, 0, currentY, self.width, self.barHeight, QColor(0, 0, 0), color, Qt.Horizontal)
            currentY += self.barHeight + self.barMargin
            
        currentY += self.barMargin
        
        # Блоки
        blockWidth = self.width // self.numColorBlocks
        block_colors = [
            QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
            QColor(255, 255, 0), QColor(0, 255, 255), QColor(255, 0, 255),
            QColor(255, 255, 255), QColor(0, 0, 0)
        ]
        for i, color in enumerate(block_colors):
            painter.fillRect(i * blockWidth + self.blockMargin, currentY, blockWidth - self.blockMargin * 2, self.blockHeight, color)
            
        painter.end()
        return image

    def _composeFinalImage(self, static_image, dynamic_image):
        """
        Compose final image with static and dynamic parts side by side.
        """
        # Рассчитываем итоговую высоту, которая соответствует высоте одного набора изображений,
        # так как они теперь будут располагаться рядом, а не друг под другом.
        final_height = static_image.height()
        final_image = QImage(self.width, final_height, QImage.Format_ARGB32)
        final_image.fill(Qt.transparent)
        
        painter = QPainter(final_image)
        
        # Разделяем холст на две половины по вертикали.
        half_width = self.width // 2
        
        # В одну половину помещаем статическое изображение, которое не будет меняться.
        painter.drawImage(0, 0, static_image, 0, 0, half_width, final_height, Qt.AutoColor)
        
        # В другую половину помещаем динамическое изображение, которое будет обновляться при изменении гаммы.
        painter.drawImage(half_width, 0, dynamic_image, 0, 0, half_width, final_height, Qt.AutoColor)
        
        painter.end()
        return QPixmap.fromImage(final_image)

    def _drawGradientBar(self, painter, x, y, width, height, startColor, endColor, orientation):
        gradient = QLinearGradient(x, y, x + width if orientation == Qt.Horizontal else x, y + height)
        gradient.setColorAt(0, startColor)
        gradient.setColorAt(1, endColor)
        painter.fillRect(x, y, width, height, gradient)

    def _applyGammaToImage(self, image, gammaValues):
        redGamma = max(gammaValues.get('red', 1.0), 0.001)
        greenGamma = max(gammaValues.get('green', 1.0), 0.001)
        blueGamma = max(gammaValues.get('blue', 1.0), 0.001)
        
        redLUT = [self._applyGammaChannel(i, redGamma) for i in range(256)]
        greenLUT = [self._applyGammaChannel(i, greenGamma) for i in range(256)]
        blueLUT = [self._applyGammaChannel(i, blueGamma) for i in range(256)]
        
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixel(x, y))
                if color.alpha() == 0: continue
                r = redLUT[color.red()]
                g = greenLUT[color.green()]
                b = blueLUT[color.blue()]
                image.setPixelColor(x, y, QColor(r, g, b, color.alpha()))

    def _applyGammaChannel(self, value, gamma):
        normalized = (value / 255.0) or 0.0
        adjusted = pow(normalized, 1.0 / gamma) if normalized > 0 else 0.0
        return int(max(0, min(255, round(adjusted * 255))))