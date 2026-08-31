#!/usr/bin/env python3
"""
Gerenciador do Editor de Canvas - Kindle Comic Splitter (Estilo Gwenview)
"""

from PIL import Image

class CanvasEditor:
    def __init__(self, canvas, master=None):
        self.canvas = canvas
        self.master = master
        
        self.is_cropping_mode = False
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None
        self.dark_overlays = []
        self.handles = []
        self.displayed_image_info = None

    def enter_crop_mode(self):
        """Ativa o modo de corte interativo na tela"""
        if self.master and hasattr(self.master, 'importer'):
            if not self.master.importer.pages:
                return False
        
        self.is_cropping_mode = True
        
        page = self.master.get_current_page() if (self.master and hasattr(self.master, 'get_current_page')) else None
        
        # Se já existe um crop_box guardado, reconstrói exatamente na posição proporcional correta
        if page and page.get('crop_box'):
            if self.displayed_image_info:
                img_tk, zoom_level, ox, oy, orig_w, orig_h = self.displayed_image_info
                disp_w = int(orig_w * zoom_level)
                disp_h = int(orig_h * zoom_level)
                
                cx1, cy1, cx2, cy2 = page['crop_box']
                canvas_rx1 = ox + (cx1 / orig_w) * disp_w
                canvas_ry1 = oy + (cy1 / orig_h) * disp_h
                canvas_rx2 = ox + (cx2 / orig_w) * disp_w
                canvas_ry2 = oy + (cy2 / orig_h) * disp_h
                
                self.current_rect = self.canvas.create_rectangle(
                    canvas_rx1, canvas_ry1, canvas_rx2, canvas_ry2,
                    outline='#00ffff', width=2, dash=(4, 4), tags="crop_elements"
                )
                self._update_overlays_and_handles()
        else:
            bbox = self.canvas.bbox("all")
            if bbox:
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                cx1, cy1 = bbox[0] + w * 0.1, bbox[1] + h * 0.1
                cx2, cy2 = bbox[2] - w * 0.1, bbox[3] - h * 0.1
                self.current_rect = self.canvas.create_rectangle(
                    cx1, cy1, cx2, cy2,
                    outline='#00ffff', width=2, dash=(4, 4), tags="crop_elements"
                )
                
                # Salva o crop_box inicial com base nas coordenadas da imagem real logo na abertura
                if page and self.displayed_image_info:
                    _, _, ox, oy, orig_w, orig_h = self.displayed_image_info
                    disp_w = w
                    disp_h = h
                    if disp_w > 0 and disp_h > 0:
                        scale_x = orig_w / disp_w
                        scale_y = orig_h / disp_h
                        img_x1 = int((cx1 - ox) * scale_x)
                        img_y1 = int((cy1 - oy) * scale_y)
                        img_x2 = int((cx2 - ox) * scale_x)
                        img_y2 = int((cy2 - oy) * scale_y)
                        page['crop_box'] = (max(0, img_x1), max(0, img_y1), min(orig_w, img_x2), min(orig_h, img_y2))

                self._update_overlays_and_handles()
        
        return True

    def exit_crop_mode(self):
        """Sai do modo de corte e limpa elementos visuais auxiliares"""
        self.is_cropping_mode = False
        self._clear_overlays_and_handles()
        if self.current_rect:
            self.canvas.delete(self.current_rect)
            self.current_rect = None

    def _clear_overlays_and_handles(self):
        for ov in self.dark_overlays:
            self.canvas.delete(ov)
        self.dark_overlays = []
        for h in self.handles:
            self.canvas.delete(h)
        self.handles = []

    def _update_overlays_and_handles(self):
        self._clear_overlays_and_handles()
        if not self.current_rect:
            return
        
        coords = self.canvas.coords(self.current_rect)
        if len(coords) != 4:
            return
        
        rx1, ry1, rx2, ry2 = coords
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        
        bx1, by1, bx2, by2 = bbox
        
        # Desenha sombreamento externo (estilo Gwenview)
        self.dark_overlays.append(self.canvas.create_rectangle(bx1, by1, bx2, ry1, fill='black', stipple='gray50', outline='', tags="crop_elements"))
        self.dark_overlays.append(self.canvas.create_rectangle(bx1, ry2, bx2, by2, fill='black', stipple='gray50', outline='', tags="crop_elements"))
        self.dark_overlays.append(self.canvas.create_rectangle(bx1, ry1, rx1, ry2, fill='black', stipple='gray50', outline='', tags="crop_elements"))
        self.dark_overlays.append(self.canvas.create_rectangle(rx2, ry1, bx2, ry2, fill='black', stipple='gray50', outline='', tags="crop_elements"))
        
        self.canvas.tag_raise(self.current_rect)

    def redraw_crop_overlays(self):
        """Redesenha overlays externos se necessário em modo ativo"""
        self._update_overlays_and_handles()

    def on_mouse_down(self, event):
        if not self.is_cropping_mode:
            return
        
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        if self.current_rect:
            coords = self.canvas.coords(self.current_rect)
            if len(coords) == 4:
                rx1, ry1, rx2, ry2 = coords
                if not (rx1 <= self.start_x <= rx2 and ry1 <= self.start_y <= ry2):
                    self.canvas.delete(self.current_rect)
                    self.current_rect = self.canvas.create_rectangle(
                        self.start_x, self.start_y, self.start_x, self.start_y,
                        outline='#00ffff', width=2, dash=(4, 4), tags="crop_elements"
                    )

    def on_mouse_drag(self, event):
        if not self.is_cropping_mode or not self.current_rect:
            return
        
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        coords = self.canvas.coords(self.current_rect)
        if len(coords) == 4:
            x1, y1 = coords[0], coords[1]
            self.canvas.coords(self.current_rect, x1, y1, cur_x, cur_y)
            self._update_overlays_and_handles()
            self._update_page_crop_box()

    def on_mouse_up(self, event):
        if not self.is_cropping_mode or not self.current_rect:
            return
        
        coords = self.canvas.coords(self.current_rect)
        if len(coords) == 4:
            x1, y1, x2, y2 = coords
            rx1, rx2 = min(x1, x2), max(x1, x2)
            ry1, ry2 = min(y1, y2), max(y1, y2)
            
            self.canvas.coords(self.current_rect, rx1, ry1, rx2, ry2)
            self._update_overlays_and_handles()
            self._update_page_crop_box()

    def _update_page_crop_box(self):
        """Mapeia as coordenadas atuais do canvas e salva persistentemente no dicionário da página"""
        if not self.current_rect or not self.master or not hasattr(self.master, 'get_current_page'):
            return
        
        coords = self.canvas.coords(self.current_rect)
        if len(coords) != 4:
            return
            
        rx1, ry1, rx2, ry2 = min(coords[0], coords[2]), min(coords[1], coords[3]), max(coords[0], coords[2]), max(coords[1], coords[3])
        page = self.master.get_current_page()
        if not page or not self.displayed_image_info:
            return
            
        _, _, ox, oy, orig_w, orig_h = self.displayed_image_info
        
        bbox = self.canvas.bbox("all")
        if bbox:
            canvas_img_w = bbox[2] - bbox[0]
            canvas_img_h = bbox[3] - bbox[1]
        else:
            canvas_img_w = orig_w
            canvas_img_h = orig_h

        if canvas_img_w > 0 and canvas_img_h > 0:
            scale_x = orig_w / canvas_img_w
            scale_y = orig_h / canvas_img_h
        else:
            scale_x = scale_y = 1.0

        img_x1 = int((rx1 - ox) * scale_x)
        img_y1 = int((ry1 - oy) * scale_y)
        img_x2 = int((rx2 - ox) * scale_x)
        img_y2 = int((ry2 - oy) * scale_y)

        img_x1 = max(0, min(img_x1, orig_w))
        img_y1 = max(0, min(img_y1, orig_h))
        img_x2 = max(0, min(img_x2, orig_w))
        img_y2 = max(0, min(img_y2, orig_h))

        if img_x2 > img_x1 and img_y2 > img_y1:
            page['crop_box'] = (img_x1, img_y1, img_x2, img_y2)

    def execute_crop(self, refresh_callback=None):
        """Executa o corte físico imediato mapeando corretamente a caixa do canvas para a imagem original"""
        if self.master and hasattr(self.master, 'get_current_page'):
            page = self.master.get_current_page()
            if not page:
                return False
            
            if self.current_rect:
                self._update_page_crop_box()
            
            crop_box = page.get('crop_box')
            if not crop_box:
                return False

            rx1, ry1, rx2, ry2 = crop_box

            if 'image' in page and isinstance(page['image'], Image.Image):
                try:
                    img_orig = page['image']
                    orig_w, orig_h = img_orig.size

                    img_x1 = max(0, min(rx1, orig_w))
                    img_y1 = max(0, min(ry1, orig_h))
                    img_x2 = max(0, min(rx2, orig_w))
                    img_y2 = max(0, min(ry2, orig_h))

                    if img_x2 > img_x1 and img_y2 > img_y1:
                        page['image'] = img_orig.crop((img_x1, img_y1, img_x2, img_y2))
                        page['marked_for_cut'] = True
                        if 'crop_box' in page:
                            del page['crop_box']
                    else:
                        return False

                except Exception as e:
                    print(f"Erro ao executar o corte da imagem: {e}")
                    return False

            self.exit_crop_mode()
            
            if refresh_callback:
                refresh_callback()
            return True
            
        return False

    def remove_crop(self, refresh_callback=None):
        """Remove a marcação de corte atual da página e da tela"""
        if self.master and hasattr(self.master, 'get_current_page'):
            page = self.master.get_current_page()
            if page:
                if 'crop_box' in page:
                    del page['crop_box']
                page['marked_for_cut'] = False
                
        self.exit_crop_mode()
        if refresh_callback:
            refresh_callback()