from pathlib import Path
import os
from dotenv import load_dotenv

#загружаем конфиг
load_dotenv()
DIR = os.environ.get("LOG_DIR")

def create_directory(dir_debug: str) -> str:
    """Создать новую директорию"""
    print(f"Создать новую директорию {dir_debug}")
    path: Path = Path(f"{DIR}\\{dir_debug}").resolve()

    if path.exists():
        return f"Директория уже создана: {DIR}\\{dir_debug}"

    path.mkdir(exist_ok=False)

    return f"Директория создана: {DIR}\\{dir_debug}"

def write_file(dir_debug: str, file_path: str, content: str) -> str:
    """Записывает файл (создает директории при необходимости)"""
    path = Path(f"{DIR}\\{dir_debug}\\{file_path}")
    try:
        with open(path, "w", encoding="utf-8") as f:
            path.write_text(content, encoding="utf-8")
        # print(f"✓ Файл успешно записан: {path}")
        return f"✓ Файл успешно записан: {path}"
    except Exception as e:
        print(f"❌ Ошибка при записи: {str(e)}")
        return f"❌ Ошибка при записи: {str(e)}"