#!/usr/bin/env python3
"""
Módulo de upscaling para painéis de HQ
"""

from PIL import Image, ImageFilter, ImageEnhance

class PanelUpscaler:
    """Upscaler para painéis de HQ usando PIL"""
    
    @staticmethod
    def upscale(image, scale=2):
        """
        Aplica upscaling a um painel
        
        Args:
            image: Imagem PIL
            scale: Fator de escala (2, 3, 4)
            
        Returns:
            Imagem PIL upscaled
        """
        width, height = image.size
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        upscaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        upscaled = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        
        enhancer = ImageEnhance.Contrast(upscaled)
        upscaled = enhancer.enhance(1.1)
        
        return upscaled

def upscale_panel(image, scale=2):
    """Função rápida para upscaling de painéis"""
    return PanelUpscaler.upscale(image, scale)
