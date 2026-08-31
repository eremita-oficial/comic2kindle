"""
Funções utilitárias para o Kindle Panel Creator
"""

import os
import tempfile
from pathlib import Path
from PIL import Image
import subprocess

def get_temp_file(extension='.png'):
    """Cria um arquivo temporário com a extensão especificada"""
    fd, path = tempfile.mkstemp(suffix=extension)
    os.close(fd)
    return Path(path)

def cleanup_temp_files():
    """Limpa arquivos temporários"""
    temp_dir = Path(tempfile.gettempdir())
    for file in temp_dir.glob("kindle_panel_*.png"):
        try:
            file.unlink()
        except:
            pass

def get_image_dimensions(image_path):
    """Obtém dimensões de uma imagem"""
    with Image.open(image_path) as img:
        return img.size

def resize_image_for_thumbnail(image, max_width=150, max_height=200):
    """Redimensiona imagem para miniatura mantendo proporção"""
    width, height = image.size
    ratio = min(max_width/width, max_height/height)
    new_size = (int(width * ratio), int(height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)

def pdf_to_images(pdf_path, dpi=150):
    """Converte PDF para imagens usando pdftoppm"""
    temp_dir = Path(tempfile.mkdtemp())
    output_prefix = temp_dir / "page"
    
    cmd = [
        'pdftoppm',
        '-png',
        '-r', str(dpi),
        '-scale-to', '1024',
        str(pdf_path),
        str(output_prefix)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        images = sorted(temp_dir.glob("*.png"))
        return images
    except subprocess.CalledProcessError as e:
        print(f"Erro ao converter PDF: {e.stderr}")
        return []
    except FileNotFoundError:
        print("pdftoppm não encontrado. Instale poppler-utils.")
        return []

def is_pdf(file_path):
    """Verifica se o arquivo é um PDF"""
    return Path(file_path).suffix.lower() == '.pdf'

def is_image(file_path):
    """Verifica se o arquivo é uma imagem suportada"""
    return Path(file_path).suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']

def create_backup(file_path):
    """Cria backup de um arquivo"""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup"
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
    return None

def human_readable_size(size_bytes):
    """Converte bytes para formato legível"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
