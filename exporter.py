#!/usr/bin/env python3
"""
Módulo Exporter - Kindle Comic Splitter (Corrigido com suporte a qualidade dinâmica e metadados)
Agora gera 4 imagens por página: 
- a: Página inteira redimensionada para 1280px altura, rotacionada 90° à esquerda, centralizada em 1264x1680
- b, c, d: Cortes da página em 1264x1680
Páginas marcadas como CAPA ou PÁGINA INTEIRA não são rotacionadas.
"""

import os
from pathlib import Path
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageOps

class Exporter:
    """Classe responsável por exportar os projetos para PDF/Kindle de forma eficiente"""

    @staticmethod
    def create_centered_image(img, target_width=1264, target_height=1680, background_color=(255, 255, 255)):
        """Redimensiona e centraliza a imagem em um fundo padrão para o Kindle (1264x1680)"""
        img_w, img_h = img.size
        ratio = min(target_width / img_w, target_height / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        background = Image.new("RGB", (target_width, target_height), background_color)
        paste_x = (target_width - new_w) // 2
        paste_y = (target_height - new_h) // 2
        
        background.paste(resized_img, (paste_x, paste_y))
        return background

    @staticmethod
    def create_rotated_slice_image(slice_img, target_width=1264, target_height=1680):
        """
        Gira a fatia 90° à esquerda, redimensiona mantendo proporção com largura máxima e altura exata,
        centraliza em um fundo preto de 1264x1680.
        """
        rotated_slice = slice_img.rotate(90, expand=True)
        final_resized = ImageOps.contain(rotated_slice, (target_width, target_height), method=Image.Resampling.LANCZOS)
        background = Image.new("RGB", (target_width, target_height), (0, 0, 0))
        
        paste_x = (target_width - final_resized.width) // 2
        paste_y = (target_height - final_resized.height) // 2
        
        background.paste(final_resized, (paste_x, paste_y))
        return background

    @staticmethod
    def create_full_page_rotated_image(img, target_width=1264, target_height=1680):
        """
        Cria a imagem "a" - página inteira rotacionada 90° à esquerda.
        1. Redimensiona para 1280px de altura (mantendo proporção)
        2. Rotaciona 90° à esquerda
        3. Centraliza em canvas 1264x1680 com fundo preto
        """
        # Passo 1: Redimensionar para altura de 1280 pixels (mantendo proporção)
        target_height_a = 1280
        ratio = target_height_a / img.height
        new_w = int(img.width * ratio)
        new_h = target_height_a
        
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Passo 2: Rotaciona 90° à esquerda
        rotated_img = img_resized.rotate(90, expand=True)
        
        # Passo 3: Cria canvas preto de 1264x1680
        background = Image.new("RGB", (target_width, target_height), (0, 0, 0))
        
        # Passo 4: Centraliza a imagem rotacionada
        paste_x = (target_width - rotated_img.width) // 2
        paste_y = (target_height - rotated_img.height) // 2
        
        background.paste(rotated_img, (paste_x, paste_y))
        return background

    @staticmethod
    def create_full_page_normal_image(img, target_width=1264, target_height=1680):
        """
        Cria a imagem para capa/página inteira - SEM ROTAÇÃO.
        Apenas redimensiona e centraliza em canvas 1264x1680 com fundo preto.
        """
        # Redimensiona para caber em 1264x1680 (mantendo proporção)
        img_w, img_h = img.size
        ratio = min(target_width / img_w, target_height / img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Cria canvas preto de 1264x1680
        background = Image.new("RGB", (target_width, target_height), (0, 0, 0))
        
        # Centraliza a imagem
        paste_x = (target_width - new_w) // 2
        paste_y = (target_height - new_h) // 2
        
        background.paste(resized_img, (paste_x, paste_y))
        return background

    @staticmethod
    def export_pdf_split(pages, output_path, parts=3, quality=95, progress_callback=None, title="", author=""):
        """
        Exporta o PDF dividindo cada página seguindo a lógica exata dos cortes,
        incluindo suporte a metadados (Título e Autor).
        Agora gera 4 imagens por página: a (página inteira rotacionada) + b, c, d (cortes)
        Páginas marcadas como CAPA ou PÁGINA INTEEIRA NÃO são rotacionadas.
        """
        try:
            safe_output_path = str(Path(output_path).resolve())
            print(f"📄 Exportando PDF Fatiado ({parts} fatias, Qualidade: {quality}): {safe_output_path}")
            
            kindle_width = 1264
            kindle_height = 1680
            
            c = canvas.Canvas(safe_output_path, pagesize=(kindle_width, kindle_height))
            
            # Aplicação dos metadados nativos do ReportLab
            if title:
                c.setTitle(title)
            if author:
                c.setAuthor(author)
            
            total_pages = len(pages)
            for i, page in enumerate(pages):
                if progress_callback and progress_callback(0, "check_cancel"):
                    return False
                
                img = page['image']
                is_cover = page.get('is_cover', False)
                is_full_page = page.get('is_full_page', False)
                crop_box = page.get('crop_box', None)
                
                # Aplica o crop_box se existir
                target_img = img
                if crop_box:
                    target_img = img.crop(crop_box)
                
                # ===== VERIFICA SE É CAPA OU PÁGINA INTEIRA =====
                is_special_page = is_cover or is_full_page or parts <= 1
                
                if is_special_page:
                    # ===== CAPA OU PÁGINA INTEIRA - SEM ROTAÇÃO =====
                    print(f"   📄 Página {i+1}: Capa/Página Inteira (SEM rotação)")
                    
                    # Cria a imagem sem rotação (apenas centralizada)
                    img_normal = Exporter.create_full_page_normal_image(target_img, kindle_width, kindle_height)
                    
                    fd, img_path = tempfile.mkstemp(suffix='.jpg')
                    os.close(fd)
                    try:
                        img_normal.save(img_path, 'JPEG', quality=quality)
                        img_reader = ImageReader(img_path)
                        c.drawImage(img_reader, 0, 0, kindle_width, kindle_height)
                        c.showPage()
                    finally:
                        if os.path.exists(img_path):
                            os.unlink(img_path)
                    
                    if progress_callback:
                        percent = int(((i + 1) / total_pages) * 100)
                        if progress_callback(percent, f"Página {i+1}/{total_pages} - Capa/Página Inteira (sem cortes)"):
                            return False
                    
                    # Pula para a próxima página (não gera cortes)
                    continue
                
                # ===== PÁGINA NORMAL - GERA IMAGEM "a" + CORTES b, c, d =====
                print(f"   📄 Página {i+1}: Normal (com rotação e cortes)")
                
                # ===== IMAGEM "a" - Página inteira rotacionada =====
                img_a = Exporter.create_full_page_rotated_image(target_img, kindle_width, kindle_height)
                
                fd, img_path_a = tempfile.mkstemp(suffix='.jpg')
                os.close(fd)
                try:
                    img_a.save(img_path_a, 'JPEG', quality=quality)
                    img_reader = ImageReader(img_path_a)
                    c.drawImage(img_reader, 0, 0, kindle_width, kindle_height)
                    c.showPage()
                finally:
                    if os.path.exists(img_path_a):
                        os.unlink(img_path_a)
                
                if progress_callback:
                    percent = int(((i + 1) / total_pages) * 50)
                    if progress_callback(percent, f"Página {i+1}/{total_pages} - Imagem a (página inteira)"):
                        return False
                
                # ===== IMAGENS b, c, d - Cortes =====
                # Redimensiona para largura de 1264 pixels (mantendo proporção)
                orig_w, orig_h = target_img.size
                ratio = kindle_width / orig_w
                new_w = kindle_width
                new_h = int(orig_h * ratio)
                resized_img = target_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                img_w, img_h = resized_img.size
                
                # Verifica altura mínima para cortes
                min_required_h = 1427
                if img_h < min_required_h:
                    temp_canvas = Image.new("RGB", (img_w, min_required_h), (0, 0, 0))
                    temp_canvas.paste(resized_img, (0, 0))
                    resized_img = temp_canvas
                    img_w, img_h = resized_img.size

                # Definição dos 3 cortes
                cut_h = 951
                box_b = (0, 0, img_w, cut_h)                    # Corte 1: Topo -> 'b'
                box_c = (0, 476, img_w, 1427)                   # Corte 2: Meio -> 'c'
                box_d = (0, img_h - cut_h, img_w, img_h)        # Corte 3: Base -> 'd'

                boxes = [box_b, box_c, box_d]
                suffixes = ['b', 'c', 'd']
                
                for j, box in enumerate(boxes):
                    if progress_callback and progress_callback(0, "check_cancel"):
                        return False
                    
                    # Recorta a fatia
                    cropped = resized_img.crop(box)
                    
                    # Processa a fatia (rotaciona 90° e centraliza em 1264x1680)
                    slice_processed = Exporter.create_rotated_slice_image(cropped, kindle_width, kindle_height)
                    
                    fd, img_path = tempfile.mkstemp(suffix='.jpg')
                    os.close(fd)
                    try:
                        slice_processed.save(img_path, 'JPEG', quality=quality)
                        img_reader = ImageReader(img_path)
                        c.drawImage(img_reader, 0, 0, kindle_width, kindle_height)
                        c.showPage()
                    finally:
                        if os.path.exists(img_path):
                            os.unlink(img_path)
                    
                    if progress_callback:
                        percent = int(50 + ((i * 3 + (j + 1)) / (total_pages * 3)) * 50)
                        if progress_callback(percent, f"Página {i+1}/{total_pages} - {suffixes[j]}"):
                            return False
            
            c.save()
            print("✅ PDF fatiado exportado com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao exportar PDF fatiado: {e}")
            import traceback
            traceback.print_exc()
            return False
