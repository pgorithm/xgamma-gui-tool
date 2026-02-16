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
            painter.fillRect(i * blockWidth, currentY, blockWidth, self.blockHeight, color)
            
        painter.end()
        return image

    def _composeFinalImage(self, static_image, dynamic_image):
        final_image = QImage(self.width, self.calculatedHeight, QImage.Format_ARGB32)
        final_image.fill(Qt.transparent)
        painter = QPainter(final_image)

        currentY = 0
        single_bar_region_height = self.barHeight + self.barMargin

        for i in range(self.numGradientBars):
            # Статическая полоса
            painter.drawImage(0, currentY, static_image, 0, i * single_bar_region_height, self.width, self.barHeight)
            currentY += self.barHeight
            # Динамическая полоса
            painter.drawImage(0, currentY, dynamic_image, 0, i * single_bar_region_height, self.width, self.barHeight)
            currentY += self.barHeight + self.barMargin

        currentY += self.barMargin
        block_y_in_source = self.barHeight * self.numGradientBars + self.barMargin * (self.numGradientBars + 1)
        blockWidth = self.width // self.numColorBlocks
        blockHeightHalf = self.blockHeight // 2
        
        for i in range(self.numColorBlocks):
            source_x = i * blockWidth
            target_x = i * blockWidth

            # Верхняя половина (статическая)
            painter.drawImage(target_x, currentY, 
                              static_image, 
                              source_x, block_y_in_source, 
                              blockWidth, blockHeightHalf)

            # Нижняя половина (динамическая)
            painter.drawImage(target_x, currentY + blockHeightHalf, 
                              dynamic_image, 
                              source_x, block_y_in_source + blockHeightHalf, 
                              blockWidth, blockHeightHalf)

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