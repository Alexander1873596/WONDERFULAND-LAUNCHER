from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
import json
import os
import sys
import subprocess
from core.config import DEFAULT_MC_VERSION, REQUIRED_JAVA_VERSION
from core.utils import check_java_version, create_launcher_profiles
from dialogs.java_dialog import JavaDownloadDialog

class MainWindowHandlers:
    """Класс для обработчиков событий главного окна"""
    
    def show_settings(self):
        loader_type = self.loader_combo.currentText()
        self.settings_page.info_label.setText(f"Версия: {self.current_mc_version}\nТип: {loader_type}\nПуть: {self.minecraft_dir}")
        self.settings_page.dir_edit.setText(str(self.minecraft_dir))
        self.settings_page.java_edit.setText(self.java_path)
        self.settings_page.memory_slider.setValue(self.memory_slider.value())
        self.stacked_widget.setCurrentWidget(self.settings_page)
        self.settings_page.update_info()
    
    def show_main(self):
        self.stacked_widget.setCurrentWidget(self.main_page)
    
    def show_customization(self):
        """Показывает страницу кастомизации (только для бета-режима)"""
        if not self.beta_enabled:
            return
            
        if not hasattr(self, 'customization_page') or self.customization_page is None:
            from gui.customization_page import CustomizationPage
            self.customization_page = CustomizationPage(self)
            self.customization_page.setStyleSheet("""
                CustomizationPage {
                    border-radius: 20px;
                }
            """)
            self.stacked_widget.addWidget(self.customization_page)
        
        self.stacked_widget.setCurrentWidget(self.customization_page)
    
    def show_mods_panel(self):
        from gui.mods_panel import ModsPanel
        self.mods_dialog = ModsPanel(self, self.minecraft_dir)
        screen = QApplication.desktop().screenGeometry()
        self.mods_dialog.move((screen.width() - self.mods_dialog.width()) // 2, (screen.height() - self.mods_dialog.height()) // 2)
        self.mods_dialog.show()
    
    def check_java_after_start(self):
        if not self.java_path:
            self.find_java_auto()
        else:
            is_valid, msg = check_java_version(self.java_path, REQUIRED_JAVA_VERSION)
            if not is_valid:
                self.find_java_auto()
    
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Выберите папку для Minecraft", str(Path.home())
        )
        if directory:
            self.settings_page.dir_edit.setText(directory)
            self.minecraft_dir = Path(directory)
            create_launcher_profiles(self.minecraft_dir)
    
    def browse_java(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите java.exe (Java 21)", "C:/",
            "Java Executable (java.exe);;Все файлы (*.*)"
        )
        if filename:
            self.settings_page.java_edit.setText(filename)
            self.java_path = filename
            is_valid, msg = check_java_version(filename, REQUIRED_JAVA_VERSION)
            if is_valid:
                self.status_label.setText(f"Java выбрана: {os.path.basename(filename)}")
            else:
                QMessageBox.warning(self, "Внимание", f"Выбранная Java не подходит:\n{msg}")
    
    def find_java_auto(self):
        self.status_label.setText("Ищем Java 21...")
        
        runtime_path = self.minecraft_dir / "runtime" / "java-runtime-gamma" / "bin"
        
        if os.name == 'nt':
            java_exe = runtime_path / "java.exe"
        else:
            java_exe = runtime_path / "java"
        
        if java_exe.exists():
            is_valid, msg = check_java_version(str(java_exe), REQUIRED_JAVA_VERSION)
            if is_valid:
                self.settings_page.java_edit.setText(str(java_exe))
                self.java_path = str(java_exe)
                self.status_label.setText("Java найдена в runtime")
                return
        
        if os.name == 'nt':
            search_paths = [
                "C:/Program Files/Java/jdk-21/bin/java.exe",
                "C:/Program Files/Java/jre-21/bin/java.exe",
                "C:/Program Files (x86)/Java/jdk-21/bin/java.exe",
                "C:/Program Files (x86)/Java/jre-21/bin/java.exe",
                str(Path.home() / ".jdks" / "jdk-21" / "bin" / "java.exe"),
            ]
        else:
            search_paths = [
                "/usr/lib/jvm/jdk-21/bin/java",
                "/usr/lib/jvm/jre-21/bin/java",
                "/usr/java/jdk-21/bin/java",
                "/opt/java/jdk-21/bin/java",
                str(Path.home() / ".jdks" / "jdk-21" / "bin" / "java"),
            ]
        
        for java_path in search_paths:
            if os.path.exists(java_path):
                is_valid, msg = check_java_version(java_path, REQUIRED_JAVA_VERSION)
                if is_valid:
                    self.settings_page.java_edit.setText(java_path)
                    self.java_path = java_path
                    self.status_label.setText(f"Java 21 найдена")
                    return
        
        self.status_label.setText("Java 21 не найдена!")
        dialog = JavaDownloadDialog(self)
        dialog.exec_()
    
    def load_settings(self):
        settings_path = Path.home() / ".ai_launcher_settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                self.minecraft_dir = Path(data.get('minecraft_dir', str(self.minecraft_dir)))
                self.java_path = data.get('java_path', "")
                self.name_edit.setText(data.get('username', "Player"))
                if hasattr(self, 'memory_slider'):
                    self.memory_slider.setValue(data.get('memory', 4096))
                    self.memory_label.setText(f"{self.memory_slider.value()} MB")
                self.loader = data.get('loader', "Vanilla")
                self.loader_combo.setCurrentText(self.loader)
                self.current_mc_version = data.get('mc_version', DEFAULT_MC_VERSION)
                self.version_label.setText(self.current_mc_version)
                
                # Определяем тип версии (если сохранен)
                version_type = data.get('version_type', 'release')
                self.version_type_label.setText(version_type)
                
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
    
    def load_beta_settings(self):
        """Загружает настройки бета-режима"""
        settings_path = Path.home() / ".pylauncher" / "beta_settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                # Ничего не делаем, просто проверяем существование
                pass
            except Exception as e:
                print(f"Ошибка загрузки бета-настроек: {e}")
    
    def save_beta_settings(self):
        """Сохраняет настройки бета-режима"""
        settings_path = Path.home() / ".pylauncher" / "beta_settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(settings_path, 'w') as f:
                json.dump({"beta_enabled": self.beta_enabled}, f)
        except Exception as e:
            print(f"Ошибка сохранения бета-настроек: {e}")
    
    def load_customization_settings(self):
        """Загружает настройки кастомизации (только для бета-режима)"""
        if not self.beta_enabled:
            return
            
        settings_path = Path.home() / ".pylauncher" / "customization.json"
        
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Загружаем шрифт
                if "font_family" in settings:
                    font = QFont(settings["font_family"])
                    if "font_size" in settings:
                        font.setPointSize(settings["font_size"])
                    if "font_bold" in settings:
                        font.setBold(settings["font_bold"])
                    if "font_italic" in settings:
                        font.setItalic(settings["font_italic"])
                    self.custom_font = font
                    self.apply_custom_font(font)
                
                # Применяем тему
                theme_name = settings.get("theme", "Темная (стандартная)")
                themes = {
                    "Темная (стандартная)": {
                        "bg_color": "#2d2d2d",
                        "text_color": "#ffffff",
                        "accent_color": "#4CAF50",
                        "button_bg": "#3d3d3d",
                        "button_hover": "#4d4d4d",
                        "bg_overlay": "rgba(0,0,0,100)",
                        "widget_bg": "rgba(42,42,42,150)"
                    },
                    "Светлая": {
                        "bg_color": "#f5f5f5",
                        "text_color": "#000000",
                        "accent_color": "#2196F3",
                        "button_bg": "#e0e0e0",
                        "button_hover": "#d0d0d0",
                        "bg_overlay": "rgba(255,255,255,50)",
                        "widget_bg": "rgba(255,255,255,180)"
                    },
                    "Синяя": {
                        "bg_color": "#1a237e",
                        "text_color": "#ffffff",
                        "accent_color": "#ff4081",
                        "button_bg": "#283593",
                        "button_hover": "#303f9f",
                        "bg_overlay": "rgba(0,0,0,70)",
                        "widget_bg": "rgba(26,35,126,150)"
                    },
                    "Зеленая": {
                        "bg_color": "#1b5e20",
                        "text_color": "#ffffff",
                        "accent_color": "#ffd600",
                        "button_bg": "#2e7d32",
                        "button_hover": "#388e3c",
                        "bg_overlay": "rgba(0,0,0,70)",
                        "widget_bg": "rgba(27,94,32,150)"
                    },
                    "Фиолетовая": {
                        "bg_color": "#4a148c",
                        "text_color": "#ffffff",
                        "accent_color": "#ff9100",
                        "button_bg": "#6a1b9a",
                        "button_hover": "#7b1fa2",
                        "bg_overlay": "rgba(0,0,0,70)",
                        "widget_bg": "rgba(74,20,140,150)"
                    }
                }
                self.apply_theme(themes.get(theme_name, themes["Темная (стандартная)"]))
                
                # Применяем фон
                custom_bg = settings.get("custom_bg")
                if custom_bg and os.path.exists(custom_bg):
                    self.set_custom_background(custom_bg)
                
                # Применяем прозрачность
                opacity = settings.get("opacity", 70)
                self.set_overlay_opacity(opacity)
                
            except Exception as e:
                print(f"Ошибка загрузки настроек кастомизации: {e}")
    
    def save_settings(self):
        data = {
            'minecraft_dir': str(self.minecraft_dir),
            'java_path': self.java_path,
            'username': self.name_edit.text(),
            'memory': self.memory_slider.value() if hasattr(self, 'memory_slider') else 4096,
            'loader': self.loader_combo.currentText(),
            'mc_version': self.current_mc_version,
            'version_type': self.version_type_label.text() if hasattr(self, 'version_type_label') else 'release',
        }
        settings_path = Path.home() / ".ai_launcher_settings.json"
        try:
            with open(settings_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")