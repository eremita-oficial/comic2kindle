#!/usr/bin/env python3
"""
Janela de progresso reutilizável para operações longas
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

class ProgressDialog:
    """Janela de progresso com barra e mensagem"""
    
    def __init__(self, parent, title="Processando", message="Aguarde...", max_value=100):
        """
        Inicializa a janela de progresso
        
        Args:
            parent: Widget pai (para centralizar)
            title: Título da janela
            message: Mensagem inicial
            max_value: Valor máximo da barra (padrão: 100)
        """
        self.parent = parent
        self.max_value = max_value
        self.current_value = 0
        self.is_cancelled = False
        self.is_closed = False
        
        # Cria a janela
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("400x150")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centraliza a janela
        self.center_window()
        
        # Widgets
        self.label_message = ttk.Label(self.window, text=message, font=('Arial', 10))
        self.label_message.pack(pady=(20, 10))
        
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(self.window, variable=self.progress_var,
                                           maximum=max_value, length=350)
        self.progress_bar.pack(pady=10)
        
        self.label_percent = ttk.Label(self.window, text="0%", font=('Arial', 9))
        self.label_percent.pack(pady=(0, 10))
        
        # Frame para botões
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Cancelar", 
                                       command=self.cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Bind para fechar com ESC
        self.window.bind('<Escape>', lambda e: self.cancel())
        
        # Força a atualização da janela
        self.window.update()
        
    def center_window(self):
        """Centraliza a janela em relação ao pai"""
        self.window.update_idletasks()
        
        width = 400
        height = 150
        
        # Obtém a posição do pai
        if self.parent:
            x_parent = self.parent.winfo_x()
            y_parent = self.parent.winfo_y()
            width_parent = self.parent.winfo_width()
            height_parent = self.parent.winfo_height()
            
            x = x_parent + (width_parent - width) // 2
            y = y_parent + (height_parent - height) // 2
        else:
            # Centraliza na tela
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def update(self, value, message=None):
        """
        Atualiza o progresso
        
        Args:
            value: Valor atual (0 a max_value)
            message: Mensagem opcional
        """
        if self.is_closed or self.is_cancelled:
            return
        
        self.current_value = min(value, self.max_value)
        self.progress_var.set(self.current_value)
        
        # Calcula porcentagem
        percent = int((self.current_value / self.max_value) * 100)
        self.label_percent.config(text=f"{percent}%")
        
        if message:
            self.label_message.config(text=message)
        
        # Força a atualização
        self.window.update()
        self.window.update_idletasks()
    
    def update_message(self, message):
        """Atualiza apenas a mensagem"""
        if not self.is_closed and not self.is_cancelled:
            self.label_message.config(text=message)
            self.window.update()
    
    def set_max_value(self, max_value):
        """Define o valor máximo da barra"""
        self.max_value = max_value
        self.progress_bar.config(maximum=max_value)
    
    def cancel(self):
        """Cancela a operação"""
        if not self.is_cancelled:
            self.is_cancelled = True
            self.label_message.config(text="Cancelando...")
            self.cancel_button.config(state=tk.DISABLED, text="Cancelando...")
            self.window.update()
    
    def is_cancelled(self):
        """Verifica se a operação foi cancelada"""
        return self.is_cancelled
    
    def close(self):
        """Fecha a janela de progresso"""
        if not self.is_closed:
            self.is_closed = True
            self.window.destroy()
    
    def run_task(self, task_func, *args, **kwargs):
        """
        Executa uma tarefa em thread separada com callback de progresso
        
        Args:
            task_func: Função da tarefa
            *args, **kwargs: Argumentos para a função
        """
        def task_wrapper():
            try:
                # Executa a tarefa com callback
                result = task_func(*args, **kwargs)
                
                # Se não foi cancelado, atualiza para 100%
                if not self.is_cancelled:
                    self.update(100, "Concluído!")
                    time.sleep(0.5)
                
                # Fecha a janela
                self.window.after(100, self.close)
                
            except Exception as e:
                # Em caso de erro
                self.window.after(0, lambda: self.show_error(str(e)))
        
        # Inicia a thread
        thread = threading.Thread(target=task_wrapper, daemon=True)
        thread.start()
        
        # Mantém a janela aberta
        self.window.wait_window()
        
        # Retorna se foi cancelado
        return not self.is_cancelled
    
    def show_error(self, error_msg):
        """Mostra mensagem de erro"""
        messagebox.showerror("Erro", f"Erro durante a operação:\n{error_msg}")
        self.close()
