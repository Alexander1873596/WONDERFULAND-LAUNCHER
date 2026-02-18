from PyQt5.QtCore import *
import json
import requests
import subprocess
import os
import shutil
import zipfile
from pathlib import Path
from core.config import FORGE_VERSIONS

class ForgeInstallThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, minecraft_dir, mc_version, java_path):
        super().__init__()
        self.minecraft_dir = Path(minecraft_dir)
        self.mc_version = mc_version
        self.java_path = java_path
        self._is_running = True
        
        # Получаем правильную версию Forge для указанной версии Minecraft
        self.forge_version = self.get_forge_version(mc_version)
        
        # Определяем основную версию Minecraft
        version_parts = mc_version.split('.')
        self.major_version = int(version_parts[1]) if len(version_parts) > 1 else 0
        self.minor_version = int(version_parts[2]) if len(version_parts) > 2 else 0
        
        # Определяем является ли версия современной (1.13+)
        self.is_modern_forge = self.major_version >= 13
        
        # Определяем правильный формат Forge в зависимости от версии
        self.determine_forge_format()
        
    def get_forge_version(self, mc_version):
        """Получает правильную версию Forge для указанной версии Minecraft"""
        # Проверяем в словаре из config.py
        if mc_version in FORGE_VERSIONS:
            return FORGE_VERSIONS[mc_version]
        
        # Для версий, которых нет в словаре, пробуем получить через API
        try:
            # Пробуем получить последнюю стабильную версию Forge для данной версии Minecraft
            api_url = f"https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "promos" in data:
                    # Ищем recommended версию для данной версии Minecraft
                    for key, value in data["promos"].items():
                        if key == f"{mc_version}-recommended":
                            return value
                        elif key == f"{mc_version}-latest":
                            # Если нет recommended, берем latest
                            return value
        except:
            pass
        
        # Если ничего не нашли, возвращаем заглушку
        return "latest"
        
    def determine_forge_format(self):
        """Определяет правильный формат Forge для разных версий Minecraft"""
        
        # Forge 1.13+ (современный формат, требует Java 8+ для 1.13-1.16, Java 17+ для 1.17+)
        if self.major_version >= 13:
            self.forge_type = "modern"
            self.version_name = f"{self.mc_version}-forge-{self.forge_version}"
            self.forge_version_id = f"{self.mc_version}-{self.forge_version}"
            self.installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{self.forge_version_id}/forge-{self.forge_version_id}-installer.jar"
            self.main_class = "cpw.mods.modlauncher.Launcher"
            self.library_path = "net/minecraftforge/forge"
            self.is_modern_forge = True
            
        # Forge 1.8 - 1.12 (старый формат с launchwrapper)
        elif self.major_version >= 8:
            self.forge_type = "legacy"
            # Для старых версий формат может быть разным
            if "-" in self.forge_version:
                self.version_name = f"{self.mc_version}-Forge{self.forge_version}"
                self.forge_version_id = self.forge_version
            else:
                self.version_name = f"{self.mc_version}-Forge{self.forge_version}-{self.mc_version}"
                self.forge_version_id = f"{self.mc_version}-{self.forge_version}-{self.mc_version}"
            self.installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{self.forge_version_id}/forge-{self.forge_version_id}-installer.jar"
            self.main_class = "net.minecraft.launchwrapper.Launch"
            self.library_path = "net/minecraftforge/forge"
            self.is_modern_forge = False
            
        # Forge 1.7.10 и старее (очень старый формат)
        else:
            self.forge_type = "very_old"
            if self.mc_version == "1.7.10":
                # Специальный случай для 1.7.10
                self.version_name = f"{self.mc_version}-Forge{self.forge_version}-{self.mc_version}"
                self.forge_version_id = f"{self.mc_version}-{self.forge_version}-{self.mc_version}"
            else:
                self.version_name = f"{self.mc_version}-Forge{self.forge_version}-{self.mc_version}"
                self.forge_version_id = f"{self.mc_version}-{self.forge_version}-{self.mc_version}"
            self.installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{self.forge_version_id}/forge-{self.forge_version_id}-installer.jar"
            self.main_class = "cpw.mods.fml.common.launcher.FMLTweaker"
            self.library_path = "net/minecraftforge/forge"
            self.is_modern_forge = False
        
        print(f"Forge тип: {self.forge_type}, современный: {self.is_modern_forge}, версия: {self.version_name}, ID: {self.forge_version_id}")
    
    def run(self):
        try:
            self.status.emit(f"Установка Forge для {self.mc_version}...")
            self.progress.emit(5)
            
            # Проверяем наличие vanilla версии
            if not self.check_vanilla_installation():
                return
            
            self.progress.emit(15)
            
            # Проверяем, установлен ли уже Forge для этой версии
            if self.check_existing_forge():
                self.status.emit("Forge уже установлен")
                self.progress.emit(100)
                self.finished.emit(True, "Forge уже установлен")
                return
            
            # Скачиваем установщик Forge
            installer_path = self.download_installer()
            if not installer_path:
                return
            
            self.progress.emit(30)
            
            # Запускаем установку в зависимости от типа Forge
            if self.forge_type in ["very_old", "legacy"]:
                success = self.install_legacy_forge(installer_path)
            else:
                success = self.install_modern_forge(installer_path)
            
            if success:
                self.progress.emit(80)
                self.status.emit("Проверка установки...")
                
                # Очищаем временные файлы
                self.cleanup_temp_files(installer_path)
                
                # Для современных версий (1.13+) НЕ исправляем JSON вручную
                if not self.is_modern_forge:
                    self.fix_forge_profile()
                
                # Для 1.7.10 обязательно проверяем launchwrapper
                if self.mc_version == "1.7.10":
                    self.download_required_libraries()
                
                if self.verify_forge_installation():
                    self.progress.emit(100)
                    self.status.emit("Forge успешно установлен!")
                    self.finished.emit(True, "Forge успешно установлен")
                else:
                    # Даже если проверка не удалась, возможно Forge установлен
                    self.status.emit("Forge установлен, но с предупреждениями")
                    self.finished.emit(True, "Forge установлен (проверьте вручную)")
            else:
                self.finished.emit(False, "Ошибка при установке Forge")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"Ошибка установки Forge: {str(e)}")
    
    def check_vanilla_installation(self):
        """Проверяет наличие vanilla Minecraft и устанавливает если нужно"""
        vanilla_dir = self.minecraft_dir / "versions" / self.mc_version
        vanilla_json = vanilla_dir / f"{self.mc_version}.json"
        vanilla_jar = vanilla_dir / f"{self.mc_version}.jar"
        
        if not vanilla_json.exists() or not vanilla_jar.exists():
            self.status.emit(f"Установка Minecraft {self.mc_version}...")
            
            callback = {
                "setStatus": lambda text: self.status.emit(text) if self._is_running else None,
                "setProgress": lambda progress: self.progress.emit(5 + int(progress * 10)) if self._is_running else None,
            }
            
            try:
                import minecraft_launcher_lib
                minecraft_launcher_lib.install.install_minecraft_version(
                    self.mc_version,
                    str(self.minecraft_dir),
                    callback=callback
                )
            except Exception as e:
                self.finished.emit(False, f"Ошибка установки Vanilla: {str(e)}")
                return False
        
        return True
    
    def check_existing_forge(self):
        """Проверяет, установлен ли уже Forge для этой версии Minecraft"""
        versions_dir = self.minecraft_dir / "versions"
        if not versions_dir.exists():
            return False
        
        # Проверяем разные возможные имена версий для нашей Minecraft
        possible_names = [
            self.version_name,
            f"{self.mc_version}-forge-{self.forge_version}",
            f"{self.mc_version}-Forge{self.forge_version}",
            f"{self.mc_version}-Forge{self.forge_version}-{self.mc_version}",
            f"Forge-{self.mc_version}",
            f"forge-{self.mc_version}",
        ]
        
        # Сначала проверяем точные имена
        for name in possible_names:
            version_dir = versions_dir / name
            json_path = version_dir / f"{name}.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Проверяем, что это действительно Forge для нашей версии
                    is_forge = False
                    if "libraries" in data:
                        for lib in data["libraries"]:
                            lib_name = lib.get("name", "")
                            if "forge" in lib_name.lower():
                                is_forge = True
                                break
                    
                    if "inheritsFrom" in data and data["inheritsFrom"] == self.mc_version:
                        is_forge = True
                    
                    if is_forge:
                        print(f"Найден существующий Forge для {self.mc_version}: {name}")
                        self.version_name = name
                        return True
                except:
                    pass
        
        # Если не нашли по точным именам, ищем по содержимому
        for version_dir in versions_dir.iterdir():
            if not version_dir.is_dir():
                continue
            
            name = version_dir.name
            # Проверяем, что версия относится к нашей Minecraft
            if self.mc_version in name and ("forge" in name.lower() or "Forge" in name):
                json_path = version_dir / f"{name}.json"
                if json_path.exists():
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Проверяем наследование
                        if "inheritsFrom" in data and data["inheritsFrom"] == self.mc_version:
                            print(f"Найден существующий Forge для {self.mc_version}: {name}")
                            self.version_name = name
                            return True
                        
                        # Проверяем библиотеки
                        if "libraries" in data:
                            for lib in data["libraries"]:
                                lib_name = lib.get("name", "")
                                if "forge" in lib_name.lower() and self.mc_version in lib_name:
                                    print(f"Найден существующий Forge для {self.mc_version}: {name}")
                                    self.version_name = name
                                    return True
                    except:
                        pass
        
        return False
    
    def download_installer(self):
        """Скачивает установщик Forge"""
        installer_path = self.minecraft_dir / "forge_installer.jar"
        
        try:
            self.status.emit("Скачивание установщика Forge...")
            
            # Список URL для попыток
            urls_to_try = [
                self.installer_url,
                f"https://maven.minecraftforge.net/net/minecraftforge/forge/{self.forge_version_id}/forge-{self.forge_version_id}-installer.jar",
                f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{self.forge_version_id}/forge-{self.forge_version_id}-installer.jar",
                f"https://maven.minecraftforge.net/net/minecraftforge/forge/{self.mc_version}-{self.forge_version}/forge-{self.mc_version}-{self.forge_version}-installer.jar",
            ]
            
            # Для старых версий добавляем специальные URL
            if self.major_version <= 8:
                urls_to_try.append(
                    f"https://maven.minecraftforge.net/net/minecraftforge/forge/{self.forge_version_id}/forge-{self.forge_version_id}-installer.jar"
                )
            
            for url in urls_to_try:
                if not self._is_running:
                    return None
                    
                try:
                    self.status.emit(f"Попытка загрузки...")
                    print(f"Пробуем URL: {url}")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(url, stream=True, timeout=30, headers=headers)
                    
                    if response.status_code == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(installer_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if not self._is_running:
                                    return None
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if total_size > 0:
                                        progress = 15 + int((downloaded / total_size) * 15)
                                        self.progress.emit(progress)
                        
                        if installer_path.stat().st_size > 100000:  # Проверяем, что файл не слишком маленький
                            self.status.emit("Установщик скачан")
                            print(f"Установщик скачан успешно: {installer_path}, размер: {installer_path.stat().st_size}")
                            return installer_path
                        else:
                            print(f"Скачанный файл слишком маленький: {installer_path.stat().st_size}")
                            installer_path.unlink(missing_ok=True)
                            
                except Exception as e:
                    print(f"Ошибка скачивания с {url}: {e}")
                    continue
            
            # Если не удалось скачать, пробуем получить информацию о версии
            self.status.emit("Попытка получить информацию о версии Forge...")
            forge_info = self.get_forge_version_info()
            if forge_info:
                self.forge_version = forge_info
                self.determine_forge_format()
                # Пробуем еще раз с новой версией
                return self.download_installer()
            
            self.finished.emit(False, f"Не удалось скачать установщик Forge для версии {self.mc_version}")
            return None
            
        except Exception as e:
            self.finished.emit(False, f"Ошибка скачивания: {str(e)}")
            return None
    
    def get_forge_version_info(self):
        """Получает информацию о доступных версиях Forge"""
        try:
            api_url = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "promos" in data:
                    # Ищем подходящую версию
                    for key, value in data["promos"].items():
                        if key.startswith(f"{self.mc_version}-"):
                            return value
        except:
            pass
        return None
    
    def install_modern_forge(self, installer_path):
        """Установка Forge для новых версий (1.13+)"""
        try:
            self.status.emit("Запуск установщика Forge...")
            self.progress.emit(40)
            
            # Для 1.17+ нужны дополнительные аргументы JVM
            jvm_args = []
            if self.major_version >= 17:
                jvm_args = [
                    "--add-opens=java.base/java.util.jar=ALL-UNNAMED",
                    "--add-opens=java.base/java.lang=ALL-UNNAMED",
                    "--add-opens=java.base/java.util=ALL-UNNAMED",
                ]
            
            cmd = [self.java_path] + jvm_args + [
                "-jar", str(installer_path),
                "--installClient",
                str(self.minecraft_dir)
            ]
            
            log_file = self.minecraft_dir / "logs" / "forge_install.log"
            log_file.parent.mkdir(exist_ok=True)
            
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            self.status.emit("Установка Forge (это может занять несколько минут)...")
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=creation_flags,
                timeout=300,
                cwd=str(self.minecraft_dir)
            )
            
            # Сохраняем лог
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {' '.join(cmd)}\n\n")
                f.write(f"STDOUT:\n{process.stdout}\n")
                f.write(f"STDERR:\n{process.stderr}\n")
            
            print(f"Forge installer output: {process.stdout}")
            if process.stderr:
                print(f"Forge installer errors: {process.stderr}")
            
            self.progress.emit(70)
            return process.returncode == 0
            
        except subprocess.TimeoutExpired:
            self.status.emit("Установка Forge превысила время ожидания")
            return False
        except Exception as e:
            print(f"Ошибка установки modern Forge: {e}")
            return False
    
    def install_legacy_forge(self, installer_path):
        """Установка Forge для старых версий (1.7.10 - 1.12)"""
        try:
            self.status.emit("Распаковка установщика Forge...")
            self.progress.emit(40)
            
            # Создаем временную папку для распаковки
            extract_dir = self.minecraft_dir / "forge_temp"
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            extract_dir.mkdir(exist_ok=True)
            
            # Распаковываем installer
            try:
                with zipfile.ZipFile(installer_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except zipfile.BadZipFile:
                self.status.emit("Ошибка: файл установщика поврежден")
                return False
            
            self.progress.emit(55)
            
            # Копируем библиотеки
            self.status.emit("Копирование библиотек...")
            
            # Ищем папку maven (может быть в корне или в version)
            maven_dirs = list(extract_dir.glob("**/maven"))
            if maven_dirs:
                libraries_src = maven_dirs[0]
            else:
                libraries_src = extract_dir / "maven"
            
            if libraries_src.exists():
                self.copy_libraries(libraries_src, self.minecraft_dir / "libraries")
            
            self.progress.emit(70)
            
            # Создаем профиль Forge
            self.status.emit("Создание профиля Forge...")
            self.create_legacy_forge_profile(extract_dir)
            
            # Очистка
            shutil.rmtree(extract_dir, ignore_errors=True)
            
            self.progress.emit(80)
            return True
            
        except Exception as e:
            print(f"Ошибка установки legacy Forge: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def copy_libraries(self, src_dir, dest_dir):
        """Копирует библиотеки из installer в папку libraries"""
        try:
            copied_count = 0
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    if file.endswith('.jar'):
                        src_file = Path(root) / file
                        
                        # Получаем относительный путь
                        try:
                            rel_path = src_file.relative_to(src_dir)
                        except ValueError:
                            continue
                        
                        dest_file = dest_dir / rel_path
                        
                        if not dest_file.exists() or dest_file.stat().st_size != src_file.stat().st_size:
                            dest_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_file, dest_file)
                            copied_count += 1
                            print(f"Скопирована библиотека: {rel_path}")
            
            print(f"Скопировано библиотек: {copied_count}")
            
        except Exception as e:
            print(f"Ошибка копирования библиотек: {e}")
    
    def create_legacy_forge_profile(self, extract_dir):
        """Создает JSON профиль для старых версий Forge (только для версий <= 1.12.2)"""
        try:
            version_dir = self.minecraft_dir / "versions" / self.version_name
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Ищем библиотеку forge для нашей версии
            forge_lib = None
            forge_version_found = None
            
            # Поиск в разных местах
            search_paths = [
                extract_dir / "maven" / "net" / "minecraftforge" / "forge",
                extract_dir / "net" / "minecraftforge" / "forge",
                self.minecraft_dir / "libraries" / "net" / "minecraftforge" / "forge",
            ]
            
            for base_path in search_paths:
                if base_path.exists():
                    versions = [d for d in base_path.iterdir() if d.is_dir()]
                    if versions:
                        # Ищем версию, соответствующую нашей Minecraft
                        for version_dir_candidate in versions:
                            version_name_candidate = version_dir_candidate.name
                            if self.mc_version in version_name_candidate or self.forge_version in version_name_candidate:
                                # Проверяем разные возможные имена JAR файлов
                                jar_names = [
                                    f"forge-{version_name_candidate}.jar",
                                    f"forge-{version_name_candidate}-universal.jar",
                                    f"forge-{version_name_candidate}-client.jar",
                                    f"forge-{self.mc_version}-{self.forge_version}.jar",
                                    f"forge-{self.forge_version}.jar",
                                ]
                                
                                for jar_name in jar_names:
                                    forge_jar = version_dir_candidate / jar_name
                                    if forge_jar.exists():
                                        forge_lib = f"net.minecraftforge:forge:{version_name_candidate}"
                                        forge_version_found = version_name_candidate
                                        print(f"Найдена библиотека Forge: {forge_lib}")
                                        break
                                
                                if forge_lib:
                                    break
            
            # Создаем JSON профиль
            profile_data = {
                "id": self.version_name,
                "inheritsFrom": self.mc_version,
                "releaseTime": "2024-01-01T00:00:00+00:00",
                "time": "2024-01-01T00:00:00+00:00",
                "type": "release",
                "mainClass": self.main_class,
                "libraries": []
            }
            
            # Добавляем аргументы для разных версий
            if self.major_version < 13:
                if self.mc_version == "1.7.10":
                    profile_data["minecraftArguments"] = "--tweakClass cpw.mods.fml.common.launcher.FMLTweaker"
                else:
                    profile_data["minecraftArguments"] = "--tweakClass cpw.mods.fml.common.launcher.FMLTweaker"
            
            # Добавляем библиотеку forge если нашли
            if forge_lib:
                profile_data["libraries"].append({
                    "name": forge_lib
                })
            
            # Добавляем необходимые библиотеки для старых версий
            if self.major_version < 13:
                # Добавляем launchwrapper - это критически важно для 1.7.10
                profile_data["libraries"].extend([
                    {
                        "name": "net.minecraft:launchwrapper:1.12"
                    },
                    {
                        "name": "org.ow2.asm:asm-all:5.2"
                    }
                ])
                
                # Добавляем библиотеки FML для 1.7.10
                if self.mc_version == "1.7.10":
                    profile_data["libraries"].append({
                        "name": f"cpw.mods:fml:1.7.10-{self.forge_version}"
                    })
            
            # Добавляем аргументы JVM для старых версий
            profile_data["arguments"] = {
                "jvm": [
                    "-Dforge.forceNoIndev=true",
                    "-Dfml.ignoreInvalidMinecraftCertificates=true",
                    "-Dfml.ignorePatchDiscrepancies=true",
                    "-Dlog4j2.formatMsgNoLookups=true"
                ]
            }
            
            # Сохраняем JSON
            json_path = version_dir / f"{self.version_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
            
            print(f"Создан профиль Forge для старой версии: {json_path}")
            
            # Сразу скачиваем необходимые библиотеки
            self.download_required_libraries()
            
            # Если не нашли библиотеку forge, но есть версия, пробуем скачать
            if not forge_lib and forge_version_found:
                self.download_forge_library(forge_version_found)
            
        except Exception as e:
            print(f"Ошибка создания legacy Forge профиля: {e}")
            import traceback
            traceback.print_exc()
    
    def download_required_libraries(self):
        """Скачивает необходимые библиотеки для Forge"""
        try:
            # Список необходимых библиотек
            required_libs = [
                {
                    "name": "net.minecraft:launchwrapper:1.12",
                    "url": "https://libraries.minecraft.net/net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar",
                    "path": "net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar"
                },
                {
                    "name": "org.ow2.asm:asm-all:5.2",
                    "url": "https://libraries.minecraft.net/org/ow2/asm/asm-all/5.2/asm-all-5.2.jar",
                    "path": "org/ow2/asm/asm-all/5.2/asm-all-5.2.jar"
                }
            ]
            
            # Добавляем специфичные для 1.7.10
            if self.mc_version == "1.7.10":
                required_libs.append({
                    "name": f"cpw.mods:fml:1.7.10-{self.forge_version}",
                    "url": f"https://maven.minecraftforge.net/cpw/mods/fml/1.7.10-{self.forge_version}/fml-1.7.10-{self.forge_version}.jar",
                    "path": f"cpw/mods/fml/1.7.10-{self.forge_version}/fml-1.7.10-{self.forge_version}.jar"
                })
            
            for lib in required_libs:
                dest_path = self.minecraft_dir / "libraries" / lib["path"]
                
                if not dest_path.exists():
                    self.status.emit(f"Скачивание {lib['name']}...")
                    
                    try:
                        response = requests.get(lib["url"], timeout=30)
                        if response.status_code == 200:
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(dest_path, 'wb') as f:
                                f.write(response.content)
                            print(f"Скачана библиотека: {lib['name']}")
                        else:
                            print(f"Не удалось скачать {lib['name']}: {response.status_code}")
                    except Exception as e:
                        print(f"Ошибка скачивания {lib['name']}: {e}")
                        
        except Exception as e:
            print(f"Ошибка при скачивании библиотек: {e}")
    
    def ensure_launchwrapper(self):
        """Проверяет наличие launchwrapper и скачивает если нужно"""
        try:
            # Путь к launchwrapper
            launchwrapper_path = self.minecraft_dir / "libraries" / "net" / "minecraft" / "launchwrapper" / "1.12" / "launchwrapper-1.12.jar"
            
            if not launchwrapper_path.exists():
                self.status.emit("Скачивание launchwrapper...")
                launchwrapper_url = "https://libraries.minecraft.net/net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar"
                
                response = requests.get(launchwrapper_url, timeout=30)
                if response.status_code == 200:
                    launchwrapper_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(launchwrapper_path, 'wb') as f:
                        f.write(response.content)
                    print("Launchwrapper скачан успешно")
                else:
                    print(f"Не удалось скачать launchwrapper: {response.status_code}")
        except Exception as e:
            print(f"Ошибка при скачивании launchwrapper: {e}")
    
    def download_forge_library(self, forge_version):
        """Скачивает библиотеку Forge отдельно"""
        try:
            # Пробуем разные варианты имени файла
            jar_names = [
                f"forge-{forge_version}.jar",
                f"forge-{forge_version}-universal.jar",
                f"forge-{forge_version}-client.jar",
                f"forge-{self.mc_version}-{self.forge_version}.jar",
            ]
            
            for jar_name in jar_names:
                lib_path = f"net/minecraftforge/forge/{forge_version}/{jar_name}"
                lib_url = f"https://maven.minecraftforge.net/{lib_path}"
                dest_path = self.minecraft_dir / "libraries" / lib_path
                
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                response = requests.get(lib_url, timeout=30)
                if response.status_code == 200:
                    with open(dest_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Скачана библиотека Forge: {lib_url}")
                    return True
        except Exception as e:
            print(f"Ошибка скачивания библиотеки Forge: {e}")
        return False
    
    def fix_forge_profile(self):
        """Исправляет JSON профиль Forge после установки (только для версий <= 1.12.2)"""
        try:
            versions_dir = self.minecraft_dir / "versions"
            
            # Ищем все папки, которые могут быть Forge для нашей версии
            for vdir in versions_dir.iterdir():
                if not vdir.is_dir():
                    continue
                
                name = vdir.name
                # Проверяем, что версия относится к нашей Minecraft
                if self.mc_version in name and ("forge" in name.lower() or "Forge" in name):
                    json_path = vdir / f"{name}.json"
                    if json_path.exists():
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            modified = False
                            
                            # Для современных версий (1.13+) НЕ исправляем JSON вручную
                            if self.is_modern_forge:
                                print(f"Современный Forge ({self.mc_version}): пропускаем исправление JSON")
                                return
                            
                            # Исправляем mainClass если нужно (только для старых версий)
                            if "mainClass" in data:
                                if self.major_version < 13:
                                    if self.mc_version == "1.7.10":
                                        if data["mainClass"] != "cpw.mods.fml.common.launcher.FMLTweaker":
                                            data["mainClass"] = "cpw.mods.fml.common.launcher.FMLTweaker"
                                            modified = True
                                    else:
                                        if data["mainClass"] != "net.minecraft.launchwrapper.Launch":
                                            data["mainClass"] = "net.minecraft.launchwrapper.Launch"
                                            modified = True
                            
                            # Добавляем аргументы если нужно (только для старых версий)
                            if self.major_version < 13:
                                if "arguments" not in data:
                                    data["arguments"] = {"jvm": [], "game": []}
                                    modified = True
                                
                                if "-Dforge.forceNoIndev=true" not in data["arguments"].get("jvm", []):
                                    data["arguments"].setdefault("jvm", []).append("-Dforge.forceNoIndev=true")
                                    modified = True
                                if "-Dfml.ignoreInvalidMinecraftCertificates=true" not in data["arguments"].get("jvm", []):
                                    data["arguments"].setdefault("jvm", []).append("-Dfml.ignoreInvalidMinecraftCertificates=true")
                                    modified = True
                            
                            # Проверяем наличие launchwrapper в библиотеках для 1.7.10
                            if self.mc_version == "1.7.10" and "libraries" in data:
                                has_launchwrapper = False
                                for lib in data["libraries"]:
                                    if "launchwrapper" in lib.get("name", "").lower():
                                        has_launchwrapper = True
                                        break
                                
                                if not has_launchwrapper:
                                    data["libraries"].append({
                                        "name": "net.minecraft:launchwrapper:1.12"
                                    })
                                    modified = True
                            
                            # Проверяем наследование
                            if "inheritsFrom" not in data:
                                data["inheritsFrom"] = self.mc_version
                                modified = True
                            elif data["inheritsFrom"] != self.mc_version:
                                data["inheritsFrom"] = self.mc_version
                                modified = True
                            
                            if modified:
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, indent=2)
                                print(f"Исправлен профиль Forge для старой версии: {json_path}")
                                
                        except Exception as e:
                            print(f"Ошибка исправления профиля {json_path}: {e}")
                    
        except Exception as e:
            print(f"Ошибка в fix_forge_profile: {e}")
    
    def verify_forge_installation(self):
        """Проверяет успешность установки Forge для нашей версии"""
        try:
            versions_dir = self.minecraft_dir / "versions"
            
            # Ищем установленную версию Forge, соответствующую нашей версии Minecraft
            forge_version_found = None
            
            for vdir in versions_dir.iterdir():
                if vdir.is_dir():
                    name = vdir.name
                    # Проверяем, что версия относится к нашей Minecraft
                    if self.mc_version in name and ("forge" in name.lower() or "Forge" in name):
                        json_path = vdir / f"{name}.json"
                        
                        if json_path.exists():
                            try:
                                with open(json_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                
                                # Проверяем наличие Forge в библиотеках
                                if "libraries" in data:
                                    for lib in data["libraries"]:
                                        lib_name = lib.get("name", "")
                                        if "forge" in lib_name.lower():
                                            # Проверяем, что версия соответствует
                                            if self.mc_version in lib_name or self.forge_version in lib_name:
                                                forge_version_found = name
                                                print(f"Найден Forge для {self.mc_version}: {name} с библиотекой {lib_name}")
                                                break
                                
                                # Также проверяем наследование
                                if "inheritsFrom" in data and data["inheritsFrom"] == self.mc_version:
                                    if not forge_version_found:
                                        forge_version_found = name
                                
                            except Exception as e:
                                print(f"Ошибка чтения {json_path}: {e}")
                                
                            if forge_version_found:
                                break
            
            if forge_version_found:
                # Обновляем имя версии
                self.version_name = forge_version_found
                
                # Для 1.7.10 проверяем наличие launchwrapper
                if self.mc_version == "1.7.10":
                    self.ensure_launchwrapper()
                    self.download_required_libraries()
                
                return True
            
            # Если не нашли, проверяем наличие библиотек Forge (только для старых версий)
            if not self.is_modern_forge:
                libraries_dir = self.minecraft_dir / "libraries" / "net" / "minecraftforge" / "forge"
                if libraries_dir.exists():
                    forge_versions = [d for d in libraries_dir.iterdir() if d.is_dir()]
                    for version_dir_candidate in forge_versions:
                        if self.mc_version in version_dir_candidate.name or self.forge_version in version_dir_candidate.name:
                            print(f"Найдены библиотеки Forge: {version_dir_candidate.name}")
                            # Пробуем создать профиль
                            self.create_missing_forge_profile(version_dir_candidate.name)
                            return True
            
            return False
            
        except Exception as e:
            print(f"Ошибка проверки Forge: {e}")
            return False
    
    def create_missing_forge_profile(self, forge_version):
        """Создает профиль Forge если он отсутствует (только для версий <= 1.12.2)"""
        # Для современных версий (1.13+) НЕ создаем профиль вручную
        if self.is_modern_forge:
            print(f"Современный Forge ({self.mc_version}): пропускаем ручное создание профиля")
            return False
            
        try:
            version_name = f"{self.mc_version}-forge-{forge_version}"
            version_dir = self.minecraft_dir / "versions" / version_name
            version_dir.mkdir(parents=True, exist_ok=True)
            
            profile_data = {
                "id": version_name,
                "inheritsFrom": self.mc_version,
                "releaseTime": "2024-01-01T00:00:00+00:00",
                "time": "2024-01-01T00:00:00+00:00",
                "type": "release",
                "mainClass": self.main_class,
                "libraries": [
                    {
                        "name": f"net.minecraftforge:forge:{forge_version}"
                    }
                ]
            }
            
            # Добавляем аргументы для старых версий
            if self.major_version < 13:
                if self.mc_version == "1.7.10":
                    profile_data["mainClass"] = "cpw.mods.fml.common.launcher.FMLTweaker"
                    profile_data["minecraftArguments"] = "--tweakClass cpw.mods.fml.common.launcher.FMLTweaker"
                else:
                    profile_data["mainClass"] = "net.minecraft.launchwrapper.Launch"
                    profile_data["minecraftArguments"] = "--tweakClass cpw.mods.fml.common.launcher.FMLTweaker"
                
                # Добавляем launchwrapper для 1.7.10
                if self.mc_version == "1.7.10":
                    profile_data["libraries"].append({
                        "name": "net.minecraft:launchwrapper:1.12"
                    })
                
                profile_data["arguments"] = {
                    "jvm": [
                        "-Dforge.forceNoIndev=true",
                        "-Dfml.ignoreInvalidMinecraftCertificates=true",
                        "-Dfml.ignorePatchDiscrepancies=true",
                    ]
                }
            
            json_path = version_dir / f"{version_name}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
            
            self.version_name = version_name
            print(f"Создан отсутствующий профиль Forge для старой версии: {json_path}")
            
            # Для 1.7.10 скачиваем launchwrapper
            if self.mc_version == "1.7.10":
                self.ensure_launchwrapper()
                self.download_required_libraries()
            
            return True
            
        except Exception as e:
            print(f"Ошибка создания отсутствующего профиля: {e}")
            return False
    
    def cleanup_temp_files(self, installer_path):
        """Удаляет временные файлы"""
        try:
            if installer_path and installer_path.exists():
                installer_path.unlink()
        except:
            pass
    
    def stop(self):
        self._is_running = False