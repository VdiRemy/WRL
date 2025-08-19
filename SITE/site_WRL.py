import streamlit as st
import plotly.express as px
import pandas as pd
import os
import warnings 
from PIL import Image
from datetime import datetime
import locale
import sqlite3 as sql
import matplotlib.pyplot as plt
import numpy as np
import sys

#acessar pasta principal para importar os módulos de lá
pasta_sup = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(pasta_sup)
from direction import folder, pasta_bd

warnings.filterwarnings("ignore")  # ->ignorar os erros que aparecem no site

pasta = folder()

# VERSÃO 17/07/2024

# {=======================Estilos da página=========================}

st.set_page_config(page_title= "Homepage WRL", page_icon=":clipboard:", layout="wide")  #->Titulo da aba no navegador
page_bg_img =""" <style>
[data-testid="stAppViewContainer"] {
             background-color: #E5E0D8;
             }

             [data-testid="stHeader"] {
             background-color: rgba(0,0,0,0);
             }

             [data-testid="stSidebar"]{
             background-color: #B3B792;
             }
             </style>"""

st.markdown(page_bg_img, unsafe_allow_html=True)

# {=======================Imagens=========================}

image_4F = Image.open(fr'{pasta}\SITE\4Furos.jpeg')
image_5F = Image.open(fr'{pasta}\SITE\5Furos.jpeg')
image_6F = Image.open(fr'{pasta}\SITE\6Furos.jpeg') 
imagem_LOGOS = Image.open(fr'{pasta}\SITE\ifes.png')

# {=======================Título=========================}

st.title("Registros de Desgaste de Furo de Lança de Convertedores LD")
st.markdown('<style>div.block-container{padding-top:1rem;}</> ',unsafe_allow_html=True)

# {=======================Barra de seleção=========================}

#st.sidebar.header("Bem-vindo!")
st.sidebar.header("Wear Register Lances")

# {=======================Seleção de Bico=========================}
conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

table_names = []
dfs = {}

for table in tables:
    table_name = table[0]
    table_names.append(table_name)
    cursor.execute(f"SELECT * FROM {table_name};")
    rows = cursor.fetchall()
    dfs[table_name] = pd.DataFrame(rows, columns=[i[0] for i in cursor.description])

table_names = table_names[1:]

conn.close()

# {=======================Leitura de arquivo=========================}

selected_tables = st.sidebar.multiselect("LANÇA:", table_names, placeholder="Selecione uma opção")

if selected_tables:

    os.chdir(fr"{pasta}")
    
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
    cursor = conn.cursor()
    print("Conectado ao banco de dados")

    comando = f"SELECT * FROM {selected_tables[0]}"
    cursor.execute(comando)
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=[i[0] for i in cursor.description])

    conn.close()
    print("Desconectado do banco de dados")

    # Filtra o grupo
    limite = 1
    grupo = st.sidebar.multiselect("GRUPO:", df["GRUPO"].unique(), placeholder="Selecione uma opção")
    if not grupo:
        df2 = df.copy()  # tem todos os dados 
    else:
        aviso_grupo = grupo
        grupo = grupo[:limite]
        df2 = df[df["GRUPO"].isin(grupo)]   # Só tem dados do grupo selecionado
        if len(aviso_grupo) > limite:
            st.sidebar.warning("Selecione no máximo uma opção de grupo")
        
    # Filtra o site
    site = st.sidebar.multiselect("SITE:".format(limite), df2["SITE"].unique(), placeholder="Selecione uma opção")
    if not site:
        df3 = df2.copy()
    else:
        aviso_site = site
        site = site[:limite]
        df3 = df2[df2["SITE"].isin(site)]  # Só tem dados do site selecionado
        
        if len(aviso_site) > limite:
            st.sidebar.warning("Selecione no máximo uma opção de site")

    # Filtra o ID com base no site selecionado
    id = st.sidebar.multiselect("ID:".format(limite), df3["ID"].unique(), placeholder="Selecione uma opção")
    if not id:
        df6 = df3.copy()  # tem todos os dados 
    else:
        aviso_id = id
        id = id[:limite]
        df6 = df3[df3["ID"].isin(id)]   # Só tem dados do ID selecionado
        if len(aviso_id) > limite:
            st.sidebar.warning("Selecione no máximo uma opção de ID")
    
        #print('df6: ', df6)
        
