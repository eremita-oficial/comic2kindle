#!/usr/bin/env python3
"""
Interface gráfica principal - comic2kindle
Com suporte a troca dinâmica de idioma via menu dedicado
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
import sys
import configparser
from pathlib import Path
import traceback
import glob
from config import *
from importer import Importer
from canvas_editor import CanvasEditor
from detector import PanelDetector
from project import ProjectManager
from exporter import Exporter
from progress_dialog import ProgressDialog


class TranslationManager:
    """Gerenciador de traduções baseado em arquivos .ini"""
    
    def __init__(self, lang_folder="lang", default_lang="English"):
        self.lang_folder = lang_folder
        self.current_lang = default_lang
        # interpolation=None evita erros com '%' literal nos arquivos .ini
        self.config = configparser.ConfigParser(interpolation=None)
        self.load_language(default_lang)
        
    def load_language(self, lang_name):
        """Carrega um arquivo de idioma baseado no nome do arquivo (ex: English, Portuguese_brazilian)"""
        file_candidates = [lang_name]
        if lang_name.lower() in ["english", "en"]:
            file_candidates = ["English", "english"]
        elif lang_name.lower() in ["português-br", "portuguese_brazilian", "portuguese-br"]:
            file_candidates = ["Portuguese_brazilian", "Portuguese-BR", "portuguese_brazilian"]

        loaded = False
        for candidate in file_candidates:
            lang_file = os.path.join(self.lang_folder, f"{candidate}.ini")
            if os.path.exists(lang_file):
                self.config.read(lang_file, encoding='utf-8')
                self.current_lang = candidate
                loaded = True
                break
        
        if not loaded:
            lang_file = os.path.join(self.lang_folder, "English.ini")
            if os.path.exists(lang_file):
                self.config.read(lang_file, encoding='utf-8')
                self.current_lang = "English"
                loaded = True
            else:
                if os.path.exists(self.lang_folder):
                    inifiles = [f.replace('.ini', '') for f in os.listdir(self.lang_folder) if f.endswith('.ini')]
                    if inifiles:
                        fallback_file = os.path.join(self.lang_folder, f"{inifiles[0]}.ini")
                        self.config.read(fallback_file, encoding='utf-8')
                        self.current_lang = inifiles[0]
                        loaded = True
                        
        return loaded
            
    def get(self, section, key, fallback="", *args):
        """Obtém uma string traduzida com formatação opcional"""
        try:
            text = self.config.get(section, key)
            if args:
                return text.format(*args)
            return text
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback if not args else fallback.format(*args)
            
    def get_available_languages(self):
        """Lista nomes amigáveis e técnicos dos idiomas disponíveis na pasta lang"""
        langs = []
        if os.path.exists(self.lang_folder):
            for f in sorted(os.listdir(self.lang_folder)):
                if f.endswith('.ini'):
                    filename = f.replace('.ini', '')
                    if filename.lower() in ["portuguese_brazilian", "portuguese-br"]:
                        display_name = "Português-BR"
                    elif filename.lower() in ["english"]:
                        display_name = "English"
                    else:
                        display_name = filename.capitalize()
                    langs.append((display_name, filename))
        return langs


class MetadataDialog(tk.simpledialog.Dialog):
    """Janela personalizada para inserir Título e Autor"""
    def __init__(self, parent, title=None, initial_title="", tr=None):
        self.initial_title = initial_title
        self.tr = tr
        super().__init__(parent, title=title)

    def body(self, master):
        lbl_title = self.tr.get("Metadata", "lbl_title", "Title:") if self.tr else "Title:"
        lbl_author = self.tr.get("Metadata", "lbl_author", "Author:") if self.tr else "Author:"
        
        ttk.Label(master, text=lbl_title).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Label(master, text=lbl_author).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.e_title = ttk.Entry(master, width=35)
        self.e_author = ttk.Entry(master, width=35)
        
        self.e_title.grid(row=0, column=1, padx=5, pady=5)
        self.e_author.grid(row=1, column=1, padx=5, pady=5)
        
        if self.initial_title:
            self.e_title.insert(0, self.initial_title)
            
        return self.e_title

    def apply(self):
        self.result = (self.e_title.get().strip(), self.e_author.get().strip())


class KindlePanelCreator:
    """Aplicação principal"""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("comic2kindle - v1.0.1")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(800, 600)
        
        if "APPDIR" in os.environ:
            self.base_dir = Path(os.environ["APPDIR"])
        else:
            self.base_dir = Path(__file__).resolve().parent

        self.user_config_dir = Path.home() / ".config" / "comic2kindle"
        self.user_lang_dir = self.user_config_dir / "lang"
        
        try:
            self.user_config_dir.mkdir(parents=True, exist_ok=True)
            self.user_lang_dir.mkdir(parents=True, exist_ok=True)
            self._ensure_default_language_files()
        except Exception as e:
            print(f"⚠️ Could not create user config directory or language files: {e}")

        self.lang_dir = self.user_lang_dir

        self.config_file = self.user_config_dir / "comic2kindle.ini"
        
        initial_lang = "English"
        if not self.config_file.exists():
            try:
                self.config_file.write_text("English", encoding="utf-8")
            except Exception as e:
                print(f"⚠️ Could not create config file: {e}")
        else:
            try:
                saved_config = self.config_file.read_text(encoding="utf-8").strip()
                if saved_config:
                    initial_lang = saved_config 
            except Exception as e:
                print(f"⚠️ Error reading config file: {e}")

        self.tr = TranslationManager(lang_folder=str(self.lang_dir), default_lang=initial_lang)
        self.importer = Importer()
        self.detector = PanelDetector()
        
        self.current_page = 0
        self.zoom_level = 1.0
        self.project_file = None
        
        self.create_menu()
        self.create_toolbar()
        self.create_layout()
        self.create_status_bar()
        
        self.canvas_editor_manager = CanvasEditor(self.canvas_editor, self)
        self.setup_keyboard_shortcuts()
        
        self.update_status()

    def _ensure_default_language_files(self):
        """Cria os arquivos .ini padrão na pasta de configuração do usuário se não existirem"""
        english_ini = self.user_lang_dir / "English.ini"
        if not english_ini.exists():
            english_content = """[Menu_File]
