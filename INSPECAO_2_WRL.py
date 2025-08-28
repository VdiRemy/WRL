import tkinter as tk
from tkinter import messagebox, filedialog
import colorama as color
import cv2
from tkinter.constants import *
from tkinter import Canvas
from customtkinter import *
from PIL import Image, ImageTk
from ultralytics import YOLO
import keyboard
import FUNCOES_TKINTER
import FUNCOES_CAMERA_WRL as fun2 #Funcções para camêra
from FUNCOES_CAMERA_WRL import DepthCamera, NoDetectionsError
import numpy as np
from INSPECAO_3_WRL import aba_dados
from direction import folder
import sys
import Splash_screen as Loading
import json
import threading

print("\n\n", color.Fore.GREEN + "Iniciando o código - Tela da câmera" + color.Style.RESET_ALL)
pasta = folder()

#CORES USADAS
verde = '#416951' #Cor botão
bege = '#C9B783' #Cor botão
marrom = '#68584A' 
verde_escuro = '#1F3422' #Titulos
fundo_branco = 'white' #fundo das letras em frames brancos

model = YOLO(fr'{pasta}\pesos\best.pt')

# # Define a classe 
# Initialize the DepthCamera
# Define global variables for storing the results

global nome_arquivo, caminho_fotoBW, caminho_fotoColorida, nome_arquivo_BW, stop
nome_arquivo = caminho_fotoBW = caminho_fotoColorida = nome_arquivo_BW = None
stop = False
def adicionar_detalhes(inp_menu):
    largura = inp_menu.winfo_screenwidth()
    altura = inp_menu.winfo_screenheight()

    # Cria um Frame para o Canvas, que ficará no fundo
    canvas_frame = tk.Frame(inp_menu, width=largura, height=altura, bg=fundo_branco)
    canvas_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    canvas = Canvas(canvas_frame, width=largura, height=altura, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Triângulo vermelho no canto superior direito
    canvas.create_polygon(largura, 0, largura, 300, largura-300, 0, fill="#94031E", outline="#94031E")

    # Triângulo verde no canto inferior esquerdo
    canvas.create_polygon(0, altura, 0, altura-300, 300, altura, fill=verde, outline=verde)

def tela(inp_janela):
    inp_janela.title("Camêra WRL")
    inp_janela.configure(background=fundo_branco)
    inp_janela.attributes("-fullscreen", True)
    
def frames_da_tela(inp_janela):
    global frame_um, frame_dois
    
    frame_um = tk.Frame(inp_janela, bd=2, bg=fundo_branco, highlightbackground='#668B8B', highlightthickness=1)
    frame_um.place(relx=0.72, rely=0.02, relwidth=0.27, relheight=0.96)
    
    frame_dois = tk.Frame(inp_janela, bd=2, bg=fundo_branco, highlightbackground='#668B8B', highlightthickness=1)
    frame_dois.place(relx=0.01, rely=0.02, relwidth=0.7, relheight=0.96)
    
    return frame_um, frame_dois

def componentes_frame1(inp_frame,inp_janela, inp_menu, dc):
    bt_voltar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "Voltar",verde, bege,3,'15','bold',"hand2", lambda: (dc.release(), FUNCOES_TKINTER.BOTAO_VOLTAR(inp_menu, inp_janela))) # #TOPLEVEL
    bt_voltar.place(relx=0.05, rely=0.88, relwidth=0.2, relheight=0.08)
    
    #OBS: por a opção de clicar aqui e tirar a foto
    btfoto_pg2 = tk.Button(inp_frame, text='CTRL', relief="ridge", cursor="circle", bd=4, bg='#545454', fg='white', font=("arial", 13))
    btfoto_pg2.place(relx=0.5, rely=0.93, anchor=CENTER)
