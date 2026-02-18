from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
import json
import os
import sys
import threading
import time
import subprocess
import uuid
import minecraft_launcher_lib

from core.config import DEFAULT_MC_VERSION, FORGE_VERSION, FABRIC_LOADER_VERSION, REQUIRED_JAVA_VERSION, DEFAULT_MINECRAFT_DIR, get_asset_path
from core.utils import check_java_version, generate_offline_uuid, create_launcher_profiles
from gui.widgets import BackgroundWidget
from gui.main_window_ui import MainWindowUI
from gui.main_window_handlers import MainWindowHandlers
from gui.main_window_game import MainWindowGame
from gui.settings_page import SettingsPage
from gui.mods_panel import ModsPanel
from gui.customization_page import CustomizationPage
from dialogs.java_dialog import JavaDownloadDialog
from dialogs.version_selector import VersionSelectorDialog  # Новый импорт
from threads.download_thread import DownloadProgressThread
from threads.forge_thread import ForgeInstallThread
from threads.fabric_thread import FabricInstallThread

# Импортируем PluginManager только если бета-функции включены
class PluginManagerStub:
    """Заглушка для менеджера плагинов, когда бета-функции отключены"""
    def __init__(self, launcher):
        self.launcher = launcher
        self.plugins = {}
        
    def load_all_plugins(self):
        pass
        
    def on_game_start(self):
        pass
        
    def on_game_stop(self):
        pass
        
    def open_plugins_folder(self):
        pass
        
    def show_plugins_dialog(self):
        pass

class WONDERFULAND(QMainWindow, MainWindowUI, MainWindowHandlers, MainWindowGame):
    def __init__(self, beta_enabled=False):
        super().__init__()
        
        # Флаг бета-функций
        self.beta_enabled = beta_enabled
        
        # Текущая версия Minecraft
        self.current_mc_version = DEFAULT_MC_VERSION
        
        # Устанавливаем флаги окна для закругленных углов
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Инициализируем менеджер плагинов (или заглушку)
        if self.beta_enabled:
            from core.plugin_manager import PluginManager
            self.plugin_manager = PluginManager(self)
        else:
            self.plugin_manager = PluginManagerStub(self)
        
        self.drag_pos = None
        self.minecraft_dir = DEFAULT_MINECRAFT_DIR
        
        self.java_path = ""
        self.loader = "Vanilla"
        self.install_success = True
        self.forge_install_success = True
        self.fabric_install_success = True
        self.current_theme = None
        self.custom_font = None
        
        # Создаем контейнер с закругленными углами
        self.central_container = QWidget()
        self.central_container.setObjectName("centralContainer")
        self.central_container.setStyleSheet("""
            #centralContainer {
                background: transparent;
                border-radius: 20px;
            }
        """)
        
        # Layout для контейнера
        container_layout = QVBoxLayout(self.central_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # stacked_widget теперь внутри контейнера
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QStackedWidget {
                border-radius: 20px;
                background: transparent;
            }
        """)
        container_layout.addWidget(self.stacked_widget)
        
        # Устанавливаем контейнер как центральный виджет
        self.setCentralWidget(self.central_container)
        
        # Инициализация страниц
        self.main_page_original = BackgroundWidget()
        self.main_page = self.main_page_original
        self.main_page.setStyleSheet("""
            BackgroundWidget {
                border-radius: 20px;
            }
        """)
        
        self.settings_page = SettingsPage(self)
        self.settings_page.setStyleSheet("""
            SettingsPage {
                border-radius: 20px;
            }
        """)
        
        self.customization_page = None
        
        self.setup_main_page()
        
        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.setCurrentWidget(self.main_page)
        
        self.load_settings()
        self.load_beta_settings()
        
        if self.beta_enabled:
            self.load_customization_settings()
        
        self.install_thread = None
        self.forge_thread = None
        self.fabric_thread = None
        
        QTimer.singleShot(1000, self.check_java_after_start)
        if self.beta_enabled:
            QTimer.singleShot(2000, self.plugin_manager.load_all_plugins)
    
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
    
    def closeEvent(self, event):
        self.save_settings()
        from core.utils import create_launcher_profiles
        create_launcher_profiles(self.minecraft_dir)
        
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.stop()
            self.install_thread.wait()
        if self.forge_thread and self.forge_thread.isRunning():
            self.forge_thread.stop()
            self.forge_thread.wait()
        if self.fabric_thread and self.fabric_thread.isRunning():
            self.fabric_thread.stop()
            self.fabric_thread.wait()
        super().closeEvent(event)
    
    @property
    def memory_slider(self):
        return self.settings_page.memory_slider
    
    @property
    def memory_label(self):
        return self.settings_page.memory_label
    
    @property
    def java_edit(self):
        return self.settings_page.java_edit