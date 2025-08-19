from tkinter import ttk, CENTER, messagebox, Canvas
from customtkinter import *
import tkinter as tk
import colorama as color
import FUNCOES_BD
import FUNCOES_TKINTER
from direction import pasta_bd

caminho = pasta_bd()

def USINAS():
    conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{caminho}\REGISTROS_WRL.db')
    comando = f"SELECT Grupo FROM DADOS_EMPRESAS "
    cursor.execute(comando)
    dados_banco = cursor.fetchall()
    FUNCOES_BD.DESCONECTA_BD(conn)

    dados_filtrados = list(set(item[0] for item in dados_banco))
    if not dados_filtrados:
        return ["---Nenhuma Usina Cadastrada---"]
    else:
        return dados_filtrados

def USINA_SITE(inp_usina):
    conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{caminho}\REGISTROS_WRL.db')
    comando = f"SELECT Site FROM DADOS_EMPRESAS WHERE Grupo = '{inp_usina}'"
    cursor.execute(comando)
    dados_banco = cursor.fetchall()
    FUNCOES_BD.DESCONECTA_BD(conn)
    
    dados_filtrados = list(set(item[0] for item in dados_banco))
    return dados_filtrados

def SITE():
    conn, cursor = FUNCOES_BD.CONECTA_BD(caminho)
    comando = f"SELECT Site FROM DADOS_EMPRESAS "
    cursor.execute(comando)
    dados_banco = cursor.fetchall()
    FUNCOES_BD.DESCONECTA_BD(conn)
    
    dados_filtrados = list(set(item[0] for item in dados_banco))
    return dados_filtrados

