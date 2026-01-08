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
import math

print("\n\n", color.Fore.GREEN + "Iniciando o código - Tela da câmera" + color.Style.RESET_ALL)
pasta = folder()

#CORES USADAS
verde = '#416951' #Cor botão
bege = '#C9B783' #Cor botão
marrom = '#68584A' 
verde_escuro = '#1F3422' #Titulos
fundo_branco = 'white' #fundo das letras em frames brancos

model = YOLO(fr'{pasta}\pesos\infrared_weight\best.pt')

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

def componentes_frame1(inp_frame, inp_janela, inp_menu, dc, comando_para_voltar):
    
    # O botão 'Voltar' agora usa o comando que foi passado como argumento.
    # A lambda complexa e com erro de sintaxe foi removida.
    bt_voltar = FUNCOES_TKINTER.CRIAR_BOTAO(
        inp_frame, 
        "Voltar",
        verde, bege, 3, '15', 'bold', "hand2", 
        inp_comando=comando_para_voltar  # Usando o comando recebido
    )
    bt_voltar.place(relx=0.05, rely=0.88, relwidth=0.4, relheight=0.08)
    
    #OBS: por a opção de clicar aqui e tirar a foto
    btfoto_pg2 = tk.Button(inp_frame, text='TIRAR FOTO (CTRL)', relief="ridge", cursor="circle", bd=4, bg='#545454', fg='white', font=("arial", 13))
    btfoto_pg2.place(relx=0.5, rely=0.93, anchor=CENTER)

