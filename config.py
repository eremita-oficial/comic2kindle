"""
Configurações do Kindle Panel Creator
"""

import os
import tempfile
from pathlib import Path

# Configurações da aplicação
APP_NAME = "Kindle Panel Creator"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Kindle Panel Creator Team"

# Diretórios
BASE_DIR = Path(__file__).parent
ICONS_DIR = BASE_DIR / "icons"
THEMES_DIR = BASE_DIR / "themes"
# Alterado para usar o diretório temporário do sistema operacional (compatível com AppImage)
TEMP_DIR = Path(tempfile.gettempdir()) / "comic2kindle_temp"

# Configurações de interface
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
THUMBNAIL_WIDTH = 150
THUMBNAIL_HEIGHT = 200
CANVAS_BG = "#2b2b2b"
PANEL_COLOR = "#00ff00"
PANEL_SELECTED_COLOR = "#ff0000"
PANEL_HANDLE_SIZE = 8

# Configurações de detecção
MIN_PANEL_AREA = 5000
MAX_PANEL_AREA = 1000000
PANEL_SENSITIVITY = 0.5
BINARY_THRESHOLD = 127

# Formatos suportados
SUPPORTED_IMAGES = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
SUPPORTED_PDF = ['.pdf']

# Configurações de exportação
PDF_DPI = 300
JPG_QUALITY = 90
CBZ_COMPRESSION = 0  # 0 = sem compressão

# Criar diretórios necessários com segurança
TEMP_DIR.mkdir(exist_ok=True, parents=True)
