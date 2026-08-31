#!/usr/bin/env python3
"""
Gerenciamento de projetos .pcc
Suporte a dois modos: Completo (imagens embutidas) e Leve (referências)
"""

import json
import pickle
import os
from pathlib import Path
from PIL import Image
import base64
from io import BytesIO

class ProjectManager:
    """Gerencia salvamento e carregamento de projetos"""
    
    @staticmethod
    def save_project(project_data, filepath, mode='full', progress_callback=None):
        """
        Salva um projeto em formato .pcc
        
        Args:
            project_data: Dicionário com os dados do projeto
            filepath: Caminho para salvar o arquivo .pcc
            mode: 'full' (imagens embutidas) ou 'light' (apenas referências)
            progress_callback: Função callback(percentual, mensagem)
        """
        try:
            data = {
                'version': '2.0',
                'mode': mode,
                'pages': []
            }
            
            total_pages = len(project_data['pages'])
            
            for i, page in enumerate(project_data['pages']):
                if progress_callback and progress_callback(0, "check_cancel"):
                    return False
                
                # Dados básicos da página (sempre salvos)
                page_data = {
                    'panels': page.get('panels', []),
                    'is_cover': page.get('is_cover', False)
                }
                
                if mode == 'full':
                    # Modo completo: imagem embutida em Base64
                    img = page['image']
                    buffered = BytesIO()
                    img.save(buffered, format='PNG')
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    page_data['image_base64'] = img_base64
                    page_data['path'] = page.get('path', '')
                else:
                    # Modo leve: apenas o caminho da imagem
                    page_data['path'] = page.get('path', '')
                    
                    # Verifica se o caminho existe
                    if not os.path.exists(page_data['path']):
                        print(f"⚠️ Aviso: Imagem não encontrada: {page_data['path']}")
                
                data['pages'].append(page_data)
                
                if progress_callback:
                    percent = int((i + 1) / total_pages * 90)
                    progress_callback(percent, f"Salvando página {i+1}/{total_pages}")
            
            if progress_callback:
                progress_callback(95, "Salvando arquivo...")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            if progress_callback:
                progress_callback(100, "Concluído!")
            
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"✅ Projeto salvo em: {filepath} ({size_mb:.2f} MB) - Modo: {mode}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar projeto: {e}")
            import traceback
            traceback.print_exc()
            if progress_callback:
                progress_callback(0, f"Erro: {str(e)}")
            return False
    
    @staticmethod
    def load_project(filepath, progress_callback=None):
        """
        Carrega um projeto .pcc (suporta modos full e light)
        
        Args:
            filepath: Caminho do arquivo .pcc
            progress_callback: Função callback(percentual, mensagem)
            
        Returns:
            Dicionário com os dados do projeto
        """
        try:
            if progress_callback:
                progress_callback(10, "Lendo arquivo...")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mode = data.get('mode', 'full')  # Compatibilidade com versões antigas
            pages = []
            total_pages = len(data['pages'])
            
            print(f"📂 Carregando projeto - Modo: {mode}")
            
            for i, page_data in enumerate(data['pages']):
                if progress_callback and progress_callback(0, "check_cancel"):
                    return None
                
                if mode == 'full':
                    # Modo completo: imagem embutida em Base64
                    img_base64 = page_data.get('image_base64', '')
                    if img_base64:
                        img_data = base64.b64decode(img_base64)
                        img = Image.open(BytesIO(img_data))
                    else:
                        # Fallback: tenta carregar do caminho
                        img_path = page_data.get('path', '')
                        if os.path.exists(img_path):
                            img = Image.open(img_path)
                        else:
                            print(f"⚠️ Imagem não encontrada: {img_path}")
                            continue
                else:
                    # Modo leve: carrega do caminho
                    img_path = page_data.get('path', '')
                    if os.path.exists(img_path):
                        img = Image.open(img_path)
                    else:
                        print(f"⚠️ Imagem não encontrada: {img_path}")
                        continue
                
                page = {
                    'path': page_data.get('path', ''),
                    'image': img,
                    'panels': page_data.get('panels', []),
                    'is_cover': page_data.get('is_cover', False)
                }
                pages.append(page)
                
                if progress_callback:
                    percent = 10 + int((i + 1) / total_pages * 80)
                    progress_callback(percent, f"Carregando página {i+1}/{total_pages}")
            
            if progress_callback:
                progress_callback(100, "Concluído!")
            
            print(f"✅ Projeto carregado: {filepath} ({len(pages)} páginas)")
            return {'pages': pages}
            
        except Exception as e:
            print(f"❌ Erro ao carregar projeto: {e}")
            import traceback
            traceback.print_exc()
            if progress_callback:
                progress_callback(0, f"Erro: {str(e)}")
            return None
    
    @staticmethod
    def get_project_info(filepath):
        """
        Retorna informações básicas do projeto sem carregar as imagens
        
        Args:
            filepath: Caminho do arquivo .pcc
            
        Returns:
            Dicionário com informações do projeto
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mode = data.get('mode', 'full')
            total_pages = len(data['pages'])
            total_panels = sum(len(p.get('panels', [])) for p in data['pages'])
            
            return {
                'mode': mode,
                'total_pages': total_pages,
                'total_panels': total_panels,
                'file_size_mb': os.path.getsize(filepath) / (1024 * 1024)
            }
            
        except Exception as e:
            print(f"❌ Erro ao ler informações do projeto: {e}")
            return None