def aba_camera(inp_janela, dados, inp_menu):
    """
    Gerencia a UI da câmera, com a ordem das funções internas corrigida.
    """
    # --- Variáveis de Estado e Controle ---
    processando_foto = False
    dc = None
    janela_tres = None
    video_loop_running = [True]
    after_id = [None]
    worker_thread = None
    splash = None

    def finalizar_e_limpar_camera():
        nonlocal worker_thread, dc, splash # Permite modificar as variáveis do escopo pai

        print(">>> [DEBUG AÇÃO] Iniciando limpeza da janela da câmera...")
        video_loop_running[0] = False
        
        # Cancela o próximo loop de vídeo agendado para evitar erros
        if after_id[0]:
            # Adiciona uma verificação para garantir que video_label exista
            if 'video_label' in locals() and video_label.winfo_exists():
                video_label.after_cancel(after_id[0])
                print(">>> [DEBUG AÇÃO] Tarefa .after() cancelada.")
        
        if dc:
            #tenta liberar a camera
            try:
                dc.release()
            except RuntimeError:
                pass
            dc = None # Quebra a referência ao objeto da câmera
        
        if splash and splash.winfo_exists():
            splash.destroy()
            splash = None
        
        if janela_tres and janela_tres.winfo_exists():
            janela_tres.destroy()
        
        # A janela anterior (inp_janela) não é destruída aqui, apenas mostrada novamente.
        # A sua destruição é responsabilidade da tela de resultados (aba_dados).
        if inp_janela and inp_janela.winfo_exists():
            inp_janela.deiconify()

        worker_thread = None
        print("Recursos da câmera limpos.")


    # --- Funções de Navegação e Callbacks da UI ---
    # Agora estas funções podem chamar 'finalizar_e_limpar_camera' sem erro.
    def handle_failure(message, imagem_erro=None, splash_obj=None):
        if "flush" not in message.lower():
            print(f"FALHA: {message}")
        
        # A chamada agora é válida porque a função foi definida antes
        finalizar_e_limpar_camera() 
        
        if imagem_erro:
            try:
                popup = tk.Toplevel(inp_janela)
                popup.title("Falha na Análise")
                popup.transient(inp_janela)  # popup modal relativo à janela principal
                popup.grab_set()

                # Carrega e redimensiona a imagem
                img = Image.open(imagem_erro)
                # img = img.resize((300, 300))  # Ajuste o tamanho conforme preferir
                # abrir em tela cheia, mas mantendo a proporção
                img = img.resize(((popup.winfo_screenwidth())-250, (popup.winfo_screenheight()-250)))
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


    def handle_success(resultado, splash_obj=None):
        nonlocal processando_foto
        print("SUCESSO: Preparando para exibir resultados.")
        ''
        if splash_obj and splash_obj.winfo_exists():
            splash_obj.destroy()

        abrir_janela_de_resultados(resultado["dados"], resultado["arquivo"])
        
    def abrir_janela_de_resultados(dados_da_inspecao, arquivo_resultado):
        # ANTES de abrir a próxima janela, DESTRUÍMOS a da câmera.
        finalizar_e_limpar_camera()
        try:
            print("abrindo aba dados")
            print("dados_da_inspecao:", dados_da_inspecao)
            print("arquivo_resultado:", arquivo_resultado)
            # Passa a referência da janela 1 (inp_janela) para a próxima etapa.
            aba_dados(inp_janela, dados_da_inspecao[0],dados_da_inspecao[5], dados_da_inspecao[4], arquivo_resultado, inp_menu, inp_janela)
        except Exception as e:
            print(f"nao abriu aba dados: {e}")

    def iniciar_processamento(dados_de_entrada):
        nonlocal splash, worker_thread
        splash_ref = [None] 
        def tarefa_alvo():
            resultado = fun2.tarefa_de_processamento_independente(dados_de_entrada)
            splash_para_fechar = splash_ref[0]
            if resultado["sucesso"]:
                inp_menu.after(0, lambda: handle_success(resultado, splash_para_fechar))
            else:
                inp_menu.after(0, lambda: handle_failure(resultado["mensagem_erro"], resultado.get("imagem_erro"), splash_para_fechar))
        
        worker_thread = threading.Thread(target=tarefa_alvo)
        def iniciar_tarefa_em_thread():
            worker_thread.start()
        
        splash_ref[0] = Loading.Splash(inp_menu, iniciar_tarefa_em_thread)
        splash_ref[0].grab_set()
        splash = splash_ref[0]
        

    # --- Inicialização da Câmera ---
    try:
        dc = DepthCamera()
        ret, _ = dc.get_simple_infrared()
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

    # --- FLUXO 2: Câmera ao Vivo (criação da UI) ---
    janela_tres = tk.Toplevel(inp_menu)
    inp_janela.withdraw()

    tela(janela_tres)
    adicionar_detalhes(janela_tres)
    frame_um, frame_dois = frames_da_tela(janela_tres)
    
    # Passa a função de limpeza diretamente para o botão
    componentes_frame1(frame_um, janela_tres, inp_menu, dc, finalizar_e_limpar_camera)
    
    video_label = tk.Label(frame_dois, bg="white")
    video_label.place(relx=0, rely=0, relwidth=1, relheight=1)
    tamanho = (video_label.winfo_width(), video_label.winfo_height())

    # Crie uma nova função para a captura em lote e agregação
    
    def exibir_video():
        nonlocal processando_foto
        if not video_loop_running[0] or not video_label.winfo_exists():
            return

        if (keyboard.is_pressed('ctrl') or keyboard.is_pressed('right control')) and not processando_foto:
            processando_foto = True
            video_loop_running[0] = False
            ret, frames = dc.only_get_frame()
            _, depth_frame, depth_image, color_frame, infra_image = dc.turn_in_array(frames)
            depth_intrin = dc.get_intrin(depth_frame)
            Abertura = math.degrees(2*math.atan(depth_intrin.width/(2*depth_intrin.fx)))

            pasta_arquivo = fun2.salvar_frames(dc)
            
            if ret:
                id_bico = dados[5]
                nome_arquivo, caminho_fotoBW, _, _ = fun2.tirar_foto(color_frame, infra_image, id_bico)
                
                lista_APP, _, qtd_furos = fun2.organizar_dados_app(dados)
                centro = fun2.definir_centro(tamanho[0], tamanho[1])
                dados_de_entrada = {
                    "model": model, "caminho_fotoBW": caminho_fotoBW, "nome_arquivo": nome_arquivo, 
                    "depth_frame" : depth_frame, "depth_image": depth_image, "Abertura": Abertura, "nome_arquivo_BW": nome_arquivo_BW,
                    "centro": centro, "lista_APP": lista_APP, "qtd_furos": qtd_furos, "caminho_arquivos": pasta_arquivo, "depth_intrin": depth_intrin
                }

                # dados_de_entrada = {
                #     "model": model, "caminho_fotoBW": caminho_fotoBW, "nome_arquivo": nome_arquivo, 
                #     "depth_frame" : depth_frame, "depth_image": depth_image, "Abertura": Abertura, "nome_arquivo_BW": nome_arquivo_BW,
                #     "centro": centro, "lista_APP": lista_APP, "qtd_furos": qtd_furos
                # }

                iniciar_processamento(dados_de_entrada)
            else:
                handle_failure("Falha ao capturar a imagem da câmera.")
            return


        # Lógica de Exibição do Feed
        ret_feed, infra_image_cam = dc.get_simple_infrared()
        if ret_feed:
            back_frame = fun2.sobrepor_molde(infra_image_cam)
            frame = cv2.cvtColor(back_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((video_label.winfo_width(), video_label.winfo_height()))
            image = ImageTk.PhotoImage(image=img)
            video_label.configure(image=image)
            video_label.image = image

        # Agenda o próximo frame se o loop deve continuar
        if video_loop_running[0] and video_label.winfo_exists():
            # Armazena o ID retornado pelo .after() na nossa lista
            after_id[0] = video_label.after(15, exibir_video)


    exibir_video()

    janela_tres.protocol("WM_DELETE_WINDOW", finalizar_e_limpar_camera)
    janela_tres.focus_force()
    janela_tres.grab_set()

    return janela_tres