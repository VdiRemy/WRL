
from tkinter import ttk
import tkinter as tk
from tkinter import messagebox, Canvas
import colorama as color
import FUNCOES_BD
import FUNCOES_TKINTER
from direction import pasta_bd

print("\n\n", color.Fore.GREEN + "Iniciando o código - Registro pre-medição" + color.Style.RESET_ALL)

# --- Funções de Acesso ao Banco de Dados (Corrigidas) ---

def tabela():
    """Busca todos os dados da tabela de empresas de forma segura."""
    conn = None # Garante que 'conn' exista fora do 'try'
    try:
        conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{pasta_bd()}\REGISTROS_WRL.db')
        comando = "SELECT Furos, Grupo, Site, BOF, TIPO, ID, ULTIMA_VIDA FROM DADOS_EMPRESAS"
        cursor.execute(comando)
        dados_tabela = cursor.fetchall()
        return dados_tabela
    except Exception as e:
        print(f"Erro ao buscar dados da tabela: {e}")
        return [] # Retorna lista vazia em caso de erro
    finally:
        # Garante que a desconexão SEMPRE aconteça
        if conn:
            FUNCOES_BD.DESCONECTA_BD(conn)

def buscar_dados_empresa(id_bico, tipo_bico):
    """Busca os dados de uma empresa específica por ID e TIPO de forma segura."""
    conn = None
    try:
        conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{pasta_bd()}\REGISTROS_WRL.db')
        # <-- CORREÇÃO: Query parametrizada para evitar SQL Injection -->
        comando = "SELECT * FROM DADOS_EMPRESAS WHERE ID = ? AND TIPO = ?"
        cursor.execute(comando, (id_bico, tipo_bico))
        dados = cursor.fetchone()
        return dados
    except Exception as e:
        print(f"Erro ao buscar dados da empresa: {e}")
        return None
    finally:
        if conn:
            FUNCOES_BD.DESCONECTA_BD(conn)

def buscar_por_id_na_tabela(id_filtro):
    """Filtra os dados da tabela por ID de forma segura."""
    conn = None
    try:
        conn, cursor = FUNCOES_BD.CONECTA_BD(fr'{pasta_bd()}\REGISTROS_WRL.db')
        comando = "SELECT Furos, Grupo, Site, BOF, TIPO, ID, ULTIMA_VIDA FROM DADOS_EMPRESAS WHERE ID = ?"
        cursor.execute(comando, (id_filtro,))
        dados_filtrados = cursor.fetchall()
        return dados_filtrados
    except Exception as e:
        print(f"Erro ao filtrar por ID: {e}")
        return []
    finally:
        if conn:
            FUNCOES_BD.DESCONECTA_BD(conn)


# --- Funções de Lógica e Validação ---

def ENTRY_INT(inp_text):
    if inp_text == "": return True
    try:
        int(inp_text)
        return True
    except ValueError:
        return False

def validador(input_widget):
    return (input_widget.register(ENTRY_INT), "%P")

def comandos_botao_continuar(inp_janela, inp_usina_grupo, inp_site, inp_BOF, inp_ID, inp_tipo, inp_furos, inp_vida, inp_usuario, inp_menu):
    
    # Validação de campos vazios
    dados_inseridos_list = [
        inp_furos.get(), inp_usina_grupo.get(), inp_site.get(), inp_BOF.get(),
        inp_tipo.get(), inp_ID.get(), inp_usuario.get().upper(), inp_vida.get()
    ]
    if '' in dados_inseridos_list:
        messagebox.showwarning("AVISO", "Preencha todos os espaços")
        return

    # Busca os dados da empresa de forma segura
    dados_empresa = buscar_dados_empresa(inp_ID.get(), inp_tipo.get())
    
    # <-- CORREÇÃO: Verifica se a busca retornou dados antes de usá-los -->
    if dados_empresa is None:
        messagebox.showerror("Erro", f"Não foi possível encontrar o bico com ID '{inp_ID.get()}' e Tipo '{inp_tipo.get()}' na base de dados.")
        return

    ultima_vida_registrada = int(dados_empresa[6])
    vida_atual = int(inp_vida.get())
    print(f"Ultima vida registrada: {ultima_vida_registrada}, Vida atual: {vida_atual}")
    if vida_atual < ultima_vida_registrada:
        messagebox.showwarning("AVISO", f"A vida informada ({vida_atual}) deve ser maior ou igual à última registrada ({ultima_vida_registrada}).")
        return

    if vida_atual == ultima_vida_registrada:
        msg_box = messagebox.askquestion("VIDA EXISTENTE", "Esta já é a última vida registrada.\nDeseja continuar mesmo assim?", icon="warning")
        if msg_box == "no":
            return
            
    # Se todas as validações passaram, continua para a próxima tela
    from INSPECAO_2_WRL import aba_camera
    aba_camera(inp_janela, dados_inseridos_list, inp_menu)

