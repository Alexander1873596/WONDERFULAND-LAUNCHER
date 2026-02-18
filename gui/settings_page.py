from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from core.config import DEFAULT_MC_VERSION
from gui.widgets import BackgroundWidget
from pathlib import Path
import json
import sys
import subprocess
import os

class SettingsPage(BackgroundWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(42, 42, 42, 150);
                width: 12px;
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
                background: rgba(42, 42, 42, 150);
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #4CAF50;
                min-width: 20px;
                border-radius: 6px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_content.setObjectName("scrollContent")
        
        settings_layout = QVBoxLayout(scroll_content)
        settings_layout.setSpacing(15)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel("Настройки")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            color: white;
            margin: 10px;
            padding: 10px;
            background: transparent;
            border: none;
        """)
        settings_layout.addWidget(title_label)
        
        beta_group = self.create_group_box("Экспериментальные функции")
        beta_layout = QVBoxLayout()
        
        self.beta_checkbox = QCheckBox("Включить бета-функции (требуется перезапуск)")
        self.beta_checkbox.setChecked(self.parent.beta_enabled)
        self.beta_checkbox.stateChanged.connect(self.on_beta_toggled)
        beta_layout.addWidget(self.beta_checkbox)
        
        beta_info = QLabel("Бета-функции включают: систему плагинов, настройку тем оформления, загрузку пользовательского фона и шрифтов")
        beta_info.setStyleSheet("color: #888; font-size: 10px; padding: 5px; background: transparent; border: none;")
        beta_info.setWordWrap(True)
        beta_layout.addWidget(beta_info)
        
        beta_group.setLayout(beta_layout)
        settings_layout.addWidget(beta_group)
        
        dir_group = self.create_group_box("Директория установки")
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit(str(self.parent.minecraft_dir))
        self.dir_edit.setReadOnly(True)
        dir_browse = QPushButton("Обзор")
        dir_browse.clicked.connect(self.parent.browse_directory)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(dir_browse)
        dir_group.setLayout(dir_layout)
        settings_layout.addWidget(dir_group)
        
        memory_group = self.create_group_box("Выделенная память")
        memory_layout = QVBoxLayout()
        
        memory_info_layout = QHBoxLayout()
        memory_info_layout.addWidget(QLabel("Объем памяти:"))
        memory_info_layout.addStretch()
        self.memory_label = QLabel("4096 MB")
        self.memory_label.setStyleSheet("color: #4CAF50; background: transparent; border: none;")
        memory_info_layout.addWidget(self.memory_label)
        memory_layout.addLayout(memory_info_layout)
        
        self.memory_slider = QSlider(Qt.Horizontal)
        self.memory_slider.setRange(2048, 16384)
        self.memory_slider.setSingleStep(512)
        self.memory_slider.setPageStep(1024)
        self.memory_slider.setValue(4096)
        self.memory_slider.setTickInterval(1024)
        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.valueChanged.connect(
            lambda v: self.memory_label.setText(f"{v} MB")
        )
        memory_layout.addWidget(self.memory_slider)
        
        memory_hint = QLabel("Рекомендуется: 4096 MB (4 ГБ) для оптимальной работы")
        memory_hint.setStyleSheet("color: #888; font-size: 10px; padding: 5px; background: transparent; border: none;")
        memory_hint.setWordWrap(True)
        memory_layout.addWidget(memory_hint)
        
        memory_group.setLayout(memory_layout)
        settings_layout.addWidget(memory_group)
        
        java_group = self.create_group_box("Путь к Java (требуется Java 21+)")
        java_layout = QVBoxLayout()
        
        java_path_layout = QHBoxLayout()
        self.java_edit = QLineEdit()
        self.java_edit.setPlaceholderText("Автоматический поиск Java 21...")
        self.java_edit.setReadOnly(True)
        java_browse = QPushButton("Указать")
        java_browse.clicked.connect(self.parent.browse_java)
        java_path_layout.addWidget(self.java_edit)
        java_path_layout.addWidget(java_browse)
        java_layout.addLayout(java_path_layout)
        
        java_auto = QPushButton("Автопоиск Java 21")
        java_auto.clicked.connect(self.parent.find_java_auto)
        java_layout.addWidget(java_auto)
        
        java_info = QLabel(f"Java 21 необходима для Minecraft {self.parent.current_mc_version}")
        java_info.setStyleSheet("color: #888; font-size: 10px; padding: 5px; background: transparent; border: none;")
        java_layout.addWidget(java_info)
        
        java_group.setLayout(java_layout)
        settings_layout.addWidget(java_group)
        
        if self.parent.beta_enabled:
            plugins_group = self.create_group_box("Управление плагинами")
            plugins_layout = QVBoxLayout()
            
            plugins_status_layout = QHBoxLayout()
            plugins_status_layout.addWidget(QLabel("Статус:"))
            plugins_status_layout.addStretch()
            self.plugins_status_label = QLabel(f"Загружено: {len(self.parent.plugin_manager.plugins)}")
            self.plugins_status_label.setStyleSheet("color: #4CAF50; background: transparent; border: none;")
            plugins_status_layout.addWidget(self.plugins_status_label)
            plugins_layout.addLayout(plugins_status_layout)
            
            btn_grid = QGridLayout()
            btn_grid.setSpacing(10)
            
            manage_btn = QPushButton("Управление")
            manage_btn.clicked.connect(self.show_plugins_manager)
            btn_grid.addWidget(manage_btn, 0, 0)
            
            load_btn = QPushButton("Загрузить плагин")
            load_btn.clicked.connect(self.load_plugin)
            btn_grid.addWidget(load_btn, 0, 1)
            
            open_folder_btn = QPushButton("Открыть папку")
            open_folder_btn.clicked.connect(self.open_plugins_folder)
            btn_grid.addWidget(open_folder_btn, 1, 0)
            
            refresh_btn = QPushButton("Обновить список")
            refresh_btn.clicked.connect(self.refresh_plugins)
            btn_grid.addWidget(refresh_btn, 1, 1)
            
            plugins_layout.addLayout(btn_grid)
            
            plugins_layout.addWidget(QLabel("Активные плагины:"))
            self.plugins_list = QListWidget()
            self.plugins_list.setMaximumHeight(100)
            self.plugins_list.setStyleSheet("""
                QListWidget {
                    background: rgba(30, 30, 30, 150);
                    color: white;
                    border: 1px solid #444;
                    border-radius: 5px;
                    padding: 5px;
                }
                QListWidget::item {
                    padding: 3px;
                    color: white;
                    background: transparent;
                }
                QListWidget::item:selected {
                    background: #4CAF50;
                }
            """)
            self.update_plugins_list()
            plugins_layout.addWidget(self.plugins_list)
            
            plugins_group.setLayout(plugins_layout)
            settings_layout.addWidget(plugins_group)
        
        info_group = self.create_group_box("Информация")
        info_layout = QVBoxLayout()
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            padding: 10px;
            background: rgba(30, 30, 30, 150);
            border-radius: 5px;
            font-size: 12px;
            color: white;
            border: none;
        """)
        info_layout.addWidget(self.info_label)
        info_group.setLayout(info_layout)
        settings_layout.addWidget(info_group)
        
        back_button = QPushButton("Назад")
        back_button.setMinimumHeight(40)
        back_button.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                font-size: 14px;
                border: none;
                border-radius: 5px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: #45a049;
                border: 2px solid white;
            }
        """)
        back_button.clicked.connect(self.parent.show_main)
        settings_layout.addWidget(back_button)
        
        settings_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        self.apply_styles()
    
    def create_group_box(self, title):
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: rgba(42, 42, 42, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background: rgba(42, 42, 42, 150);
                border-radius: 4px;
                color: white;
            }
        """)
        return group
    
    def apply_styles(self):
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(30, 30, 30, 180);
                color: white;
                border: 1px solid #444;
                padding: 8px;
                border-radius: 5px;
                selection-background-color: #4CAF50;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background: rgba(50, 50, 50, 200);
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
                border: 1px solid #555;
                min-width: 80px;
            }
            QPushButton:hover {
                background: rgba(70, 70, 70, 200);
                border: 2px solid #4CAF50;
            }
            QPushButton:pressed {
                background: rgba(40, 40, 40, 200);
            }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 8px;
                background: rgba(30, 30, 30, 180);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #444;
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #45a049;
            }
            QLabel {
                color: white;
                background: transparent;
                border: none;
            }
            QScrollArea {
                border: none;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555;
                background: rgba(30, 30, 30, 180);
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
    
    def on_beta_toggled(self, state):
        self.parent.beta_enabled = (state == Qt.Checked)
        self.parent.save_beta_settings()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Перезапуск лаунчера")
        msg.setText("Для применения изменений необходимо перезапустить лаунчер. Желаете перезапустить сейчас?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if msg.exec_() == QMessageBox.Yes:
            self.restart_launcher()
    
    def restart_launcher(self):
        try:
            self.parent.save_settings()
            
            if getattr(sys, 'frozen', False):
                executable = sys.executable
                args = [sys.executable]
            else:
                executable = sys.executable
                args = [sys.executable] + sys.argv
            
            if self.parent.beta_enabled:
                args.append("--beta")
            
            subprocess.Popen(args)
            self.parent.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось перезапустить лаунчер: {str(e)}")
    
    def update_info(self):
        loader_type = self.parent.loader_combo.currentText() if hasattr(self.parent, 'loader_combo') else "Vanilla"
        
        info_text = f"<b>Версия Minecraft:</b> {self.parent.current_mc_version}\n<b>Тип загрузчика:</b> {loader_type}\n<b>Путь к игре:</b> {self.parent.minecraft_dir}\n<b>Java:</b> {self.parent.java_path if self.parent.java_path else 'Не указана'}\n<b>Память:</b> {self.memory_slider.value()} MB"
        
        self.info_label.setText(info_text)
        
        if self.parent.beta_enabled:
            self.update_plugins_status()
    
    def update_plugins_status(self):
        if not self.parent.beta_enabled:
            return
            
        plugin_count = len(self.parent.plugin_manager.plugins)
        self.plugins_status_label.setText(f"Загружено: {plugin_count}")
        self.update_plugins_list()
    
    def update_plugins_list(self):
        if not self.parent.beta_enabled:
            return
            
        self.plugins_list.clear()
        for name, plugin in self.parent.plugin_manager.plugins.items():
            self.plugins_list.addItem(f"{plugin.name} v{plugin.version}")
    
    def open_plugins_folder(self):
        if self.parent.beta_enabled:
            self.parent.plugin_manager.open_plugins_folder()
    
    def show_plugins_manager(self):
        if self.parent.beta_enabled:
            self.parent.plugin_manager.show_plugins_dialog()
            self.update_plugins_status()
    
    def refresh_plugins(self):
        if self.parent.beta_enabled:
            self.parent.plugin_manager.load_all_plugins()
            self.update_plugins_status()
            self.parent.status_label.setText("Список плагинов обновлен")
    
    def load_plugin(self):
        if not self.parent.beta_enabled:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл плагина",
            str(Path.home()),
            "Python файлы (*.py);;Все файлы (*.*)"
        )
        
        if file_path:
            try:
                file_name = Path(file_path).name
                plugin_name = Path(file_path).stem
                
                dest_path = self.parent.plugin_manager.plugins_dir / file_name
                
                if dest_path.exists():
                    reply = QMessageBox.question(
                        self,
                        "Плагин уже существует",
                        f"Плагин {file_name} уже существует. Перезаписать?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                
                import shutil
                shutil.copy2(file_path, dest_path)
                
                if self.parent.plugin_manager.enable_plugin(plugin_name):
                    self.parent.status_label.setText(f"Плагин {plugin_name} успешно загружен")
                    self.update_plugins_status()
                    
                    QMessageBox.information(
                        self,
                        "Успешно",
                        f"Плагин {plugin_name} успешно загружен и активирован!"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Предупреждение",
                        f"Плагин {file_name} скопирован, но не удалось активировать. Проверьте формат плагина."
                    )
                    
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Не удалось загрузить плагин: {str(e)}"
                )