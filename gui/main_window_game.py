from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import threading
import time
import subprocess
import os
import uuid
import json
import minecraft_launcher_lib
from core.config import DEFAULT_MC_VERSION, REQUIRED_JAVA_VERSION, get_asset_path, get_recommended_java_version, get_recommended_forge_version, get_recommended_fabric_version
from core.utils import generate_offline_uuid, check_java_version, create_launcher_profiles, get_java_major_version
from threads.download_thread import DownloadProgressThread
from threads.forge_thread import ForgeInstallThread
from threads.fabric_thread import FabricInstallThread
from dialogs.java_dialog import JavaDownloadDialog

class MainWindowGame:
    """Класс для игровых функций главного окна"""
    
    def launch_game(self):
        """Запуск игры"""
        username = self.name_edit.text().strip()
        if not username:
            QMessageBox.critical(self, "Ошибка", "Введите имя игрока")
            return
        
        if not self.java_path:
            QMessageBox.critical(self, "Ошибка", "Java не найдена! Укажите путь к Java.")
            return
        
        # Проверяем совместимость Java с выбранной версией Minecraft
        if not self.check_java_compatibility():
            return
        
        # Создаем launcher_profiles.json если его нет
        create_launcher_profiles(self.minecraft_dir)
        
        # Блокируем кнопку запуска
        self.play_button.setEnabled(False)
        
        # Вызываем событие плагинов
        if self.beta_enabled:
            self.plugin_manager.on_game_start()
        
        # Обновляем UI кнопки
        if not hasattr(self.play_button, 'icon') or self.play_button.icon().isNull():
            self.play_button.setText("ЗАГРУЗКА...")
        else:
            self.play_button.setIcon(QIcon())
            self.play_button.setText("ЗАГРУЗКА...")
        
        # Показываем прогресс бар
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # Получаем параметры запуска
        loader = self.loader_combo.currentText()
        mc_version = self.current_mc_version
        memory = self.memory_slider.value() if hasattr(self, 'memory_slider') else 4096
        
        # Запускаем поток установки и запуска
        thread = threading.Thread(
            target=self.launch_thread,
            args=(username, memory, loader, mc_version),
            daemon=True
        )
        thread.start()
    
    def check_java_compatibility(self):
        """Проверяет совместимость текущей Java с выбранной версией Minecraft"""
        recommended_java = get_recommended_java_version(self.current_mc_version)
        current_java = get_java_major_version(self.java_path)
        
        if current_java == 0:
            QMessageBox.critical(self, "Ошибка", "Не удалось определить версию Java")
            return False
        
        print(f"Проверка Java: требуется {recommended_java}, установлена {current_java}")
        
        # Если версия Java подходит, просто продолжаем
        if current_java >= recommended_java:
            return True
        
        # Если версия не подходит, спрашиваем пользователя
        reply = QMessageBox.question(
            self,
            "Версия Java",
            f"Minecraft {self.current_mc_version} рекомендуется Java {recommended_java}.\n"
            f"У вас Java {current_java}.\n\n"
            "Хотите скачать и установить подходящую версию Java?\n"
            "Если нет, запуск будет продолжен с текущей Java (может не работать).",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Yes:
            dialog = JavaDownloadDialog(self, self.current_mc_version)
            if dialog.exec_() == QDialog.Accepted:
                return True
            return False
        elif reply == QMessageBox.No:
            # Продолжаем с текущей Java
            QMessageBox.warning(self, "Предупреждение", 
                               f"Запуск с Java {current_java} может не работать. Рекомендуется Java {recommended_java}.")
            return True
        else:
            return False
    
    def launch_thread(self, username, memory_mb, loader, mc_version):
        """Поток установки и запуска игры"""
        try:
            version_name = mc_version
            
            # Установка Forge если выбран
            if loader == "Forge":
                self.update_status("Установка Forge...")
                
                self.forge_install_success = False
                
                # Создаем поток установки Forge
                self.forge_thread = ForgeInstallThread(
                    self.minecraft_dir,
                    mc_version,
                    self.java_path
                )
                self.forge_thread.progress.connect(self.update_progress)
                self.forge_thread.status.connect(self.update_status)
                self.forge_thread.finished.connect(self.on_forge_install_finished)
                
                self.forge_thread.start()
                
                # Ждем завершения установки
                while self.forge_thread.isRunning():
                    QApplication.processEvents()
                    time.sleep(0.1)
                
                if not self.forge_install_success:
                    self.show_error("Не удалось установить Forge")
                    return
                
                # Получаем имя установленной версии
                version_name = self.forge_thread.version_name
                print(f"Forge установлен, версия для запуска: {version_name}")
                
            # Установка Fabric если выбран
            elif loader == "Fabric":
                self.update_status("Установка Fabric...")
                
                self.fabric_install_success = False
                
                # Создаем поток установки Fabric
                self.fabric_thread = FabricInstallThread(
                    self.minecraft_dir,
                    mc_version,
                    self.java_path
                )
                self.fabric_thread.progress.connect(self.update_progress)
                self.fabric_thread.status.connect(self.update_status)
                self.fabric_thread.finished.connect(self.on_fabric_install_finished)
                
                self.fabric_thread.start()
                
                # Ждем завершения установки
                while self.fabric_thread.isRunning():
                    QApplication.processEvents()
                    time.sleep(0.1)
                
                if not self.fabric_install_success:
                    self.show_error("Не удалось установить Fabric")
                    return
                
                # Получаем имя установленной версии
                version_name = self.fabric_thread.version_name
                print(f"Fabric установлен, версия для запуска: {version_name}")
            
            # Установка Vanilla
            else:
                self.update_status(f"Проверка Minecraft {version_name}...")
                
                # Проверяем установку Vanilla
                version_dir = self.minecraft_dir / "versions" / version_name
                version_json = version_dir / f"{version_name}.json"
                version_jar = version_dir / f"{version_name}.jar"
                
                # Получаем список установленных версий
                installed_versions = minecraft_launcher_lib.utils.get_installed_versions(str(self.minecraft_dir))
                version_installed = any(ver["id"] == version_name for ver in installed_versions)
                
                # Если версия не установлена или повреждена
                if not version_installed or not version_json.exists() or not version_jar.exists():
                    self.update_status(f"Установка {version_name}...")
                    
                    # Удаляем поврежденную установку если есть
                    if version_dir.exists():
                        import shutil
                        try:
                            shutil.rmtree(version_dir)
                            self.update_status("Удалена поврежденная установка...")
                        except:
                            pass
                    
                    self.install_success = False
                    
                    # Запускаем установку
                    self.install_thread = DownloadProgressThread(self.minecraft_dir, version_name)
                    self.install_thread.progress.connect(self.update_progress)
                    self.install_thread.status.connect(self.update_status)
                    self.install_thread.finished.connect(self.on_install_finished)
                    
                    self.install_thread.start()
                    
                    # Ждем завершения установки
                    while self.install_thread.isRunning():
                        QApplication.processEvents()
                        time.sleep(0.1)
                    
                    if not self.install_success:
                        self.show_error(f"Не удалось установить {version_name}")
                        return
                    
                    # Проверяем еще раз после установки
                    if not version_json.exists() or not version_jar.exists():
                        self.show_error(f"Установка завершена, но файлы не найдены")
                        return
                else:
                    self.update_status(f"Версия {version_name} уже установлена")
            
            # Запускаем игру
            self.update_status("Запуск игры...")
            success = self.run_game(username, memory_mb, version_name, mc_version)
            
            if not success:
                self.show_error("Не удалось запустить игру")
            else:
                self.update_status("Игра запущена!")
                QMetaObject.invokeMethod(self, "delayed_close")
                
        except Exception as e:
            self.show_error(f"Исключение: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.restore_ui()
    
    def get_forge_version_name(self, mc_version):
        """Возвращает правильное имя версии Forge для разных версий Minecraft"""
        forge_ver = get_recommended_forge_version(mc_version)
        version_parts = mc_version.split('.')
        major_version = int(version_parts[1]) if len(version_parts) > 1 else 0
        
        if major_version >= 17:  # 1.17+
            return f"{mc_version}-forge-{forge_ver}"
        elif major_version >= 13:  # 1.13 - 1.16
            return f"{mc_version}-forge-{forge_ver}"
        elif mc_version == "1.7.10":  # 1.7.10 специальный случай
            return f"{mc_version}-Forge{forge_ver}-{mc_version}"
        else:  # 1.8 - 1.12
            if "-" in forge_ver:
                return f"{mc_version}-Forge{forge_ver}"
            else:
                return f"{mc_version}-Forge{forge_ver}-{mc_version}"
    
    def get_fabric_version_name(self, mc_version):
        """Возвращает правильное имя версии Fabric"""
        fabric_ver = get_recommended_fabric_version(mc_version)
        return f"fabric-loader-{fabric_ver}-{mc_version}"
    
    def find_correct_version(self, base_version, loader_type):
        """Находит правильную установленную версию для указанного базового Minecraft"""
        versions_dir = self.minecraft_dir / "versions"
        if not versions_dir.exists():
            return None
        
        # Приводим к нижнему регистру для поиска
        base_lower = base_version.lower()
        loader_lower = loader_type.lower()
        
        candidates = []
        
        for vdir in versions_dir.iterdir():
            if not vdir.is_dir():
                continue
            
            name = vdir.name
            name_lower = name.lower()
            
            # Проверяем, что версия относится к нашему базовому Minecraft
            if base_lower in name_lower:
                # Проверяем тип загрузчика
                if loader_lower == "forge":
                    if "forge" in name_lower:
                        candidates.append(name)
                elif loader_lower == "fabric":
                    if "fabric" in name_lower:
                        candidates.append(name)
                else:  # vanilla
                    if "forge" not in name_lower and "fabric" not in name_lower:
                        candidates.append(name)
        
        # Сортируем кандидатов (более длинные имена обычно более специфичные)
        candidates.sort(key=len, reverse=True)
        
        if candidates:
            print(f"Найдены кандидаты для {base_version} ({loader_type}): {candidates}")
            return candidates[0]
        
        return None
    
    def run_game(self, username, memory_mb, version_name, original_version=None):
        """Запускает игру с указанными параметрами"""
        try:
            actual_version_name = version_name
            loader_type = "vanilla"
            
            # Определяем тип загрузчика по имени версии
            if "forge" in version_name.lower():
                loader_type = "forge"
            elif "fabric" in version_name.lower():
                loader_type = "fabric"
            
            # Если версия не найдена, пробуем найти подходящую
            version_json = self.minecraft_dir / "versions" / actual_version_name / f"{actual_version_name}.json"
            if not version_json.exists() and original_version:
                # Пробуем найти правильную версию
                found = self.find_correct_version(original_version, loader_type)
                if found:
                    actual_version_name = found
                    version_json = self.minecraft_dir / "versions" / actual_version_name / f"{actual_version_name}.json"
                    print(f"Используем найденную версию: {actual_version_name}")
            
            if not version_json.exists():
                self.show_error(f"Версия {actual_version_name} не найдена")
                return False
            
            # Определяем версию Minecraft из имени
            mc_version = original_version if original_version else actual_version_name
            # Извлекаем основную версию (например, из "1.7.10-Forge10.13.4.1614-1.7.10" получаем "1.7.10")
            if "-" in actual_version_name:
                parts = actual_version_name.split('-')
                for part in parts:
                    if part.count('.') >= 2 and part[0].isdigit():
                        mc_version = part
                        break
            
            version_parts = mc_version.split('.')
            major_version = int(version_parts[1]) if len(version_parts) > 1 else 0
            
            print(f"Запуск: {actual_version_name}, Minecraft {mc_version} (major {major_version}), Тип: {loader_type}")
            
            # Загружаем JSON версии для анализа
            try:
                with open(version_json, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
            except Exception as e:
                print(f"Ошибка чтения JSON версии: {e}")
                version_data = {}
            
            # Определяем, является ли это современным Forge (1.13+)
            is_modern_forge = False
            if loader_type == "forge" and major_version >= 13:
                is_modern_forge = True
                print(f"Обнаружен современный Forge ({mc_version})")
            
            # Базовая конфигурация
            options = {
                "username": username,
                "uuid": generate_offline_uuid(username),
                "token": "0",
                "launcherName": "WONDERFULAND",
                "launcherVersion": "1.0",
                "gameDirectory": str(self.minecraft_dir),
            }
            
            # Базовые JVM аргументы
            jvm_args = [f"-Xmx{memory_mb}M", f"-Xms{max(512, memory_mb // 2)}M"]
            
            # Добавляем общие JVM аргументы
            jvm_args.extend([
                "-Djava.awt.headless=false",
                f"-Dminecraft.launcher.brand=WONDERFULAND",
                f"-Dminecraft.launcher.version=1.0",
            ])
            
            # Добавляем аргументы для старых версий Java
            java_version = get_java_major_version(self.java_path)
            if java_version >= 9:
                jvm_args.extend([
                    "--add-opens=java.base/java.util.jar=ALL-UNNAMED",
                    "--add-opens=java.base/java.lang=ALL-UNNAMED",
                ])
            
            # ===== ОБРАБОТКА ДЛЯ РАЗНЫХ ВЕРСИЙ FORGE =====
            if loader_type == "forge":
                # Для современных Forge (1.13+) НЕ переопределяем mainClass и аргументы
                if is_modern_forge:
                    print(f"Современный Forge ({mc_version}): используем настройки из JSON")
                    # Берем mainClass из JSON если он там есть
                    if "mainClass" in version_data:
                        options["mainClass"] = version_data["mainClass"]
                        print(f"mainClass из JSON: {options['mainClass']}")
                    
                    # Добавляем аргументы JVM из JSON если они есть
                    if "arguments" in version_data and "jvm" in version_data["arguments"]:
                        for arg in version_data["arguments"]["jvm"]:
                            if isinstance(arg, str) and arg not in jvm_args:
                                jvm_args.append(arg)
                    
                    # Добавляем специфичные для версии аргументы
                    if major_version >= 17:  # 1.17+
                        jvm_args.extend([
                            "--add-opens=java.base/java.security=ALL-UNNAMED",
                            "--add-opens=java.base/java.io=ALL-UNNAMED",
                            "--add-opens=java.base/jdk.internal.loader=ALL-UNNAMED",
                            "--add-opens=java.base/java.net=ALL-UNNAMED",
                            "--add-opens=java.base/java.nio=ALL-UNNAMED",
                        ])
                    
                else:  # Старые Forge (<=1.12.2)
                    # Определяем main class в зависимости от версии
                    if major_version >= 8:  # 1.8 - 1.12
                        options["mainClass"] = "net.minecraft.launchwrapper.Launch"
                        options["gameArguments"] = ["--tweakclass", "cpw.mods.fml.common.launcher.FMLTweaker"]
                        jvm_args.extend([
                            "-Dforge.forceNoIndev=true",
                            "-Dfml.ignoreInvalidMinecraftCertificates=true",
                            "-Dfml.ignorePatchDiscrepancies=true",
                        ])
                        
                    else:  # 1.7.10 и старее
                        options["mainClass"] = "cpw.mods.fml.common.launcher.FMLTweaker"
                        options["gameArguments"] = []
                        
                        jvm_args.extend([
                            "-Dforge.forceNoIndev=true",
                            "-Dfml.ignoreInvalidMinecraftCertificates=true",
                            "-Dfml.ignorePatchDiscrepancies=true",
                            "-Dfml.log.level=INFO",
                        ])
                        
                        # Для 1.7.10 проверяем наличие launchwrapper
                        if mc_version == "1.7.10":
                            self.download_launchwrapper_if_needed()
            
            # ===== ОБРАБОТКА ДЛЯ ВСЕХ ВЕРСИЙ FABRIC =====
            elif loader_type == "fabric":
                options["mainClass"] = "net.fabricmc.loader.impl.launch.knot.KnotClient"
                jvm_args.append("-Dfabric.skipMcProvider=true")
            
            options["jvmArguments"] = jvm_args
            
            # Путь к Java
            if self.java_path:
                options["executablePath"] = self.java_path
            
            # Добавляем аргументы из JSON если они есть и не были добавлены ранее
            if "arguments" in version_data:
                if "jvm" in version_data["arguments"] and not is_modern_forge:
                    for arg in version_data["arguments"]["jvm"]:
                        if isinstance(arg, str) and arg not in jvm_args:
                            jvm_args.append(arg)
                
                # Добавляем game аргументы
                if "game" in version_data["arguments"]:
                    options["gameArguments"] = version_data["arguments"]["game"]
            
            # Получаем команду запуска
            try:
                command = minecraft_launcher_lib.command.get_minecraft_command(
                    actual_version_name,
                    str(self.minecraft_dir),
                    options
                )
            except Exception as e:
                self.show_error(f"Ошибка получения команды запуска: {str(e)}\n\nПроверьте установку Minecraft и попробуйте переустановить версию.")
                return False
            
            print(f"Запуск Minecraft {actual_version_name}")
            print(f"Команда: {' '.join(command)}")
            print(f"MainClass: {options.get('mainClass', 'не указан')}")
            print(f"Тип Forge: {'современный (1.13+)' if is_modern_forge else 'старый (<=1.12.2)' if loader_type == 'forge' else 'не Forge'}")
            
            # Сохраняем команду для отладки
            debug_file = self.minecraft_dir / "last_launch_command.txt"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(' '.join(command))
            except:
                pass
            
            # Запускаем процесс
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(self.minecraft_dir),
                    creationflags=creation_flags,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    bufsize=1
                )
            except Exception as e:
                self.show_error(f"Ошибка запуска процесса: {str(e)}")
                return False
            
            # Сохраняем вывод игры в лог
            log_file = self.minecraft_dir / "logs" / "game_output.log"
            try:
                log_file.parent.mkdir(exist_ok=True, parents=True)
            except:
                pass
            
            def save_output():
                """Сохраняет вывод игры в лог-файл"""
                try:
                    with open(log_file, 'w', encoding='utf-8', buffering=1) as f:
                        while True:
                            if process.poll() is not None:
                                try:
                                    out, err = process.communicate(timeout=1)
                                    if out:
                                        f.write(out)
                                        print(f"MC: {out.strip()}")
                                    if err:
                                        f.write(f"ERROR: {err}")
                                        print(f"MC Error: {err.strip()}")
                                except:
                                    pass
                                break
                            
                            try:
                                line = process.stdout.readline()
                                if line:
                                    f.write(line)
                                    print(f"MC: {line.strip()}")
                                else:
                                    time.sleep(0.1)
                            except:
                                time.sleep(0.1)
                except Exception as e:
                    print(f"Ошибка сохранения лога: {e}")
            
            output_thread = threading.Thread(target=save_output, daemon=True)
            output_thread.start()
            
            # Даем время на запуск
            time.sleep(5)
            
            # Проверяем не завершился ли процесс сразу
            if process.poll() is not None:
                try:
                    stderr_output = process.stderr.read() if process.stderr else ""
                except:
                    stderr_output = "Не удалось прочитать ошибку"
                
                error_msg = f"Игра завершилась сразу после запуска.\n\n"
                
                # Анализируем ошибку
                if "ClassNotFoundException" in stderr_output:
                    if "net.minecraft.launchwrapper.Launch" in stderr_output:
                        error_msg += "Ошибка: Используется неправильный main class для этой версии Forge.\n"
                        error_msg += f"Текущая версия: {actual_version_name}\n"
                        error_msg += f"Minecraft {mc_version} (major {major_version})\n\n"
                        
                        if major_version >= 13:
                            error_msg += "Для Forge 1.13+ правильный main class: cpw.mods.modlauncher.Launcher\n"
                            error_msg += "Установщик Forge должен был создать правильный JSON. Попробуйте переустановить Forge."
                        else:
                            error_msg += "Для старых версий Forge (<=1.12.2) правильный main class: net.minecraft.launchwrapper.Launch\n"
                    else:
                        error_msg += "Ошибка: Неправильная установка Minecraft или Forge.\n"
                        error_msg += f"Попробуйте удалить папку versions/{actual_version_name} и установить заново."
                elif "java.lang.NoClassDefFoundError" in stderr_output:
                    error_msg += "Ошибка: Отсутствуют необходимые библиотеки.\n"
                    error_msg += "Попробуйте переустановить версию."
                elif "UnsupportedClassVersionError" in stderr_output:
                    error_msg += "Ошибка: Неподходящая версия Java.\n"
                    recommended = get_recommended_java_version(mc_version)
                    error_msg += f"Для Minecraft {mc_version} требуется Java {recommended}.\n"
                    error_msg += f"Скачайте Java {recommended} и укажите путь к ней в настройках."
                elif "java.lang.reflect.InaccessibleObjectException" in stderr_output:
                    error_msg += "Ошибка: Проблема с доступом к модулям Java.\n"
                    error_msg += "Для версий 1.17+ требуется Java 17+ с дополнительными аргументами."
                elif "Could not find or load main class" in stderr_output:
                    error_msg += "Ошибка: Не найден главный класс игры.\n"
                    error_msg += "Проверьте установку Minecraft."
                else:
                    error_msg += f"Ошибка:\n{stderr_output[:500]}"
                
                # Добавляем информацию о Java версии
                java_ver = get_java_major_version(self.java_path)
                error_msg += f"\n\nJava версия: {java_ver}"
                
                # Добавляем информацию о версии
                error_msg += f"\nВерсия Minecraft: {actual_version_name}"
                if loader_type == "forge":
                    error_msg += f" (Forge)"
                    error_msg += f"\nТип Forge: {'современный (1.13+)' if major_version >= 13 else 'старый (<=1.12.2)'}"
                elif loader_type == "fabric":
                    error_msg += f" (Fabric)"
                
                # Добавляем main class
                error_msg += f"\nMain class: {options.get('mainClass', 'не указан')}"
                
                # Добавляем путь к лог-файлу
                error_msg += f"\n\nПодробности в файле: {log_file}"
                
                self.show_error(error_msg)
                return False
            
            return True
            
        except Exception as e:
            print(f"Error running game: {e}")
            import traceback
            traceback.print_exc()
            self.show_error(f"Ошибка запуска: {str(e)}")
            return False
    
    def download_launchwrapper_if_needed(self):
        """Скачивает библиотеку launchwrapper для 1.7.10 если её нет"""
        try:
            launchwrapper_path = self.minecraft_dir / "libraries" / "net" / "minecraft" / "launchwrapper" / "1.12" / "launchwrapper-1.12.jar"
            
            if not launchwrapper_path.exists():
                print("Launchwrapper не найден, пытаемся скачать...")
                launchwrapper_url = "https://libraries.minecraft.net/net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar"
                
                import requests
                response = requests.get(launchwrapper_url, timeout=30)
                if response.status_code == 200:
                    launchwrapper_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(launchwrapper_path, 'wb') as f:
                        f.write(response.content)
                    print("Launchwrapper скачан успешно")
                    return str(launchwrapper_path)
                else:
                    print(f"Не удалось скачать launchwrapper: {response.status_code}")
                    return None
            else:
                print(f"Launchwrapper уже существует: {launchwrapper_path}")
                return str(launchwrapper_path)
        except Exception as e:
            print(f"Ошибка при скачивании launchwrapper: {e}")
            return None
    
    def on_install_finished(self, success, message):
        """Обработчик завершения установки Vanilla"""
        self.install_success = success
        if not success:
            self.show_error(message)
    
    def on_forge_install_finished(self, success, message):
        """Обработчик завершения установки Forge"""
        self.forge_install_success = success
        if not success:
            self.show_error(message)
    
    def on_fabric_install_finished(self, success, message):
        """Обработчик завершения установки Fabric"""
        self.fabric_install_success = success
        if not success:
            self.show_error(message)
    
    def restore_ui(self):
        """Восстанавливает UI после запуска"""
        QMetaObject.invokeMethod(self, "restore_ui_slot")
    
    @pyqtSlot()
    def restore_ui_slot(self):
        """Слот для восстановления UI"""
        self.play_button.setEnabled(True)
        play_icon_path = get_asset_path("play.png")
        if os.path.exists(play_icon_path):
            self.play_button.setIcon(QIcon(play_icon_path))
        else:
            self.play_button.setText("ИГРАТЬ")
        self.play_button.setText("")
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
    
    def update_status(self, text):
        """Обновляет статус в UI"""
        QMetaObject.invokeMethod(self.status_label, "setText",
                                 Q_ARG(str, text))
    
    def update_progress(self, value):
        """Обновляет прогресс бар"""
        QMetaObject.invokeMethod(self.progress_bar, "setValue",
                                 Q_ARG(int, value))
    
    def show_error(self, text):
        """Показывает сообщение об ошибке"""
        QMetaObject.invokeMethod(self, "show_message_box",
                                 Q_ARG(str, "Ошибка"),
                                 Q_ARG(str, text),
                                 Q_ARG(int, QMessageBox.Critical))
    
    @pyqtSlot(str, str, int)
    def show_message_box(self, title, text, icon):
        """Слот для показа сообщения"""
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.exec_()
    
    @pyqtSlot()
    def delayed_close(self):
        """Закрывает лаунчер с задержкой"""
        QTimer.singleShot(2000, self.close)
    
    def get_installed_versions(self):
        """Возвращает список установленных версий"""
        try:
            versions = minecraft_launcher_lib.utils.get_installed_versions(str(self.minecraft_dir))
            return [v["id"] for v in versions]
        except:
            return []
    
    def is_version_installed(self, version_name):
        """Проверяет установлена ли указанная версия"""
        installed = self.get_installed_versions()
        return version_name in installed
    
    def get_version_type(self, version_name):
        """Определяет тип версии по имени"""
        if "forge" in version_name.lower():
            return "Forge"
        elif "fabric" in version_name.lower():
            return "Fabric"
        else:
            return "Vanilla"
    
    def verify_version_files(self, version_name):
        """Проверяет целостность файлов версии"""
        version_dir = self.minecraft_dir / "versions" / version_name
        json_file = version_dir / f"{version_name}.json"
        jar_file = version_dir / f"{version_name}.jar"
        
        return json_file.exists() and jar_file.exists()
    
    def repair_version(self, version_name):
        """Пытается восстановить поврежденную версию"""
        try:
            version_dir = self.minecraft_dir / "versions" / version_name
            
            # Проверяем JSON
            json_path = version_dir / f"{version_name}.json"
            if not json_path.exists():
                return False
            
            # Проверяем JAR
            jar_path = version_dir / f"{version_name}.jar"
            if not jar_path.exists():
                # Пробуем скопировать из vanilla версии
                vanilla_jar = self.minecraft_dir / "versions" / self.current_mc_version / f"{self.current_mc_version}.jar"
                if vanilla_jar.exists():
                    import shutil
                    shutil.copy2(vanilla_jar, jar_path)
                    return True
            
            return False
        except:
            return False