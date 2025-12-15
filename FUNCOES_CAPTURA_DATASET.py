import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
import os
from datetime import datetime
import keyboard

# Importações dos seus módulos
import FUNCOES_TKINTER
from FUNCOES_CAMERA_WRL import DepthCamera, sobrepor_molde
import cam
from direction import folder

def aba_captura_dataset(inp_menu):
    """
    Cria e gerencia a janela para captura de imagens para o dataset.
    """
    print("\nAbrindo a aba de Captura para Dataset")
    pasta = folder()
    
    # --- Configurações da Janela ---
    janela_captura = tk.Toplevel(inp_menu)
    janela_captura.title("Captura para Dataset")
    janela_captura.attributes("-fullscreen", True)
    janela_captura.configure(bg="#2d2d2d")
    
    # Esconde o menu principal
    inp_menu.withdraw()

    # --- Variáveis de Estado ---
    camera_ok = False
    cam_obj = None  # Variável para armazenar o objeto da câmera ativa

    try:
        # Tenta inicializar a câmera Realsense (DepthCamera)
        dc = DepthCamera()
        ret, _ = dc.get_simple_frame()
        if not ret:
            raise RuntimeError("Não foi possível abrir a câmera Realsense.")
        
        cam_obj = dc
        print("Câmera Realsense inicializada com sucesso.")
        camera_ok = True
    except Exception as e:
        print(f"Erro ao inicializar a Realsense: {e}. Tentando a webcam padrão...")
        try:
            # Se falhou, tenta a webcam padrão
            cam = cv2.VideoCapture(0)
            ret, frame = cam.read()
            if not ret:
                raise RuntimeError("Não foi possível abrir a webcam padrão.")
            
            cam_obj = cam
            print("Webcam padrão inicializada com sucesso.")
            camera_ok = True
        except Exception as e:
            messagebox.showerror("Erro de Câmera", f"Não foi possível inicializar nenhuma câmera: {e}")
            camera_ok = False

    video_loop_running = [True]
    capture_count = 0

    # --- Funções de Lógica e Limpeza ---
    def cleanup_and_close():
        """Função centralizada para fechar recursos e a janela de forma segura."""
        print(">>> Encerrando a captura de dataset...")
        video_loop_running[0] = False
        if cam_obj:
            if isinstance(cam_obj, DepthCamera):
                cam_obj.release()
            elif isinstance(cam_obj, cv2.VideoCapture):
                cam_obj.release()
        janela_captura.destroy()
        inp_menu.deiconify()

    def salvar_imagem_capturada(infra_img):
        """Salva a imagem infravermelha com um timestamp único."""
        nonlocal capture_count
        try:
            dir_infra = os.path.join(pasta, 'dataset', 'infrared')
            os.makedirs(dir_infra, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"capture_{timestamp}.png"
            
            cv2.imwrite(os.path.join(dir_infra, filename), infra_img)
            print("Imagem infravermelha salva em:", os.path.join(dir_infra, filename))
            capture_count += 1
            label_contador.config(text=f"Imagens Capturadas: {capture_count}")
            print(f"Imagem salva: {filename}")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar a imagem: {e}")

    # --- Criação dos Widgets ---
    # ... (O código dos widgets é o mesmo) ...
    frame_video = tk.Frame(janela_captura, bg="red")
    frame_video.place(relx=0.02, rely=0.02, relwidth=0.75, relheight=0.96)
    label_video = tk.Label(frame_video, bg="white")
    label_video.pack(fill=tk.BOTH, expand=True)

    frame_controles = tk.Frame(janela_captura, bg="#2d2d2d")
    frame_controles.place(relx=0.78, rely=0.02, relwidth=0.20, relheight=0.96)

    label_titulo = FUNCOES_TKINTER.CRIAR_LABEL(frame_controles, "Controles", "#2d2d2d", "white", "calibri", '24', "bold")
    label_titulo.pack(pady=20, fill=tk.X)

    label_instrucoes = FUNCOES_TKINTER.CRIAR_LABEL(
        frame_controles, 
        'Pressione "C" para capturar\n\nPressione "ESC" para sair', 
        "#2d2d2d", "white", "calibri", '14', 'normal'
    )
    label_instrucoes.pack(pady=40, fill=tk.X)

    label_contador = FUNCOES_TKINTER.CRIAR_LABEL(
        frame_controles, 
        f"Imagens Capturadas: {capture_count}", 
        "#2d2d2d", "#4CAF50", "Arial", 15, "bold"
    )
    label_contador.pack(pady=20, fill=tk.X)

    botao_voltar = FUNCOES_TKINTER.CRIAR_BOTAO(
        frame_controles, "Voltar ao Menu", "#f44336", "#FFFFFF", 2, 16, "bold", "hand2", cleanup_and_close
    )
    botao_voltar.pack(side=tk.BOTTOM, fill=tk.X, ipady=10, pady=20)

    # --- Loop de Vídeo ---
    def exibir_video():
        if not video_loop_running[0] or not cam_obj:
            return

        # Lógica de captura unificada
        if isinstance(cam_obj, DepthCamera):
            # Captura da Realsense
            ret, infra_frame = cam_obj.get_simple_frame()
            if not ret:
                label_video.after(15, exibir_video)
                return
            display_frame = sobrepor_molde(infra_frame)
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_GRAY2RGB)
            
        elif isinstance(cam_obj, cv2.VideoCapture):
            # Captura da webcam
            ret, frame = cam_obj.read()
            if not ret:
                label_video.after(15, exibir_video)
                return
            infra_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Converte para escala de cinza
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # RGB para exibir corretamente no Tkinter

        img = Image.fromarray(display_frame)
        
        # Redimensiona e exibe
        img = img.resize((label_video.winfo_width(), label_video.winfo_height()))
        image = ImageTk.PhotoImage(image=img)

        label_video.config(image=image)
        label_video.image = image

        if keyboard.is_pressed('c'):
            salvar_imagem_capturada(infra_frame)
            label_video.after(200, exibir_video)
            return

        label_video.after(15, exibir_video)

    # Inicia o loop de vídeo se a câmera estiver OK
    if camera_ok:
        janela_captura.deiconify()
        exibir_video()
    else:
        cleanup_and_close()

    janela_captura.protocol("WM_DELETE_WINDOW", cleanup_and_close)
    janela_captura.bind('<Escape>', lambda event: cleanup_and_close())
    
    return janela_captura