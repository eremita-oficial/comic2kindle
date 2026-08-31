"""
Módulo de importação de imagens, PDFs e CBZ
"""

import os
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
import glob
import zipfile
import tempfile
import shutil
import subprocess

from utils import pdf_to_images, is_pdf, is_image
from config import SUPPORTED_IMAGES

class Importer:
    """Classe para importação de arquivos"""
    
    def __init__(self):
        self.pages = []
        self.current_page = 0
        self.suggested_name = ""
        self.source_path = ""
        self.source_dir = ""
        
    def load_images_from_folder(self, folder_path):
        """
        Carrega todas as imagens de uma pasta
        
        Args:
            folder_path: Caminho da pasta
            
        Returns:
            Lista de páginas carregadas
        """
        folder = Path(folder_path).resolve()
        
        print(f"📂 Carregando imagens de: {folder}")
        
        if not folder.exists():
            print(f"❌ Pasta não encontrada: {folder}")
            return []
        
        if not folder.is_dir():
            print(f"❌ Não é uma pasta: {folder}")
            return []
        
        self.source_path = str(folder)
        self.source_dir = str(folder.parent)
        self.suggested_name = folder.name
        
        # Lista todas as imagens na pasta
        images = []
        extensions = [
            '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif',
            '*.JPG', '*.JPEG', '*.PNG', '*.BMP', '*.TIFF', '*.TIF'
        ]
        
        for ext in extensions:
            pattern = str(folder / ext)
            found = glob.glob(pattern)
            images.extend(found)
        
        images = sorted(set(images))
        
        print(f"🔍 Encontrados {len(images)} arquivos de imagem")
        
        if len(images) > 0:
            print("📋 Primeiros arquivos encontrados:")
            for img in images[:5]:
                print(f"  - {os.path.basename(img)}")
            if len(images) > 5:
                print(f"  ... e mais {len(images)-5} arquivos")
        else:
            print("⚠️ Nenhum arquivo de imagem encontrado!")
            return []
        
        self.pages = []
        
        for img_path in images:
            try:
                print(f"📖 Carregando: {os.path.basename(img_path)}")
                img = Image.open(img_path)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                self.pages.append({
                    'path': str(img_path),
                    'image': img,
                    'panels': [],
                    'is_cover': False,
                    'is_full_page': False,
                    'marked_for_cut': False
                })
                print(f"✅ Carregada: {os.path.basename(img_path)} ({img.size[0]}x{img.size[1]})")
                
            except Exception as e:
                print(f"❌ Erro ao carregar {os.path.basename(img_path)}: {e}")
        
        print(f"✅ Total de páginas carregadas: {len(self.pages)}")
        return self.pages
    
    def load_cbr(self, cbr_path):
        """
        Carrega um arquivo CBR (Comic Book RAR)
        
        Args:
            cbr_path: Caminho do arquivo .cbr
            
        Returns:
            Lista de páginas carregadas
        """
        print(f"📚 Carregando CBR: {cbr_path}")
        
        if not os.path.exists(cbr_path):
            print(f"❌ Arquivo não encontrado: {cbr_path}")
            return []
        
        if not cbr_path.lower().endswith('.cbr'):
            print(f"❌ Não é um arquivo CBR: {cbr_path}")
            return []
        
        try:
            p = Path(cbr_path)
            self.source_path = str(p.resolve())
            self.source_dir = str(p.parent)
            self.suggested_name = p.stem
            
            # Cria pasta temporária para extração
            temp_dir = tempfile.mkdtemp(prefix="kindle_cbr_")
            print(f"📂 Extraindo para: {temp_dir}")
            
            # Verifica se o unrar está disponível
            try:
                # Tenta extrair usando unrar
                result = subprocess.run(
                    ['unrar', 'x', '-inul', cbr_path, temp_dir],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    # Se unrar falhar, tenta usar rar
                    result = subprocess.run(
                        ['rar', 'x', '-inul', cbr_path, temp_dir],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode != 0:
                        raise Exception("Falha ao extrair CBR. Verifique se o 'unrar' ou 'rar' está instalado.")
                
                print(f"✅ CBR extraído com sucesso")
                
            except FileNotFoundError:
                print("❌ 'unrar' ou 'rar' não encontrado. Instale o pacote unrar:")
                print("  - Ubuntu/Debian: sudo apt-get install unrar")
                print("  - macOS: brew install unrar")
                print("  - Windows: Baixe e instale o WinRAR ou 7-Zip")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return []
            
            # Lista todos os arquivos extraídos
            extracted_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Verifica se é imagem
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')):
                        extracted_files.append(file_path)
            
            # Ordena os arquivos (tenta ordem numérica)
            extracted_files.sort(key=lambda x: self._natural_sort_key(x))
            
            print(f"🔍 Encontradas {len(extracted_files)} imagens no CBR")
            
            if len(extracted_files) == 0:
                print("❌ Nenhuma imagem encontrada no CBR")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return []
            
            # Carrega as imagens
            self.pages = []
            
            for i, img_path in enumerate(extracted_files):
                try:
                    print(f"📖 Carregando: {os.path.basename(img_path)}")
                    img = Image.open(img_path)
                    
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    self.pages.append({
                        'path': str(img_path),
                        'image': img,
                        'panels': [],
                        'is_cover': (i == 0),  # Primeira imagem marcada como capa
                        'is_full_page': False,
                        'marked_for_cut': False
                    })
                    print(f"✅ Carregada: {os.path.basename(img_path)} ({img.size[0]}x{img.size[1]})")
                    
                except Exception as e:
                    print(f"❌ Erro ao carregar {os.path.basename(img_path)}: {e}")
            
            # Armazena o caminho da pasta temporária para limpeza posterior
            self._temp_cbr_dir = temp_dir
            
            print(f"✅ Total de páginas carregadas do CBR: {len(self.pages)}")
            return self.pages
            
        except Exception as e:
            print(f"❌ Erro ao carregar CBR: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def load_cbz(self, cbz_path):
        """
        Carrega um arquivo CBZ (Comic Book Zip)
        
        Args:
            cbz_path: Caminho do arquivo .cbz
            
        Returns:
            Lista de páginas carregadas
        """
        print(f"📚 Carregando CBZ: {cbz_path}")
        
        if not os.path.exists(cbz_path):
            print(f"❌ Arquivo não encontrado: {cbz_path}")
            return []
        
        if not cbz_path.lower().endswith('.cbz'):
            print(f"❌ Não é um arquivo CBZ: {cbz_path}")
            return []
        
        try:
            p = Path(cbz_path)
            self.source_path = str(p.resolve())
            self.source_dir = str(p.parent)
            self.suggested_name = p.stem
            
            # Cria pasta temporária para extração
            temp_dir = tempfile.mkdtemp(prefix="kindle_cbz_")
            print(f"📂 Extraindo para: {temp_dir}")
            
            # Extrai o arquivo CBZ (ZIP)
            with zipfile.ZipFile(cbz_path, 'r') as cbz:
                cbz.extractall(temp_dir)
                print(f"✅ Extraídos {len(cbz.namelist())} arquivos")
            
            # Lista todos os arquivos extraídos
            extracted_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Verifica se é imagem
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')):
                        extracted_files.append(file_path)
            
            # Ordena os arquivos (tenta ordem numérica)
            extracted_files.sort(key=lambda x: self._natural_sort_key(x))
            
            print(f"🔍 Encontradas {len(extracted_files)} imagens no CBZ")
            
            if len(extracted_files) == 0:
                print("❌ Nenhuma imagem encontrada no CBZ")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return []
            
            # Carrega as imagens
            self.pages = []
            
            for i, img_path in enumerate(extracted_files):
                try:
                    print(f"📖 Carregando: {os.path.basename(img_path)}")
                    img = Image.open(img_path)
                    
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    self.pages.append({
                        'path': str(img_path),
                        'image': img,
                        'panels': [],
                        'is_cover': (i == 0),  # Primeira imagem marcada como capa
                        'is_full_page': False,
                        'marked_for_cut': False
                    })
                    print(f"✅ Carregada: {os.path.basename(img_path)} ({img.size[0]}x{img.size[1]})")
                    
                except Exception as e:
                    print(f"❌ Erro ao carregar {os.path.basename(img_path)}: {e}")
            
            # Armazena o caminho da pasta temporária para limpeza posterior
            self._temp_cbz_dir = temp_dir
            
            print(f"✅ Total de páginas carregadas do CBZ: {len(self.pages)}")
            return self.pages
            
        except zipfile.BadZipFile:
            print(f"❌ Arquivo CBZ corrompido ou inválido: {cbz_path}")
            return []
        except Exception as e:
            print(f"❌ Erro ao carregar CBZ: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _natural_sort_key(self, filename):
        """Chave de ordenação natural para nomes de arquivo"""
        import re
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        def alphanum_key(key):
            return [convert(c) for c in re.split('([0-9]+)', os.path.basename(key))]
        return alphanum_key(filename)
    
    def load_pdf(self, pdf_path):
        """Carrega um PDF e converte para imagens"""
        if not is_pdf(pdf_path):
            raise ValueError("Arquivo não é um PDF")
        
        print(f"📄 Carregando PDF: {pdf_path}")
        
        p = Path(pdf_path)
        self.source_path = str(p.resolve())
        self.source_dir = str(p.parent)
        self.suggested_name = p.stem
        
        image_paths = pdf_to_images(pdf_path)
        
        if not image_paths:
            print("❌ Nenhuma imagem foi extraída do PDF")
            return []
        
        print(f"🔍 Extraídas {len(image_paths)} imagens do PDF")
        
        self.pages = []
        
        for img_path in image_paths:
            try:
                print(f"📖 Carregando página: {os.path.basename(img_path)}")
                img = Image.open(img_path)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                self.pages.append({
                    'path': str(img_path),
                    'image': img,
                    'panels': [],
                    'is_cover': False,
                    'is_full_page': False,
                    'marked_for_cut': False
                })
                
            except Exception as e:
                print(f"❌ Erro ao carregar página do PDF: {e}")
        
        print(f"✅ Total de páginas carregadas: {len(self.pages)}")
        return self.pages
    
    def load_image(self, image_path):
        """Carrega uma única imagem"""
        try:
            p = Path(image_path)
            self.source_path = str(p.resolve())
            self.source_dir = str(p.parent)
            self.suggested_name = p.stem
            
            img = Image.open(image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            self.pages = [{
                'path': str(image_path),
                'image': img,
                'panels': [],
                'is_cover': False,
                'is_full_page': False,
                'marked_for_cut': False
            }]
            
            print(f"✅ Imagem carregada: {os.path.basename(image_path)}")
            return self.pages
            
        except Exception as e:
            print(f"❌ Erro ao carregar imagem: {e}")
            return []
    
    def get_page_count(self):
        """Retorna o número de páginas"""
        return len(self.pages)
    
    def get_page(self, index):
        """Retorna uma página específica"""
        if 0 <= index < len(self.pages):
            return self.pages[index]
        return None
    
    def set_cover(self, index, is_cover=True):
        """Define se uma página é capa"""
        if 0 <= index < len(self.pages):
            self.pages[index]['is_cover'] = is_cover
    
    def remove_page(self, index):
        """Remove uma página do projeto"""
        if 0 <= index < len(self.pages):
            removed = self.pages.pop(index)
            print(f"🗑️ Página {index+1} removida: {removed.get('path', 'Sem caminho')}")
            return True
        return False
    
    def get_image_cv2(self, page_index):
        """Retorna a imagem em formato OpenCV"""
        page = self.get_page(page_index)
        if page:
            img = page['image']
            img_array = np.array(img)
            return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return None
    
    def cleanup_temp_files(self):
        """Limpa arquivos temporários do CBZ e CBR"""
        if hasattr(self, '_temp_cbz_dir') and os.path.exists(self._temp_cbz_dir):
            try:
                shutil.rmtree(self._temp_cbz_dir)
                print(f"🧹 Pasta temporária CBZ removida: {self._temp_cbz_dir}")
            except Exception as e:
                print(f"⚠️ Erro ao remover pasta temporária CBZ: {e}")
        
        if hasattr(self, '_temp_cbr_dir') and os.path.exists(self._temp_cbr_dir):
            try:
                shutil.rmtree(self._temp_cbr_dir)
                print(f"🧹 Pasta temporária CBR removida: {self._temp_cbr_dir}")
            except Exception as e:
                print(f"⚠️ Erro ao remover pasta temporária CBR: {e}")