label = File
open_folder = Open image folder
open_cbr = Open CBR
open_cbz = Open CBZ
save_full = Save Full Project
save_light = Save Project (Light)
open_project = Open project
export_full_std = Export PDF (Full Pages) - Standard file size
export_full_light = Export PDF (Full Pages Light) - Min. file size
export_split_std = Export PDF (3 Panels) - Standard file size
export_split_light = Export PDF (3 Panels Light) - Min. file size
exit = Exit

[Menu_Edit]
label = Edit
auto_trim = Detect Margins (Auto-Trim)
percent_trim = Detect Margins (%)
remove_marking = Remove Margin Markings
cut_margins = Cut Margins [Del]
mark_cut = Mark Page for Cutting
cut_page = Cut Page
unmark_cut = Remove Cut Marking
remove_page = Remove Page [Ctrl+Del]
remove_specific = Remove Specific Pages
mark_cover = Mark as Cover
mark_full = Mark as Full Page

[Menu_View]
label = View
zoom_in = Zoom In +
zoom_out = Zoom Out -
fit_height = Fit to Height
zoom_100 = Zoom 100%
prev_page = Previous Page
next_page = Next Page

[Menu_Help]
label = Help
language = Language
about = About
about_desc = comic2kindle v1.0.1\\nComic to PDF converter.
shortcuts = Keyboard Shortcuts
shortcuts_text = 📋 KEYBOARD SHORTCUTS\\n    ← / →          Previous / next page\\n    Ctrl+O         Open Folder / CBR / CBZ\\n    Ctrl+S         Save Project (Full)\\n    Ctrl+Shift+S   Save Project (Light)\\n    Ctrl+Shift+O   Open Project\\n    ESC            Remove cut mark\\n    Del            Cut margins\\n    Ctrl+Delete    Remove current page\\n    Ctrl++/-       Zoom\\n    Ctrl+0         Fit to height\\n    Ctrl+9         Zoom 100%\\n    Ctrl+Q         Quit
close = Close
language_changed = Language changed successfully!

[Toolbar]
fit = Fit

[Status]
ready = Ready
loading_folder = Loading folder {}...
no_images_folder = No images found in folder.
loaded_images = Loaded {} images.
error_loading = Error loading images: {}
loading_cbr = Loading CBR...
no_images_cbr = No images found in CBR.
loaded_cbr = Loaded {} images from CBR.
error_cbr = Error loading CBR: {}
loading_cbz = Loading CBZ...
no_images_cbz = No images found in CBZ.
loaded_cbz = Loaded {} images from CBZ.
error_cbz = Error loading CBZ: {}
page_removed = Page {} removed.
saving = Saving project...
saved = Project saved: {}
error_saving = Error saving project.
opening = Opening project...
opened = Project opened: {}
error_opening = Error opening project.
exporting = Exporting PDF ({}) ...
success_export = PDF ({}) successfully exported to:\\n{}
error_export = Error exporting PDF.
no_doc = Ready - No document loaded

[Dialogs]
capa_msg = Keep cover as full page?
warn_no_pages = No pages loaded.
warn_no_project = No project loaded.
confirm_remove_page = Remove page {} of {}?
remove_pages_prompt = Pages to remove (Total: {}):\\nEx: 1,3,5-10
remove_pages_title = Remove Pages
confirm_remove_pages = Remove {} page(s)?
pages_removed = {} page(s) removed successfully.

[Metadata]
title = Insert metadata
lbl_title = Title:
lbl_author = Author:
"""
            try:
                english_ini.write_text(english_content, encoding="utf-8")
            except Exception as e:
                print(f"⚠️ Could not create default English.ini: {e}")

        pt_ini = self.user_lang_dir / "Portuguese_brazilian.ini"
        if not pt_ini.exists():
            pt_content = """[Menu_File]
label = Arquivo
open_folder = Abrir pasta de imagens
open_cbr = Abrir CBR
open_cbz = Abrir CBZ
save_full = Salvar Projeto Completo
save_light = Salvar Projeto (Leve)
open_project = Abrir projeto
export_full_std = Exportar PDF (Páginas Inteiras) - Arq. padrão
export_full_light = Exportar PDF (Páginas Inteiras Light) - Arq. Menor
export_split_std = Exportar PDF (3 Painéis) - Arq. Padrão
export_split_light = Exportar PDF (3 Painéis Light) - Arq. Menor
exit = Sair

[Menu_Edit]
label = Editar
auto_trim = Detectar Margens (Auto-Trim)
percent_trim = Detectar Margens (%)
remove_marking = Remover Marcações de Margem
cut_margins = Cortar Margens [Del]
mark_cut = Marcar Página para Corte
cut_page = Cortar Página
unmark_cut = Remover Marcação de Corte
remove_page = Remover Página [Ctrl+Del]
remove_specific = Remover Páginas Específicas
mark_cover = Marcar como Capa
mark_full = Marcar como Página Inteira

[Menu_View]
label = Visualizar
zoom_in = Ampliar +
zoom_out = Reduzir -
fit_height = Ajustar à Altura
zoom_100 = Zoom 100%
prev_page = Página Anterior
next_page = Próxima Página

[Menu_Help]
label = Ajuda
language = Idioma
about = Sobre
about_desc = comic2kindle v1.0.1\\nConversor de Quadrinhos para PDF.
shortcuts = Atalhos de Teclado
shortcuts_text = 📋 ATALHOS DE TECLADO\\n    ← / →          Página anterior / próxima\\n    Ctrl+O         Abrir Pasta / CBR / CBZ\\n    Ctrl+S         Salvar Projeto (Completo)\\n    Ctrl+Shift+S   Salvar Projeto (Leve)\\n    Ctrl+Shift+O   Open Project\\n    ESC            Remover marca de corte\\n    Del            Cortar margens\\n    Ctrl+Delete    Remover página atual\\n    Ctrl++/-       Zoom\\n    Ctrl+0         Ajustar à altura\\n    Ctrl+9         Zoom 100%\\n    Ctrl+Q         Sair
close = Fechar
language_changed = Idioma alterado com sucesso!

[Toolbar]
fit = Ajustar