def OnClick(event, listaCli, usina, site, BOF, ID, Furos, Tipo):
    selected_items = listaCli.selection()
    if not selected_items: return
    
    # Pega os valores do item selecionado (apenas o primeiro)
    item_selecionado = listaCli.item(selected_items[0], 'values')
    
    # Limpa e insere os novos valores
    entries = [Furos, usina, site, BOF, Tipo, ID]
    for entry in entries:
        entry.delete(0, tk.END)
        
    Furos.insert(tk.END, item_selecionado[0])
    usina.insert(tk.END, item_selecionado[1])
    site.insert(tk.END, item_selecionado[2])
    BOF.insert(tk.END, item_selecionado[3])
    Tipo.insert(tk.END, item_selecionado[4])
    ID.insert(tk.END, item_selecionado[5])

# --- Funções de Construção da UI (sem alterações significativas) ---

#CORES USADAS
verde = '#416951'
bege = '#C9B783'
marrom = '#68584A'
verde_escuro = '#1F3422'
fundo_branco = 'white'

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
    inp_janela.title("INICIAR INSPECÇÃO")
    inp_janela.configure(background=fundo_branco)
    inp_janela.attributes("-fullscreen", True)
    
def frames_da_tela(inp_janela):
    global frame_1
    frame_1 = tk.Frame(inp_janela, bg=fundo_branco)
    frame_1.place(relx=0.01, rely=0.02, relwidth=0.98, relheight=0.96)
    return frame_1

