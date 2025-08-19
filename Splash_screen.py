import threading
import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage, Canvas
from customtkinter import *
from direction import folder
from PIL import Image, ImageTk, ImageFilter

class Splash(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Carregando...")
        self.geometry("1280x720")
        self.parent = parent
        self.callback = callback
        self.image_path = (fr'{folder()}\ICONES_FOTOS\loading_images\loading.png')
        
        self.overrideredirect(1)
        self.configure(bg='#242424')
        self.attributes('-alpha', 0.9)
        self.attributes('-transparentcolor', '#242424')
        
        self.canvas = tk.Canvas(
            self, 
            width=500, 
            height=500, 
            bg='#242424',
            highlightthickness=0
        )
        self.canvas.pack(expand=True)

        self.original_image = Image.open(self.image_path).convert('RGBA')
        self.original_image = self.original_image.filter(ImageFilter.GaussianBlur(radius=0.3))

        self.photo_image = None
        self.current_angle = 0
        
        # --- MUDANÇA PRINCIPAL ---
        # Adiciona uma flag para controlar o loop de animação
        self.running = True
        
        self.rotate_image()
        self.start_loading()

    def rotate_image(self):
        # A animação só continua se a flag 'running' for True
        if not self.running:
            return

        rotated = self.original_image.rotate(
            self.current_angle, 
            resample=Image.BICUBIC,
            expand=False
        )
        self.photo_image = ImageTk.PhotoImage(rotated)
        
        self.canvas.delete("all")
        self.canvas.create_image(
            250, 250,
            image=self.photo_image,
            anchor=tk.CENTER
        )

        self.current_angle = (self.current_angle - 10) % 360
        self.after(50, self.rotate_image)

    def start_loading(self):
        self.thread = threading.Thread(target=self.run_task)
        self.thread.start()

    def run_task(self):
        try:
            self.callback()
        except Exception as e:
            print(f"Erro durante o carregamento: {e}")

    # --- MUDANÇA PRINCIPAL ---
    # Sobrescreve o método destroy para parar a animação primeiro
    def destroy(self):
        self.running = False
        super().destroy()