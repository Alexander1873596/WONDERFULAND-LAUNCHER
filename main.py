import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QFontDatabase, QPalette, QColor
from PyQt5.QtCore import Qt

from core.config import get_asset_path
from core.utils import create_launcher_profiles
from gui.main_window import WONDERFULAND

def setup_app_style(app):
    """Настройка стиля приложения"""
    app.setStyle('Fusion')
    
    # загрузить шрифт по умолчанию
    try:
        font_path = get_asset_path("mine.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            font = QFont(font_family, 9)
            app.setFont(font)
    except:
        pass
    
    # Темная тема по умолчанию
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    
    return app

def main():
    app = QApplication(sys.argv)
    app = setup_app_style(app)
    
    beta_enabled = "--beta" in sys.argv
    
    launcher = WONDERFULAND(beta_enabled=beta_enabled)
    launcher.show()
    
    create_launcher_profiles(launcher.minecraft_dir)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()