from tkinter import ttk, CENTER, Canvas, messagebox
import tkinter as tk
import sqlite3 as sql
import colorama as color
import customtkinter
from PIL import Image, ImageTk
import pyrealsense2 as rs
import FUNCOES_BD
import FUNCOES_TKINTER
import FUNCOES_CAMERA_WRL as fun2 #Funcções para camêra
from direction import folder, pasta_bd
import os

pasta = folder()

#CORES USADAS
verde = '#416951' #Cor botão
bege = '#C9B783' #Cor botão
marrom = '#68584A'
verde_escuro = '#1F3422' #Titulos
fundo_branco = 'white' #fundo das letras em frames brancos

def selecao(inp_ID, inp_tipo): # {=========Leitura Grupo, SIte, BOF e ID(FRAME 1)=========}
    global ID
    
    inp_ID = int(inp_ID)
    ID = inp_ID
    
    conn, cursor = FUNCOES_BD.CONECTA_BD(fr"{pasta_bd()}\REGISTROS_WRL.db")
    
    # <-- CORREÇÃO: Query parametrizada para evitar SQL Injection -->
    comando = "SELECT * FROM DADOS_EMPRESAS WHERE ID = ? AND TIPO = ?"
    cursor.execute(comando, (inp_ID, inp_tipo))
    
    dados = cursor.fetchall()
    FUNCOES_BD.DESCONECTA_BD(conn)
    
    if not dados:
        messagebox.showerror("Erro", f"Nenhum dado de empresa encontrado para ID {inp_ID} e Tipo {inp_tipo}.")
        return None, None
        
    grupo_completo = list(dados[0])
    dados = [item for sublist in dados for item in sublist]
    grupo_completo = grupo_completo[0]
    lista_grupo = grupo_completo.split('/')
    
    return dados, lista_grupo

# A função 'tabela' antiga foi removida, pois será substituída pela chamada à nova função.

def imagens(registro_foto): # {=========Informações para imagens(FRAME 2)=========}
    
    endereco_pastafotos = fr"{pasta}\FOTOS_ANALISE"
    endereco_pastaguias = fr"{pasta}\FOTOS_GUIA"
    
    # Trata o caso de registro_foto ser None para evitar crash
    if registro_foto is None:
        return None, None
    arquivofoto = os.path.join(endereco_pastafotos, registro_foto)
    arquivoguia = os.path.join(endereco_pastaguias, registro_foto)
    return arquivofoto, arquivoguia

def voltar_menu(aba_menu, insp_1,insp_2, insp_3):
    aba_menu.deiconify() # Exiba a janela da aba 1
    insp_3.destroy()  # Destrua a janela da aba 2
    insp_2.destroy()  # Destrua a janela cadastro
    insp_1.destroy()