[Status]
ready = Pronto
loading_folder = Carregando pasta {}...
no_images_folder = Nenhuma imagem encontrada na pasta.
loaded_images = {} imagens carregadas.
error_loading = Erro ao carregar imagens: {}
loading_cbr = Carregando CBR...
no_images_cbr = Nenhuma imagem encontrada no CBR.
loaded_cbr = {} imagens carregadas do CBR.
error_cbr = Erro ao carregar CBR: {}
loading_cbz = Carregando CBZ...
no_images_cbz = Nenhuma imagem encontrada no CBZ.
loaded_cbz = {} imagens carregadas do CBZ.
error_cbz = Erro ao carregar CBZ: {}
page_removed = Página {} removida.
saving = Salvando projeto...
saved = Projeto salvo: {}
error_saving = Erro ao salvar projeto.
opening = Abrindo projeto...
opened = Projeto aberto: {}
error_opening = Erro ao abrir projeto.
exporting = Exportando PDF ({}) ...
success_export = PDF ({}) exportado com sucesso para:\\n{}
error_export = Erro ao exportar PDF.
no_doc = Pronto - Nenhum documento carregado

[Dialogs]
capa_msg = Manter capa como página inteira?
warn_no_pages = Nenhuma página carregada.
warn_no_project = Nenhum projeto carregado.
confirm_remove_page = Remover página {} de {}?
remove_pages_prompt = Páginas para remover (Total: {}):\\nEx: 1,3,5-10
remove_pages_title = Remover Páginas
confirm_remove_pages = Remover {} página(s)?
pages_removed = {} página(s) removida(s) com sucesso.

