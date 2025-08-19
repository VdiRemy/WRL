from tkinter import ttk, CENTER, messagebox, Canvas
from customtkinter import *
import tkinter as tk
import colorama as color
import FUNCOES_BD
import FUNCOES_TKINTER
from direction import pasta_bd

def ENTRY_INT(inp_text): #Limite do número inteiro do "validador"
    if inp_text == "": return True
    try:
        value = int(inp_text)
    except ValueError: return False
    
    return 0 <= value <= 10000000000 #Qual a vida máxima geralmente?

def validador(input): #Só aceita número inteiro
    return input.register(ENTRY_INT), "%P"

def add_placeholder(entry, placeholder):
    # Adiciona o placeholder inicial
    entry.insert(0, placeholder)
    entry.config(fg='grey', font = ('arial',15))

    def on_focus_in(event):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg='black', font = ('arial',18))

    def on_focus_out(event): 
        if entry.get() == '':
            entry.insert(0, placeholder)
            entry.config(fg='grey', font = ('arial',15))

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    
""" validate= "key",font=("Arial", 18), validatecommand= validador(inp_frame)"""

def ENTRY_STRING(inp_text):
    return all(char.isalpha() or char.isspace() for char in inp_text) or inp_text == ""

def tabela(): # {=========Informações da tabela(FRAME 2)=========}
    conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{pasta_bd()}\REGISTROS_WRL.db')
    comando = f"SELECT * FROM DADOS_EMPRESAS "
    cursor.execute(comando)
    dados_tabela =cursor.fetchall()
    FUNCOES_BD.DESCONECTA_BD(conn)

    return dados_tabela

#CORES USADAS
verde = '#416951' #Cor botão
bege = '#C9B783' #Cor botão
marrom = '#68584A' 
verde_escuro = '#1F3422' #Titulos
fundo_branco = 'white' #fundo das letras em frames brancos

