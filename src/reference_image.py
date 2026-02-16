import math
from PyQt5.QtGui import QPixmap, QPainter, QColor, QImage, QLinearGradient
from PyQt5.QtCore import Qt


class ReferenceImageGenerator:
    """Generator for reference test pattern image."""
    
    def __init__(self, width=600):
        """
        Initialize image generator.
        
        Args:
            width (int): Image width in pixels
        """
        self.width = width
        self.barHeight = 30  # Высота одной градиентной полосы
        self.barMargin = 5   # Отступ между полосами в паре и между парами
        self.blockHeight = 80 # Высота одного блока цвета
        self.blockMargin = 5 # Отступ между блоками цвета
        self.numColorBlocks = 8 # Количество цветовых блоков
        self.numGradientBars = 3 # Количество градиентных полос

        self.calculatedHeight = self._calculateImageHeight()

    def _calculateImageHeight(self):
        """Рассчитывает общую высоту генерируемого изображения."""
        # Высота для градиентных полос: (высота_полосы * 2 + отступ_между_парами) * количество_пар - отступ_между_парами
        gradients_height = (self.barHeight * 2 + self.barMargin) * self.numGradientBars - self.barMargin
        # Высота для цветовых блоков: высота_блока + отступ_сверху_и_снизу
        blocks_height = self.blockHeight + self.blockMargin * 2
        
        # Общая высота = высота_градиентов + высота_блоков + небольшой_отступ_между_ними
        return gradients_height + self.barMargin + blocks_height

    def generateImage(self, gammaValues=None):
        """Генерирует комбинированное эталонное изображение со статическими и динамическими компонентами.

        Args:
            gammaValues (dict, optional): Словарь, содержащий значения гаммы ('red', 'green', 'blue')
                для динамической части. По умолчанию для всех каналов используется 1.0.

        Returns:
            QPixmap: Итоговое комбинированное эталонное изображение.
        """
        if gammaValues is None:
            gammaValues = {'red': 1.0, 'green': 1.0, 'blue': 1.0}

        image = QImage(self.width, self.calculatedHeight, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        currentY = 0

        # Отрисовка градиентных полос (статическая и динамическая части)
        for i in range(self.numGradientBars):
            color_map = [
                QColor(255, 0, 0),
                QColor(0, 255, 0),
                QColor(0, 0, 255)
            ][i]
            channel = ['red', 'green', 'blue'][i]

            # Статическая полоса
            self._drawGradientBar(painter, 0, currentY, self.width, self.barHeight,
                                  QColor(0, 0, 0), color_map, Qt.Horizontal)
            currentY += self.barHeight
            
            # Динамическая полоса
            dynamic_color_map = self._applyGammaToColor(color_map, gammaValues[channel], channel)
            self._drawGradientBar(painter, 0, currentY, self.width, self.barHeight,
                                  QColor(0, 0, 0), dynamic_color_map, Qt.Horizontal,
                                  gammaValues[channel] if channel else 1.0)
            currentY += self.barHeight + self.barMargin
        
        # Добавляем небольшой отступ перед блоками цветов
        currentY += self.barMargin

        # Отрисовка цветовых блоков (статическая и динамическая части)
        blockWidth = self.width // self.numColorBlocks
        colors = [
            QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
            QColor(255, 255, 0), QColor(0, 255, 255), QColor(255, 0, 255),
            QColor(255, 255, 255), QColor(0, 0, 0)
        ]

        for i, color in enumerate(colors):
            x = i * blockWidth + self.blockMargin
            width = blockWidth - self.blockMargin * 2

            # Статическая часть блока
            painter.fillRect(x, currentY, width // 2, self.blockHeight, color)

            # Динамическая часть блока
            dynamic_color = self._applyGammaToColor(color, gammaValues['red'] if i == 0 else gammaValues['green'] if i == 1 else gammaValues['blue'] if i == 2 else 1.0, 'all') # TODO: Уточнить применение гаммы к смешанным цветам
            painter.fillRect(x + width // 2, currentY, width // 2, self.blockHeight, dynamic_color)

        painter.end()
        return QPixmap.fromImage(image)

    def _drawGradientBar(self, painter, x, y, width, height, startColor, endColor, orientation, gamma=1.0):
        gradient = QLinearGradient(x, y, x + width if orientation == Qt.Horizontal else x, y + height)
        
        # Применяем гамма-коррекцию к цветам градиента, если это динамическая полоса
        if gamma != 1.0:
            startColor = self._applyGammaToColor(startColor, gamma)
            endColor = self._applyGammaToColor(endColor, gamma)

        gradient.setColorAt(0, startColor)
        gradient.setColorAt(1, endColor)
        
        painter.fillRect(x, y, width, height, gradient)

    def _applyGammaToColor(self, color, gamma, channel='all'):
        redGamma = gamma if channel == 'red' or channel == 'all' else 1.0
        greenGamma = gamma if channel == 'green' or channel == 'all' else 1.0
        blueGamma = gamma if channel == 'blue' or channel == 'all' else 1.0

        r = self._applyGammaChannel(color.red(), redGamma)
        g = self._applyGammaChannel(color.green(), greenGamma)
        b = self._applyGammaChannel(color.blue(), blueGamma)

        return QColor(r, g, b, color.alpha())

    def _applyGammaChannel(self, value, gamma):
        normalized = (value / 255.0) or 0.0
        adjusted = pow(normalized, 1.0 / gamma) if normalized > 0 else 0.0
        return int(max(0, min(255, round(adjusted * 255))))