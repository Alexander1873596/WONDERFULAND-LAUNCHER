from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import minecraft_launcher_lib
import threading
import time
from core.config import VERSION_TYPES

class VersionSelectorDialog(QDialog):
    
    def __init__(self, parent=None, current_version=None):
        super().__init__(parent)
        self.parent = parent
        self.current_version = current_version
        self.versions = []
        self.filtered_versions = []
        self.loading_thread = None
        self.selected_version = None
        self.drag_pos = None
        
        self.init_ui()
        self.load_versions()
        
    def init_ui(self):
        self.setWindowTitle("Выбор версии Minecraft")
        self.setFixedSize(800, 500)
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
            QListWidget {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555;
            }
            QListWidget::item:selected {
                background: #4CAF50;
            }
            QListWidget::item:hover {
                background: #4d4d4d;
            }
            QPushButton {
                background: #3d3d3d;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: 1px solid #555;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #4d4d4d;
                border: 1px solid #4CAF50;
            }
            QPushButton:pressed {
                background: #2d2d2d;
            }
            QPushButton:disabled {
                background: #2d2d2d;
                color: #666;
                border: 1px solid #444;
            }
            QComboBox {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 4px;
            }
            QComboBox:hover {
                border: 1px solid #4CAF50;
            }
            QComboBox::drop-down {
                border: 0px;
                background: transparent;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background: #3d3d3d;
                color: white;
                selection-background-color: #4CAF50;
                border: 1px solid #555;
            }
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555;
                background: #3d3d3d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background: #3d3d3d;
                height: 20px;
                color: white;
            }
            QProgressBar::chunk {
                background: #4CAF50;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background: #2d2d2d;
                width: 12px;
                border: none;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4CAF50;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #45a049;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #2d2d2d;
                height: 12px;
                border: none;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #4CAF50;
                min-width: 20px;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        title_bar = QHBoxLayout()
        title_label = QLabel("Выберите версию Minecraft")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #4CAF50;")
        title_bar.addWidget(title_label)
        
        layout.addLayout(title_bar)
        
        filter_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск версии...")
        self.search_edit.textChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.search_edit, 2)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("Все типы", "all")
        for version_type in VERSION_TYPES:
            display_name = {
                "release": "Релизы",
                "snapshot": "Снимки",
                "old_beta": "Бета",
                "old_alpha": "Альфа"
            }.get(version_type, version_type)
            self.type_combo.addItem(display_name, version_type)
        self.type_combo.currentIndexChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.type_combo, 1)
        
        # ОСТАВЛЯЕМ ЧЕКБОКС "Только установленные"
        self.installed_checkbox = QCheckBox("Только установленные")
        self.installed_checkbox.stateChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.installed_checkbox, 1)
        
        layout.addLayout(filter_layout)
        
        self.versions_list = QListWidget()
        self.versions_list.setStyleSheet("""
            QListWidget {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555;
            }
            QListWidget::item:selected {
                background: #4CAF50;
            }
            QListWidget::item:hover {
                background: #4d4d4d;
            }
        """)
        self.versions_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.versions_list)
        
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("Загрузка списка версий...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888;")
        self.status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        self.status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(self.status_layout)
        
        buttons_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_versions)
        buttons_layout.addWidget(self.refresh_btn)
        
        buttons_layout.addStretch()
        
        self.select_btn = QPushButton("Выбрать")
        self.select_btn.clicked.connect(self.accept)
        self.select_btn.setEnabled(False)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #45a049;
                border: 1px solid white;
            }
            QPushButton:disabled {
                background: #2d2d2d;
                color: #666;
            }
        """)
        buttons_layout.addWidget(self.select_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(buttons_layout)
    
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
    
    def load_versions(self):
        self.versions_list.clear()
        self.versions_list.addItem("Загрузка списка версий...")
        self.versions_list.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.status_label.setText("Загрузка списка версий...")
        self.progress_bar.show()
        
        self.loading_thread = threading.Thread(target=self._load_versions_thread, daemon=True)
        self.loading_thread.start()
    
    def _load_versions_thread(self):
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
            
            installed_versions = []
            if hasattr(self.parent, 'minecraft_dir'):
                installed_versions = minecraft_launcher_lib.utils.get_installed_versions(str(self.parent.minecraft_dir))
            installed_ids = [v["id"] for v in installed_versions]
            
            for version in versions:
                version["installed"] = version["id"] in installed_ids
                if "releaseTime" in version and not isinstance(version["releaseTime"], str):
                    version["releaseTime"] = str(version["releaseTime"])
            
            QMetaObject.invokeMethod(self, "_update_versions_list", 
                                     Q_ARG(list, versions))
            
        except Exception as e:
            QMetaObject.invokeMethod(self, "_show_error", 
                                     Q_ARG(str, f"Ошибка загрузки версий: {str(e)}"))
    
    @pyqtSlot(list)
    def _update_versions_list(self, versions):
        self.versions = versions
        self.filter_versions()
        
        self.versions_list.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Найдено версий: {len(self.versions)}")
        
        if self.current_version:
            for i in range(self.versions_list.count()):
                item = self.versions_list.item(i)
                if item and item.text().startswith(self.current_version):
                    self.versions_list.setCurrentItem(item)
                    self.select_btn.setEnabled(True)
                    break
    
    @pyqtSlot(str)
    def _show_error(self, error_msg):
        self.versions_list.clear()
        self.versions_list.addItem(error_msg)
        self.versions_list.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText("Ошибка загрузки")
        
        QMessageBox.critical(self, "Ошибка", error_msg)
    
    def filter_versions(self):
        self.versions_list.clear()
        
        search_text = self.search_edit.text().lower()
        filter_type = self.type_combo.currentData()
        # ОСТАВЛЯЕМ show_only_installed, чекбокс работает
        show_only_installed = self.installed_checkbox.isChecked()
        
        self.filtered_versions = []
        
        for version in self.versions:
            version_id = version["id"]
            version_type = version.get("type", "unknown")
            # ОСТАВЛЯЕМ is_installed для фильтрации
            is_installed = version.get("installed", False)
            
            # ОСТАВЛЯЕМ фильтр "Только установленные"
            if show_only_installed and not is_installed:
                continue
            
            if filter_type != "all" and version_type != filter_type:
                continue
                
            if search_text and search_text not in version_id.lower():
                continue
            
            self.filtered_versions.append(version)
        
        def sort_key(v):
            type_order = {"release": 0, "snapshot": 1, "old_beta": 2, "old_alpha": 3}
            type_priority = type_order.get(v.get("type", "unknown"), 4)
            release_time = v.get("releaseTime", "")
            if release_time is None:
                release_time = ""
            return (type_priority, release_time)
        
        self.filtered_versions.sort(key=sort_key)
        self.filtered_versions.reverse()
        
        for version in self.filtered_versions:
            version_id = version["id"]
            version_type = version.get("type", "unknown")
            # УДАЛЯЕМ is_installed из отображения, но оставляем для внутреннего использования
            # is_installed = version.get("installed", False)
            
            # УДАЛЯЕМ типы иконок (●, ○, β, α) - просто используем версию без символов
            # УДАЛЯЕМ галочку (✓) - просто используем версию без символов
            
            # Просто текст версии, без символов и галочек
            item_text = f"{version_id}"
            
            item = QListWidgetItem(item_text)
            
            # Оставляем цветовое выделение для разных типов версий
            if version_type == "release":
                item.setForeground(QColor("#4CAF50"))
            elif version_type == "snapshot":
                item.setForeground(QColor("#FF9800"))
            elif version_type == "old_beta":
                item.setForeground(QColor("#2196F3"))
            elif version_type == "old_alpha":
                item.setForeground(QColor("#9C27B0"))
            
            item.setData(Qt.UserRole, version)
            
            self.versions_list.addItem(item)
        
        if self.versions_list.count() == 0:
            self.versions_list.addItem("Нет версий, соответствующих фильтрам")
            self.select_btn.setEnabled(False)
        else:
            self.select_btn.setEnabled(True)
    
    def get_selected_version(self):
        current_item = self.versions_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
    
    def accept(self):
        self.selected_version = self.get_selected_version()
        if self.selected_version:
            super().accept()
        else:
            QMessageBox.warning(self, "Предупреждение", "Выберите версию")