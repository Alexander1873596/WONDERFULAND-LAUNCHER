import subprocess
import re
import uuid
import os
import json
from pathlib import Path
from core.config import ensure_dir_exists

def get_java_major_version(java_path):
    """Определяет мажорную версию Java"""
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        result = subprocess.run(
            [java_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creation_flags
        )
        output = result.stderr or result.stdout
        
        # Специальная обработка для Java 8 (версия 1.8)
        if 'version "1.8' in output or '1.8.0' in output:
            return 8
        
        patterns = [
            r'version "(\d+)',
            r'openjdk version "(\d+)',
            r'(\d+)\.\d+\.\d+',
            r'java version "1\.(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                if '1\.' in pattern:
                    return int(match.group(1))
                else:
                    return int(match.group(1))
        
        return 0
    except subprocess.TimeoutExpired:
        print("Java version check timed out")
        return 0
    except Exception as e:
        print(f"Error getting Java version: {e}")
        return 0

def check_java_version(java_path, required_version):
    """Проверяет версию Java"""
    try:
        if not os.path.exists(java_path):
            return False, f"Java не найдена по пути: {java_path}"
        
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        
        result = subprocess.run(
            [java_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creation_flags
        )
        output = result.stderr or result.stdout
        
        major_version = get_java_major_version(java_path)
        
        if major_version == 0:
            return False, "Не удалось определить версию Java"
        
        print(f"Detected Java version: {major_version}")
        
        if major_version < required_version:
            return False, f"Minecraft требует Java {required_version}+, а у вас Java {major_version}"
        
        return True, f"Java {major_version} подходит"
        
    except subprocess.TimeoutExpired:
        return False, "Проверка Java зависла (таймаут 10 сек)"
    except Exception as e:
        print(f"Java version check error: {e}")
        return False, f"Ошибка проверки Java: {str(e)}"

def generate_offline_uuid(username):
    """Генерирует UUID для офлайн режима"""
    namespace_uuid = uuid.UUID('ba3f5aed-5b9c-11ea-bc55-0242ac130003')
    return str(uuid.uuid3(namespace_uuid, username))

def create_launcher_profiles(minecraft_dir):
    """Создает launcher_profiles.json если его нет"""
    minecraft_dir = Path(minecraft_dir)
    ensure_dir_exists(minecraft_dir)
    
    launcher_profiles_path = minecraft_dir / "launcher_profiles.json"
    
    if not launcher_profiles_path.exists():
        launcher_profiles = {
            "profiles": {},
            "settings": {
                "crashAssistance": True,
                "enableAdvanced": False,
                "enableAnalytics": True,
                "enableHistorical": False,
                "enableReleases": True,
                "enableSnapshots": False,
                "keepLauncherOpen": False,
                "profileSorting": "ByLastPlayed",
                "showGameLog": False,
                "showMenu": True,
                "soundOn": False
            },
            "version": 3,
            "selectedProfile": "",
            "clientToken": str(uuid.uuid4()),
            "authenticationDatabase": {}
        }
        
        try:
            with open(launcher_profiles_path, 'w', encoding='utf-8') as f:
                json.dump(launcher_profiles, f, indent=2)
            print(f"Created launcher_profiles.json at {launcher_profiles_path}")
        except Exception as e:
            print(f"Error creating launcher_profiles.json: {e}")
    else:
        try:
            with open(launcher_profiles_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "version" not in data:
                data["version"] = 3
            
            if "profiles" not in data:
                data["profiles"] = {}
            
            if "clientToken" not in data:
                data["clientToken"] = str(uuid.uuid4())
            
            with open(launcher_profiles_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Ошибка чтения launcher_profiles.json: {e}")
            if launcher_profiles_path.exists():
                try:
                    os.remove(launcher_profiles_path)
                except:
                    pass
            create_launcher_profiles(minecraft_dir)