def adicionar_detalhes(inp_menu):
    largura = inp_menu.winfo_screenwidth()
    altura = inp_menu.winfo_screenheight()

    # Cria um Frame para o Canvas, que ficará no fundo
    canvas_frame = tk.Frame(inp_menu, width=largura, height=altura, bg= fundo_branco)
    canvas_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    canvas = Canvas(canvas_frame, width=largura, height=altura, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Triângulo vermelho no canto superior direito
    canvas.create_polygon(largura, 0, largura, 300, largura-300, 0, fill="#94031E", outline="#94031E")

    # Triângulo verde no canto inferior esquerdo
    canvas.create_polygon(0, altura, 0, altura-300, 300, altura, fill=verde, outline=verde)

def tela(inp_janela):
    inp_janela.title("CADASTRAR USINA")
    inp_janela.configure(background= fundo_branco)
    inp_janela.attributes("-fullscreen", True)
    # inp_janela.geometry("1200x600")
    # inp_janela.resizable(True, True) #se quiser impedir que amplie ou diminua a tela, altere para False
    # inp_janela.maxsize(width=1200, height=600) #limite máximo da tela
    # inp_janela.minsize(width=700, height=450) #limite minimo da tela

def frames_da_tela(inp_janela): 
    global frame_1
    frame_1 = tk.Frame( inp_janela,
                        bg= fundo_branco)
    frame_1.place(relx=0.01, rely=0.02,relwidth=0.98, relheight=0.96)

def componentes_frame1(inp_frame,inp_janela, inp_menu):
    # {=======================Títulos=========================}
    titulo_1 = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Cadastrar Usina", fundo_branco, verde_escuro, 'arial', '25', 'bold')
    titulo_1.place(relx=0.15, rely=0.05) 
    
    titulo_2 = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Primeiro Registro\nda nova Usina", fundo_branco, verde_escuro, 'arial', '25', 'bold')
    titulo_2.place(relx =0.65, rely=0.05)

    # {=======================USINA - PAÍS=========================}
    label_usina_pais = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "País: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_usina_pais.place(relx=0.03, rely=0.3)

    input_usina_pais = tk.Entry(inp_frame, validate= "key",font=("Arial", 18),  validatecommand="key")
    input_usina_pais.place(relx=0.12, rely=0.3, relwidth=0.34, relheight=0.07)
    vcmd2 = (input_usina_pais.register(ENTRY_STRING), '%P')
    input_usina_pais.config(validatecommand = vcmd2)

    # {=======================USINA - ESTADO=========================}
    label_usina_estado = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Estado: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_usina_estado.place(relx=0.03, rely=0.45)

    estados_brasileiros = [ "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", 
                            "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO" ]
    
    estado_var = StringVar()
    estado_combobox = ttk.Combobox(inp_frame, textvariable = estado_var, font=("Arial", 18), state="readonly")
    estado_combobox['values'] = estados_brasileiros
    estado_combobox.place(relx=0.12, rely=0.45, relwidth=0.35, relheight=0.07)
    
    # {=======================USINA - NOME=========================}
    label_usina_nome = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Usina: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_usina_nome.place(relx=0.03, rely=0.6)

    input_usina_nome = tk.Entry(inp_frame, validate= "key",font=("Arial", 18),  validatecommand="key")
    input_usina_nome.place(relx=0.11, rely=0.6, relwidth=0.35, relheight=0.07)
    
    # {=======================SITE=========================}
    label_site = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Site: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_site.place(relx=0.03, rely=0.75)

    input_site = tk.Entry(inp_frame, validate= "key",font=("Arial", 18),  validatecommand="key")
    input_site.place(relx=0.11, rely=0.75, relwidth=0.35, relheight=0.07)

    # {=======================Divisória=========================}
    label_divisor = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "", bege, marrom, 'arial', '20', 'bold')
    label_divisor.place(relx=0.5, rely=0.1, relwidth=0.005, relheight=0.85)
    
    # {=======================FUROS=========================}
    label_furos = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Furos: ", fundo_branco, marrom, 'arial', '20', 'bold' )
    label_furos.place(relx=0.53, rely=0.3)

    input_furos = tk.Entry(inp_frame, validate= "key",font=("Arial", 18),  validatecommand= validador(inp_frame))
    input_furos.place(relx=0.63, rely=0.3, relwidth=0.26, relheight=0.07)
    
    # {=======================TIPO=========================}
    label_tipo = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Tipo: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_tipo.place(relx=0.53, rely=0.45)

    input_tipo = tk.Entry(inp_frame,font=("Arial", 18))
    input_tipo.place(relx=0.63, rely=0.45, relwidth=0.26, relheight=0.07)
    add_placeholder(input_tipo, "externa/interna")
    
    # {=======================BOF=========================}
    label_BOF = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "BOF: ", fundo_branco, marrom, 'arial', '20', 'bold' )
    label_BOF.place(relx=0.53, rely=0.6)

    input_BOF = tk.Entry(inp_frame, validate= "key",font=("Arial", 18),  validatecommand= validador(inp_frame))
    input_BOF.place(relx=0.63, rely=0.6, relwidth=0.26, relheight=0.07)
    
    # {=======================ID=========================}
    label_ID = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "ID: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_ID.place(relx=0.53, rely=0.75)

    input_ID = tk.Entry(inp_frame, validate= "key",font=("Arial", 18),  validatecommand= validador(inp_frame))
    input_ID.place(relx=0.63, rely=0.75, relwidth=0.26, relheight=0.07)
    
    # {=======================Botão Voltar, Continuar e excluir=========================}
    bt_voltar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "VOLTAR",verde, bege,3,'15','bold',"hand2",lambda: FUNCOES_TKINTER.BOTAO_VOLTAR( inp_menu, inp_janela))
    bt_voltar.place(relx=0.05, rely=0.89, relwidth=0.2, relheight=0.08)
    
    # bt_continuar = fun1.CRIAR_BOTAO(inp_frame, "DELETAR", verde, bege,3,'15','bold',"hand2")#,lambda: deletar(inp_menu, inp_janela)
    # bt_continuar.place(relx=0.4, rely=0.89, relwidth=0.2, relheight=0.08)

    bt_continuar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "SALVAR",verde, bege,3,'15','bold',"hand2", lambda: salvar(inp_menu, inp_janela))#,
    bt_continuar.place(relx=0.75, rely=0.89, relwidth=0.2, relheight=0.08)

    # {======================= Mostrando avisos =========================}
    def salvar(aba_1, aba_2):
        # {======================= Dados Obtidos =========================}
        dados_obtidos = []
        input_grupo = input_usina_nome.get().upper() + '/' + estado_combobox.get() + '/' + input_usina_pais.get().upper()

        dados_obtidos.append(input_furos.get().replace(" ", ""))
        
        if input_grupo != '//':
            dados_obtidos.append(input_grupo.replace(" ", ""))
        else:
            dados_obtidos.append('')
        
        dados_obtidos.append(input_site.get().replace(" ", ""))
        dados_obtidos.append(input_BOF.get().replace(" ", ""))
        
        if input_tipo.get() != 'externa/interna':
            dados_obtidos.append(input_tipo.get().replace(" ", ""))
        else:
            dados_obtidos.append('')
        
        dados_obtidos.append(input_ID.get().replace(" ", ""))
        dados_obtidos.append('0') #vida inicial
        
        todos_tabela = tabela()

        # Verificar se todos os campos de usina foram preenchidos
        flag = True
        
        if input_usina_nome.get() == '' or estado_combobox.get() == '' or  input_usina_pais.get() == '' or input_site.get()== ''  :
            flag = False

        if not flag:
            messagebox.showwarning("AVISO","Preencha os dados de usina")
            return

        # Verificar se o registro já existe
        if tuple(dados_obtidos) in todos_tabela:
            messagebox.showwarning("AVISO","Já existe este registro")
            return

        # Verificar se o ID já existe
        flag = False
        for tupla in todos_tabela:
            ultimo_algarismo_tupla = str(tupla[-2])  # Obtém o último dígito da tupla
            if dados_obtidos[5] == ultimo_algarismo_tupla:
                flag = True
                messagebox.showwarning("AVISO","Este ID já existe")
                break
        
        # Registrar só a usina e não lança
        if dados_obtidos[0] == '' and dados_obtidos[3] == '' and dados_obtidos[4] == '' and dados_obtidos[5] == '' and dados_obtidos[1] != '' and dados_obtidos[2] != '' and dados_obtidos[6] != '':
            flag = True

        else:
            if dados_obtidos[0] == '' or dados_obtidos[3] == '' or dados_obtidos[4] == '' or dados_obtidos[5] == '' :
                messagebox.showwarning("AVISO","Preencha todos os dados da lança\nou não preencha nenhum (Furos, Tipo, BOF e ID)")
                flag = False
                return

    
        conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{pasta_bd()}\REGISTROS_WRL.db')
        conn.commit()
        comando = f"INSERT INTO DADOS_EMPRESAS VALUES (?, ?, ?, ?, ?, ?, ?)"
        registros = (dados_obtidos[0], dados_obtidos[1], dados_obtidos[2], dados_obtidos[3], dados_obtidos[4],  dados_obtidos[5], dados_obtidos[6])
        cursor.execute(comando, registros)
        conn.commit()
        print("\n\n", color.Fore.CYAN + "DADOS SALVOS - CADASTRO_BICO_WRL" + color.Style.RESET_ALL)
        FUNCOES_BD.DESCONECTA_BD(conn)
        FUNCOES_TKINTER.BOTAO_VOLTAR(aba_1, aba_2)
    
def aba_cadastro_usina(inp_janela):
    janela_atual = tk.Toplevel(inp_janela)
    tela(janela_atual)
    adicionar_detalhes(janela_atual)
    frames_da_tela(janela_atual)
    componentes_frame1(frame_1, janela_atual, inp_janela)
    
    janela_atual.transient(inp_janela)
    janela_atual.focus_force()
    janela_atual.grab_set()
    return janela_atual