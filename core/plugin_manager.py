import importlib.util
import inspect
import sys
from pathlib import Path
import json
import os
from PyQt5.QtWidgets import QAction, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel, QCheckBox
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QPainter, QFont, QIcon

class PluginInterface:
    """Базовый класс для всех плагинов"""
    
    def __init__(self, launcher):
        self.launcher = launcher
        self.name = "Без имени"
        self.version = "1.0.0"
        self.author = "Неизвестен"
        self.description = ""
        
    def on_load(self):
        """Вызывается при загрузке плагина"""
        pass
        
    def on_unload(self):
        """Вызывается при выгрузке плагина"""
        pass
        
    def on_game_start(self):
        """Вызывается перед запуском игры"""
        pass
        
    def on_game_stop(self):
        """Вызывается после завершения игры"""
        pass
        
    def on_settings_open(self):
        """Вызывается при открытии настроек"""
        pass
        
    def get_menu_actions(self):
        """Возвращает список действий для меню плагинов"""
        return []
        
    def create_tab(self):
        """Создает вкладку в лаунчере (опционально)"""
        return None

class PluginManager(QObject):
    """Менеджер плагинов"""
    
    plugin_loaded = pyqtSignal(str)
    plugin_error = pyqtSignal(str, str)
    
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.plugins_dir = Path.home() / ".pylauncher" / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins = {}  # имя -> объект плагина
        self.plugin_modules = {}  # имя -> модуль
        self.enabled_plugins = self.load_enabled_plugins()
        
        # Создаем меню плагинов в главном окне
        self.create_plugins_menu()
        
    def create_plugins_menu(self):
        """Создает меню плагинов в главном окне"""
        # Добавляем кнопку плагинов в верхнюю панель
        if hasattr(self.launcher, 'main_page'):
            main_layout = self.launcher.main_page.layout()
            if main_layout and main_layout.count() > 0:
                top_panel = main_layout.itemAt(0)
                if top_panel and isinstance(top_panel, QHBoxLayout):
                    self.plugins_button = QPushButton()
                    self.plugins_button.setFixedSize(45, 45)
                    
                    # Создаем иконку по умолчанию
                    pixmap = QPixmap(45, 45)
                    pixmap.fill(Qt.transparent)
                    painter = QPainter(pixmap)
                    painter.setPen(Qt.white)
                    painter.setFont(QFont("Arial", 20))
                    painter.drawText(pixmap.rect(), Qt.AlignCenter, "")
                    painter.end()
                    self.plugins_button.setIcon(QIcon(pixmap))
                    
                    self.plugins_button.setIconSize(QSize(45, 45))
                    self.plugins_button.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: none;
                            padding: 0px;
                        }
                        QPushButton:hover {
                            opacity: 0.8;
                        }
                    """)
                    
                    # Создаем меню для кнопки
                    self.plugins_menu = QMenu()
                    self.plugins_button.setMenu(self.plugins_menu)
                    self.plugins_menu.aboutToShow.connect(self.update_plugins_menu)
                    
                    # Добавляем кнопку в топ-панель (перед кнопкой выхода)
                    top_panel.insertWidget(top_panel.count() - 1, self.plugins_button)
        
    def update_plugins_menu(self):
        """Обновляет меню плагинов"""
        self.plugins_menu.clear()
        
        # Добавляем пункт управления плагинами
        manage_action = QAction("Управление плагинами", self.launcher)
        manage_action.triggered.connect(self.show_plugins_dialog)
        self.plugins_menu.addAction(manage_action)
        
        self.plugins_menu.addSeparator()
        
        # Добавляем плагины
        if self.plugins:
            for name, plugin in self.plugins.items():
                plugin_menu = QMenu(plugin.name, self.launcher)
                
                # Добавляем действия плагина
                actions = plugin.get_menu_actions()
                if actions:
                    for action in actions:
                        plugin_menu.addAction(action)
                else:
                    no_actions = QAction("Нет действий", self.launcher)
                    no_actions.setEnabled(False)
                    plugin_menu.addAction(no_actions)
                
                self.plugins_menu.addMenu(plugin_menu)
        else:
            no_plugins = QAction("Нет загруженных плагинов", self.launcher)
            no_plugins.setEnabled(False)
            self.plugins_menu.addAction(no_plugins)
    
    def show_plugins_dialog(self):
        """Показывает диалог управления плагинами"""
        dialog = QDialog(self.launcher)
        dialog.setWindowTitle("Управление плагинами")
        dialog.setFixedSize(600, 400)
        dialog.setModal(True)
        
        # Устанавливаем стиль для диалога
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background: #3d3d3d;
                color: white;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #555;
            }
            QPushButton:hover {
                background: #4d4d4d;
            }
            QCheckBox {
                color: white;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Список плагинов
        plugins_list = QListWidget()
        plugins_list.setStyleSheet("""
            QListWidget {
                background: #3d3d3d;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #555;
            }
            QListWidget::item:selected {
                background: #4CAF50;
            }
        """)
        
        # Сканируем доступные плагины
        available_plugins = self.scan_plugins()
        
        for plugin_name, plugin_info in available_plugins.items():
            item = QListWidgetItem(plugins_list)
            
            # Создаем виджет для элемента
            widget = QWidget()
            widget.setStyleSheet("background: transparent;")
            item_layout = QHBoxLayout(widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            
            # Информация о плагине
            info_layout = QVBoxLayout()
            name_label = QLabel(f"<b>{plugin_info.get('name', plugin_name)}</b> v{plugin_info.get('version', '1.0.0')}")
            name_label.setStyleSheet("color: white;")
            info_layout.addWidget(name_label)
            
            desc_label = QLabel(plugin_info.get('description', 'Нет описания'))
            desc_label.setStyleSheet("color: #888; font-size: 10px;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)
            
            author_label = QLabel(f"Автор: {plugin_info.get('author', 'Неизвестен')}")
            author_label.setStyleSheet("color: #666; font-size: 9px;")
            info_layout.addWidget(author_label)
            
            item_layout.addLayout(info_layout)
            item_layout.addStretch()
            
            # Кнопка включения/выключения
            enabled_btn = QCheckBox("Включен")
            enabled_btn.setChecked(plugin_name in self.enabled_plugins)
            enabled_btn.stateChanged.connect(lambda state, name=plugin_name: self.toggle_plugin(name, state))
            item_layout.addWidget(enabled_btn)
            
            item.setSizeHint(widget.sizeHint())
            plugins_list.addItem(item)
            plugins_list.setItemWidget(item, widget)
        
        layout.addWidget(plugins_list)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Обновить список")
        refresh_btn.clicked.connect(lambda: self.refresh_plugins_list(plugins_list))
        buttons_layout.addWidget(refresh_btn)
        
        open_folder_btn = QPushButton("Открыть папку плагинов")
        open_folder_btn.clicked.connect(self.open_plugins_folder)
        buttons_layout.addWidget(open_folder_btn)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    
    def refresh_plugins_list(self, list_widget):
        """Обновляет список плагинов"""
        list_widget.clear()
        
        available_plugins = self.scan_plugins()
        
        for plugin_name, plugin_info in available_plugins.items():
            item = QListWidgetItem(list_widget)
            
            widget = QWidget()
            widget.setStyleSheet("background: transparent;")
            item_layout = QHBoxLayout(widget)
            item_layout.setContentsMargins(5, 5, 5, 5)
            
            info_layout = QVBoxLayout()
            name_label = QLabel(f"<b>{plugin_info.get('name', plugin_name)}</b> v{plugin_info.get('version', '1.0.0')}")
            name_label.setStyleSheet("color: white;")
            info_layout.addWidget(name_label)
            
            desc_label = QLabel(plugin_info.get('description', 'Нет описания'))
            desc_label.setStyleSheet("color: #888; font-size: 10px;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)
            
            author_label = QLabel(f"Автор: {plugin_info.get('author', 'Неизвестен')}")
            author_label.setStyleSheet("color: #666; font-size: 9px;")
            info_layout.addWidget(author_label)
            
            item_layout.addLayout(info_layout)
            item_layout.addStretch()
            
            enabled_btn = QCheckBox("Включен")
            enabled_btn.setChecked(plugin_name in self.enabled_plugins)
            enabled_btn.stateChanged.connect(lambda state, name=plugin_name: self.toggle_plugin(name, state))
            item_layout.addWidget(enabled_btn)
            
            item.setSizeHint(widget.sizeHint())
            list_widget.addItem(item)
            list_widget.setItemWidget(item, widget)
    
    def open_plugins_folder(self):
        """Открывает папку с плагинами"""
        import subprocess
        import os
        
        path = str(self.plugins_dir)
        if os.name == 'nt':
            subprocess.run(['explorer', path])
        elif os.name == 'posix':
            subprocess.run(['open', path])
    
    def scan_plugins(self):
        """Сканирует папку на наличие плагинов"""
        plugins = {}
        
        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
                
            plugin_name = plugin_file.stem
            
            # Пытаемся загрузить метаданные
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Ищем класс плагина
                plugin_class = None
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj != PluginInterface:
                        plugin_class = obj
                        break
                
                if plugin_class:
                    # Создаем временный экземпляр для получения метаданных
                    temp_plugin = plugin_class(self.launcher)
                    plugins[plugin_name] = {
                        'name': temp_plugin.name,
                        'version': temp_plugin.version,
                        'author': temp_plugin.author,
                        'description': temp_plugin.description,
                        'class': plugin_class,
                        'file': plugin_file
                    }
            except Exception as e:
                print(f"Ошибка сканирования плагина {plugin_name}: {e}")
                self.plugin_error.emit(plugin_name, str(e))
        
        return plugins
    
    def toggle_plugin(self, plugin_name, enabled):
        """Включает или выключает плагин"""
        if enabled:
            self.enable_plugin(plugin_name)
        else:
            self.disable_plugin(plugin_name)
        
        # Сохраняем состояние
        self.save_enabled_plugins()
    
    def enable_plugin(self, plugin_name):
        """Включает плагин"""
        if plugin_name in self.plugins:
            return True
            
        plugin_file = self.plugins_dir / f"{plugin_name}.py"
        if not plugin_file.exists():
            return False
        
        try:
            # Загружаем модуль
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)
            
            # Находим класс плагина
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj != PluginInterface:
                    plugin_class = obj
                    break
            
            if plugin_class:
                # Создаем экземпляр плагина
                plugin = plugin_class(self.launcher)
                self.plugins[plugin_name] = plugin
                self.plugin_modules[plugin_name] = module
                
                # Вызываем on_load
                plugin.on_load()
                
                # Добавляем в список включенных
                if plugin_name not in self.enabled_plugins:
                    self.enabled_plugins.append(plugin_name)
                
                self.plugin_loaded.emit(plugin_name)
                print(f"Плагин {plugin_name} загружен")
                
                # Добавляем вкладку если есть
                tab = plugin.create_tab()
                if tab and hasattr(self.launcher, 'stacked_widget'):
                    self.launcher.stacked_widget.addWidget(tab)
                
                return True
        except Exception as e:
            print(f"Ошибка загрузки плагина {plugin_name}: {e}")
            self.plugin_error.emit(plugin_name, str(e))
        
        return False
    
    def disable_plugin(self, plugin_name):
        """Выключает плагин"""
        if plugin_name in self.plugins:
            try:
                # Вызываем on_unload
                self.plugins[plugin_name].on_unload()
                
                # Удаляем из списков
                del self.plugins[plugin_name]
                
                if plugin_name in self.plugin_modules:
                    del self.plugin_modules[plugin_name]
                
                if plugin_name in self.enabled_plugins:
                    self.enabled_plugins.remove(plugin_name)
                
                print(f"Плагин {plugin_name} выгружен")
            except Exception as e:
                print(f"Ошибка выгрузки плагина {plugin_name}: {e}")
    
    def load_enabled_plugins(self):
        """Загружает список включенных плагинов"""
        settings_path = Path.home() / ".pylauncher" / "plugins_enabled.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def save_enabled_plugins(self):
        """Сохраняет список включенных плагинов"""
        settings_path = Path.home() / ".pylauncher" / "plugins_enabled.json"
        try:
            with open(settings_path, 'w') as f:
                json.dump(self.enabled_plugins, f)
        except Exception as e:
            print(f"Ошибка сохранения списка плагинов: {e}")
    
    def load_all_plugins(self):
        """Загружает все включенные плагины"""
        for plugin_name in self.enabled_plugins:
            self.enable_plugin(plugin_name)
    
    def on_game_start(self):
        """Вызывается при запуске игры"""
        for plugin in self.plugins.values():
            try:
                plugin.on_game_start()
            except Exception as e:
                print(f"Ошибка в плагине {plugin.name}: {e}")
    
    def on_game_stop(self):
        """Вызывается при завершении игры"""
        for plugin in self.plugins.values():
            try:
                plugin.on_game_stop()
            except Exception as e:
                print(f"Ошибка в плагине {plugin.name}: {e}")
    
    def on_settings_open(self):
        """Вызывается при открытии настроек"""
        for plugin in self.plugins.values():
            try:
                plugin.on_settings_open()
            except Exception as e:
                print(f"Ошибка в плагине {plugin.name}: {e}")