# {=======================Logos IFES e fuso horário=========================}
st.sidebar.image(imagem_LOGOS, width=250) 

locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
data_atual = datetime.today()
data_formatada = data_atual.strftime("%d de %B de %Y - %H:%M")
st.sidebar.write(data_formatada)

# {=======================Texto na página=========================}
st.markdown('''<div style="text-align: justify;">
            <H4>
            </H4></div>
            ''', unsafe_allow_html=True)

# # {======================= Parte superior da tela =========================}
if not selected_tables:
    # # {======================= Gráficos de pizza =========================}
    # # {======================= Para USIMINAS/ES/BRASIL =========================}
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    query = "SELECT GERAL, COUNT(*) as quantidade FROM B6 WHERE GRUPO = 'USIMINAS/ES/BRASIL' GROUP BY GERAL"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Verificando os estados
    df = df[df['GERAL'].isin(['Bom', 'Estável', 'Crítico'])]

    # Definindo as cores para cada estado
    colors = {
        'Bom': '#88DF76',
        'Estável': '#D4884A',
        'Crítico': '#CF5B47'}

    # Mapeando as cores para os estados
    state_colors = [colors[state] for state in df['GERAL']]

    # Criando o gráfico de pizza
    fig1, ax = plt.subplots(figsize=(4, 4))
    ax.pie(df['quantidade'], labels=df['GERAL'], colors=state_colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    ax.set_title('GRUPO USIMINAS/ES/BRASIL')
    # Remover fundo
    fig1.patch.set_visible(False)  # Remove o fundo da figura
    ax.axis('off')  # Remove o eixo

    # # # {======================= Para MINERADORA/BH/BRASIL =========================}
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    query = "SELECT GERAL, COUNT(*) as quantidade FROM B6 WHERE GRUPO = 'MINERADORA/BH/BRASIL' GROUP BY GERAL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Verificando os estados
    df = df[df['GERAL'].isin(['Bom', 'Estável', 'Crítico'])]
    # Mapeando as cores para os estados
    state_colors = [colors[state] for state in df['GERAL']]

   # Criando o gráfico de pizza
    fig2, ax = plt.subplots(figsize=(4, 4))
    ax.pie(df['quantidade'], labels=df['GERAL'], colors=state_colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    ax.set_title('GRUPO MINERADORA/BH/BRASIL')
    # Remover fundo
    fig2.patch.set_visible(False)  # Remove o fundo da figura
    ax.axis('off')  # Remove o eixo

    # # {======================= Tabelas =========================}
    # # {======================= ID X ESTADO =========================}
    # USIMINAS/ES/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    cursor = conn.cursor()
    # Extraindo dados ID e ESTADO do banco 
    comando = "SELECT ID, GERAL FROM B6 WHERE GRUPO = 'USIMINAS/ES/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()

    tabela1_US = pd.DataFrame(resultados, columns=["ID", "ESTADO GERAL DAS LANÇAS"])
    # Removendo duplicatas com base na coluna 'ID'
    tabela1_US = tabela1_US.drop_duplicates(subset='ID')
    # Ordenando em ordem crescente pelo 'ID'
    tabela1_US = tabela1_US.sort_values(by='ID')

     # MINERADORA/BH/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    cursor = conn.cursor()
    # Extraindo dados ID e ESTADO do banco 
    comando = "SELECT ID, GERAL FROM B6 WHERE GRUPO = 'MINERADORA/BH/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()

    tabela1_MN = pd.DataFrame(resultados, columns=["ID", "ESTADO GERAL DAS LANÇAS"])
    # Removendo duplicatas com base na coluna 'ID'
    tabela1_MN = tabela1_MN.drop_duplicates(subset='ID')
    # Ordenando em ordem crescente pelo 'ID'
    tabela1_MN = tabela1_MN.sort_values(by='ID')

    # # {======================= ID X MANUTENÇÃO =========================}
    # USIMINAS/ES/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
    cursor = conn.cursor()
    # Extraindo dados ID, VIDA e DATA do banco
    comando = "SELECT ID, VIDA, DATA FROM B6 WHERE GRUPO = 'USIMINAS/ES/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()
    # Criando um DataFrame
    tabela = pd.DataFrame(resultados, columns=["ID", "VIDA", "DATA DA ÚLTIMA MANUTENÇÃO"])
    # Encontrando o índice da maior VIDA para cada ID
    idx = tabela.groupby('ID')['VIDA'].idxmax()
    # Selecionando as linhas com a maior VIDA para cada ID
    tabela2_US = tabela.loc[idx, ['ID', 'DATA DA ÚLTIMA MANUTENÇÃO']]
    # Ordenando em ordem crescente pelo 'ID'
    tabela2_US = tabela2_US.sort_values(by='ID')

    # MINERADORA/BH/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
    cursor = conn.cursor()
    # Extraindo dados ID, VIDA e DATA do banco
    comando = "SELECT ID, VIDA, DATA FROM B6 WHERE GRUPO = 'MINERADORA/BH/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()
    # Criando um DataFrame
    tabelaMN = pd.DataFrame(resultados, columns=["ID", "VIDA", "DATA DA ÚLTIMA MANUTENÇÃO"])
    # Encontrando o índice da maior VIDA para cada ID
    idx = tabelaMN.groupby('ID')['VIDA'].idxmax()
    # Selecionando as linhas com a maior VIDA para cada ID
    tabela2_MN = tabelaMN.loc[idx, ['ID', 'DATA DA ÚLTIMA MANUTENÇÃO']]
    # Ordenando em ordem crescente pelo 'ID'
    tabela2_MN = tabela2_MN.sort_values(by='ID')

    # Função para aplicar estilos - Tabela USIMINAS
    def highlight_cols(s):
        return ['background-color: #d9d9d9']*len(s)

    # Aplicando estilos
    tabela1_US = tabela1_US.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '500px'
    }).apply(highlight_cols, axis=1)

    tabela2_US = tabela2_US.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '150px'
    }).apply(highlight_cols, axis=1)

    # Aplicando estilos - Tabela MINERADORA
    tabela1_MN = tabela1_MN.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '500px'
    }).apply(highlight_cols, axis=1)

    tabela2_MN = tabela2_MN.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '150px'
    }).apply(highlight_cols, axis=1)


    # Exibindo os gráfico e tabelas
    col1_US, col2_US, col3_US = st.columns(3)
    with col1_US:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>SITUAÇÃO GERAL DAS LANÇAS</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.pyplot(fig1)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2_US:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>a) Estado das lanças</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela1_US,hide_index=True)
        
    with col3_US:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>b) Últimos registros</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela2_US,hide_index=True)
    st.divider()

    # Exibindo os gráfico e tabelas
    col1_MN, col2_MN, col3_MN = st.columns(3)
    with col1_MN:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>SITUAÇÃO GERAL DAS LANÇAS</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.pyplot(fig2)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2_MN:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>a) Estado das lanças</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela1_MN,hide_index=True)
    with col3_MN:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>b) Últimos registros</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela2_MN,hide_index=True)
  

