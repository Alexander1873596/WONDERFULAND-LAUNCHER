from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os
from core.config import DEFAULT_MC_VERSION, get_asset_path

class MainWindowUI:
    
    def setup_main_page(self):
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        top_panel = QHBoxLayout()
        top_panel.setContentsMargins(10, 10, 10, 10)
        top_panel.addStretch()
        
        if self.beta_enabled:
            self.customize_button = QPushButton()
            self.customize_button.setFixedSize(45, 45)
            customize_icon_path = get_asset_path("customize.png")
            if os.path.exists(customize_icon_path):
                self.customize_button.setIcon(QIcon(customize_icon_path))
            else:
                pixmap = QPixmap(45, 45)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.setPen(Qt.white)
                painter.setFont(QFont("Arial", 20))
                painter.drawText(pixmap.rect(), Qt.AlignCenter, "C")
                painter.end()
                self.customize_button.setIcon(QIcon(pixmap))
            self.customize_button.setIconSize(QSize(45, 45))
            self.customize_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            self.customize_button.clicked.connect(self.show_customization)
            top_panel.addWidget(self.customize_button)
        
        self.mods_button = QPushButton()
        self.mods_button.setFixedSize(45, 45)
        mods_icon_path = get_asset_path("mods.png")
        if os.path.exists(mods_icon_path):
            self.mods_button.setIcon(QIcon(mods_icon_path))
        else:
            pixmap = QPixmap(45, 45)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 20))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "M")
            painter.end()
            self.mods_button.setIcon(QIcon(pixmap))
        self.mods_button.setIconSize(QSize(45, 45))
        self.mods_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.mods_button.clicked.connect(self.show_mods_panel)
        top_panel.addWidget(self.mods_button)
        
        self.exit_button = QPushButton()
        self.exit_button.setFixedSize(45, 45)
        exit_icon_path = get_asset_path("exit.png")
        if os.path.exists(exit_icon_path):
            self.exit_button.setIcon(QIcon(exit_icon_path))
        else:
            pixmap = QPixmap(45, 45)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 20))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "X")
            painter.end()
            self.exit_button.setIcon(QIcon(pixmap))
        self.exit_button.setIconSize(QSize(45, 45))
        self.exit_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.exit_button.clicked.connect(self.close)
        top_panel.addWidget(self.exit_button)
        
        main_layout.addLayout(top_panel)
        
        top_layout = QHBoxLayout()
        title_label = QLabel()
        logo_path = get_asset_path("logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            title_label.setPixmap(pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            title_label.setText("WONDERFULAND")
            title_label.setStyleSheet("font-size: 48px; font-weight: bold; color: white;")
        title_label.setAlignment(Qt.AlignCenter)
        top_layout.addStretch()
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        
        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)
        bottom_layout.setContentsMargins(30, 0, 30, 0)
        
        name_group = QGroupBox("Имя игрока")
        name_group.setFixedWidth(200)
        name_layout = QVBoxLayout()
        self.name_edit = QLineEdit("Player")
        name_layout.addWidget(self.name_edit)
        name_group.setLayout(name_layout)
        bottom_layout.addWidget(name_group)
        
        self.version_group = QGroupBox("Версия")
        self.version_group.setFixedWidth(150)
        self.version_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: rgba(42, 42, 42, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                background: rgba(42, 42, 42, 150);
                color: white;
                font-size: 11px;
            }
            QGroupBox:hover {
                border: 1px solid #4CAF50;
                background-color: rgba(58, 58, 58, 150);
            }
        """)
        
        self.version_group.enterEvent = lambda event: self.version_group.setCursor(Qt.PointingHandCursor)
        self.version_group.leaveEvent = lambda event: self.version_group.setCursor(Qt.ArrowCursor)
        self.version_group.mousePressEvent = self.on_version_group_click
        
        version_layout = QVBoxLayout()
        version_layout.setSpacing(2)
        version_layout.setContentsMargins(5, 5, 5, 5)
        
        self.version_label = QLabel(self.current_mc_version)
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #4CAF50; padding: 2px;")
        self.version_label.setWordWrap(True)
        version_layout.addWidget(self.version_label)
        
        self.version_type_label = QLabel("release")
        self.version_type_label.setAlignment(Qt.AlignCenter)
        self.version_type_label.setStyleSheet("color: #888; font-size: 9px;")
        version_layout.addWidget(self.version_type_label)
        
        self.version_group.setLayout(version_layout)
        bottom_layout.addWidget(self.version_group)

        loader_group = QGroupBox("Лоадер")
        loader_group.setFixedWidth(130)
        loader_layout = QVBoxLayout()
        loader_layout.setContentsMargins(5, 5, 5, 5)
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["Vanilla", "Forge", "Fabric"])
        self.loader_combo.setCurrentText("Vanilla")
        self.loader_combo.setStyleSheet("font-size: 11px;")
        loader_layout.addWidget(self.loader_combo)
        loader_group.setLayout(loader_layout)
        bottom_layout.addWidget(loader_group)
        
        bottom_layout.addStretch()
        
        self.play_button = QPushButton()
        play_icon_path = get_asset_path("play.png")
        if os.path.exists(play_icon_path):
            self.play_button.setIcon(QIcon(play_icon_path))
        else:
            self.play_button.setText("ИГРАТЬ")
            self.play_button.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.play_button.setIconSize(QSize(250, 150))
        self.play_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
                font-size: 16px;
                font-weight: bold;
                color: white;
            }
            QPushButton:disabled {
                opacity: 0.5;
            }
        """)
        self.play_button.setFixedSize(250, 50)
        self.play_button.clicked.connect(self.launch_game)
        bottom_layout.addWidget(self.play_button)
        
        self.settings_button = QPushButton()
        settings_icon_path = get_asset_path("settings.png")
        if os.path.exists(settings_icon_path):
            self.settings_button.setIcon(QIcon(settings_icon_path))
        else:
            pixmap = QPixmap(55, 55)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 25))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "S")
            painter.end()
            self.settings_button.setIcon(QIcon(pixmap))
        self.settings_button.setIconSize(QSize(55, 55))
        self.settings_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)
        self.settings_button.clicked.connect(self.show_settings)
        bottom_layout.addWidget(self.settings_button)
        
        main_layout.addLayout(bottom_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                background: rgba(51, 51, 51, 180);
                height: 18px;
            }
            QProgressBar::chunk {
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Готов к запуску")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888; margin: 5px; font-size: 11px;")
        main_layout.addWidget(self.status_label)
        
        self.setWindowTitle("WONDERFULAND")
        self.setFixedSize(1100, 600)
        
        icon_path = get_asset_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.apply_styles()
    
    def on_version_group_click(self, event):
        if event.button() == Qt.LeftButton:
            self.show_version_selector()
    
    def show_version_selector(self):
        from dialogs.version_selector import VersionSelectorDialog
        dialog = VersionSelectorDialog(self, self.current_mc_version)
        if dialog.exec_() == QDialog.Accepted:
            selected_version = dialog.get_selected_version()
            if selected_version:
                self.current_mc_version = selected_version["id"]
                self.version_label.setText(selected_version["id"])
                self.version_type_label.setText(selected_version.get("type", "release"))
                self.status_label.setText(f"Выбрана версия: {selected_version['id']}")
    
    def apply_styles(self):
        self.setStyleSheet("""
            QLabel { 
                color: white; 
                background: transparent;
                border: none;
                font-size: 11px;
            }
            QLineEdit {
                background: rgba(51, 51, 51, 180);
                color: white;
                border: 1px solid #444;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
            QGroupBox {
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: rgba(42, 42, 42, 150);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                background: rgba(42, 42, 42, 150);
                color: white;
                font-size: 11px;
            }
            QGroupBox:hover {
                border: 1px solid #4CAF50;
            }
            QPushButton {
                background: rgba(51, 51, 51, 180);
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #444;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(58, 58, 58, 180);
                border: 1px solid #4CAF50;
            }
            QPushButton[iconOnly="true"] {
                background: transparent;
                border: none;
            }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 6px;
                background: rgba(51, 51, 51, 180);
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #444;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QComboBox {
                background: rgba(51, 51, 51, 180);
                color: white;
                border: 1px solid #444;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #4CAF50;
            }
            QComboBox::drop-down {
                border: 0px;
                background: transparent;
                width: 18px;
            }
            QComboBox:on {
                padding-top: 2px;
                padding-left: 3px;
            }
            QComboBox QAbstractItemView {
                background: #2d2d2d;
                color: white;
                selection-background-color: #4CAF50;
                border: 1px solid #444;
                font-size: 11px;
            }
            QCheckBox {
                color: white;
                spacing: 4px;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
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