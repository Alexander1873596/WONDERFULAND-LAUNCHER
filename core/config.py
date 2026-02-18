import os
import sys
from pathlib import Path

# Версии Minecraft, Forge и Fabric (по умолчанию)
DEFAULT_MC_VERSION = "1.21.4"
FORGE_VERSION = "54.1.13"  # Для 1.21.4
FABRIC_LOADER_VERSION = "0.18.4"
FABRIC_INSTALLER_VERSION = "1.0.1"
REQUIRED_JAVA_VERSION = 21

# Типы версий для фильтрации
VERSION_TYPES = ["release", "snapshot", "old_beta", "old_alpha"]

# Словарь соответствия версий Minecraft и рекомендуемых версий Java
JAVA_VERSION_REQUIREMENTS = {
    "1.21.4": 21,
    "1.21": 21,
    "1.20.6": 21,
    "1.20.4": 21,
    "1.20.1": 21,
    "1.19.4": 21,
    "1.19.2": 17,
    "1.18.2": 17,
    "1.17.1": 17,
    "1.16.5": 11,
    "1.15.2": 11,
    "1.14.4": 11,
    "1.13.2": 11,
    "1.12.2": 8,
    "1.11.2": 8,
    "1.10.2": 8,
    "1.9.4": 8,
    "1.8.9": 8,
    "1.7.10": 8,
}

# Словарь соответствия версий Minecraft и Forge
FORGE_VERSIONS = {
    "1.7.10": "10.13.4.1614-1.7.10",
    "1.8.9": "11.15.1.2318-1.8.9",
    "1.12.2": "14.23.5.2860",
    "1.13.2": "25.0.219",
    "1.14.4": "28.2.26",
    "1.15.2": "31.2.57",
    "1.16.5": "36.2.39",
    "1.17.1": "37.1.1",
    "1.18.2": "40.2.14",
    "1.19.2": "43.2.21",
    "1.19.4": "45.1.0",
    "1.20.1": "47.1.3",
    "1.20.4": "49.0.14",
    "1.20.6": "50.1.0",
    "1.21": "51.0.33",
    "1.21.1": "52.0.16",
    "1.21.4": "54.1.13",
}

# Словарь соответствия версий Minecraft и Fabric
FABRIC_VERSIONS = {
    "1.21.4": "0.16.9",
    "1.21": "0.16.9",
    "1.20.6": "0.16.9",
    "1.20.4": "0.15.11",
    "1.20.1": "0.14.25",
    "1.19.4": "0.14.25",
    "1.19.2": "0.14.25",
    "1.18.2": "0.14.25",
    "1.17.1": "0.14.25",
    "1.16.5": "0.14.25",
    "1.15.2": "0.14.25",
    "1.14.4": "0.14.25",
}

# Определяем путь к проекту
def get_project_dir():
    if getattr(sys, 'frozen', False):
        # Запуск из собранного exe
        return Path(sys.executable).parent
    else:
        # Запуск из исходников
        return Path(__file__).parent.parent

PROJECT_DIR = get_project_dir()

# Пути к ресурсам
def get_asset_path(filename):
    """Возвращает полный путь к файлу в папке assets"""
    # Проверяем разные возможные расположения assets
    possible_paths = [
        PROJECT_DIR / "assets" / filename,  # рядом с exe/assets
        PROJECT_DIR / "_internal" / "assets" / filename,  # внутри _internal
        Path(__file__).parent.parent / "assets" / filename,  # исходники
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    print(f"Предупреждение: файл {filename} не найден")
    return str(PROJECT_DIR / "assets" / filename)  # возвращаем ожидаемый путь

ASSETS_DIR = PROJECT_DIR / "assets"

# Путь к директории Minecraft по умолчанию
if os.name == 'nt':
    DEFAULT_MINECRAFT_DIR = Path(os.getenv('APPDATA')) / ".minecraft"
else:
    DEFAULT_MINECRAFT_DIR = Path.home() / ".minecraft"

def ensure_dir_exists(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_recommended_java_version(mc_version):
    """Возвращает рекомендуемую версию Java для указанной версии Minecraft"""
    return JAVA_VERSION_REQUIREMENTS.get(mc_version, 21)

def get_recommended_forge_version(mc_version):
    """Возвращает рекомендуемую версию Forge для указанной версии Minecraft"""
    return FORGE_VERSIONS.get(mc_version, FORGE_VERSION)

def get_recommended_fabric_version(mc_version):
    """Возвращает рекомендуемую версию Fabric для указанной версии Minecraft"""
    return FABRIC_VERSIONS.get(mc_version, FABRIC_LOADER_VERSION)