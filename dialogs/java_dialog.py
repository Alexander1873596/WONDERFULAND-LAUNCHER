from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os
import minecraft_launcher_lib
import threading
import time
from pathlib import Path
from core.config import get_recommended_java_version, get_asset_path
from core.utils import check_java_version

class JavaDownloadDialog(QDialog):
    # Создаем сигналы для обновления UI из потока
    download_success_signal = pyqtSignal(str)
    download_error_signal = pyqtSignal(str)
    progress_update_signal = pyqtSignal(int)
    status_update_signal = pyqtSignal(str)
    
    def __init__(self, parent, mc_version=None):
        super().__init__(parent)
        self.parent = parent
        self.mc_version = mc_version or parent.current_mc_version
        self.recommended_java = get_recommended_java_version(self.mc_version)
        self.download_thread = None
        self.drag_pos = None
        self.is_downloading = False
        self.init_ui()
        
        # Подключаем сигналы к слотам
        self.download_success_signal.connect(self.on_download_success)
        self.download_error_signal.connect(self.on_download_error)
        self.progress_update_signal.connect(self.on_progress_update)
        self.status_update_signal.connect(self.on_status_update)
        
    def init_ui(self):
        self.setWindowTitle(f"Скачивание Java {self.recommended_java}")
        self.setFixedSize(600, 420)
        self.setModal(True)
        
        # Стандартные флаги окна
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        self.setStyleSheet("""
            QDialog {
                background: #2d2d2d;
                border: 2px solid #444;
            }
            QLabel {
                color: white;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton {
                background: #3d3d3d;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                border: 1px solid #555;
                min-width: 140px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #4d4d4d;
                border: 1px solid #4CAF50;
            }
            QPushButton:disabled {
                background: #2d2d2d;
                color: #666;
                border: 1px solid #444;
            }
            QPushButton#downloadBtn {
                background: #4CAF50;
                border: none;
            }
            QPushButton#downloadBtn:hover {
                background: #45a049;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                height: 30px;
                background: #3d3d3d;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Заголовок
        title_label = QLabel(f"Скачивание Java {self.recommended_java}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50; margin: 5px;")
        layout.addWidget(title_label)
        
        # Информация о версии
        version_info = QLabel(f"Minecraft {self.mc_version}")
        version_info.setAlignment(Qt.AlignCenter)
        version_info.setStyleSheet("font-size: 14px; color: #888; margin: 0; padding: 0;")
        layout.addWidget(version_info)
        
        # Основная информация
        info_frame = QFrame()
        info_frame.setStyleSheet("background: #3d3d3d; border-radius: 5px; padding: 5px;")
        info_layout = QVBoxLayout(info_frame)
        
        info_text = QLabel(f"<b>Требуется Java {self.recommended_java}</b>")
        info_text.setAlignment(Qt.AlignCenter)
        info_text.setStyleSheet("font-size: 14px; color: #4CAF50;")
        info_layout.addWidget(info_text)
        
        desc_text = QLabel(
            f"Ваша текущая версия Java не подходит для запуска Minecraft {self.mc_version}.\n"
            f"Лаунчер автоматически скачает и установит подходящую версию Java."
        )
        desc_text.setWordWrap(True)
        desc_text.setAlignment(Qt.AlignCenter)
        desc_text.setStyleSheet("font-size: 12px; color: white; padding: 10px;")
        info_layout.addWidget(desc_text)
        
        path_text = QLabel(f"Папка установки: {self.parent.minecraft_dir / 'runtime'}")
        path_text.setAlignment(Qt.AlignCenter)
        path_text.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(path_text)
        
        layout.addWidget(info_frame)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Статус
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold; min-height: 25px;")
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        self.download_btn = QPushButton(f"Скачать Java {self.recommended_java}")
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        button_layout.addWidget(self.download_btn)
        
        self.manual_btn = QPushButton("Указать вручную")
        self.manual_btn.clicked.connect(self.manual_select)
        self.manual_btn.setCursor(Qt.PointingHandCursor)
        button_layout.addWidget(self.manual_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Предупреждение для старых версий
        if self.recommended_java == 8:
            warning_frame = QFrame()
            warning_frame.setStyleSheet("background: #3d3d3d; border-radius: 3px; margin-top: 5px;")
            warning_layout = QHBoxLayout(warning_frame)
            warning_layout.setContentsMargins(10, 10, 10, 10)
            
            warning_icon = QLabel("⚠️")
            warning_icon.setStyleSheet("font-size: 20px; color: #FFA500; padding: 0;")
            warning_icon.setFixedWidth(30)
            warning_layout.addWidget(warning_icon)
            
            warning_text = QLabel(
                "Для старых версий Minecraft (1.7.10 - 1.12.2) требуется Java 8. "
                "После установки лаунчер автоматически найдет и использует её."
            )
            warning_text.setWordWrap(True)
            warning_text.setStyleSheet("color: #FFA500; font-size: 11px;")
            warning_layout.addWidget(warning_text, 1)
            
            layout.addWidget(warning_frame)
    
    def start_download(self):
        """Запускает скачивание в отдельном потоке"""
        if self.is_downloading:
            return
            
        self.is_downloading = True
        self.download_btn.setEnabled(False)
        self.manual_btn.setEnabled(False)
        self.cancel_btn.setText("Прервать")
        
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.show()
        self.status_label.setText("Подготовка к скачиванию...")
        
        # Запускаем скачивание в отдельном потоке
        self.download_thread = threading.Thread(target=self.download_java, daemon=True)
        self.download_thread.start()
        
        # Таймер для проверки статуса потока
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_download_status)
        self.timer.start(100)
    
    def download_java(self):
        """Скачивает Java (выполняется в отдельном потоке)"""
        try:
            # Определяем runtime для нужной версии Java
            if self.recommended_java == 8:
                runtime_name = "java-runtime-alpha"
            elif self.recommended_java == 11:
                runtime_name = "java-runtime-beta"
            elif self.recommended_java == 17:
                runtime_name = "java-runtime-delta"
            else:  # 21+
                runtime_name = "java-runtime-gamma"
            
            java_dir = self.parent.minecraft_dir / "runtime"
            java_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем callback для обновления прогресса
            def set_status(text):
                self.status_update_signal.emit(text)
            
            def set_progress(progress):
                self.progress_update_signal.emit(int(progress * 100))
            
            callback = {
                "setStatus": set_status,
                "setProgress": set_progress,
                "setMax": lambda max_val: None
            }
            
            # Обновляем статус
            self.status_update_signal.emit(f"Скачивание Java {self.recommended_java}...")
            
            # Скачиваем Java
            minecraft_launcher_lib.runtime.install_jvm_runtime(
                runtime_name,
                str(java_dir),
                callback=callback
            )
            
            # Даем время на завершение записи файлов
            time.sleep(2)
            
            # Ищем установленную Java
            self.status_update_signal.emit("Поиск установленной Java...")
            java_path = self.find_installed_java()
            
            if java_path:
                self.download_success_signal.emit(java_path)
            else:
                # Если не нашли, пробуем найти в подпапках
                self.status_update_signal.emit("Расширенный поиск Java...")
                java_path = self.find_java_deep()
                if java_path:
                    self.download_success_signal.emit(java_path)
                else:
                    self.download_error_signal.emit("Java установлена, но путь не найден")
                
        except Exception as e:
            self.download_error_signal.emit(str(e))
    
    def find_installed_java(self):
        """Ищет установленную Java в стандартной папке runtime"""
        runtime_path = self.parent.minecraft_dir / "runtime"
        
        # Определяем нужную папку runtime
        if self.recommended_java == 8:
            runtime_name = "java-runtime-alpha"
        elif self.recommended_java == 11:
            runtime_name = "java-runtime-beta"
        elif self.recommended_java == 17:
            runtime_name = "java-runtime-delta"
        else:
            runtime_name = "java-runtime-gamma"
        
        # Проверяем разные возможные пути
        possible_paths = [
            runtime_path / runtime_name / "bin" / "java.exe",
            runtime_path / runtime_name / "bin" / "java",
            runtime_path / runtime_name / "jre" / "bin" / "java.exe",
            runtime_path / runtime_name / "jre" / "bin" / "java",
            runtime_path / runtime_name / "contents" / "home" / "bin" / "java",  # для Mac
        ]
        
        for java_path in possible_paths:
            if java_path.exists():
                is_valid, msg = check_java_version(str(java_path), self.recommended_java)
                if is_valid:
                    return str(java_path)
        
        return None
    
    def find_java_deep(self):
        """Глубокий поиск Java во всех подпапках runtime"""
        runtime_path = self.parent.minecraft_dir / "runtime"
        
        if not runtime_path.exists():
            return None
        
        # Ищем все файлы java.exe или java
        for root, dirs, files in os.walk(runtime_path):
            for file in files:
                if file.lower() in ["java.exe", "java"]:
                    java_path = Path(root) / file
                    is_valid, msg = check_java_version(str(java_path), self.recommended_java)
                    if is_valid:
                        print(f"Найдена Java: {java_path}")
                        return str(java_path)
        
        return None
    
    def check_download_status(self):
        """Проверяет статус скачивания"""
        if not self.download_thread or not self.download_thread.is_alive():
            self.timer.stop()
    
    @pyqtSlot(int)
    def on_progress_update(self, value):
        """Обновляет прогресс бар"""
        self.progress_bar.setValue(value)
    
    @pyqtSlot(str)
    def on_status_update(self, text):
        """Обновляет статус"""
        self.status_label.setText(text)
    
    @pyqtSlot(str)
    def on_download_success(self, java_path):
        """Вызывается при успешном скачивании"""
        self.status_label.setText("Java успешно установлена!")
        self.progress_bar.setValue(100)
        
        # Устанавливаем путь к Java
        self.parent.java_path = java_path
        self.parent.java_edit.setText(java_path)
        
        # Показываем сообщение об успехе
        QMessageBox.information(self, "Успешно", 
                               f"Java {self.recommended_java} успешно установлена!\n\n"
                               f"Путь: {java_path}")
        
        self.accept()
    
    @pyqtSlot(str)
    def on_download_error(self, error_msg):
        """Вызывается при ошибке скачивания"""
        self.status_label.setText(f"Ошибка: {error_msg}")
        self.progress_bar.hide()
        
        self.download_btn.setEnabled(True)
        self.manual_btn.setEnabled(True)
        self.cancel_btn.setText("Отмена")
        self.is_downloading = False
        
        # Показываем информацию о том, где искали Java
        runtime_path = self.parent.minecraft_dir / "runtime"
        QMessageBox.critical(self, "Ошибка", 
                            f"Не удалось найти установленную Java.\n\n"
                            f"Папка установки: {runtime_path}\n"
                            f"Ошибка: {error_msg}\n\n"
                            "Попробуйте указать путь к Java вручную.")
    
    def manual_select(self):
        """Ручной выбор Java"""
        self.parent.browse_java()
        self.accept()
    
    def reject(self):
        """Переопределяем закрытие окна"""
        if self.is_downloading:
            reply = QMessageBox.question(self, "Подтверждение", 
                                        "Скачивание еще не завершено. Прервать?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        super().reject()