from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
import shutil
import os
from core.config import get_asset_path

class ModsPanel(QWidget):
    def __init__(self, parent, minecraft_dir):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.drag_pos = None
        self.minecraft_dir = minecraft_dir
        self.mods_dir = self.minecraft_dir / "mods"
        self.mods_dir.mkdir(exist_ok=True)
        self.init_ui()
        self.update_mods_list()
        
    def init_ui(self):
        self.setWindowTitle("Установка модов")
        self.setFixedSize(800, 500)
        self.setAcceptDrops(True)
        
        main_layout = QVBoxLayout(self)
        
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("Установка модов")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        title_bar.addWidget(title_label)
        
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        close_btn.setIcon(QIcon(get_asset_path("exit.png")))
        close_btn.setIconSize(QSize(30, 30))
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        
        main_layout.addLayout(title_bar)
        
        content_layout = QHBoxLayout()
        
        drop_area = QWidget()
        drop_area.setAcceptDrops(True)
        drop_layout = QVBoxLayout(drop_area)
        drop_layout.setAlignment(Qt.AlignCenter)
        
        info_label = QLabel("Перетащите JAR-файлы модов сюда")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 18px; color: #4CAF50; border: 2px dashed #555; border-radius: 10px; padding: 20px;")
        drop_layout.addWidget(info_label)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: white;")
        drop_layout.addWidget(self.status_label)
        
        content_layout.addWidget(drop_area)
        
        mods_group = QGroupBox("Установленные моды")
        mods_layout = QVBoxLayout()
        self.mods_list = QListWidget()
        self.mods_list.setStyleSheet("""
            QListWidget {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background: #4CAF50;
            }
        """)
        mods_layout.addWidget(self.mods_list)
        
        delete_btn = QPushButton("Удалить выбранный")
        delete_btn.clicked.connect(self.delete_selected_mod)
        delete_btn.setStyleSheet("""
            QPushButton { 
                background: #3d3d3d; 
                color: red; 
                padding: 8px; 
                border-radius: 4px; 
                border: 1px solid #555;
            }
            QPushButton:hover { 
                background: #4d4d4d; 
                border: 1px solid #FF0000;
            }
        """)
        mods_layout.addWidget(delete_btn)
        
        mods_group.setLayout(mods_layout)
        content_layout.addWidget(mods_group)
        
        main_layout.addLayout(content_layout)
        
        self.setStyleSheet("""
            QWidget { background: #2d2d2d; border: 1px solid #444; border-radius: 10px; }
            QGroupBox { color: white; border: 1px solid #444; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: white; }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
            event.accept()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.jar'):
                    event.accept()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        installed = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.jar'):
                try:
                    dest_path = self.mods_dir / Path(file_path).name
                    if not dest_path.exists():
                        shutil.copy(file_path, dest_path)
                        installed.append(Path(file_path).name)
                except Exception as e:
                    self.status_label.setText(f"Ошибка установки {Path(file_path).name}: {str(e)}")
                    return
        
        if installed:
            self.status_label.setText(f"Установлены: {', '.join(installed)}")
            self.update_mods_list()
        else:
            self.status_label.setText("Нет JAR-файлов")
    
    def update_mods_list(self):
        self.mods_list.clear()
        for mod_file in self.mods_dir.glob("*.jar"):
            self.mods_list.addItem(mod_file.name)
    
    def delete_selected_mod(self):
        item = self.mods_list.currentItem()
        if item:
            mod_name = item.text()
            mod_path = self.mods_dir / mod_name
            if mod_path.exists():
                try:
                    os.remove(mod_path)
                    self.update_mods_list()
                    self.status_label.setText(f"Мод {mod_name} удален")
                except Exception as e:
                    self.status_label.setText(f"Ошибка удаления: {str(e)}")
            else:
                self.status_label.setText("Мод не найден")
        else:
            self.status_label.setText("Выберите мод для удаления")