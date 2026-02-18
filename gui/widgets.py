from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPixmap, QColor
from pathlib import Path
from core.config import get_asset_path

class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.custom_background = None
        self.overlay_opacity = 50
        self.setStyleSheet("""
            BackgroundWidget {
                margin: 0px;
                padding: 0px;
                border: none;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # пользовательский фон если есть
        if self.custom_background and Path(self.custom_background).exists():
            pixmap = QPixmap(self.custom_background)
            if not pixmap.isNull():
                # Масштаб под размер виджета
                scaled_pixmap = pixmap.scaled(self.width(), self.height(), 
                                             Qt.KeepAspectRatioByExpanding, 
                                             Qt.SmoothTransformation)
                
                # Центрируем изображение
                x = (self.width() - scaled_pixmap.width()) // 2
                y = (self.height() - scaled_pixmap.height()) // 2
                painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # Используем стандартный фон
            pixmap = QPixmap(get_asset_path("background.png"))
            if not pixmap.isNull():
                painter.drawPixmap(0, 0, self.width(), self.height(), pixmap)
        
        # темный слой
        painter.fillRect(0, 0, self.width(), self.height(), 
                        QColor(0, 0, 0, int(self.overlay_opacity * 2.55)))
    
    def set_background_image(self, image_path):
        """Устанавливает пользовательское изображение для фона"""
        self.custom_background = image_path
        self.update()
    
    def set_overlay_opacity(self, opacity):
        """Устанавливает прозрачность затемнения (0-100)"""
        self.overlay_opacity = max(0, min(100, opacity))
        self.update()