def tabela(): # {=========Informações da tabela(FRAME 2)=========}
    conn, cursor = FUNCOES_BD.CONECTA_BD((fr'{caminho}\REGISTROS_WRL.db'))
    comando = f"SELECT * FROM DADOS_EMPRESAS "
    cursor.execute(comando)
    dados_tabela =cursor.fetchall()
    FUNCOES_BD.DESCONECTA_BD(conn)

    return dados_tabela

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
            entry.config(fg='black', font=('Arial', 18))

    def on_focus_out(event): 
        if entry.get() == '':
            entry.insert(0, placeholder)
            entry.config(fg='grey', font=('Arial', 15))

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

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
    canvas_frame = tk.Frame(inp_menu, width=largura, height=altura, bg=fundo_branco)
    canvas_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    canvas = Canvas(canvas_frame, width=largura, height=altura, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Triângulo vermelho no canto superior direito
    canvas.create_polygon(largura, 0, largura, 300, largura-300, 0, fill="#94031E", outline="#94031E")

    # Triângulo verde no canto inferior esquerdo
    canvas.create_polygon(0, altura, 0, altura-300, 300, altura, fill=verde, outline=verde)
    
def tela(inp_janela):
    inp_janela.title("CADASTRAR BICO")
    inp_janela.configure(background= fundo_branco)
    inp_janela.attributes("-fullscreen", True)
    # inp_janela.geometry("1200x600")
    # inp_janela.resizable(True, True) #se quiser impedir que amplie ou diminua a tela, altere para False
    # inp_janela.maxsize(width=1200, height=600) #limite máximo da tela
    # inp_janela.minsize(width=700, height=450) #limite minimo da tela

def frames_da_tela(inp_janela): 
    global frame_1, frame_2
    frame_1 = tk.Frame( inp_janela,
                        bg= fundo_branco)
    frame_1.place(relx=0.01, rely=0.02,relwidth=0.43, relheight=0.96)

    frame_2 = tk.Frame( inp_janela,
                        bg= fundo_branco)
    frame_2.place(relx=0.45, rely=0.02,relwidth=0.54, relheight=0.96)
    
def componentes_frame1(inp_frame,inp_janela, inp_menu):
    #OBS: por filtros pro ID, tipo e BOF( para não confundir os locais),mas para isso preciso de parametrosoferecidos pelo cliente
    # {=======================Título=========================}
    titulo = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Cadastrar Bico", fundo_branco, verde_escuro, 'arial', '25', 'bold')
    titulo.place(relx=0.3, rely=0.05) 

    # {=======================USINA=========================}
    label_usina = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Usina: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_usina.place(relx=0.03, rely=0.2)

    Var_Usina = tk.StringVar(inp_frame)

    input_Usina = tk.OptionMenu(inp_frame, Var_Usina, *USINAS()) 
    input_Usina.config(font=("Arial", 18))
    input_Usina.place(relx=0.2, rely=0.2, relwidth=0.75, relheight=0.07)

    # {=======================SITE=========================}
    label_site = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Site: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_site.place(relx=0.03, rely=0.35)

    Var_site = tk.StringVar(inp_frame)

    def update_sites(*args):
        selected_usina = Var_Usina.get()
        sites = USINA_SITE(selected_usina) if selected_usina else SITE()
        menu = input_site["menu"]
        menu.delete(0, "end")
        for site in sites:
            menu.add_command(label=site, command=lambda s=site: Var_site.set(s))

    Var_Usina.trace("w", update_sites)

    input_site = tk.OptionMenu(inp_frame, Var_site, "") 
    input_site.config(font=("Arial", 18))
    input_site.place(relx=0.15, rely=0.35, relwidth=0.8, relheight=0.07)

    # {=======================FUROS=========================}
    label_furos = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Furos: ", fundo_branco, marrom, 'arial', '20', 'bold' )
    label_furos.place(relx=0.03, rely=0.5)

    input_furos = tk.Entry(inp_frame, validate= "key",font=("Arial", 18), validatecommand= validador(inp_frame))
    input_furos.place(relx=0.2, rely=0.5, relwidth=0.26, relheight=0.07)
    
    # {=======================TIPO=========================}
    label_tipo = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Tipo: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_tipo.place(relx=0.49, rely=0.5)

    input_tipo = tk.Entry(inp_frame,font=("Arial", 18))
    input_tipo.place(relx=0.64, rely=0.5, relwidth=0.26, relheight=0.07)
    add_placeholder(input_tipo, "externa/interna")
    
    # {=======================BOF=========================}
    label_BOF = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "BOF: ", fundo_branco, marrom, 'arial', '20', 'bold' )
    label_BOF.place(relx=0.03, rely=0.65)

    input_BOF = tk.Entry(inp_frame, validate= "key",font=("Arial", 18), validatecommand= validador(inp_frame))
    input_BOF.place(relx=0.2, rely=0.65, relwidth=0.26, relheight=0.07)
    
    # {=======================ID=========================}
    label_ID = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "ID: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_ID.place(relx=0.49, rely=0.65)

    input_ID = tk.Entry(inp_frame, validate= "key",font=("Arial", 18), validatecommand= validador(inp_frame))
    input_ID.place(relx=0.64, rely=0.65, relwidth=0.26, relheight=0.07)
    
    # {=======================Botão Voltar, Continuar e excluir=========================}
    bt_voltar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "VOLTAR",verde, bege,3,'18','bold',"hand2",lambda: FUNCOES_TKINTER.BOTAO_VOLTAR( inp_menu, inp_janela))
    bt_voltar.place(relx=0.05, rely=0.89, relwidth=0.2, relheight=0.08)
    
    bt_continuar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "DELETAR", verde, bege,3,'18','bold',"hand2",lambda: deletar(inp_menu, inp_janela))
    bt_continuar.place(relx=0.4, rely=0.89, relwidth=0.2, relheight=0.08)

    bt_continuar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "SALVAR",verde, bege,3,'18','bold',"hand2",lambda: salvar(inp_menu, inp_janela))
    bt_continuar.place(relx=0.75, rely=0.89, relwidth=0.2, relheight=0.08)
    
    # {======================= Mostrando avisos =========================}
    def salvar(aba_1, aba_2):
        dados_obtidos = []
        
        dados_obtidos.append(input_furos.get())
        dados_obtidos.append(Var_Usina.get())
        dados_obtidos.append(Var_site.get())
        dados_obtidos.append(input_BOF.get())
        dados_obtidos.append(input_tipo.get())
        dados_obtidos.append(input_ID.get())
        dados_obtidos.append('0') #vida inicial
        
        todos_tabela = tabela()
        print('\nDados obtidos - CADASTRO_BICO_WRL: ', dados_obtidos)
        
        flag = True
        for dado in dados_obtidos:
            if dado == '':
                flag = False
                break
        
        if not flag: # Verificar se todos os campos foram preenchidos
            messagebox.showwarning("AVISO","Preencha todos os espaços")
            return

        if tuple(dados_obtidos) in todos_tabela: # Verificar se o registro já existe
            messagebox.showwarning("AVISO","Já existe este registro")
            return

        flag = False
        for tupla in todos_tabela: # Verificar se o ID já existe
            ultimo_algarismo_tupla = str(tupla[-2])
            if dados_obtidos[5] == ultimo_algarismo_tupla:
                flag = True
                messagebox.showwarning("AVISO","Este ID já existe")
                break
        
        if flag:
            return
        
        conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{caminho}\REGISTROS_WRL.db')
        conn.commit()
        comando = f"INSERT INTO DADOS_EMPRESAS VALUES (?, ?, ?, ?, ?, ?, ?)"
        registros = (dados_obtidos[0], dados_obtidos[1], dados_obtidos[2], dados_obtidos[3], dados_obtidos[4],  dados_obtidos[5], dados_obtidos[6])
        cursor.execute(comando, registros)
        conn.commit()
        print("\n\n", color.Fore.CYAN + "DADOS SALVOS - CADASTRO_BICO_WRL" + color.Style.RESET_ALL)
        FUNCOES_BD.DESCONECTA_BD(conn)
        messagebox.showinfo("showinfo", "Dados salvos com sucesso")
        FUNCOES_TKINTER.BOTAO_VOLTAR(aba_1, aba_2)
    
    def deletar(aba_1, aba_2):
        dados_obtidos = []
            
        dados_obtidos.append(input_furos.get())
        dados_obtidos.append(Var_Usina.get())
        dados_obtidos.append(Var_site.get())
        dados_obtidos.append(input_BOF.get())
        dados_obtidos.append(input_tipo.get())
        dados_obtidos.append(input_ID.get())

        todos_tabela = tabela()
        todos_tabela = [linha[:-1] for linha in todos_tabela]

        flag = True
        for dado in dados_obtidos:
            if dado == '':
                flag = False
                break

        if not flag:
            messagebox.showwarning("AVISO","Preencha todos os espaços")
            return

        # Verificar se o registro já existe
        if tuple(dados_obtidos) in todos_tabela:
            resposta = messagebox.askokcancel("askokcancel", f"Tem certeza que deseja\n excluir os dados deste ID?")
            if resposta:
                print(f"Deletando {dados_obtidos}")
                conn, cursor = FUNCOES_BD.CONECTA_BD(caminho)
                comando = f"DELETE FROM DADOS_EMPRESAS WHERE ID = ? "
                cursor.execute(comando, (input_ID.get(),))
                conn.commit()
                print("\n\n", color.Fore.RED + "DADOS DELETADOS - CADASTRO_BICO_WRL" + color.Style.RESET_ALL)
                FUNCOES_BD.DESCONECTA_BD(conn)

                messagebox.showinfo("showinfo", "Dados deletados")
        else:
            messagebox.showwarning("AVISO","Registro não encontrado")
            return
        
        FUNCOES_TKINTER.BOTAO_VOLTAR(aba_1, aba_2)
    