# {=======================Informações com a pré-seleção=========================}
# {========= Filtros para o gráfico =========}
if selected_tables and not grupo:
    # # {======================= Gráfico de pizza - Considerando lanças de 4 e 6 furos =========================}
    # # {======================= Para USIMINAS/ES/BRASIL =========================}
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    query = "SELECT GERAL, COUNT(*) as quantidade FROM B6 WHERE GRUPO = 'USIMINAS/ES/BRASIL' GROUP BY GERAL"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Verificando os estados
    df = df[df['GERAL'].isin(['Bom', 'Estável', 'Crítico'])]

    # Definindo as cores para cada estado
    colors = {
        'Bom': '#88DF76',
        'Estável': '#D4884A',
        'Crítico': '#CF5B47'}

    # Mapeando as cores para os estados
    state_colors = [colors[state] for state in df['GERAL']]

    # Criando o gráfico de pizza
    fig1, ax = plt.subplots(figsize=(4, 4))
    ax.pie(df['quantidade'], labels=df['GERAL'], colors=state_colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    ax.set_title('GRUPO USIMINAS/ES/BRASIL')
    # Remover fundo
    fig1.patch.set_visible(False)  # Remove o fundo da figura
    ax.axis('off')  # Remove o eixo

    # # # {======================= Para MINERADORA/BH/BRASIL =========================}
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    query = "SELECT GERAL, COUNT(*) as quantidade FROM B6 WHERE GRUPO = 'MINERADORA/BH/BRASIL' GROUP BY GERAL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Verificando os estados
    df = df[df['GERAL'].isin(['Bom', 'Estável', 'Crítico'])]
    # Mapeando as cores para os estados
    state_colors = [colors[state] for state in df['GERAL']]

   # Criando o gráfico de pizza
    fig2, ax = plt.subplots(figsize=(4, 4))
    ax.pie(df['quantidade'], labels=df['GERAL'], colors=state_colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    ax.set_title('GRUPO MINERADORA/BH/BRASIL')
    # Remover fundo
    fig2.patch.set_visible(False)  # Remove o fundo da figura
    ax.axis('off')  # Remove o eixo

    # # {======================= Tabelas =========================}
    # # {======================= ID X ESTADO =========================}
    # USIMINAS/ES/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    cursor = conn.cursor()
    # Extraindo dados ID e ESTADO do banco 
    comando = "SELECT ID, GERAL FROM B6 WHERE GRUPO = 'USIMINAS/ES/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()

    tabela1_US = pd.DataFrame(resultados, columns=["ID", "ESTADO GERAL DAS LANÇAS"])
    # Removendo duplicatas com base na coluna 'ID'
    tabela1_US = tabela1_US.drop_duplicates(subset='ID')
    # Ordenando em ordem crescente pelo 'ID'
    tabela1_US = tabela1_US.sort_values(by='ID')

     # MINERADORA/BH/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    cursor = conn.cursor()
    # Extraindo dados ID e ESTADO do banco 
    comando = "SELECT ID, GERAL FROM B6 WHERE GRUPO = 'MINERADORA/BH/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()

    tabela1_MN = pd.DataFrame(resultados, columns=["ID", "ESTADO GERAL DAS LANÇAS"])
    # Removendo duplicatas com base na coluna 'ID'
    tabela1_MN = tabela1_MN.drop_duplicates(subset='ID')
    # Ordenando em ordem crescente pelo 'ID'
    tabela1_MN = tabela1_MN.sort_values(by='ID')

    # # {======================= ID X MANUTENÇÃO =========================}
    # USIMINAS/ES/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
    cursor = conn.cursor()
    # Extraindo dados ID, VIDA e DATA do banco
    comando = "SELECT ID, VIDA, DATA FROM B6 WHERE GRUPO = 'USIMINAS/ES/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()
    # Criando um DataFrame
    tabela = pd.DataFrame(resultados, columns=["ID", "VIDA", "DATA DA ÚLTIMA MANUTENÇÃO"])
    # Encontrando o índice da maior VIDA para cada ID
    idx = tabela.groupby('ID')['VIDA'].idxmax()
    # Selecionando as linhas com a maior VIDA para cada ID
    tabela2_US = tabela.loc[idx, ['ID', 'DATA DA ÚLTIMA MANUTENÇÃO']]
    # Ordenando em ordem crescente pelo 'ID'
    tabela2_US = tabela2_US.sort_values(by='ID')

    # MINERADORA/BH/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
    cursor = conn.cursor()
    # Extraindo dados ID, VIDA e DATA do banco
    comando = "SELECT ID, VIDA, DATA FROM B6 WHERE GRUPO = 'MINERADORA/BH/BRASIL'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()
    # Criando um DataFrame
    tabelaMN = pd.DataFrame(resultados, columns=["ID", "VIDA", "DATA DA ÚLTIMA MANUTENÇÃO"])
    # Encontrando o índice da maior VIDA para cada ID
    idx = tabelaMN.groupby('ID')['VIDA'].idxmax()
    # Selecionando as linhas com a maior VIDA para cada ID
    tabela2_MN = tabelaMN.loc[idx, ['ID', 'DATA DA ÚLTIMA MANUTENÇÃO']]
    # Ordenando em ordem crescente pelo 'ID'
    tabela2_MN = tabela2_MN.sort_values(by='ID')

    # Função para aplicar estilos - Tabela USIMINAS
    def highlight_cols(s):
        return ['background-color: #d9d9d9']*len(s)

    # Aplicando estilos
    tabela1_US = tabela1_US.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '500px'
    }).apply(highlight_cols, axis=1)

    tabela2_US = tabela2_US.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '150px'
    }).apply(highlight_cols, axis=1)

    # Aplicando estilos - Tabela MINERADORA
    tabela1_MN = tabela1_MN.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '500px'
    }).apply(highlight_cols, axis=1)

    tabela2_MN = tabela2_MN.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '150px'
    }).apply(highlight_cols, axis=1)
    
    # Exibindo os gráfico e tabelas
    col1_US, col2_US, col3_US = st.columns(3)
    with col1_US:
        st.markdown(f"""<h2 style='font-size:18px; text-align:center;'>SITUAÇÃO GERAL DAS LANÇAS - {selected_tables[0]} </h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.pyplot(fig1)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2_US:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>a) Estado das lanças</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela1_US,hide_index=True)
        
    with col3_US:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>b) Últimos registros</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela2_US,hide_index=True)
    st.divider()

    # Exibindo os gráfico e tabelas
    col1_MN, col2_MN, col3_MN = st.columns(3)
    with col1_MN:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>SITUAÇÃO GERAL DAS LANÇAS</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.pyplot(fig2)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2_MN:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>a) Estado das lanças</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela1_MN,hide_index=True)
    with col3_MN:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>b) Últimos registros</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela2_MN,hide_index=True)

if selected_tables and grupo:
    # Gráfico 
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    query = f"SELECT GERAL, COUNT(*) as quantidade FROM {selected_tables[0]} WHERE GRUPO = '{grupo[0]}' GROUP BY GERAL"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Verificando os estados
    df = df[df['GERAL'].isin(['Bom', 'Estável', 'Crítico'])]

    # Definindo as cores para cada estado
    colors = {
        'Bom': '#88DF76',
        'Estável': '#D4884A',
        'Crítico': '#CF5B47'}

    # Mapeando as cores para os estados
    state_colors = [colors[state] for state in df['GERAL']]

    # Criando o gráfico de pizza
    fig3, ax = plt.subplots(figsize=(4, 4))
    ax.pie(df['quantidade'], labels=df['GERAL'], colors=state_colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    ax.set_title(f'{grupo[0]}')
    # Remover fundo
    fig3.patch.set_visible(False)  # Remove o fundo da figura
    ax.axis('off')  # Remove o eixo

    # # {======================= Tabelas =========================}
    # Função para aplicar estilos 
    def highlight_cols(s):
        return ['background-color: #d9d9d9']*len(s)

    # # {======================= ID X ESTADO =========================}
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    cursor = conn.cursor()
    # Extraindo dados ID e ESTADO do banco 
    comando = f"SELECT ID, GERAL FROM {selected_tables[0]} WHERE GRUPO = '{grupo[0]}'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()

    tabela1 = pd.DataFrame(resultados, columns=["ID", "ESTADO GERAL DAS LANÇAS"])
    # Removendo duplicatas com base na coluna 'ID'
    tabela1 = tabela1.drop_duplicates(subset='ID')
    # Ordenando em ordem crescente pelo 'ID'
    tabela1 = tabela1.sort_values(by='ID')

    # # {======================= ID X MANUTENÇÃO =========================}
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_WRL.db')
    cursor = conn.cursor()
    # Extraindo dados ID, VIDA e DATA do banco
    comando = f"SELECT ID, VIDA, DATA FROM {selected_tables[0]} WHERE GRUPO = '{grupo[0]}'"
    cursor.execute(comando)
    # Obter os resultados
    resultados = cursor.fetchall()
    conn.close()
    # Criando um DataFrame
    tabela2 = pd.DataFrame(resultados, columns=["ID", "VIDA", "DATA DA ÚLTIMA MANUTENÇÃO"])
    # Encontrando o índice da maior VIDA para cada ID
    idx = tabela2.groupby('ID')['VIDA'].idxmax()
    # Selecionando as linhas com a maior VIDA para cada ID
    tabela2 = tabela2.loc[idx, ['ID', 'DATA DA ÚLTIMA MANUTENÇÃO']]
    # Ordenando em ordem crescente pelo 'ID'
    tabela2 = tabela2.sort_values(by='ID')

    # Aplicando estilos
    tabela1 = tabela1.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '500px'
    }).apply(highlight_cols, axis=1)

    tabela2 = tabela2.style.set_table_styles(
        [{'selector': 'th', 'props': [('font-size', '16px')]}]
    ).set_properties(**{
        'text-align': 'center',
        'width': '150px'
    }).apply(highlight_cols, axis=1)

    # Exibindo os gráfico e tabelas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<h2 style='font-size:18px; text-align:center;'>SITUAÇÃO GERAL DAS LANÇAS - {selected_tables[0]} </h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.pyplot(fig3)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>a) Estado das lanças</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela1,hide_index=True)
        
    with col3:
        st.markdown("""<h2 style='font-size:18px; text-align:center;'>b) Últimos registros</h2>""", unsafe_allow_html=True)
        st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
        st.dataframe(tabela2,hide_index=True)
    st.divider()

if id and selected_tables:
    # {=======================Gráfico de pizza=========================}
    # Gráfico para USIMINAS/ES/BRASIL
    conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
    query = f"SELECT ESTADO, COUNT(*) as quantidade FROM {selected_tables[0]} WHERE GRUPO = '{grupo[0]}' AND ID = '{id[0]}' GROUP BY ESTADO"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Verificando os estados
    df = df[df['ESTADO'].isin(['Bom', 'Estável', 'Crítico'])]

    # Definindo as cores para cada estado
    colors = {
        'Bom': '#88DF76',
        'Estável': '#D4884A',
        'Crítico': '#CF5B47'}

    # Mapeando as cores para os estados
    state_colors = [colors[state] for state in df['ESTADO']]

    # Criando o gráfico de pizza
    fig_id, ax = plt.subplots(figsize=(4, 4))
    ax.pie(df['quantidade'], labels=df['ESTADO'], colors=state_colors, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  
    ax.set_title(f'Situação dos furos da lança {id[0]}')
    fig_id.set_size_inches(2, 2)  # Ajuste o tamanho da figura (largura, altura)
    # Remover fundo
    fig_id.patch.set_visible(False)  # Remove o fundo da figura
    ax.axis('off')  # Remove o eixo

    # {=======================Gráfico principal=========================}

    st.markdown(f"# Gráfico de desgaste - Análise com todos os diâmetros\n # ID: {', '.join(id)}")

    filtered_df = df3[df3["ID"].isin(id)] # Gráficos gerados a partir do id
    #print('filtered: ', filtered_df)

    #{=======================Seleção de Datas=========================}
    col1, col2 = st.columns((2))
    
    startDate = pd.to_datetime(filtered_df["DATA"]).min()
    endDate = pd.to_datetime(filtered_df["DATA"]).max()
    
    with col1:
        date1 = st.date_input("Data de início", startDate, format="DD/MM/YYYY")

    with col2:
        date2 = st.date_input("Data final", endDate, format="DD/MM/YYYY")

    # Filtrar os diâmetros exibidos por data
    df_date = pd.to_datetime(filtered_df['DATA'])
    
    inicio = pd.to_datetime(date1)
    fim = pd.to_datetime(date2)
    
    filtered_df_date = filtered_df[
    (df_date >= pd.to_datetime(date1)) &
    (df_date <= pd.to_datetime(date2))
    ]

    if inicio > endDate or fim < startDate:
        st.write(f'Não há registros no intervalo de data informado')

    else:
    # Selecionar as colunas desejadas
        if not filtered_df.empty:
            # Transformar o DataFrame para o formato longo
            long_df = pd.melt(filtered_df_date, id_vars=['ID','VIDA'], 
                            value_vars=df3.columns[11:],
                            var_name='Região', value_name='DIÂMETRO [mm²]')

            # Criar o gráfico de linhas
            fig = px.line(long_df, 
                        x='VIDA', 
                        y='DIÂMETRO [mm²]', 
                        color='Região', 
                        line_group='ID', 
                        markers=True, 
                        template='seaborn', 
                        facet_col='ID', 
                        title="Valores dos Diâmetros ao Longo da Vida")

            # Exibir o gráfico no Streamlit
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            #{=======================Segundo gráfico=========================}
            vida = st.selectbox("Vida:".format(limite), filtered_df_date["VIDA"].unique(), placeholder="Selecione uma opção") 

            # Filtrar linhas
            filtro_vida = filtered_df[filtered_df['VIDA'] == vida]

            if not filtro_vida.empty:
                # Pegar o primeiro valor encontrado na coluna 'VIDA' correspondente
                registro = filtro_vida['ARQUIVO'].values[0]
                data = filtro_vida['DATA'].values[0]
                hora = filtro_vida['HORA'].values[0]
                tipo = filtro_vida['TIPO'].values[0]
                usuario = filtro_vida['USUARIO'].values[0]
            else:
                st.write("Registro não localizado")
            
            # {=======================Gráfico de pizza=========================}
            # Gráfico para USIMINAS/ES/BRASIL
            conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
            query = f"SELECT ESTADO, COUNT(*) as quantidade FROM {selected_tables[0]} WHERE GRUPO = '{grupo[0]}' AND ID = '{id[0]}' AND VIDA = '{vida}' GROUP BY ESTADO"
            df = pd.read_sql_query(query, conn)
            conn.close()

            # Verificando os estados
            df = df[df['ESTADO'].isin(['Bom', 'Estável', 'Crítico'])]

            # Definindo as cores para cada estado
            colors = {
                'Bom': '#88DF76',
                'Estável': '#D4884A',
                'Crítico': '#CF5B47'}

            # Mapeando as cores para os estados
            state_colors = [colors[state] for state in df['ESTADO']]

            # Criando o gráfico de pizza
            fig_vida, ax = plt.subplots(figsize=(4, 4))
            ax.pie(df['quantidade'], labels=df['ESTADO'], colors=state_colors, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  
            fig_vida.set_size_inches(2, 2)  # Ajuste o tamanho da figura (largura, altura)
            # Remover fundo
            fig_vida.patch.set_visible(False)  # Remove o fundo da figura
            ax.axis('off')  # Remove o eixo

            # # {======================= REGIÃO X DIAMETROS =========================}
            conn = sql.connect(fr'{pasta_bd()}\REGISTROS_DESGASTE.db')
            cursor = conn.cursor()
            # Extraindo dados ID e ESTADO do banco 
            comando = f"SELECT REGIÃO, MEDIDA, ESTADO FROM {selected_tables[0]} WHERE GRUPO = '{grupo[0]}' AND VIDA = '{vida}'"
            cursor.execute(comando)
            # Obter os resultados
            resultados = cursor.fetchall()
            conn.close()

            tabela2 = pd.DataFrame(resultados, columns=["REGIÃO", "DIÂMETROS", "ESTADO"])
            # Removendo duplicatas com base na coluna 'ID'
            tabela2 = tabela2.drop_duplicates(subset='REGIÃO')
            # Ordenando em ordem crescente pelo 'ID'
            tabela2 = tabela2.sort_values(by='REGIÃO')
            
            image_7F = Image.open(fr'{pasta}\FOTOS_GUIA\{registro}') 

            # Exibindo os gráfico e tabelas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""<h2 style='font-size:18px; text-align:center;'>REGISTRO</h2>""", unsafe_allow_html=True)
                st.image(image_7F, caption='Segmentação')
            with col2:
                st.markdown("""<h2 style='font-size:18px; text-align:center;'>a) DIÂMETROS</h2>""", unsafe_allow_html=True)
                st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
                st.dataframe(tabela2,hide_index=True)
            with col3:
                st.markdown(f"""<h2 style='font-size:18px; text-align:center;'>SITUAÇÃO DOS FUROS - VIDA {vida} </h2>""", unsafe_allow_html=True)
                st.markdown("<div style='display:flex; justify-content:center;'>", unsafe_allow_html=True)
                st.pyplot(fig_vida)
                st.markdown("</div>", unsafe_allow_html=True)
            st.divider()
            
        else:
            st.write("Selecione pelo menos um ID para visualizar os dados.")
    
        st.markdown(f"# Gráfico de desgaste - Diâmetros específicos\n # ID: {', '.join(id)}")
        
        # Selecionar a coluna desejada para plotar
        selected_column = st.multiselect("Selecione a região desejada:", df3.columns[11:], placeholder="Selecione uma opção")

        if not filtered_df.empty:
            if selected_column:
                # Renomear a coluna selecionada para "Diâmetro (mm²)"
                long_df2 = pd.melt(filtered_df_date, id_vars=['ID','VIDA'], 
                                value_vars=selected_column, 
                                var_name='Região', value_name='DIÂMETRO [mm²]')
    
                # Criar o gráfico de linhas
                fig = px.line(long_df2, 
                            x='VIDA', 
                            y='DIÂMETRO [mm²]', 
                            color='Região', 
                            line_group='ID', 
                            markers=True, 
                            template='seaborn', 
                            facet_col='ID', 
                            title=f"Valores dos Diâmetros ao Longo da Vida")
                
                # Exibir o gráfico no Streamlit
                st.plotly_chart(fig, use_container_width=True)
                st.divider()

            else:
                st.write("Selecione a região desejada para exibir o gráfico")
                
        else:
            st.write("Nenhum dado disponível para a região selecionada.")

# # {=======================Créditos=========================}

# st.caption('Este é um Projeto desenvolvido por alunos do **IFES** com os seguintes colaboradores:')
# col1, col2 = st.columns(2)
# with col1:
#     st.caption('**Orientador:** Gustavo Maia de Almeida')
#     st.caption('**Co-orientador:** Caio Mario Carletti Vilela Santos')
#     st.divider()
    
#     st.caption('**3D Protótipo:** Robson Almeida de Souza')
#     st.caption('**3D Protótipo:** Waleska Sulke dos Santos')
#     st.caption('**3D Protótipo:** Matheus Policário Amorim')
    
# with col2:
#     st.caption('**Melhorias de precisão:** Davi Nobel Vilela de Souza')
#     st.caption('**Melhorias de precisão:** Júlia Rosa Celante')
#     st.caption('**Melhorias de precisão:** Remerson Victor Silva da Assurreição')
#     st.caption('**Melhorias de precisão:** Caio victor delaqua Lima')
#     st.caption('**Melhorias de precisão:** Arthur Candido Maria')
    
#     st.caption('**Plataforma Online:** Waleska Sulke dos Santos')
#     st.caption('**Plataforma Online:** Júlia Rosa Celante')
    
# st.divider()