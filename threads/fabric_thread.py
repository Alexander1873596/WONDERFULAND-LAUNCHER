from PyQt5.QtCore import *
import json
import requests
import os
from pathlib import Path
import minecraft_launcher_lib
from core.config import FABRIC_VERSIONS

class FabricInstallThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, minecraft_dir, mc_version, java_path):
        super().__init__()
        self.minecraft_dir = Path(minecraft_dir)
        self.mc_version = mc_version
        self.java_path = java_path
        self._is_running = True
        
        # Получаем правильную версию Fabric для указанной версии Minecraft
        self.loader_version = self.get_fabric_loader_version(mc_version)
        self.version_name = f"fabric-loader-{self.loader_version}-{self.mc_version}"
        
    def get_fabric_loader_version(self, mc_version):
        """Получает правильную версию Fabric Loader для указанной версии Minecraft"""
        # Проверяем в словаре
        if mc_version in FABRIC_VERSIONS:
            return FABRIC_VERSIONS[mc_version]
        
        # Для неизвестных версий используем заглушку
        return "0.14.25"
    
    def run(self):
        try:
            self.status.emit(f"Установка Fabric для {self.mc_version}...")
            self.progress.emit(10)
            
            # Проверяем наличие vanilla версии
            if not self.check_vanilla_installation():
                return
            
            self.progress.emit(20)
            
            # Проверяем, установлен ли уже Fabric
            if self.check_existing_fabric():
                self.status.emit("Fabric уже установлен")
                self.progress.emit(100)
                self.finished.emit(True, "Fabric уже установлен")
                return
            
            # Создаем профиль Fabric
            if not self.create_fabric_profile():
                return
            
            self.progress.emit(40)
            
            # Скачиваем библиотеки Fabric
            if not self.download_fabric_libraries():
                self.status.emit("Предупреждение: Некоторые библиотеки не скачались")
            
            self.progress.emit(80)
            
            # Проверяем установку
            if self.verify_installation():
                self.progress.emit(100)
                self.status.emit("Fabric успешно установлен!")
                self.finished.emit(True, "Fabric успешно установлен")
            else:
                self.finished.emit(False, "Не удалось проверить установку Fabric")
                
        except Exception as e:
            self.finished.emit(False, f"Ошибка установки Fabric: {str(e)}")
    
    def check_vanilla_installation(self):
        """Проверяет наличие vanilla Minecraft и устанавливает если нужно"""
        vanilla_dir = self.minecraft_dir / "versions" / self.mc_version
        vanilla_json = vanilla_dir / f"{self.mc_version}.json"
        vanilla_jar = vanilla_dir / f"{self.mc_version}.jar"
        
        if not vanilla_json.exists() or not vanilla_jar.exists():
            self.status.emit(f"Установка Minecraft {self.mc_version}...")
            
            callback = {
                "setStatus": lambda text: self.status.emit(text),
                "setProgress": lambda progress: self.progress.emit(10 + int(progress * 10)),
            }
            
            try:
                minecraft_launcher_lib.install.install_minecraft_version(
                    self.mc_version,
                    str(self.minecraft_dir),
                    callback=callback
                )
            except Exception as e:
                self.finished.emit(False, f"Ошибка установки Vanilla: {str(e)}")
                return False
        
        return True
    
    def check_existing_fabric(self):
        """Проверяет, установлен ли уже Fabric"""
        version_dir = self.minecraft_dir / "versions" / self.version_name
        json_path = version_dir / f"{self.version_name}.json"
        
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if "libraries" in data:
                    for lib in data["libraries"]:
                        if "name" in lib and "fabric" in lib["name"].lower():
                            return True
            except:
                pass
        return False
    
    def create_fabric_profile(self):
        """Создает JSON профиль Fabric"""
        try:
            # Создаем директорию для версии
            version_dir = self.minecraft_dir / "versions" / self.version_name
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Удаляем возможный старый JAR файл
            old_jar = version_dir / f"{self.version_name}.jar"
            if old_jar.exists():
                try:
                    os.remove(old_jar)
                except:
                    pass
            
            # Создаем правильный JSON профиль для Fabric
            profile_data = {
                "id": self.version_name,
                "inheritsFrom": self.mc_version,
                "releaseTime": "2024-01-01T00:00:00+00:00",
                "time": "2024-01-01T00:00:00+00:00",
                "type": "release",
                "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "arguments": {
                    "game": [],
                    "jvm": [
                        "-Dfabric.skipMcProvider=true"
                    ]
                },
                "libraries": [
                    {
                        "name": f"net.fabricmc:fabric-loader:{self.loader_version}",
                        "url": "https://maven.fabricmc.net/"
                    }
                ]
            }
            
            # Сохраняем JSON
            json_path = version_dir / f"{self.version_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
            
            print(f"Создан профиль Fabric: {json_path}")
            return True
            
        except Exception as e:
            print(f"Ошибка создания профиля Fabric: {e}")
            self.finished.emit(False, f"Ошибка создания профиля Fabric: {str(e)}")
            return False
    
    def download_fabric_libraries(self):
        """Скачивает библиотеки Fabric"""
        try:
            # Библиотеки Fabric, которые нужно скачать
            fabric_libraries = [
                {
                    "name": f"net.fabricmc:fabric-loader:{self.loader_version}",
                    "url": "https://maven.fabricmc.net/"
                },
                {
                    "name": f"net.fabricmc:intermediary:{self.mc_version}",
                    "url": "https://maven.fabricmc.net/"
                }
            ]
            
            # Добавляем ASM для старых версий
            version_parts = self.mc_version.split('.')
            major_version = int(version_parts[1]) if len(version_parts) > 1 else 0
            
            if major_version < 16:
                fabric_libraries.extend([
                    {
                        "name": "org.ow2.asm:asm:9.2",
                        "url": "https://repo.maven.apache.org/maven2/"
                    },
                    {
                        "name": "org.ow2.asm:asm-analysis:9.2",
                        "url": "https://repo.maven.apache.org/maven2/"
                    },
                    {
                        "name": "org.ow2.asm:asm-commons:9.2",
                        "url": "https://repo.maven.apache.org/maven2/"
                    },
                    {
                        "name": "org.ow2.asm:asm-tree:9.2",
                        "url": "https://repo.maven.apache.org/maven2/"
                    },
                    {
                        "name": "org.ow2.asm:asm-util:9.2",
                        "url": "https://repo.maven.apache.org/maven2/"
                    }
                ])
            
            total = len(fabric_libraries)
            
            for i, lib in enumerate(fabric_libraries):
                if not self._is_running:
                    return False
                
                parts = lib["name"].split(":")
                if len(parts) >= 3:
                    group, artifact, version = parts[0], parts[1], parts[2]
                    
                    base_url = lib["url"]
                    if not base_url.endswith("/"):
                        base_url += "/"
                    
                    lib_path = group.replace(".", "/") + f"/{artifact}/{version}/{artifact}-{version}.jar"
                    lib_url = base_url + lib_path
                    
                    dest_path = self.minecraft_dir / "libraries" / lib_path.replace("/", os.sep)
                    
                    if not dest_path.exists():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        try:
                            self.status.emit(f"Скачивание: {artifact}")
                            response = requests.get(lib_url, timeout=30)
                            if response.status_code == 200:
                                with open(dest_path, 'wb') as f:
                                    f.write(response.content)
                                print(f"Скачана библиотека: {artifact}")
                            else:
                                print(f"Не удалось скачать {artifact}: HTTP {response.status_code}")
                        except Exception as e:
                            print(f"Ошибка скачивания {artifact}: {e}")
                
                # Обновляем прогресс
                progress = 40 + int((i + 1) / total * 35)
                self.progress.emit(progress)
            
            return True
            
        except Exception as e:
            print(f"Ошибка при скачивании библиотек: {e}")
            return False
    
    def verify_installation(self):
        """Проверяет успешность установки Fabric"""
        try:
            # Проверяем наличие JSON профиля
            json_path = self.minecraft_dir / "versions" / self.version_name / f"{self.version_name}.json"
            if not json_path.exists():
                print(f"JSON не найден: {json_path}")
                return False
            
            # Проверяем, что нет JAR файла (Fabric не должен его иметь)
            jar_path = self.minecraft_dir / "versions" / self.version_name / f"{self.version_name}.jar"
            if jar_path.exists():
                try:
                    os.remove(jar_path)
                    print(f"Удален лишний JAR файл: {jar_path}")
                except:
                    pass
            
            # Проверяем наличие vanilla JAR
            vanilla_jar = self.minecraft_dir / "versions" / self.mc_version / f"{self.mc_version}.jar"
            if not vanilla_jar.exists():
                print(f"Vanilla JAR не найден: {vanilla_jar}")
                return False
            
            # Проверяем наличие библиотеки fabric-loader
            loader_lib = self.minecraft_dir / "libraries" / "net" / "fabricmc" / "fabric-loader" / self.loader_version / f"fabric-loader-{self.loader_version}.jar"
            if not loader_lib.exists():
                print(f"Библиотека Fabric Loader не найдена: {loader_lib}")
                # Пробуем скачать снова
                self.download_specific_library(f"net.fabricmc:fabric-loader:{self.loader_version}", "https://maven.fabricmc.net/")
            
            print("Все проверки Fabric пройдены успешно")
            return True
            
        except Exception as e:
            print(f"Ошибка проверки установки: {e}")
            return False
    
    def download_specific_library(self, library_name, base_url):
        """Скачивает конкретную библиотеку"""
        try:
            parts = library_name.split(":")
            if len(parts) < 3:
                return
            
            group, artifact, version = parts[0], parts[1], parts[2]
            
            if not base_url.endswith("/"):
                base_url += "/"
            
            lib_path = group.replace(".", "/") + f"/{artifact}/{version}/{artifact}-{version}.jar"
            lib_url = base_url + lib_path
            dest_path = self.minecraft_dir / "libraries" / lib_path.replace("/", os.sep)
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            response = requests.get(lib_url, timeout=30)
            if response.status_code == 200:
                with open(dest_path, 'wb') as f:
                    f.write(response.content)
                print(f"Скачана недостающая библиотека: {artifact}")
                return True
        except Exception as e:
            print(f"Ошибка скачивания библиотеки: {e}")
        return False
    
    def stop(self):
        self._is_running = False