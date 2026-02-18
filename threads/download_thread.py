from PyQt5.QtCore import *
import minecraft_launcher_lib
from pathlib import Path

class DownloadProgressThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, minecraft_dir, version_name):
        super().__init__()
        self.minecraft_dir = minecraft_dir
        self.version_name = version_name
        self._is_running = True
        
    def run(self):
        try:
            callback = {
                "setStatus": lambda text: self.status.emit(text) if self._is_running else None,
                "setProgress": lambda progress: self.progress.emit(int(progress * 100)) if self._is_running else None,
                "setMax": lambda max_val: None
            }
            
            self.status.emit(f"Установка Minecraft {self.version_name}...")
            
            minecraft_launcher_lib.install.install_minecraft_version(
                self.version_name,
                str(self.minecraft_dir),
                callback=callback
            )
            
            # Проверяем успешность установки
            version_dir = Path(self.minecraft_dir) / "versions" / self.version_name
            json_file = version_dir / f"{self.version_name}.json"
            jar_file = version_dir / f"{self.version_name}.jar"
            
            if json_file.exists() and jar_file.exists():
                self.finished.emit(True, "Установка завершена")
            else:
                self.finished.emit(False, "Файлы не найдены после установки")
            
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def stop(self):
        self._is_running = False