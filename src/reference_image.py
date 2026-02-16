"""Reference Image Generation Module.

This module provides functionality to generate a reference test pattern image
for display gamma calibration. The generated image includes various gradients
and color blocks to assist in visual gamma assessment.
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
        """Generates a reference test pattern image with gradients and color blocks.

    Args:
        gammaValues (dict, optional): A dictionary containing 'red', 'green', and 'blue'
            gamma values. If None, default values of 1.0 are used for all channels.

    Returns:
        QPixmap: The generated reference image, with gamma correction applied if specified.
    """
        if gammaValues is None:
            gammaValues = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        
        # Инициализируем QImage для эффективной отрисовки графических примитивов и последующей работы с пикселями.
        image = QImage(self.width, self.height, QImage.Format_RGB32)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Заполняем фон нейтральным серым цветом, чтобы обеспечить однородную основу для тестового паттерна.
        painter.fillRect(0, 0, self.width, self.height, QColor(128, 128, 128))
        
        # Рисуем горизонтальные градиентные полосы для каждого цветового канала, чтобы визуально оценить их отклик на гамма-коррекцию.
        barHeight = self.height // 4
        margin = 10
        
        # Градиент для красного канала, чтобы проверить линейность его отображения.
        self._drawGradientBar(
            painter,
            0, margin,
            self.width, barHeight - margin * 2,
            QColor(0, 0, 0),
            QColor(255, 0, 0),
            Qt.Horizontal
        )
        
        # Градиент для зеленого канала, чтобы проверить линейность его отображения.
        self._drawGradientBar(
            painter,
            0, barHeight + margin,
            self.width, barHeight - margin * 2,
            QColor(0, 0, 0),
            QColor(0, 255, 0),
            Qt.Horizontal
        )
        
        # Градиент для синего канала, чтобы проверить линейность его отображения.
        self._drawGradientBar(
            painter,
            0, barHeight * 2 + margin,
            self.width, barHeight - margin * 2,
            QColor(0, 0, 0),
            QColor(0, 0, 255),
            Qt.Horizontal
        )
        
        # Добавляем блок цветовых образцов в нижней части изображения для быстрой оценки смешивания цветов и насыщенности.
        blockY = barHeight * 3
        blockHeight = barHeight - margin * 2
        blockWidth = self.width // 8
        
        # Отрисовываем фиксированные цветовые блоки для каждого основного и смешанного цвета, чтобы оценить их точное отображение после гамма-коррекции.
        colors = [
            QColor(255, 0, 0),      # Красный компонент для проверки отдельных каналов.
            QColor(0, 255, 0),      # Зеленый компонент для проверки отдельных каналов.
            QColor(0, 0, 255),      # Синий компонент для проверки отдельных каналов.
            QColor(255, 255, 0),    # Желтый (красный + зеленый) для проверки смешивания.
            QColor(0, 255, 255),    # Циан (зеленый + синий) для проверки смешивания.
            QColor(255, 0, 255),    # Маджента (красный + синий) для проверки смешивания.
            QColor(255, 255, 255),  # Белый (все компоненты максимальны) для проверки максимальной яркости.
            QColor(0, 0, 0)         # Черный (все компоненты минимальны) для проверки минимальной яркости.
        ]
        
        for i, color in enumerate(colors):
            x = i * blockWidth + margin
            painter.fillRect(
                x, blockY + margin,
                blockWidth - margin * 2, blockHeight,
                color
            )
        
        painter.end()
        
        # Применяем гамма-коррекцию к сгенерированному изображению, чтобы отразить текущие настройки системы или запрошенные значения.
        self._applyGammaToImage(image, gammaValues)
        
        # Конвертируем QImage в QPixmap для оптимизации отображения в GUI-элементах.
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
        """Applies gamma correction to the image based on provided gamma values.

    Args:
        image (QImage): The QImage object to which gamma correction will be applied.
        gammaValues (dict): A dictionary containing 'red', 'green', and 'blue' gamma values.
    """
        redGamma = max(gammaValues.get('red', 1.0), 0.001)
        greenGamma = max(gammaValues.get('green', 1.0), 0.001)
        blueGamma = max(gammaValues.get('blue', 1.0), 0.001)
        
        # Создаем lookup tables для каждого канала для ускорения обработки
        # Это позволяет избежать повторных вычислений pow() для одинаковых значений
        redLUT = [self._applyGammaChannel(i, redGamma) for i in range(256)]
        greenLUT = [self._applyGammaChannel(i, greenGamma) for i in range(256)]
        blueLUT = [self._applyGammaChannel(i, blueGamma) for i in range(256)]
        
        # Применяем гамма-коррекцию к каждому пикселю, используя предварительно вычисленные таблицы для повышения производительности.
        for y in range(image.height()):
            for x in range(image.width()):
                color = QColor(image.pixel(x, y))
                r = redLUT[color.red()]
                g = greenLUT[color.green()]
                b = blueLUT[color.blue()]
                image.setPixelColor(x, y, QColor(r, g, b))

    def _applyGammaChannel(self, value, gamma):
        """Applies gamma correction to a single color channel value.

    This helper function normalizes the input value (0-255) to a 0.0-1.0 range,
    applies the gamma power function, and then scales it back to 0-255.

    Args:
        value (int): The original 8-bit color channel value (0-255).
        gamma (float): The gamma value to apply.

    Returns:
        int: The gamma-corrected 8-bit color channel value (0-255).
    """
        normalized = (value / 255.0) or 0.0
        adjusted = pow(normalized, 1.0 / gamma) if normalized > 0 else 0.0
        return int(max(0, min(255, round(adjusted * 255))))