[Metadata]
title = Inserir metadados
lbl_title = Título:
lbl_author = Autor:
"""
            try:
                pt_ini.write_text(pt_content, encoding="utf-8")
            except Exception as e:
                print(f"⚠️ Could not create default Portuguese_brazilian.ini: {e}")

    def change_language(self, lang_filename):
        """Troca o idioma, reconstrói a interface e salva o identificador real no arquivo .ini"""
        if self.tr.load_language(lang_filename):
            try:
                self.user_config_dir.mkdir(parents=True, exist_ok=True)
                self.config_file.write_text(lang_filename, encoding="utf-8")
            except Exception as e:
                print(f"⚠️ Error saving language to config file: {e}")

            self.root.config(menu="")  
            self.create_menu()         
            self.update_status()
            
            messagebox.showinfo(
                "Language", 
                self.tr.get("Menu_Help", "language_changed", "Language changed successfully!"),
                parent=self.root
            )
        else:
            messagebox.showerror("Error", f"Could not load language: {lang_filename}")

    def get_current_page(self):
        return self.importer.get_page(self.current_page)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr.get("Menu_File", "label", "File"), menu=file_menu)
        file_menu.add_command(label=self.tr.get("Menu_File", "open_folder", "Open image folder"), command=self.open_folder)
        file_menu.add_command(label=self.tr.get("Menu_File", "open_cbr", "Open CBR"), command=self.open_cbr, accelerator="Ctrl+O")
        file_menu.add_command(label=self.tr.get("Menu_File", "open_cbz", "Open CBZ"), command=self.open_cbz)
        file_menu.add_separator()
        file_menu.add_command(label=self.tr.get("Menu_File", "save_full", "Save Full Project"), command=self.save_project_full, accelerator="Ctrl+S")
        file_menu.add_command(label=self.tr.get("Menu_File", "save_light", "Save Project (Light)"), command=self.save_project_light, accelerator="Ctrl+Shift+S")
        file_menu.add_command(label=self.tr.get("Menu_File", "open_project", "Open project"), command=self.open_project, accelerator="Ctrl+Shift+O")
        file_menu.add_separator()
        file_menu.add_command(label=self.tr.get("Menu_File", "export_full_std", "Export PDF (Full Pages) (Standard)"), 
                              command=lambda: self.export_pdf_pages_full(quality=95))
        file_menu.add_command(label=self.tr.get("Menu_File", "export_full_light", "Export PDF (Full Pages) (Light)"), 
                              command=lambda: self.export_pdf_pages_full(quality=80))
        file_menu.add_command(label=self.tr.get("Menu_File", "export_split_std", "Export PDF (3 Panels) (Standard)"), 
                              command=lambda: self.export_pdf_split(3, quality=95))
        file_menu.add_command(label=self.tr.get("Menu_File", "export_split_light", "Export PDF (3 Panels) (Light)"), 
                              command=lambda: self.export_pdf_split(3, quality=80))
        file_menu.add_separator()
        file_menu.add_command(label=self.tr.get("Menu_File", "exit", "Exit"), command=self.root.quit, accelerator="Ctrl+Q")

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr.get("Menu_Edit", "label", "Edit"), menu=edit_menu)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "auto_trim", "Detect Margins (Auto-Trim)"), command=self.detect_margins_auto_trim)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "percent_trim", "Detect Margins (%)"), command=self.detect_margins_percent)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "remove_marking", "Remove Margin Markings"), command=self.remove_margins_marking)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "cut_margins", "Cut Margins [Del]"), command=self.execute_cut_margins)
        edit_menu.add_separator()
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "mark_cut", "Mark Page for Cutting"), command=self.mark_for_cutting)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "cut_page", "Cut Page"), command=self.cut_page)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "unmark_cut", "Remove Cut Marking"), command=self.unmark_for_cutting)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "remove_page", "Remove Page [Ctrl+Del]"), command=self.remove_current_page)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "remove_specific", "Remove Specific Pages"), command=self.remove_specific_pages)
        edit_menu.add_separator()
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "mark_cover", "Mark as Cover"), command=self.mark_as_cover)
        edit_menu.add_command(label=self.tr.get("Menu_Edit", "mark_full", "Mark as Full Page"), command=self.mark_as_full_page)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr.get("Menu_View", "label", "View"), menu=view_menu)
        view_menu.add_command(label=self.tr.get("Menu_View", "zoom_in", "Zoom In +"), command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label=self.tr.get("Menu_View", "zoom_out", "Zoom Out -"), command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label=self.tr.get("Menu_View", "fit_height", "Fit to Height"), command=self.fit_to_height, accelerator="Ctrl+0")
        view_menu.add_command(label=self.tr.get("Menu_View", "zoom_100", "Zoom 100%"), command=self.zoom_reset, accelerator="Ctrl+9")
        view_menu.add_separator()
        view_menu.add_command(label=self.tr.get("Menu_View", "prev_page", "Previous Page"), command=self.prev_page, accelerator="←")
        view_menu.add_command(label=self.tr.get("Menu_View", "next_page", "Next Page"), command=self.next_page, accelerator="→")

        # Language Menu (Between View and Help)
        lang_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr.get("Menu_Help", "language", "Language"), menu=lang_menu)
        
        available_langs = self.tr.get_available_languages()
        for display_name, filename in available_langs:
            is_current = (filename.lower() == self.tr.current_lang.lower())
            prefix = "✓ " if is_current else ""
            lang_menu.add_command(
                label=f"{prefix}{display_name}", 
                command=lambda f=filename: self.change_language(f)
            )

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.tr.get("Menu_Help", "label", "Help"), menu=help_menu)
        help_menu.add_command(label=self.tr.get("Menu_Help", "about", "About"), command=self.show_about)
        help_menu.add_command(label=self.tr.get("Menu_Help", "shortcuts", "Keyboard Shortcuts"), command=self.show_shortcuts)

    def create_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        ttk.Button(toolbar, text="◀", command=self.prev_page, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="▶", command=self.next_page, width=3).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        ttk.Button(toolbar, text="🔍+", command=self.zoom_in, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="🔍-", command=self.zoom_out, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text=self.tr.get("Toolbar", "fit", "Fit"), command=self.fit_to_height, width=6).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="100%", command=self.zoom_reset, width=4).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        self.page_label = ttk.Label(toolbar, text="Page 0/0")
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.zoom_label = ttk.Label(toolbar, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=10)

    def create_layout(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_frame = ttk.Frame(main_frame, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        ttk.Label(left_frame, text="📚 Thumbnails", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        thumb_frame = ttk.Frame(left_frame)
        thumb_frame.pack(fill=tk.BOTH, expand=True)
        
        self.thumb_canvas = tk.Canvas(thumb_frame, bg='#f0f0f0', highlightthickness=0)
        thumb_scrollbar = ttk.Scrollbar(thumb_frame, orient=tk.VERTICAL, command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=thumb_scrollbar.set)
        
        thumb_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.thumb_inner = ttk.Frame(self.thumb_canvas)
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor=tk.NW)
        
        self.thumb_canvas.bind('<Configure>', self.on_thumb_configure)
        self.thumb_inner.bind('<Configure>', self.on_thumb_inner_configure)
        
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_container = ttk.Frame(center_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        canvas_h_scroll = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        canvas_v_scroll = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        
        self.canvas_editor = tk.Canvas(canvas_container, width=600, height=500, bg='#2b2b2b', 
                                     xscrollcommand=canvas_h_scroll.set, yscrollcommand=canvas_v_scroll.set,
                                     highlightthickness=0)
        
        canvas_h_scroll.config(command=self.canvas_editor.xview)
        canvas_v_scroll.config(command=self.canvas_editor.yview)
        
        self.canvas_editor.grid(row=0, column=0, sticky='nsew')
        canvas_h_scroll.grid(row=1, column=0, sticky='ew')
        canvas_v_scroll.grid(row=0, column=1, sticky='ns')
        
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        self.canvas_editor.bind('<Configure>', self.on_canvas_configure)

    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_frame, text=self.tr.get("Status", "ready", "Ready"), relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.page_info = ttk.Label(self.status_frame, text="Page 0/0", relief=tk.SUNKEN)
        self.page_info.pack(side=tk.RIGHT)

    def setup_keyboard_shortcuts(self):
        self.root.bind('<Control-o>', lambda e: self.open_folder())
        self.root.bind('<Control-O>', lambda e: self.open_folder())
        self.root.bind('<Control-s>', lambda e: self.save_project_full())
        self.root.bind('<Control-S>', lambda e: self.save_project_full())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_project_light())
        self.root.bind('<Control-Shift-O>', lambda e: self.open_project())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<Control-Q>', lambda e: self.root.quit())
        
        self.root.bind('<Left>', lambda e: self.prev_page())
        self.root.bind('<Right>', lambda e: self.next_page())
        
        self.root.bind('<Control-Delete>', lambda e: self.remove_current_page())
        self.root.bind('<Control-KeyPress-Delete>', lambda e: self.remove_current_page())
        
        self.root.bind('<Delete>', lambda e: self.execute_cut_margins())
        self.root.bind('<BackSpace>', lambda e: self.execute_cut_margins())
        self.root.bind('<Escape>', lambda e: self.unmark_for_cutting())
        
        self.canvas_editor.bind('<Button-1>', lambda e: self.canvas_editor_manager.on_mouse_down(e))
        self.canvas_editor.bind('<B1-Motion>', lambda e: self.canvas_editor_manager.on_mouse_drag(e))
        self.canvas_editor.bind('<ButtonRelease-1>', lambda e: self.canvas_editor_manager.on_mouse_up(e))
        
        self.root.bind('<Control-plus>', lambda e: self.zoom_in())
        self.root.bind('<Control-KP_Add>', lambda e: self.zoom_in())
        self.root.bind('<Control-equal>', lambda e: self.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.zoom_out())
        self.root.bind('<Control-KP_Subtract>', lambda e: self.zoom_out())
        self.root.bind('<Control-0>', lambda e: self.fit_to_height())
        self.root.bind('<Control-9>', lambda e: self.zoom_reset())

    def refresh_ui(self):
        self.update_display()
        self.update_thumbnails()
        self.update_status()

    def fit_to_height(self):
        page = self.importer.get_page(self.current_page)
        if not page: return
        
        img_width, img_height = page['image'].size
        canvas_height = self.canvas_editor.winfo_height()
        if canvas_height < 10: canvas_height = 500
            
        self.zoom_level = (canvas_height - 20) / img_height
        self.zoom_level = max(0.1, min(2.0, self.zoom_level))
        
        self.update_display()
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def on_canvas_configure(self, event): self.update_display()
    def on_thumb_configure(self, event): self.thumb_canvas.itemconfig(1, width=event.width)
    def on_thumb_inner_configure(self, event): self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))

    def go_to_page(self, index):
        if 0 <= index < len(self.importer.pages):
            self.canvas_editor_manager.exit_crop_mode()
            self.current_page = index
            self.update_display()
            self.update_thumbnails()

    def prev_page(self):
        if self.current_page > 0:
            self.canvas_editor_manager.exit_crop_mode()
            self.current_page -= 1
            self.update_display()
            self.update_thumbnails()

    def next_page(self):
        if self.current_page < len(self.importer.pages) - 1:
            self.canvas_editor_manager.exit_crop_mode()
            self.current_page += 1
            self.update_display()
            self.update_thumbnails()

    def zoom_in(self):
        self.zoom_level = min(2.0, self.zoom_level + 0.1)
        self.update_display()
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def zoom_out(self):
        self.zoom_level = max(0.1, self.zoom_level - 0.1)
        self.update_display()
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def zoom_reset(self):
        self.zoom_level = 1.0
        self.update_display()
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def open_folder(self):
        folder = filedialog.askdirectory(title=self.tr.get("Menu_File", "open_folder", "Select folder"))
        if not folder: return
        
        self.status_label.config(text=self.tr.get("Status", "loading_folder", "Loading...", folder))
        self.root.update()
        
        try:
            self.importer.pages = []
            pages = self.importer.load_images_from_folder(folder)
            
            self.importer.suggested_name = os.path.basename(folder)
            self.importer.source_dir = folder
            
            if len(pages) == 0:
                image_files = []
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
                    image_files.extend(glob.glob(os.path.join(folder, ext)))
                image_files = sorted(set(image_files))
                for img_path in image_files:
                    try:
                        img = Image.open(img_path)
                        if img.mode != 'RGB': img = img.convert('RGB')
                        self.importer.pages.append({
                            'path': str(img_path), 'image': img, 'panels': [],
                            'is_cover': False, 'is_full_page': False, 'marked_for_cut': False
                        })
                    except Exception as e: print(f"  ❌ Error: {e}")
                pages = self.importer.pages
                
            if len(pages) == 0:
                messagebox.showwarning("Warning", self.tr.get("Status", "no_images_folder", "No images found."))
                self.status_label.config(text=self.tr.get("Status", "no_images_folder", "No images found"))
                return
                
            self.current_page = 0
            self.fit_to_height()
            self.update_thumbnails()
            self.update_display()
            self.status_label.config(text=self.tr.get("Status", "loaded_images", "", len(self.importer.pages)))
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", self.tr.get("Status", "error_loading", "", str(e)))
            self.status_label.config(text=self.tr.get("Status", "error_loading", "", str(e)))

    def open_cbr(self):
        file_path = filedialog.askopenfilename(
            title=self.tr.get("Menu_File", "open_cbr", "Select CBR"),
            filetypes=[("Comic Book RAR", "*.cbr"), ("All files", "*.*")]
        )
        if file_path:
            self.status_label.config(text=self.tr.get("Status", "loading_cbr", "Loading CBR..."))
            self.root.update()
            try:
                self.importer.pages = []
                pages = self.importer.load_cbr(file_path)
                
                self.importer.suggested_name = Path(file_path).stem
                self.importer.source_dir = os.path.dirname(file_path)
                
                for p in self.importer.pages:
                    if 'marked_for_cut' not in p: p['marked_for_cut'] = False
                    if 'is_full_page' not in p: p['is_full_page'] = False
                    
                if len(pages) == 0:
                    messagebox.showwarning("Warning", self.tr.get("Status", "no_images_cbr", "No images in CBR."))
                    self.status_label.config(text=self.tr.get("Status", "no_images_cbr", "No images in CBR"))
                    return
                    
                self.current_page = 0
                self.fit_to_height()
                
                if messagebox.askyesno("Cover", self.tr.get("Dialogs", "capa_msg", "Keep cover as full page?")):
                    self.importer.set_cover(0, True)
                    
                self.update_thumbnails()
                self.update_display()
                self.status_label.config(text=self.tr.get("Status", "loaded_cbr", "", len(self.importer.pages)))
                
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Error", self.tr.get("Status", "error_cbr", "", str(e)))
                self.status_label.config(text=self.tr.get("Status", "error_cbr", "", str(e)))

    def open_cbz(self):
        file_path = filedialog.askopenfilename(
            title=self.tr.get("Menu_File", "open_cbz", "Select CBZ"),
            filetypes=[("Comic Book Zip", "*.cbz"), ("All files", "*.*")]
        )
        if file_path:
            self.status_label.config(text=self.tr.get("Status", "loading_cbz", "Loading CBZ..."))
            self.root.update()
            try:
                self.importer.pages = []
                pages = self.importer.load_cbz(file_path)
                
                self.importer.suggested_name = Path(file_path).stem
                self.importer.source_dir = os.path.dirname(file_path)
                
                for p in self.importer.pages:
                    if 'marked_for_cut' not in p: p['marked_for_cut'] = False
                    if 'is_full_page' not in p: p['is_full_page'] = False
                    
                if len(pages) == 0:
                    messagebox.showwarning("Warning", self.tr.get("Status", "no_images_cbz", "No images in CBZ."))
                    self.status_label.config(text=self.tr.get("Status", "no_images_cbz", "No images in CBZ"))
                    return
                    
                self.current_page = 0
                self.fit_to_height()
                
                if messagebox.askyesno("Cover", self.tr.get("Dialogs", "capa_msg", "Keep cover as full page?")):
                    self.importer.set_cover(0, True)
                    
                self.update_thumbnails()
                self.update_display()
                self.status_label.config(text=self.tr.get("Status", "loaded_cbz", "", len(self.importer.pages)))
                
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Error", self.tr.get("Status", "error_cbz", "", str(e)))
                self.status_label.config(text=self.tr.get("Status", "error_cbz", "", str(e)))

    def remove_current_page(self):
        if not self.importer.pages:
            messagebox.showinfo("Warning", self.tr.get("Dialogs", "warn_no_pages", "No pages"))
            return
        total = len(self.importer.pages)
        page_num = self.current_page + 1
        
        msg = self.tr.get("Dialogs", "confirm_remove_page", "Remove page {} of {}?", page_num, total)
        if not messagebox.askyesno("Confirm", msg, icon='warning'): return
            
        if self.importer.remove_page(self.current_page):
            if self.current_page >= len(self.importer.pages):
                self.current_page = len(self.importer.pages) - 1
            if self.current_page < 0: self.current_page = 0
            self.update_thumbnails()
            self.update_display()
            self.status_label.config(text=self.tr.get("Status", "page_removed", "", page_num))

    def remove_specific_pages(self):
        if not self.importer.pages:
            messagebox.showinfo("Warning", self.tr.get("Dialogs", "warn_no_pages", "No pages"))
            return
        total_pages = len(self.importer.pages)
        prompt = self.tr.get("Dialogs", "remove_pages_prompt", "Pages to remove (Total: {})", total_pages)
        title = self.tr.get("Dialogs", "remove_pages_title", "Remove Pages")
        
        res = simpledialog.askstring(title, prompt, initialvalue="")
        if not res: return
        
        pages_to_remove = set()
        try:
            parts = res.split(',')
            for part in parts:
                part = part.strip()
                if not part: continue
                if '-' in part:
                    subparts = part.split('-')
                    if len(subparts) != 2: raise ValueError(f"Invalid range: {part}")
                    start, end = int(subparts[0].strip()), int(subparts[1].strip())
                    if start > end: start, end = end, start
                    for p in range(start, end + 1): pages_to_remove.add(p)
                else: pages_to_remove.add(int(part))
        except Exception as e:
            messagebox.showerror("Error", f"Invalid format: {e}")
            return
            
        indices_to_remove = [p - 1 for p in pages_to_remove if 1 <= p <= total_pages]
        if not indices_to_remove:
            messagebox.showwarning("Warning", "No valid pages.")
            return
            
        msg = self.tr.get("Dialogs", "confirm_remove_pages", "Remove {} page(s)?", len(indices_to_remove))
        if not messagebox.askyesno("Confirm", msg, icon='warning'): return
            
        indices_to_remove.sort(reverse=True)
        for idx in indices_to_remove: self.importer.remove_page(idx)
            
        if self.current_page >= len(self.importer.pages):
            self.current_page = max(0, len(self.importer.pages) - 1)
        self.refresh_ui()
        messagebox.showinfo("Success", self.tr.get("Status", "pages_removed", "", len(indices_to_remove)))

    def _save_project(self, mode='full'):
        if not self.importer.pages:
            messagebox.showwarning("Warning", self.tr.get("Dialogs", "warn_no_project", "No project"))
            return
        mode_names = {'full': 'Full', 'light': 'Light'}
        filepath = filedialog.asksaveasfilename(
            title=f"Save Project ({mode_names[mode]})", 
            defaultextension=".pcc", 
            filetypes=[("comic2kindle Project", "*.pcc")]
        )
        if filepath:
            if mode == 'light' and not filepath.endswith('_light.pcc'):
                base = filepath.rsplit('.', 1)[0]
                filepath = f"{base}_light.pcc"
            progress = ProgressDialog(self.root, self.tr.get("Status", "saving", "Saving..."), "...")
            project_data = {'pages': self.importer.pages}
            def update_progress(percent, message):
                if message == "check_cancel": return progress.is_cancelled
                progress.update(percent, message)
            success = ProjectManager.save_project(project_data, filepath, mode, update_progress)
            progress.close()
            if success:
                self.project_file = filepath
                self.status_label.config(text=self.tr.get("Status", "saved", "", os.path.basename(filepath)))
            else:
                messagebox.showerror("Error", self.tr.get("Status", "error_saving", "Error saving"))

    def save_project_full(self): self._save_project(mode='full')
    def save_project_light(self): self._save_project(mode='light')

    def open_project(self):
        filepath = filedialog.askopenfilename(
            title=self.tr.get("Menu_File", "open_project", "Open Project"), 
            filetypes=[("comic2kindle Project", "*.pcc")]
        )
        if filepath:
            progress = ProgressDialog(self.root, self.tr.get("Status", "opening", "Opening..."), "...")
            def update_progress(percent, message):
                if message == "check_cancel": return progress.is_cancelled
                progress.update(percent, message)
            project_data = ProjectManager.load_project(filepath, update_progress)
            progress.close()
            if project_data:
                self.importer.pages = project_data['pages']
                for p in self.importer.pages:
                    if 'marked_for_cut' not in p: p['marked_for_cut'] = False
                    if 'is_full_page' not in p: p['is_full_page'] = False
                self.current_page = 0
                self.fit_to_height()
                self.project_file = filepath
                self.update_thumbnails()
                self.update_display()
                self.status_label.config(text=self.tr.get("Status", "opened", "", os.path.basename(filepath)))
            else:
                messagebox.showerror("Error", self.tr.get("Status", "error_opening", "Error opening"))

    def _get_suggested_title(self):
        suggested = getattr(self.importer, 'suggested_name', "")
        if not suggested and self.project_file:
            p = Path(self.project_file)
            suggested = p.stem.replace('_light', '')
        if not suggested:
            suggested = "comic2kindle"
        return suggested

    def export_pdf_split(self, parts=3, quality=95):
        if not self.importer.pages:
            messagebox.showwarning("Warning", self.tr.get("Dialogs", "warn_no_pages", "No pages"))
            return
            
        base_name = self._get_suggested_title()
            
        dialog = MetadataDialog(
            self.root, 
            title=self.tr.get("Metadata", "title", "Insert metadata"),
            initial_title=base_name,
            tr=self.tr
        )
        
        if not dialog.result: return
        book_title, book_author = dialog.result
        
        if not book_title: book_title = base_name
            
        initial_dir = getattr(self.importer, 'source_dir', "")
        if not initial_dir and self.project_file:
            initial_dir = str(Path(self.project_file).parent)
            
        mode_suffix = "kindle" if quality >= 90 else "kindle_light"
        initial_file = f"{base_name}_[{mode_suffix}].pdf"
        mode_title_str = "Hi-fi" if quality >= 90 else "Light"
        
        filepath = filedialog.asksaveasfilename(
            title=f"Save PDF ({mode_title_str})",
            initialfile=initial_file,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialdir=initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.expanduser("~")
        )
        if not filepath: return
            
        progress = ProgressDialog(self.root, self.tr.get("Status", "exporting", "", mode_title_str), "...")
        def update_progress(percent, message):
            if message == "check_cancel": return progress.is_cancelled
            progress.update(percent, message)
            
        success = Exporter.export_pdf_split(
            self.importer.pages, filepath, parts=parts, quality=quality,
            progress_callback=update_progress, title=book_title, author=book_author
        )
        progress.close()
        
        if success:
            messagebox.showinfo("Success", self.tr.get("Status", "success_export", "", mode_title_str, filepath))
            self.status_label.config(text=self.tr.get("Status", "exported", "", os.path.basename(filepath)))
        else:
            messagebox.showerror("Error", self.tr.get("Status", "error_export", "Export error"))

    def export_pdf_pages_full(self, quality=95):
        if not self.importer.pages:
            messagebox.showwarning("Warning", self.tr.get("Dialogs", "warn_no_pages", "No pages"))
            return
            
        base_name = self._get_suggested_title()
            
        dialog = MetadataDialog(
            self.root, 
            title=self.tr.get("Metadata", "title", "Insert metadata"),
            initial_title=base_name,
            tr=self.tr
        )
        
        if not dialog.result: return
        book_title, book_author = dialog.result
        
        if not book_title: book_title = base_name
            
        initial_dir = getattr(self.importer, 'source_dir', "")
        if not initial_dir and self.project_file:
            initial_dir = str(Path(self.project_file).parent)
            
        mode_suffix = "pages_full" if quality >= 90 else "full_pages_light"
        initial_file = f"{base_name}_[{mode_suffix}].pdf"
        mode_title_str = "Pages Full" if quality >= 90 else "Full Pages Light"
        
        filepath = filedialog.asksaveasfilename(
            title=f"Save PDF ({mode_title_str})",
            initialfile=initial_file,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialdir=initial_dir if initial_dir and os.path.isdir(initial_dir) else os.path.expanduser("~")
        )
        if not filepath: return
            
        progress = ProgressDialog(self.root, self.tr.get("Status", "exporting", "", mode_title_str), "...")
        def update_progress(percent, message):
            if message == "check_cancel": return progress.is_cancelled
            progress.update(percent, message)
            
        temp_pages = [dict(p, is_full_page=True) for p in self.importer.pages]
        success = Exporter.export_pdf_split(
            temp_pages, filepath, parts=3, quality=quality,
            progress_callback=update_progress, title=book_title, author=book_author
        )
        progress.close()
        
        if success:
            messagebox.showinfo("Success", self.tr.get("Status", "success_export", "", mode_title_str, filepath))
            self.status_label.config(text=self.tr.get("Status", "exported", "", os.path.basename(filepath)))
        else:
            messagebox.showerror("Error", self.tr.get("Status", "error_export", "Export error"))

    def detect_margins_auto_trim(self):
        if not self.importer.pages:
            messagebox.showwarning("Warning", self.tr.get("Dialogs", "warn_no_pages", "No pages"))
            return
        count = 0
        for page in self.importer.pages:
            if page.get('is_cover', False) or page.get('is_full_page', False): continue
            img = page.get('image')
            if img and isinstance(img, Image.Image):
                try:
                    gray = img.convert("L")
                    w, h = gray.size
                    bg_color = gray.getpixel((0, 0))
                    diff = gray.point(lambda p: 0 if abs(p - bg_color) < 25 else 255)
                    bbox = diff.getbbox()
                    if bbox:
                        bx1, by1, bx2, by2 = bbox
                        x1, y1 = max(0, bx1 - 5), max(0, by1 - 5)
                        x2, y2 = min(w, bx2 + 5), min(h, by2 + 5)
                        if x2 > x1 and y2 > y1:
                            page['crop_box'] = (x1, y1, x2, y2)
                            count += 1
                except Exception as e: print(f"Error: {e}")
        self.refresh_ui()
        messagebox.showinfo("Auto-Trim", f"Pre-markings applied to {count} of {len(self.importer.pages)} pages.")

    def detect_margins_percent(self):
        if not self.importer.pages:
            messagebox.showwarning("Warning", self.tr.get("Dialogs", "warn_no_pages", "No pages"))
            return
        res = simpledialog.askstring(
            self.tr.get("Menu_Edit", "percent_trim", "Margins (%)"), 
            "Enter percentages (Left, Right, Top, Bottom):\nEx: 5,5,3,5", 
            initialvalue="5,5,3,5"
        )
        if not res: return
        try:
            parts = [float(p.strip()) for p in res.split(',')]
            if len(parts) != 4: raise ValueError("Provide 4 values.")
            p_left, p_right, p_top, p_bottom = parts
        except Exception as e:
            messagebox.showerror("Error", f"Invalid format: {e}")
            return
        count = 0
        for page in self.importer.pages:
            if page.get('is_cover', False) or page.get('is_full_page', False): continue
            img = page.get('image')
            if img and isinstance(img, Image.Image):
                w, h = img.size
                x1, y1 = int(w * (p_left / 100.0)), int(h * (p_top / 100.0))
                x2, y2 = int(w * (1.0 - p_right / 100.0)), int(h * (1.0 - p_bottom / 100.0))
                if x2 > x1 and y2 > y1:
                    page['crop_box'] = (x1, y1, x2, y2)
                    count += 1
        self.refresh_ui()
        messagebox.showinfo("Info", f"Crop applied to {count} pages.")

    def remove_margins_marking(self):
        if not self.importer.pages: return
        count = sum(1 for p in self.importer.pages if 'crop_box' in p)
        for page in self.importer.pages:
            if 'crop_box' in page: del page['crop_box']
        self.canvas_editor_manager.exit_crop_mode()
        self.refresh_ui()
        messagebox.showinfo("Info", f"Markings removed from {count} pages.")

    def execute_cut_margins(self):
        if not self.importer.pages: return
        count = 0
        for page in self.importer.pages:
            crop_box = page.get('crop_box')
            if crop_box and 'image' in page and isinstance(page['image'], Image.Image):
                try:
                    img_orig = page['image']
                    x1, y1, x2, y2 = map(int, crop_box)
                    orig_w, orig_h = img_orig.size
                    if x2 <= orig_w and y2 <= orig_h:
                        page['image'] = img_orig.crop((x1, y1, x2, y2))
                        page['marked_for_cut'] = True
                        del page['crop_box']
                        count += 1
                except Exception as e: print(f"Error: {e}")
        self.canvas_editor_manager.exit_crop_mode()
        self.refresh_ui()

    def mark_for_cutting(self): self.canvas_editor_manager.enter_crop_mode()
    
    def cut_page(self):
        page = self.get_current_page()
        if not page: return
        if not self.canvas_editor_manager.is_cropping_mode and not page.get('crop_box'):
            messagebox.showwarning("Warning", "Mark the page for cutting first")
            return
        self.canvas_editor_manager.execute_crop(self.refresh_ui)
        
    def unmark_for_cutting(self): self.canvas_editor_manager.remove_crop(self.refresh_ui)

    def mark_as_cover(self):
        page = self.importer.get_page(self.current_page)
        if page:
            page['is_cover'] = True
            page['is_full_page'] = False
            page['marked_for_cut'] = False
            if 'crop_box' in page: del page['crop_box']
            self.refresh_ui()
            messagebox.showinfo("Info", "Page marked as cover")

    def mark_as_full_page(self):
        page = self.importer.get_page(self.current_page)
        if page:
            page['is_cover'] = False
            page['is_full_page'] = True
            page['marked_for_cut'] = False
            if 'crop_box' in page: del page['crop_box']
            self.refresh_ui()
            messagebox.showinfo("Info", "Page set as full page")

    def update_thumbnails(self):
        for widget in self.thumb_inner.winfo_children(): widget.destroy()
        if not self.importer.pages: return
        for i, page in enumerate(self.importer.pages):
            thumb_frame = ttk.Frame(self.thumb_inner)
            thumb_frame.pack(pady=4, padx=5, fill=tk.X)
            try:
                img_source = page['image']
                if page.get('marked_for_cut') and page.get('crop_box'):
                    img_source = img_source.crop(page['crop_box'])
                img = img_source.copy()
                img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                btn = tk.Button(thumb_frame, image=photo, command=lambda idx=i: self.go_to_page(idx),
                                borderwidth=2, relief=tk.SUNKEN if i == self.current_page else tk.RAISED)
                btn.image = photo
                btn.pack(side=tk.TOP, anchor=tk.CENTER)
                label_text = f"{i+1}"
                if page.get('is_cover', False): label_text += " 📘"
                elif page.get('is_full_page', False): label_text += " 📄"
                elif page.get('marked_for_cut', False) or page.get('crop_box'): label_text += " ✂️"
                ttk.Label(thumb_frame, text=label_text, font=('Arial', 9, 'bold'), anchor='center').pack(side=tk.TOP, fill=tk.X, pady=(2, 0))
            except Exception as e: print(f"Error thumbnail {i}: {e}")
        self.update_status()

    def update_display(self):
        page = self.importer.get_page(self.current_page)
        if not page: return
        self.canvas_editor.delete("all")
        img = page['image']
        orig_w, orig_h = img.size
        disp_w = int(orig_w * self.zoom_level)
        disp_h = int(orig_h * self.zoom_level)
        resized_img = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(resized_img)
        canvas_w, canvas_h = self.canvas_editor.winfo_width(), self.canvas_editor.winfo_height()
        ox, oy = max(0, (canvas_w - disp_w) // 2), max(0, (canvas_h - disp_h) // 2)
        self.canvas_editor.create_image(ox, oy, anchor=tk.NW, image=img_tk)
        self.canvas_editor.image_reference = img_tk
        self.canvas_editor.config(scrollregion=(0, 0, max(canvas_w, disp_w + ox*2), max(canvas_h, disp_h + oy*2)))
        self.canvas_editor_manager.displayed_image_info = (img_tk, self.zoom_level, ox, oy, orig_w, orig_h)
        if page.get('crop_box'):
            cx1, cy1, cx2, cy2 = page['crop_box']
            canvas_rx1 = ox + (cx1 / orig_w) * disp_w
            canvas_ry1 = oy + (cy1 / orig_h) * disp_h
            canvas_rx2 = ox + (cx2 / orig_w) * disp_w
            canvas_ry2 = oy + (cy2 / orig_h) * disp_h
            self.canvas_editor_manager.current_rect = self.canvas_editor.create_rectangle(
                canvas_rx1, canvas_ry1, canvas_rx2, canvas_ry2, outline='#00ffff', width=2, dash=(4, 4), tags="crop_elements"
            )
            self.canvas_editor_manager.is_cropping_mode = True
            self.canvas_editor_manager._update_overlays_and_handles()
        else:
            self.canvas_editor_manager.is_cropping_mode = False
            self.canvas_editor_manager.current_rect = None
            self.canvas_editor_manager._clear_overlays_and_handles()
        self.update_page_info()

    def update_page_info(self):
        total = len(self.importer.pages)
        page = self.importer.get_page(self.current_page)
        if page and page.get('is_cover'): status_txt = "Cover"
        elif page and page.get('is_full_page'): status_txt = "Full"
        elif page and (page.get('marked_for_cut') or page.get('crop_box')): status_txt = "Crop"
        else: status_txt = "Std"
        self.page_label.config(text=f"Page {self.current_page+1}/{total}")
        self.page_info.config(text=f"Page {self.current_page+1}/{total} | {status_txt}")
        self.zoom_label.config(text=f"{int(self.zoom_level*100)}%")

    def update_status(self):
        total = len(self.importer.pages)
        if total > 0:
            covers = sum(1 for p in self.importer.pages if p.get('is_cover', False))
            full_pages = sum(1 for p in self.importer.pages if p.get('is_full_page', False))
            cuts = sum(1 for p in self.importer.pages if p.get('marked_for_cut', False) or p.get('crop_box', False))
            self.status_label.config(text=f"📚 {total} pg | {full_pages} full | {cuts} crop | {covers} cov")
        else:
            self.status_label.config(text=self.tr.get("Status", "no_doc", "Ready - No document loaded"))

    def show_about(self):
        about_msg = self.tr.get("Menu_Help", "about_desc", "comic2kindle v1.0.1\nComic to PDF converter.")
        about_msg = about_msg.replace('\\n', '\n')
        messagebox.showinfo(self.tr.get("Menu_Help", "about", "About"), about_msg, parent=self.root)

    def show_shortcuts(self):
        win = tk.Toplevel(self.root)
        win.title(self.tr.get("Menu_Help", "shortcuts", "Keyboard Shortcuts"))
        win.geometry("600x500")
        win.minsize(600, 350)
        
        shortcuts = self.tr.get("Menu_Help", "shortcuts_text", """
📋 KEYBOARD SHORTCUTS
← / →          Previous / next page
Ctrl+O         Open Folder / CBR / CBZ
Ctrl+S         Save Project (Full)
Ctrl+Shift+S   Save Project (Light)
Ctrl+Shift+O   Open Project
ESC            Remove cut mark
Del            Cut margins
Ctrl+Delete    Remove current page
Ctrl++/-       Zoom
Ctrl+0         Fit to height
Ctrl+9         Zoom 100%
Ctrl+Q         Quit
""")
        shortcuts = shortcuts.replace('\\n', '\n')
        ttk.Label(win, text=shortcuts, font=('Courier', 10), justify=tk.LEFT).pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        close_btn_text = self.tr.get("Menu_Help", "close", "Close")
        ttk.Button(win, text=close_btn_text, command=win.destroy).pack(pady=10)

    def run(self): self.root.mainloop()

if __name__ == "__main__":
    app = KindlePanelCreator()
    app.run()