def componentes_frame2_refatorado(inp_frame, lista_dados_inspecao, dc, on_photo_taken_callback):
    borda = tk.Label(inp_frame, bg="white")
    borda.place(relx=0, rely=0, relwidth=1, relheight=1)

    def escolher_imagem_local():
        caminho_imagem = filedialog.askopenfilename(
            title="Selecione uma imagem",
            filetypes=[("Arquivos de imagem", "*.png;*.jpg;*.jpeg;*.bmp")]
        )
        if caminho_imagem:
            img = cv2.imread(caminho_imagem)
            return img
        return None

    def exibir_video():
        global nome_arquivo, caminho_fotoBW, caminho_fotoColorida, nome_arquivo_BW
        global lista_APP, qtd_furos, Abertura, infra_image, centro, depth_frame
        
        if not borda.winfo_exists():
            return

        ret, color_image, infra_image_cam = dc.get_simple_frame()

        if not ret:  
            # Não conseguiu pegar da câmera → pergunta imagem
            infra_image_cam = escolher_imagem_local()
            if infra_image_cam is None:
                print("Nenhuma imagem selecionada. Encerrando...")
                return
            ret = True  # força fluxo normal

        if ret:
            infra_image = infra_image_cam  
            back_frame = fun2.sobrepor_molde(infra_image)
            lista_APP, id_bico, qtd_furos = fun2.organizar_dados_app(lista_dados_inspecao)
            
            frame = cv2.cvtColor(back_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((borda.winfo_width(), borda.winfo_height()))
            image = ImageTk.PhotoImage(image=img)
            borda.configure(image=image)
            borda.image = image
            centro = fun2.definir_centro(borda.winfo_height(), borda.winfo_width())

            if keyboard.is_pressed('ctrl') or keyboard.is_pressed('right control'):
                if hasattr(dc, "get_frame"):  
                    ret, depth_frame, color_frame, _, Abertura = dc.get_frame()
                    nome_arquivo, caminho_fotoBW, caminho_fotoColorida, nome_arquivo_BW = \
                        fun2.tirar_foto(color_frame, infra_image, id_bico)
                    if hasattr(dc, "release"):
                        try:
                            dc.release()
                        except RuntimeError:
                            pass
                on_photo_taken_callback()
                return
        
        borda.after(10, exibir_video)

    exibir_video()


def aba_camera(inp_janela, dados, inp_menu):
    """
    Gerencia a UI da câmera, o fluxo de captura (local ou ao vivo),
    e o processamento da imagem de forma assíncrona e segura.
    """
    # --- Variáveis de Estado e Controle ---
    global splash
    processando_foto = False  # Flag para evitar múltiplas capturas ("debounce")

    # --- Funções de Navegação e Callbacks da UI ---

    def handle_failure(message, imagem_erro=None):
        print(f"FALHA: {message}")

        # Fecha o splash se existir
        if 'splash' in globals() and splash.winfo_exists():
            splash.destroy()
            print("Splash destruído após falha.")

        if imagem_erro:
            try:
                popup = tk.Toplevel(inp_janela)
                popup.title("Falha na Análise")
                popup.transient(inp_janela)  # popup modal relativo à janela principal
                popup.grab_set()

                # Carrega e redimensiona a imagem
                img = Image.open(imagem_erro)
                img = img.resize((300, 300))  # Ajuste o tamanho conforme preferir
                photo = ImageTk.PhotoImage(img)

                label_img = tk.Label(popup, image=photo)
                label_img.image = photo  # mantém referência
                label_img.pack(padx=10, pady=10)

                label_msg = tk.Label(popup, text=message, fg='red')
                label_msg.pack(padx=10, pady=5)

                btn_ok = tk.Button(popup, text="OK", command=popup.destroy)
                btn_ok.pack(pady=10)
            except Exception as e:
                print(f"Erro ao mostrar imagem no popup: {e}")
                messagebox.showwarning("Falha na Análise", f"{message}\nTente novamente.")
        else:
            messagebox.showwarning("Falha na Análise", f"{message}\nTente novamente.")

        processando_foto = False
        inp_janela.deiconify()

    def handle_success(resultado):
        """Chamado quando o processamento é concluído com sucesso."""
        nonlocal processando_foto
        print("SUCESSO: Preparando para exibir resultados.")

        if 'splash' in globals() and splash.winfo_exists():
            splash.destroy()
            print("Splash destruído com sucesso.")
        
        # Destrói a janela da câmera para uma transição limpa
        if 'janela_tres' in locals() and janela_tres.winfo_exists():
            janela_tres.destroy()
            print("Janela da câmera destruída com sucesso.")

        abrir_janela_de_resultados(resultado["dados"], resultado["arquivo"])
        print("Resultados exibidos com sucesso.")
        processando_foto = False # Libera para um novo ciclo completo
        inp_janela.deiconify()
        print("Processamento de foto resetado.")

    def abrir_janela_de_resultados(dados_da_inspecao, arquivo_resultado):
        """Abre a tela final com os dados da inspeção."""
        # Esta função chama a próxima tela da sua aplicação
        print("DAdos da inspeção")
        for i in range(len(dados_da_inspecao)):
            print(f"\n{dados_da_inspecao[i]}")

        try:
            print("abrindo aba dados")
            aba_dados(inp_janela, dados_da_inspecao[0],dados_da_inspecao[5], dados_da_inspecao[4], arquivo_resultado, inp_menu, inp_janela)
        except:
            print("nao abriu")
    # --- Função de Orquestração do Processamento ---

    def iniciar_processamento(dados_de_entrada):
        global splash

        # Função alvo que será executada na nova thread
        def tarefa_alvo():
            # Chama a função de lógica desacoplada (que vamos corrigir no Erro 2)
            resultado = fun2.tarefa_de_processamento_independente(dados_de_entrada)
            
            # Enfileira a atualização da UI de volta para a thread principal
            if resultado["sucesso"]:
                inp_menu.after(0, lambda: handle_success(resultado))
            else:
                # Passa também a imagem, se existir
                inp_menu.after(0, lambda: handle_failure(
                    resultado["mensagem_erro"], 
                    resultado.get("imagem_erro")
                ))

        # Cria a thread
        worker_thread = threading.Thread(target=tarefa_alvo)

        # A função que o Splash vai chamar depois de aparecer
        def iniciar_tarefa_em_thread():
            worker_thread.start()

        # CORREÇÃO AQUI: Passe 'iniciar_tarefa_em_thread' como o callback
        splash = Loading.Splash(inp_menu, iniciar_tarefa_em_thread)
        splash.grab_set()
    # --- Lógica Principal da Função 'aba_camera' ---

    # Tenta inicializar a câmera
    try:
        dc = DepthCamera()
        ret, _, _ = dc.get_simple_frame()
        if not ret: raise RuntimeError("Não foi possível obter o frame inicial da câmera.")
        camera_ok = True
    except Exception as e:
        print(f"Falha ao inicializar câmera: {e}")
        camera_ok = False

    # --- FLUXO 1: Imagem Local (se a câmera falhar) ---
    if not camera_ok:
        messagebox.showwarning("Aviso", "Nenhuma câmera detectada.\nSelecione uma imagem para processamento.")
        arquivo_imagem = filedialog.askopenfilename(
            title="Selecione a imagem", filetypes=[("Imagens", "*.png;*.jpg;*.jpeg")]
        )
        if not arquivo_imagem:
            handle_failure("Nenhuma imagem selecionada.")
            return

        # Prepara o dicionário de dados como se a imagem viesse da câmera
        lista_APP, _, qtd_furos = fun2.organizar_dados_app(dados)
        dados_de_entrada = {
            "model": model, "caminho_fotoBW": arquivo_imagem, "nome_arquivo": [arquivo_imagem],
            "depth_frame": np.zeros((480, 640), dtype=np.uint16), "Abertura": 80.18755238290139,
            "nome_arquivo_BW": arquivo_imagem, "centro": (320, 240),
            "lista_APP": lista_APP, "qtd_furos": qtd_furos
        }
        
        print("Processo iniciado com imagem local.")
        iniciar_processamento(dados_de_entrada)
        return # Finaliza a execução para não criar a UI da câmera

    # --- FLUXO 2: Câmera ao Vivo ---
    
    # Cria a janela da câmera
    janela_tres = tk.Toplevel(inp_menu)
    tela(janela_tres)
    adicionar_detalhes(janela_tres)
    frame_um, frame_dois = frames_da_tela(janela_tres)
    componentes_frame1(frame_um, janela_tres, inp_menu, dc)
    
    # Lógica do Frame de Vídeo (refatorada para clareza)
    video_label = tk.Label(frame_dois, bg="white")
    video_label.place(relx=0, rely=0, relwidth=1, relheight=1)

    def exibir_video():
        nonlocal processando_foto # Permite modificar a flag
        
        if not video_label.winfo_exists(): return

        # Lógica de Captura e Callback
        if (keyboard.is_pressed('ctrl') or keyboard.is_pressed('right control')) and not processando_foto:
            processando_foto = True # Trava para evitar múltiplas capturas

            ret_foto, depth_frame, color_frame, infra_image, Abertura = dc.get_frame()
            if ret_foto:
                id_bico = dados[5]
                nome_arquivo, caminho_fotoBW, _, nome_arquivo_BW = fun2.tirar_foto(color_frame, infra_image, id_bico)
                
                lista_APP, _, qtd_furos = fun2.organizar_dados_app(dados)
                centro = fun2.definir_centro(video_label.winfo_height(), video_label.winfo_width())

                # Prepara dados para o processamento
                dados_de_entrada = {
                    "model": model, "caminho_fotoBW": caminho_fotoBW, "nome_arquivo": nome_arquivo,
                    "depth_frame": depth_frame, "Abertura": Abertura, "nome_arquivo_BW": nome_arquivo_BW,
                    "centro": centro, "lista_APP": lista_APP, "qtd_furos": qtd_furos
                }
                iniciar_processamento(dados_de_entrada)
            else:
                handle_failure("Falha ao capturar a imagem da câmera no momento da foto.")
            
            # Não agenda o próximo frame, parando o loop de vídeo
            return

        # Lógica de Exibição do Feed
        ret_feed, _, infra_image_cam = dc.get_simple_frame()
        if ret_feed:
            back_frame = fun2.sobrepor_molde(infra_image_cam)
            frame = cv2.cvtColor(back_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((video_label.winfo_width(), video_label.winfo_height()))
            image = ImageTk.PhotoImage(image=img)
            video_label.configure(image=image)
            video_label.image = image

        # Agenda o próximo frame se não estiver processando
        if video_label.winfo_exists():
            video_label.after(15, exibir_video)

    # Inicia o loop de vídeo
    exibir_video()

    # Configurações finais da janela da câmera
    janela_tres.focus_force()
    janela_tres.grab_set()
    inp_janela.withdraw()

    return janela_tres