def adicionar_detalhes(inp_menu):
    largura = inp_menu.winfo_screenwidth()
    altura = inp_menu.winfo_screenheight()
    canvas_frame = tk.Frame(inp_menu, width=largura, height=altura, bg=fundo_branco)
    canvas_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    canvas = Canvas(canvas_frame, width=largura, height=altura, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.create_polygon(largura, 0, largura, 300, largura-300, 0, fill="#94031E", outline="#94031E")
    canvas.create_polygon(0, altura, 0, altura-300, 300, altura, fill=verde, outline=verde)

def tela(inp_janela):
    inp_janela.title("DADOS DA INSPECÇÃO")
    inp_janela.configure(background= fundo_branco)
    inp_janela.attributes("-fullscreen", True)
    
def frames_da_tela(inp_janela):
    global frame_1, frame_2
    frame_1 = tk.Frame(inp_janela, bd=2, bg=fundo_branco, highlightthickness=1)
    frame_1.place(relx=0.4, rely=0.02, relwidth=0.59, relheight=0.96)
    frame_2 = tk.Frame(inp_janela, bd=2, bg=fundo_branco, highlightthickness=1)
    frame_2.place(relx=0.01, rely=0.02, relwidth=0.38, relheight=0.96)
    return frame_1, frame_2

def componentes_frame1(inp_ID, qtd_furos, inp_tipo, int_arquivo, inp_menu, janela_cadastro1, janela_cadastro2, inp_janela):
    dados, lista_grupo = selecao(inp_ID, inp_tipo)
    
    if dados is None: # Se a seleção inicial falhar, para a execução
        voltar_menu(inp_menu, janela_cadastro1, janela_cadastro2, inp_janela)
        return

    grupo = dados[1]
    site = dados[2]
    BOF = dados[3]
    ID = dados[5]
    vida = dados[6]
    
    # --- CORREÇÃO PRINCIPAL ABAIXO ---

    # 1. Determina qual tabela buscar com base na 'qtd_furos'
    # print(f"inp_ID {inp_ID},\n inp_tipo {inp_tipo},\n int_arquivo {int_arquivo},\n inp_menu {inp_menu},\n janela_cadastro1 {janela_cadastro1},\n janela_cadastro2 {janela_cadastro2},\n inp_janela {inp_janela}")
    
    if '4' in qtd_furos:
        tabela_para_buscar = 'B4'
    elif '6' in qtd_furos:
        tabela_para_buscar = 'B6'
    else:
        messagebox.showerror("Erro de Lógica", f"Não foi possível determinar a tabela para o tipo: {inp_tipo}")
        return

    # 2. Chama a nova função segura, passando a tabela e o arquivo corretos
    print(f"verificando se dados do {int_arquivo} estao em {tabela_para_buscar}")
    dados2 = FUNCOES_BD.buscar_registro_por_arquivo(tabela_para_buscar, int_arquivo)
    
    # 3. Adiciona a verificação de segurança para o resultado
    if dados2 is None:
        messagebox.showerror("Erro de Dados", f"Não foi possível encontrar os dados para o arquivo '{int_arquivo}' na tabela '{tabela_para_buscar}'.")
        return

    # O resto do código continua igual, mas agora com a certeza de que 'dados2' não é None
    
    data_foto = dados2[9]
    hora_foto = dados2[10]
    medidas_foto = dados2[11:]
    print("medidas foto", medidas_foto)
    
    # ... (O resto da sua função 'componentes_frame1' para criar os labels e a tabela ttk continua aqui) ...
    # ... (Copie e cole o restante da sua função original a partir daqui) ...
    # {=======================Título=========================}
    titulo1_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1, "Dados do Bico",fundo_branco,"#2F4F4F",'arial', '25', 'bold')
    titulo1_pg1.place(relx=0.32, rely=0.03)
    # {=======================Grupo=========================}
    grupo_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"Grupo:",fundo_branco,verde_escuro,'verdana', '20','bold')
    grupo_pg1.place(relx=0.05, rely=0.15)
    grupo_pg1 = tk.Label(frame_1, text=grupo, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    grupo_pg1.place(relx=0.2, rely=0.15)
    # {=======================Site=========================}
    site_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"Site:",fundo_branco,verde_escuro,'verdana', '20','bold')
    site_pg1.place(relx=0.05, rely=0.25)
    site_pg1 = tk.Label(frame_1, text=site, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    site_pg1.place(relx=0.15, rely=0.25)
    # {=======================BOF=========================}
    BOF_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"BOF:",fundo_branco,verde_escuro,'verdana', '20','bold')
    BOF_pg1.place(relx=0.05, rely=0.35)
    site_pg1 = tk.Label(frame_1, text=BOF, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    site_pg1.place(relx=0.15, rely=0.35)
    # {=======================ID=========================}
    ID_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"ID:",fundo_branco,verde_escuro,'verdana', '20','bold')
    ID_pg1.place(relx=0.05, rely=0.45)
    ID_informado_pg1 = tk.Label(frame_1, text=ID, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    ID_informado_pg1.place(relx=0.12, rely=0.45)
    # {=======================Data=========================}
    Data_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"Data:",fundo_branco,verde_escuro,'verdana', '20','bold')
    Data_pg1.place(relx=0.05, rely=0.6)
    Data_informado_pg1 = tk.Label(frame_1, text=data_foto, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    Data_informado_pg1.place(relx=0.17, rely=0.6)
    # {=======================Hora=========================}
    Hora_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"Hora:",fundo_branco,verde_escuro,'verdana', '20','bold')
    Hora_pg1.place(relx=0.05, rely=0.7)
    Hora_informado_pg1 = tk.Label(frame_1, text=hora_foto, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    Hora_informado_pg1.place(relx=0.17, rely=0.7)
    # {=======================Vida=========================}
    Vida_pg1 = FUNCOES_TKINTER.CRIAR_LABEL(frame_1,"Vida:",fundo_branco,verde_escuro,'verdana', '20','bold')
    Vida_pg1.place(relx=0.05, rely=0.8)
    Vida_informado_pg1 = tk.Label(frame_1, text=vida, font=('verdana', '20'), bg=fundo_branco, fg=verde_escuro)
    Vida_informado_pg1.place(relx=0.17, rely=0.8)
    # {=======================Botão Continuar=========================}
    btContinuar_pg1 = tk.Button(frame_1, text='MENU', cursor="hand2", bd=4, bg=verde, fg=bege, font=("arial", 13, 'bold'), command=lambda: voltar_menu(inp_menu, janela_cadastro1, janela_cadastro2, inp_janela))
    btContinuar_pg1.place(relx=0.55, rely=0.9, relwidth=0.12, relheight=0.08)
    # {=======================Registros=========================}
    tabela_pg1 = ttk.Treeview(frame_1, height=12, column=("col1", "col2"), style="mystyle.Treeview")
    style = ttk.Style()
    style.configure("Treeview.Heading", font=('Verdana', 15, 'bold'))
    style.configure("mystyle.Treeview", highlightthickness=0, bd=0, font=('Verdana', 13))
    tabela_pg1.column("#0", width=0, stretch=tk.NO)
    tabela_pg1.heading("#0", text="")
    tabela_pg1.heading("#1", text="Classe")
    tabela_pg1.heading("#2", text="Diametro(mm)")
    tabela_pg1.column("#1", width=150, anchor='center')
    tabela_pg1.column("#2", width=200, anchor='center')
    i = 1
    for dado in medidas_foto:
        if i == 1:
            tabela_pg1.insert("", tk.END, values=('Bico', dado))
        else:
            tabela_pg1.insert("", tk.END, values=(f'Furo {i-1}', dado))
        i += 1
    tabela_pg1.place(relx=0.45, rely=0.35, relwidth=0.5, relheight=0.5)


def componentes_frame2(inp_janela, nome_arquivo):
    
    # A função 'imagens' parece redundante aqui, podemos pegar os caminhos diretamente.
    # Vamos assumir que 'nome_arquivo' é o caminho completo da foto principal.
    # Se 'imagens' for necessária para encontrar a foto guia, mantenha-a.
    arquivofoto, arquivoguia = imagens(nome_arquivo)
    print('\nArquivo_foto=', arquivofoto, '\nArquivo guia= ', arquivoguia)

    # --- VERIFICAÇÃO DE ARQUIVOS ---
    if arquivofoto is None or not os.path.exists(arquivofoto):
        print(f"AVISO: Arquivo de foto não encontrado: {arquivofoto}")
        messagebox.showwarning("Imagem não encontrada", "Não foi possível carregar a imagem da análise.")
        return
    if arquivoguia is None or not os.path.exists(arquivoguia):
        print(f"AVISO: Arquivo guia não encontrado: {arquivoguia}")
        messagebox.showwarning("Imagem não encontrada", "Não foi possível carregar a imagem guia.")
        return

    print("arquivos verificados")
    try:
        # --- CORREÇÃO: Carregando a Imagem 1 (Foto da Análise) com Pillow ---
        # 1. Abre a imagem com a biblioteca PIL (Pillow)
        pil_image1 = Image.open(arquivofoto)
        
        # 2. Redimensiona a imagem para um tamanho fixo (ajuste conforme necessário)
        #    Isso é mais flexível que o subsample.
        pil_image1 = pil_image1.resize((400, 300), Image.Resampling.LANCZOS)
        
        # 3. Converte a imagem do Pillow para um formato que o Tkinter entende
        img1_pg1 = ImageTk.PhotoImage(pil_image1)
        
        fotoimg1_pg1 = tk.Label(frame_2, borderwidth=3, highlightthickness=4, 
                                highlightbackground='gray', bg=fundo_branco, image=img1_pg1)
        
        # Guarda uma referência da imagem para evitar que ela seja deletada pelo garbage collector
        fotoimg1_pg1.image = img1_pg1 
        fotoimg1_pg1.place(relx=0.5, rely=0.25, anchor=CENTER)

        # --- CORREÇÃO: Carregando a Imagem 2 (Guia) com Pillow ---
        pil_image2 = Image.open(arquivoguia)
        pil_image2 = pil_image2.resize((400, 300), Image.Resampling.LANCZOS)
        img2_pg1 = ImageTk.PhotoImage(pil_image2)

        fotoimg2_pg1 = tk.Label(frame_2, borderwidth=3, highlightthickness=4,
                                highlightbackground='gray', bg=fundo_branco, image=img2_pg1)
        
        # Guarda a referência da segunda imagem
        fotoimg2_pg1.image = img2_pg1
        fotoimg2_pg1.place(relx=0.5, rely=0.7, anchor=CENTER)

        # --- WRL Label ---
        titulo2_pg1 = tk.Label(frame_2, text="Wear Register Lances (WRL)",
                               font=('italic', '18'), bg=fundo_branco, fg="#94031E")
        titulo2_pg1.place(relx=0.01, rely=0.94)
        
    except Exception as e:
        messagebox.showerror("Erro ao Carregar Imagem", f"Não foi possível carregar as imagens.\n\nErro: {e}")
        print(f"ERRO CRÍTICO ao carregar imagens com Pillow: {e}")

def aba_dados(inp_janela, qtd_furos,inp_ID,inp_tipo, int_arquivo,inp_menu,janela_cadastro1):
    janela = tk.Toplevel(inp_janela)
    tela(janela)
    adicionar_detalhes(janela)
    frames_da_tela(janela)
    componentes_frame1(inp_ID, qtd_furos, inp_tipo, int_arquivo,inp_menu,janela_cadastro1,inp_janela,janela)
    componentes_frame2(janela, int_arquivo)
    
    janela.transient(inp_janela)
    janela.focus_force()
    janela.grab_set()
    janela.deiconify()
    print("fim da aba dados")
    return janela
    
print("\n\n", color.Fore.GREEN + "Iniciando o código - Dados do bico" + color.Style.RESET_ALL)
print(color.Fore.RED + "Finalizando o código - Dados do bico" + color.Style.RESET_ALL, "\n")