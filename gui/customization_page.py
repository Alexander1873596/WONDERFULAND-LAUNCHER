from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pathlib import Path
import json
import shutil
import os
from core.config import get_asset_path
from gui.widgets import BackgroundWidget

class CustomizationPage(BackgroundWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.themes = {
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
        self.custom_bg_path = None
        self.init_ui()
        self.load_customization_settings()
        
    def init_ui(self):
        settings_layout = QVBoxLayout(self)
        
        # Заголовок
        title_label = QLabel("Настройка внешнего вида")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin: 10px;")
        settings_layout.addWidget(title_label)
        
        # Группа выбора шрифта
        font_group = QGroupBox("Шрифт лаунчера")
        font_layout = QVBoxLayout()
        
        font_preview_layout = QHBoxLayout()
        self.font_preview = QLabel("Образец шрифта")
        self.font_preview.setAlignment(Qt.AlignCenter)
        self.font_preview.setStyleSheet("""
            border: 1px solid #444;
            border-radius: 5px;
            padding: 10px;
            background: rgba(30, 30, 30, 150);
            min-height: 50px;
        """)
        font_preview_layout.addWidget(self.font_preview)
        font_layout.addLayout(font_preview_layout)
        
        font_buttons_layout = QHBoxLayout()
        
        select_font_btn = QPushButton("Выбрать шрифт")
        select_font_btn.clicked.connect(self.select_font)
        font_buttons_layout.addWidget(select_font_btn)
        
        reset_font_btn = QPushButton("Сбросить")
        reset_font_btn.clicked.connect(self.reset_font)
        font_buttons_layout.addWidget(reset_font_btn)
        
        font_layout.addLayout(font_buttons_layout)
        
        font_group.setLayout(font_layout)
        settings_layout.addWidget(font_group)
        
        # Группа выбора темы
        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.themes.keys()))
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        # Предпросмотр темы
        preview_layout = QHBoxLayout()
        
        self.bg_preview = QLabel()
        self.bg_preview.setFixedSize(50, 50)
        self.bg_preview.setStyleSheet("border: 2px solid white; border-radius: 5px;")
        preview_layout.addWidget(self.bg_preview)
        preview_layout.addWidget(QLabel("Фон"))
        
        self.accent_preview = QLabel()
        self.accent_preview.setFixedSize(50, 50)
        self.accent_preview.setStyleSheet("border: 2px solid white; border-radius: 5px;")
        preview_layout.addWidget(self.accent_preview)
        preview_layout.addWidget(QLabel("Акцент"))
        
        self.text_preview = QLabel("Текст")
        self.text_preview.setStyleSheet("padding: 5px; border: 1px solid white; border-radius: 3px;")
        preview_layout.addWidget(self.text_preview)
        
        theme_layout.addLayout(preview_layout)
        theme_group.setLayout(theme_layout)
        settings_layout.addWidget(theme_group)
        
        # Группа загрузки своего фона
        bg_group = QGroupBox("Свой фон (изображение)")
        bg_layout = QVBoxLayout()
        
        upload_layout = QHBoxLayout()
        
        self.upload_image_btn = QPushButton("Загрузить изображение")
        self.upload_image_btn.clicked.connect(self.upload_image)
        upload_layout.addWidget(self.upload_image_btn)
        
        self.reset_bg_btn = QPushButton("Сбросить")
        self.reset_bg_btn.clicked.connect(self.reset_background)
        upload_layout.addWidget(self.reset_bg_btn)
        
        bg_layout.addLayout(upload_layout)
        
        self.bg_info_label = QLabel("Текущий фон: стандартный")
        self.bg_info_label.setWordWrap(True)
        self.bg_info_label.setStyleSheet("color: #888; padding: 5px;")
        bg_layout.addWidget(self.bg_info_label)
        
        bg_group.setLayout(bg_layout)
        settings_layout.addWidget(bg_group)
        
        # Группа дополнительных настроек
        extra_group = QGroupBox("Дополнительно")
        extra_layout = QVBoxLayout()
        
        # Прозрачность
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Прозрачность затемнения:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(70)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("70%")
        opacity_layout.addWidget(self.opacity_label)
        extra_layout.addLayout(opacity_layout)
        
        extra_group.setLayout(extra_layout)
        settings_layout.addWidget(extra_group)
        
        settings_layout.addStretch()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_customization)
        buttons_layout.addWidget(save_btn)
        
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self.apply_customization)
        buttons_layout.addWidget(apply_btn)
        
        back_btn = QPushButton("Назад")
        back_btn.clicked.connect(self.parent.show_main)
        buttons_layout.addWidget(back_btn)
        
        settings_layout.addLayout(buttons_layout)
        
        self.apply_styles()
        
    def apply_styles(self):
        """Применяет стили к странице кастомизации"""
        self.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 15px;
                padding-top: 10px;
                background-color: rgba(42, 42, 42, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background: rgba(42, 42, 42, 150);
            }
            QComboBox, QCheckBox, QLabel {
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
        """)
        
    def select_font(self):
        """Открывает диалог выбора шрифта"""
        font, ok = QFontDialog.getFont(self.parent.font(), self, "Выберите шрифт для лаунчера")
        if ok:
            self.parent.custom_font = font
            self.parent.apply_custom_font(font)
            self.update_font_preview(font)
            self.parent.status_label.setText("Шрифт применен")
    
    def reset_font(self):
        """Сбрасывает шрифт на стандартный"""
        self.parent.custom_font = None
        self.parent.reset_to_default_font()
        self.update_font_preview(self.parent.font())
        self.parent.status_label.setText("Шрифт сброшен")
    
    def update_font_preview(self, font):
        """Обновляет предпросмотр шрифта"""
        self.font_preview.setFont(font)
        self.font_preview.setText(f"Образец шрифта: {font.family()} {font.pointSize()}")
        
    def on_theme_changed(self, theme_name):
        """Обработчик изменения темы"""
        theme = self.themes.get(theme_name, self.themes["Темная (стандартная)"])
        
        # Обновляем предпросмотр
        self.bg_preview.setStyleSheet(f"background: {theme['bg_color']}; border: 2px solid white; border-radius: 5px;")
        self.accent_preview.setStyleSheet(f"background: {theme['accent_color']}; border: 2px solid white; border-radius: 5px;")
        self.text_preview.setStyleSheet(f"color: {theme['text_color']}; padding: 5px; border: 1px solid white; border-radius: 3px;")
        
    def upload_image(self):
        """Загрузка изображения для фона"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение для фона",
            str(Path.home()),
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            # Копируем в папку с настройками
            custom_dir = Path.home() / ".pylauncher" / "custom"
            custom_dir.mkdir(parents=True, exist_ok=True)
            
            # Удаляем старые фоны
            for old_file in custom_dir.glob("custom_bg.*"):
                try:
                    os.remove(old_file)
                except:
                    pass
            
            dest_path = custom_dir / f"custom_bg{Path(file_path).suffix}"
            shutil.copy2(file_path, dest_path)
            
            self.custom_bg_path = str(dest_path)
            self.bg_info_label.setText(f"Изображение: {Path(file_path).name}")
            self.parent.status_label.setText("Изображение загружено")
        
    def reset_background(self):
        """Сброс фона на стандартный"""
        self.custom_bg_path = None
        self.bg_info_label.setText("Текущий фон: стандартный")
        
        # Удаляем сохраненные фоны
        custom_dir = Path.home() / ".pylauncher" / "custom"
        if custom_dir.exists():
            for old_file in custom_dir.glob("custom_bg.*"):
                try:
                    os.remove(old_file)
                except:
                    pass
        
    def on_opacity_changed(self, value):
        """Обработчик изменения прозрачности"""
        self.opacity_label.setText(f"{value}%")
        
    def apply_customization(self):
        """Применяет настройки кастомизации"""
        theme_name = self.theme_combo.currentText()
        theme = self.themes.get(theme_name, self.themes["Темная (стандартная)"])
        
        # Применяем тему к родительскому окну
        if hasattr(self.parent, 'apply_theme'):
            self.parent.apply_theme(theme)
        
        # Применяем фон
        if self.custom_bg_path:
            if hasattr(self.parent, 'set_custom_background'):
                self.parent.set_custom_background(self.custom_bg_path)
        else:
            if hasattr(self.parent, 'reset_background'):
                self.parent.reset_background()
        
        # Применяем прозрачность
        opacity = self.opacity_slider.value()
        if hasattr(self.parent, 'set_overlay_opacity'):
            self.parent.set_overlay_opacity(opacity)
        
        self.parent.status_label.setText("Настройки внешнего вида применены")
        
    def save_customization(self):
        """Сохраняет настройки кастомизации"""
        settings = {
            "theme": self.theme_combo.currentText(),
            "custom_bg": self.custom_bg_path,
            "opacity": self.opacity_slider.value()
        }
        
        # Сохраняем информацию о шрифте если есть
        if hasattr(self.parent, 'custom_font') and self.parent.custom_font:
            font = self.parent.custom_font
            settings["font_family"] = font.family()
            settings["font_size"] = font.pointSize()
            settings["font_bold"] = font.bold()
            settings["font_italic"] = font.italic()
        
        settings_path = Path.home() / ".pylauncher" / "customization.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        self.apply_customization()
        self.parent.status_label.setText("Настройки сохранены")
        
    def load_customization_settings(self):
        """Загружает настройки кастомизации"""
        settings_path = Path.home() / ".pylauncher" / "customization.json"
        
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.theme_combo.setCurrentText(settings.get("theme", "Темная (стандартная)"))
                self.custom_bg_path = settings.get("custom_bg")
                self.opacity_slider.setValue(settings.get("opacity", 70))
                
                if self.custom_bg_path and os.path.exists(self.custom_bg_path):
                    self.bg_info_label.setText(f"Изображение: {Path(self.custom_bg_path).name}")
                    
            except Exception as e:
                print(f"Ошибка загрузки настроек кастомизации: {e}")