def componentes_frame1(inp_frame, inp_janela, inp_menu):
    titulo = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Selecionar Bico", fundo_branco, verde_escuro, 'arial', '35', 'bold')
    titulo.place(relx=0.5, rely=0.05, anchor='center')

    # Entradas de texto
    label_usina = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Usina/Grupo: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_usina.place(relx=0.05, rely=0.15)
    input_usina = tk.Entry(inp_frame, font=("Arial", 20))
    input_usina.place(relx=0.05, rely=0.2, relwidth=0.3, relheight=0.06)

    label_site = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Site: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_site.place(relx=0.05, rely=0.3)
    input_site = tk.Entry(inp_frame, font=("Arial", 20))
    input_site.place(relx=0.05, rely=0.35, relwidth=0.3, relheight=0.06)

    label_BOF = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "BOF: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_BOF.place(relx=0.05, rely=0.45)
    input_BOF = tk.Entry(inp_frame, font=("Arial", 20))
    input_BOF.place(relx=0.05, rely=0.5, relwidth=0.3, relheight=0.06)
    
    label_ID = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "ID: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_ID.place(relx=0.05, rely=0.6)
    input_ID = tk.Entry(inp_frame, font=("Arial", 20))
    input_ID.place(relx=0.05, rely=0.65, relwidth=0.13, relheight=0.06)
    
    label_Furos = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Furos: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_Furos.place(relx=0.22, rely=0.6)
    input_Furos = tk.Entry(inp_frame, font=("Arial", 20), validate="key", validatecommand=validador(inp_frame))
    input_Furos.place(relx=0.22, rely=0.65, relwidth=0.13, relheight=0.06)

    label_tipo = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Tipo: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_tipo.place(relx=0.05, rely=0.75)
    input_tipo = tk.Entry(inp_frame, font=("Arial", 20))
    input_tipo.place(relx=0.05, rely=0.8, relwidth=0.13, relheight=0.06)
    
    label_vida = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Vida: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_vida.place(relx=0.22, rely=0.75)
    input_vida = tk.Entry(inp_frame, font=("Arial", 20), validate="key", validatecommand=validador(inp_frame))
    input_vida.place(relx=0.22, rely=0.8, relwidth=0.13, relheight=0.06)

    label_divisor = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "", bege, marrom, 'arial', '20', 'bold')
    label_divisor.place(relx=0.37, rely=0.15, relwidth=0.005, relheight=0.71)
    
    label_usuario = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Usuário: ", fundo_branco, marrom, 'arial', '20', 'bold')
    label_usuario.place(relx=0.4, rely=0.75)
    input_usuario = tk.Entry(inp_frame, font=("Arial", 20))
    input_usuario.place(relx=0.4, rely=0.8, relwidth=0.55, relheight=0.06)

    # Botões
    bt_voltar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "MENU", verde, bege, 3, '20', 'bold', "hand2", lambda: FUNCOES_TKINTER.BOTAO_VOLTAR(inp_menu, inp_janela))
    bt_voltar.place(relx=0.05, rely=0.9, relwidth=0.13, relheight=0.06)

    bt_continuar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "PRÓXIMO", verde, bege, 3, '20', 'bold', "hand2", lambda: comandos_botao_continuar(inp_janela, input_usina, input_site, input_BOF, input_ID, input_tipo, input_Furos, input_vida, input_usuario, inp_menu))
    bt_continuar.place(relx=0.82, rely=0.9, relwidth=0.13, relheight=0.06)
    
    # --- Tabela (Treeview) com Lógica de Busca Refatorada ---
    
    label_aviso = FUNCOES_TKINTER.CRIAR_LABEL(inp_frame, "Clique sobre a\nlinha desejada", bege, verde, 'calibri', '18', 'bold')
    label_aviso.place(relx=0.8, rely=0.15)
    
    filtrar_ID = tk.Entry(inp_frame, font=("Arial", 20), validate="key", validatecommand=validador(inp_frame))
    filtrar_ID.place(relx=0.4, rely=0.2, relwidth=0.1, relheight=0.06)

    Tabela = ttk.Treeview(inp_frame, height=10, column=("col1", "col2", "col3", "col4", "col5", "col6", "col7"), style="mystyle.Treeview")
    
    def popular_tabela(dados):
        """Limpa e popula a tabela com novos dados."""
        Tabela.delete(*Tabela.get_children())
        for dado in dados:
            Tabela.insert("", tk.END, values=dado)

    def buscar_id():
        """Busca por ID ou lista todos se o campo estiver vazio."""
        id_filtro = filtrar_ID.get()
        if not id_filtro:
            dados_tabela = tabela() # Busca todos
        else:
            dados_tabela = buscar_por_id_na_tabela(id_filtro)
            if not dados_tabela:
                messagebox.showwarning("ID Não Encontrado", f"O ID '{id_filtro}' não foi encontrado.")
                dados_tabela = tabela() # Mostra todos novamente se não encontrar
        popular_tabela(dados_tabela)

    bt_buscar = FUNCOES_TKINTER.CRIAR_BOTAO(inp_frame, "Buscar ID", bege, verde, 3, '20', "", "hand2", buscar_id)
    bt_buscar.place(relx=0.5, rely=0.2, relwidth=0.13, relheight=0.06)

    style = ttk.Style()
    style.configure("Treeview.Heading", font=('Verdana', 12, 'bold'))
    style.configure("mystyle.Treeview", highlightthickness=0, bd=0, font=('Verdana', 11))

    Tabela.column("#0", width=0, stretch=tk.NO)
    Tabela.heading("#0", text="")
    Tabela.heading("#1", text="Furos")
    Tabela.heading("#2", text="Grupo")
    Tabela.heading("#3", text="Site")
    Tabela.heading("#4", text="BOF")
    Tabela.heading("#5", text="TIPO")
    Tabela.heading("#6", text="ID")
    Tabela.heading("#7", text="Ult. Vida")
    
    # Configuração de colunas...
    Tabela.column("#1", width=50, anchor='center')
    Tabela.column("#2", width=150)
    Tabela.column("#3", width=80)
    Tabela.column("#4", width=50, anchor='center')
    Tabela.column("#5", width=100, anchor='center')
    Tabela.column("#6", width=50, anchor='center')
    Tabela.column("#7", width=80, anchor='center')

    Tabela.place(relx=0.4, rely=0.29, relwidth=0.55, relheight=0.45)
    scroolLista = tk.Scrollbar(inp_frame, orient='vertical', command=Tabela.yview)
    Tabela.configure(yscrollcommand=scroolLista.set)
    scroolLista.place(relx=0.95, rely=0.29, relwidth=0.01, relheight=0.45)
    Tabela.bind("<ButtonRelease-1>", lambda event: OnClick(event, Tabela, input_usina, input_site, input_BOF, input_ID, input_Furos, input_tipo))
    
    # Popula a tabela inicialmente
    buscar_id()


# --- Função Principal de Entrada ---

def aba_cadastro(inp_janela):
    janela_dois = tk.Toplevel(inp_janela)
    
    tela(janela_dois)
    adicionar_detalhes(janela_dois)
    frames_da_tela(janela_dois)
    componentes_frame1(frame_1, janela_dois, inp_janela)
    
    inp_janela.withdraw()

    janela_dois.transient(inp_janela)
    janela_dois.focus_force()
    janela_dois.grab_set()

    return janela_dois
    
print(color.Fore.RED + "Finalizando o código - Registro pre-medição" + color.Style.RESET_ALL, "\n")