def componentes_frame2(inp_frame):
    # {=======================Título=========================}
    titulo = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Bicos Registrados", fundo_branco, verde_escuro, 'arial', '25', 'bold')
    titulo.place(relx =0.3, rely=0.05) 
    
    Tabela = ttk.Treeview(inp_frame, height=10,column=("col1", "col2", "col3", "col4", "col5","col6","col7" ),style="mystyle.Treeview")

    style = ttk.Style()
    style.configure("Treeview.Heading", font=('Verdana', 12,'bold'))
    style.configure("mystyle.Treeview", highlightthickness=0, bd=0, font=('Verdana', 11))

    Tabela.column("#0", width=0, stretch=tk.NO)# Ocultando a primeira coluna
    Tabela.heading("#0", text="")

    Tabela.heading("#1", text="Furos")
    Tabela.heading("#2", text="Grupo")
    Tabela.heading("#3", text="Site")
    Tabela.heading("#4", text="BOF")
    Tabela.heading("#5", text="TIPO")
    Tabela.heading("#6", text="ID")
    Tabela.heading("#7", text="Ult. Vida")
    
    Tabela.column("#1", width=15, anchor='center')
    Tabela.column("#2", width=150)
    Tabela.column("#3", width=75)
    Tabela.column("#4", width=10, anchor='center')
    Tabela.column("#5", width=15, anchor='center')
    Tabela.column("#6", width=10, anchor='center')
    Tabela.column("#7", width=15, anchor='center')
    
    for dado in tabela():
        Tabela.insert("", tk.END, values=(dado[0], dado[1], dado[2], dado[3], dado[4], dado[5], dado[6]))
        
    Tabela.place(relx=0.05, rely=0.2, relwidth=0.89, relheight=0.75)
    
    scroolLista = tk.Scrollbar(inp_frame, orient='vertical', command=Tabela.yview)
    Tabela.configure(yscrollcommand = scroolLista.set)
    scroolLista.place(relx=0.94, rely=0.2, relwidth=0.02, relheight=0.75)
       
def aba_cadastro_bico(inp_janela):
    janela_atual = tk.Toplevel(inp_janela)
    tela(janela_atual)
    adicionar_detalhes(janela_atual)
    frames_da_tela(janela_atual)
    componentes_frame1(frame_1, janela_atual, inp_janela)
    componentes_frame2(frame_2)
    
    janela_atual.transient(inp_janela)
    janela_atual.focus_force()
    janela_atual.grab_set()
    return janela_atual