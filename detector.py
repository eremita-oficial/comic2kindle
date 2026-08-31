"""
Detecção automática de painéis em HQs usando OpenCV
Suporte a quatro métodos: Padrão, Eren Çakar, Halford e IA (YOLO)
"""

import cv2
import numpy as np
from PIL import Image
import math
import os
from typing import List, Tuple, Optional

class PanelDetector:
    """Detector de painéis usando processamento de imagem e IA"""
    
    def __init__(self):
        self.sensitivity = 0.5
        self.min_panel_area = 5000
        self.max_panel_area = 1000000
        self.binary_threshold = 127
        self.reading_direction = 'ltr'  # 'ltr' ou 'rtl'
        self.ai_model = None
        self.ai_model_path = "best.pt"
        
    def _load_ai_model(self):
        """Carrega o modelo de IA sob demanda"""
        if self.ai_model is None:
            try:
                from ultralytics import YOLO
                if os.path.exists(self.ai_model_path):
                    print("🧠 Carregando modelo de IA...")
                    self.ai_model = YOLO(self.ai_model_path)
                    print("✅ Modelo de IA carregado com sucesso!")
                else:
                    print(f"⚠️ Modelo de IA não encontrado: {self.ai_model_path}")
                    return False
            except ImportError:
                print("⚠️ Biblioteca ultralytics não instalada. Execute: pip install ultralytics")
                return False
            except Exception as e:
                print(f"⚠️ Erro ao carregar modelo de IA: {e}")
                return False
        return True
        
    def detect_panels(self, image: Image.Image, is_cover: bool = False, method: str = 'standard') -> List[List[int]]:
        """
        Detecta painéis em uma imagem usando o método especificado
        
        Args:
            image: Imagem PIL
            is_cover: Se True, retorna a página inteira como um único painel
            method: 'standard', 'eren', 'halford' ou 'ai'
            
        Returns:
            Lista de painéis no formato [x1, y1, x2, y2]
        """
        # Se for capa, retorna a página inteira
        if is_cover:
            width, height = image.size
            return [[0, 0, width, height]]
        
        try:
            if method == 'ai':
                panels = self.detect_panels_ai(image)
                if not panels or len(panels) < 2:
                    print("⚠️ IA não encontrou painéis. Usando método Padrão como fallback.")
                    return self.detect_panels_standard(image)
                return panels
            elif method == 'eren':
                panels = self.detect_panels_eren(image)
                if not panels or len(panels) < 2:
                    print("⚠️ Método Eren Çakar não encontrou painéis. Usando método Padrão como fallback.")
                    return self.detect_panels_standard(image)
                return panels
            elif method == 'halford':
                panels = self.detect_panels_halford(image)
                if not panels or len(panels) < 2:
                    print("⚠️ Método Halford não encontrou painéis. Usando método Padrão como fallback.")
                    return self.detect_panels_standard(image)
                return panels
            else:
                return self.detect_panels_standard(image)
        except Exception as e:
            print(f"⚠️ Erro no método {method}: {e}. Usando método Padrão como fallback.")
            return self.detect_panels_standard(image)
    
    def detect_panels_ai(self, image: Image.Image) -> List[List[int]]:
        """
        Método IA: usa modelo YOLO treinado para detecção de painéis
        """
        # Carrega o modelo
        if not self._load_ai_model():
            return []
        
        try:
            # Converte PIL para formato aceito pelo YOLO
            img_array = np.array(image)
            
            # Executa a predição
            results = self.ai_model.predict(source=img_array, conf=0.25, iou=0.7, verbose=False)
            
            # Extrai as bounding boxes
            panels = []
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = box.conf[0].item()
                # Filtra por confiança mínima
                if confidence > 0.3:
                    panels.append([int(x1), int(y1), int(x2), int(y2)])
            
            # Se não encontrou nada, retorna vazio
            if not panels:
                return []
            
            # Ordena os painéis
            panels = self.sort_panels(panels)
            
            # Refina os painéis (remove sobreposições)
            panels = self.refine_panels(panels, image.size)
            
            print(f"🧠 IA detectou {len(panels)} painéis")
            return panels
            
        except Exception as e:
            print(f"⚠️ Erro na detecção por IA: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def detect_panels_standard(self, image: Image.Image) -> List[List[int]]:
        """
        Método padrão: baseado em contornos e binarização
        """
        # Converte PIL para OpenCV
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Pré-processamento
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Binarização adaptativa
        binary = self.adaptive_threshold(gray)
        
        # Remoção de ruído
        denoised = self.remove_noise(binary)
        
        # Detecção de contornos
        contours = self.find_contours(denoised)
        
        # Filtragem de contornos
        filtered = self.filter_contours(contours, img_bgr.shape)
        
        # Ordenação dos painéis
        panels = self.sort_panels(filtered)
        
        # Ajuste fino
        panels = self.refine_panels(panels, img_bgr.shape)
        
        return panels
    
    def detect_panels_eren(self, image: Image.Image) -> List[List[int]]:
        """
        Método Eren Çakar: baseado em detecção de linhas e gutters
        """
        # Converte PIL para OpenCV
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        height, width = img_bgr.shape[:2]
        
        # Estratégia 1: Detecção de linhas com Hough
        panels = self._detect_panels_hough(img_bgr, height, width)
        if panels and len(panels) >= 2:
            return panels
        
        # Estratégia 2: Detecção de bordas com projeção
        panels = self._detect_panels_projection(img_bgr, height, width)
        if panels and len(panels) >= 2:
            return panels
        
        # Estratégia 3: Divisão por grid adaptativo
        panels = self._detect_panels_grid(img_bgr, height, width)
        if panels and len(panels) >= 2:
            return panels
        
        return []
    
    def detect_panels_halford(self, image: Image.Image) -> List[List[int]]:
        """
        Método Halford: baseado em detecção de bordas Canny + dilatação + agrupamento por sobreposição
        """
        # Converte PIL para OpenCV
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        height, width = img_bgr.shape[:2]
        img_area = height * width
        
        # 1. Converte para escala de cinza
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # 2. Aplica detector Canny
        edges = cv2.Canny(gray, 30, 100, apertureSize=3)
        
        # 3. Dilatação para engrossar as bordas (2 iterações)
        kernel = np.ones((3, 3), np.uint8)
        thick_edges = cv2.dilate(edges, kernel, iterations=2)
        
        # 4. Preenchimento de buracos (binary_fill_holes)
        inverted = cv2.bitwise_not(thick_edges)
        filled = self._binary_fill_holes(inverted)
        filled = cv2.bitwise_not(filled)
        
        # 5. Encontra contornos das áreas preenchidas
        contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 6. Cria bounding boxes a partir dos contornos
        bboxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area > 0.005 * img_area:
                bboxes.append([x, y, x + w, y + h])
        
        # 7. Agrupa bounding boxes que se sobrepõem
        panels = self._group_overlapping_bboxes(bboxes)
        
        # 8. Remove painéis muito pequenos
        panels = [p for p in panels if (p[2] - p[0]) * (p[3] - p[1]) > self.min_panel_area]
        
        # 9. Ordena painéis recursivamente (algoritmo do Halford)
        panels = self._sort_panels_halford(panels)
        
        return panels
    
    def _binary_fill_holes(self, image: np.ndarray) -> np.ndarray:
        """Preenche buracos em uma imagem binária usando OpenCV"""
        contours, hierarchy = cv2.findContours(image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        
        if hierarchy is None:
            return image
        
        result = image.copy()
        for i, cnt in enumerate(contours):
            if hierarchy[0][i][3] != -1:
                cv2.drawContours(result, [cnt], -1, 255, -1)
        
        return result
    
    def _group_overlapping_bboxes(self, bboxes: List[List[int]]) -> List[List[int]]:
        """Agrupa bounding boxes que se sobrepõem"""
        if not bboxes:
            return []
        
        def do_overlap(a, b):
            return (a[0] < b[2] and a[2] > b[0] and
                    a[1] < b[3] and a[3] > b[1])
        
        def merge(a, b):
            return [min(a[0], b[0]), min(a[1], b[1]),
                    max(a[2], b[2]), max(a[3], b[3])]
        
        grouped = []
        for bbox in bboxes:
            merged = False
            for i, group in enumerate(grouped):
                if do_overlap(bbox, group):
                    grouped[i] = merge(group, bbox)
                    merged = True
                    break
            if not merged:
                grouped.append(bbox)
        
        changed = True
        while changed:
            changed = False
            new_grouped = []
            for bbox in grouped:
                merged = False
                for i, group in enumerate(new_grouped):
                    if do_overlap(bbox, group):
                        new_grouped[i] = merge(group, bbox)
                        merged = True
                        changed = True
                        break
                if not merged:
                    new_grouped.append(bbox)
            grouped = new_grouped
        
        return grouped
    
    def _sort_panels_halford(self, panels: List[List[int]]) -> List[List[int]]:
        """Ordena painéis usando o algoritmo recursivo do Halford"""
        if not panels or len(panels) <= 1:
            return panels
        
        def are_aligned(a, b, axis):
            return (a[0 + axis] < b[2 + axis] and
                    b[0 + axis] < a[2 + axis])
        
        def cluster_bboxes(bboxes, axis=0):
            if not bboxes:
                return []
            
            clusters = []
            
            for bbox in bboxes:
                found = False
                for cluster in clusters:
                    if any(are_aligned(b, bbox, axis=axis) for b in cluster):
                        cluster.append(bbox)
                        found = True
                        break
                if not found:
                    clusters.append([bbox])
            
            clusters.sort(key=lambda c: c[0][0 + axis])
            
            for i, cluster in enumerate(clusters):
                if len(cluster) > 1:
                    clusters[i] = cluster_bboxes(
                        bboxes=cluster,
                        axis=1 if axis == 0 else 0
                    )
            
            return clusters
        
        def flatten(l):
            for el in l:
                if isinstance(el, list):
                    yield from flatten(el)
                else:
                    yield el
        
        clustered = cluster_bboxes(panels)
        return list(flatten(clustered))
    
    def _detect_panels_hough(self, img_bgr, height, width):
        """Estratégia 1: Usa Transformada de Hough para detectar linhas"""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, 
                                minLineLength=30, maxLineGap=15)
        
        if lines is None:
            return []
        
        horizontal_lines = []
        vertical_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.atan2(y2 - y1, x2 - x1) * 180 / np.pi
            
            if abs(angle) < 15 or abs(abs(angle) - 180) < 15:
                horizontal_lines.append((x1, y1, x2, y2))
            elif abs(abs(angle) - 90) < 15:
                vertical_lines.append((x1, y1, x2, y2))
        
        h_lines = self._group_lines(horizontal_lines, axis='horizontal', threshold=15)
        v_lines = self._group_lines(vertical_lines, axis='vertical', threshold=15)
        
        if len(h_lines) < 2 and len(v_lines) < 2:
            return []
        
        return self._create_panels_from_lines(h_lines, v_lines, width, height)
    
    def _detect_panels_projection(self, img_bgr, height, width):
        """Estratégia 2: Usa projeção de bordas para detectar gutters"""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        h_projection = np.sum(binary, axis=1)
        v_projection = np.sum(binary, axis=0)
        
        h_gutters = []
        v_gutters = []
        
        threshold_h = np.max(h_projection) * 0.3
        for i in range(1, len(h_projection) - 1):
            if h_projection[i] < threshold_h:
                h_gutters.append(i)
        
        threshold_v = np.max(v_projection) * 0.3
        for i in range(1, len(v_projection) - 1):
            if v_projection[i] < threshold_v:
                v_gutters.append(i)
        
        h_gutters = self._group_gutters(h_gutters, threshold=20)
        v_gutters = self._group_gutters(v_gutters, threshold=20)
        
        if len(h_gutters) < 2 and len(v_gutters) < 2:
            return []
        
        return self._create_panels_from_gutters(h_gutters, v_gutters, width, height)
    
    def _detect_panels_grid(self, img_bgr, height, width):
        """Estratégia 3: Divide a imagem em grid baseado na área"""
        image_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        panels = self.detect_panels_standard(image_pil)
        
        if panels and len(panels) >= 2:
            return panels
        
        aspect_ratio = width / height
        
        if aspect_ratio > 1.2:
            cols = 2
            rows = 1
        elif aspect_ratio < 0.8:
            cols = 1
            rows = 2
        else:
            cols = 2
            rows = 2
        
        panel_width = width // cols
        panel_height = height // rows
        
        panels = []
        for r in range(rows):
            for c in range(cols):
                x1 = c * panel_width
                y1 = r * panel_height
                x2 = x1 + panel_width
                y2 = y1 + panel_height
                panels.append([x1, y1, x2, y2])
        
        return panels
    
    def _group_lines(self, lines, axis='horizontal', threshold=20):
        """Agrupa linhas próximas"""
        if not lines:
            return []
        
        if axis == 'horizontal':
            lines_sorted = sorted(lines, key=lambda l: (l[1] + l[3]) / 2)
        else:
            lines_sorted = sorted(lines, key=lambda l: (l[0] + l[2]) / 2)
        
        grouped = []
        current_group = [lines_sorted[0]]
        
        for line in lines_sorted[1:]:
            if axis == 'horizontal':
                current_avg = sum((l[1] + l[3]) / 2 for l in current_group) / len(current_group)
                line_avg = (line[1] + line[3]) / 2
            else:
                current_avg = sum((l[0] + l[2]) / 2 for l in current_group) / len(current_group)
                line_avg = (line[0] + line[2]) / 2
            
            if abs(line_avg - current_avg) < threshold:
                current_group.append(line)
            else:
                if axis == 'horizontal':
                    avg_y = sum((l[1] + l[3]) / 2 for l in current_group) / len(current_group)
                    grouped.append(avg_y)
                else:
                    avg_x = sum((l[0] + l[2]) / 2 for l in current_group) / len(current_group)
                    grouped.append(avg_x)
                current_group = [line]
        
        if current_group:
            if axis == 'horizontal':
                avg_y = sum((l[1] + l[3]) / 2 for l in current_group) / len(current_group)
                grouped.append(avg_y)
            else:
                avg_x = sum((l[0] + l[2]) / 2 for l in current_group) / len(current_group)
                grouped.append(avg_x)
        
        return grouped
    
    def _group_gutters(self, gutters, threshold=20):
        """Agrupa gutters próximos"""
        if not gutters:
            return []
        
        gutters_sorted = sorted(gutters)
        grouped = []
        current_group = [gutters_sorted[0]]
        
        for g in gutters_sorted[1:]:
            if g - current_group[-1] < threshold:
                current_group.append(g)
            else:
                grouped.append(int(sum(current_group) / len(current_group)))
                current_group = [g]
        
        if current_group:
            grouped.append(int(sum(current_group) / len(current_group)))
        
        return grouped
    
    def _create_panels_from_lines(self, h_lines, v_lines, width, height):
        """Cria painéis a partir das linhas detectadas"""
        panels = []
        
        h_lines = [0] + h_lines + [height]
        v_lines = [0] + v_lines + [width]
        
        for i in range(len(h_lines) - 1):
            for j in range(len(v_lines) - 1):
                x1 = int(v_lines[j])
                y1 = int(h_lines[i])
                x2 = int(v_lines[j + 1])
                y2 = int(h_lines[i + 1])
                
                if x2 - x1 > 20 and y2 - y1 > 20:
                    panels.append([x1, y1, x2, y2])
        
        return panels
    
    def _create_panels_from_gutters(self, h_gutters, v_gutters, width, height):
        """Cria painéis a partir dos gutters detectados"""
        panels = []
        
        h_gutters = [0] + h_gutters + [height]
        v_gutters = [0] + v_gutters + [width]
        
        for i in range(len(h_gutters) - 1):
            for j in range(len(v_gutters) - 1):
                x1 = int(v_gutters[j])
                y1 = int(h_gutters[i])
                x2 = int(v_gutters[j + 1])
                y2 = int(h_gutters[i + 1])
                
                if x2 - x1 > 20 and y2 - y1 > 20:
                    panels.append([x1, y1, x2, y2])
        
        return panels
    
    def adaptive_threshold(self, gray: np.ndarray) -> np.ndarray:
        """Aplica threshold adaptativo"""
        if self.sensitivity > 0.7:
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV, 11, 2
            )
        else:
            _, binary = cv2.threshold(
                gray, 0, 255, 
                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
        
        return binary
    
    def remove_noise(self, binary: np.ndarray) -> np.ndarray:
        """Remove ruído da imagem binária"""
        kernel = np.ones((3, 3), np.uint8)
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)
        return opened
    
    def find_contours(self, binary: np.ndarray) -> List[np.ndarray]:
        """Encontra contornos na imagem binária"""
        contours, _ = cv2.findContours(
            binary, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        min_area = self.min_panel_area * (1 - self.sensitivity * 0.5)
        filtered = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
        
        return filtered
    
    def filter_contours(self, contours: List[np.ndarray], 
                        shape: Tuple[int, int]) -> List[List[int]]:
        """Filtra e converte contornos para retângulos"""
        height, width = shape[:2]
        panels = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w < 20 or h < 20:
                continue
            
            area = w * h
            if area < self.min_panel_area or area > self.max_panel_area:
                continue
            
            aspect_ratio = w / h
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                continue
            
            expand = int(min(w, h) * 0.02)
            x1 = max(0, x - expand)
            y1 = max(0, y - expand)
            x2 = min(width, x + w + expand)
            y2 = min(height, y + h + expand)
            
            panels.append([x1, y1, x2, y2])
        
        return panels
    
    def sort_panels(self, panels: List[List[int]]) -> List[List[int]]:
        """Ordena painéis em ordem de leitura usando algoritmo de linhas"""
        if not panels:
            return panels
        
        if len(panels) <= 1:
            return panels
        
        rows = self._group_into_rows(panels)
        
        sorted_panels = []
        for row in rows:
            if self.reading_direction == 'ltr':
                row.sort(key=lambda p: p[0])
            else:
                row.sort(key=lambda p: -p[0])
            sorted_panels.extend(row)
        
        return sorted_panels
    
    def _group_into_rows(self, panels: List[List[int]]) -> List[List[List[int]]]:
        """Agrupa painéis em linhas baseado na sobreposição vertical"""
        if not panels:
            return []
        
        sorted_by_y = sorted(panels, key=lambda p: p[1])
        
        rows = []
        current_row = [sorted_by_y[0]]
        
        for panel in sorted_by_y[1:]:
            panel_center_y = (panel[1] + panel[3]) / 2
            
            avg_top = sum(p[1] for p in current_row) / len(current_row)
            avg_bottom = sum(p[3] for p in current_row) / len(current_row)
            
            if avg_top <= panel_center_y <= avg_bottom:
                current_row.append(panel)
            else:
                rows.append(current_row)
                current_row = [panel]
        
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def refine_panels(self, panels: List[List[int]], 
                      shape: Tuple[int, int]) -> List[List[int]]:
        """Refina os painéis detectados"""
        if len(panels) <= 1:
            return panels
        
        refined = []
        for panel in panels:
            overlap = False
            for existing in refined:
                if self.calculate_overlap(panel, existing) > 0.7:
                    if self.calculate_area(panel) > self.calculate_area(existing):
                        refined.remove(existing)
                        refined.append(panel)
                    overlap = True
                    break
            
            if not overlap:
                refined.append(panel)
        
        return refined
    
    def calculate_overlap(self, rect1: List[int], rect2: List[int]) -> float:
        """Calcula a sobreposição entre dois retângulos"""
        x1 = max(rect1[0], rect2[0])
        y1 = max(rect1[1], rect2[1])
        x2 = min(rect1[2], rect2[2])
        y2 = min(rect1[3], rect2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = self.calculate_area(rect1)
        area2 = self.calculate_area(rect2)
        
        return intersection / min(area1, area2)
    
    def calculate_area(self, rect: List[int]) -> float:
        """Calcula a área de um retângulo"""
        return (rect[2] - rect[0]) * (rect[3] - rect[1])
    
    def set_sensitivity(self, value: float):
        """Ajusta a sensibilidade da detecção (0.0 - 1.0)"""
        self.sensitivity = max(0.0, min(1.0, value))
    
    def set_reading_direction(self, direction: str):
        """Define a direção de leitura"""
        if direction in ['ltr', 'rtl']:
            self.reading_direction = direction
    
    def set_min_panel_area(self, area: int):
        """Define a área mínima de um painel"""
        self.min_panel_area = max(100, area)
    
    def set_max_panel_area(self, area: int):
        """Define a área máxima de um painel"""
        self.max_panel_area = min(10000000, area)
