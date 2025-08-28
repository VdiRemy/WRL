import sqlite3 as sql
from customtkinter import *
from direction import pasta_bd

def CONECTA_BD(inp_caminho):
    conn = sql.connect(inp_caminho, timeout=10)
    cursor = conn.cursor(); print("\nConectando ao BD - FUNCOES_WRL")
    return conn, cursor
    
def DESCONECTA_BD(conn):
    conn.close(); print("Desconectando do BD - FUNCOES_WRL\n")

def buscar_registro_por_arquivo(nome_tabela, nome_arquivo):
    """
    Busca um registro em uma tabela específica (B4 ou B6) pelo nome do arquivo.
    É segura contra SQL Injection e flexível.
    """
    # 1. Validação de Segurança: Garante que apenas B4 ou B6 possam ser consultadas.
    #    Isso previne SQL Injection no nome da tabela.
    if nome_tabela not in ['B4', 'B6']:
        print(f"ERRO DE SEGURANÇA: Tentativa de consultar tabela não permitida: {nome_tabela}")
        return None

    conn, cursor = CONECTA_BD(fr"{pasta_bd()}\REGISTROS_WRL.db")
    dados_encontrados = None
    try:
        # 2. Query Segura e Dinâmica:
        #    O nome da tabela é inserido de forma segura (após validação).
        #    O valor do arquivo é passado como um parâmetro '?' para segurança.
        comando = f"SELECT * FROM {nome_tabela} WHERE ARQUIVO = ?"
        
        # Executa a query com o parâmetro em uma tupla
        cursor.execute(comando, (nome_arquivo,))
        dados_encontrados = cursor.fetchone()
        print("dados encontrados: ", dados_encontrados)
        
    except Exception as e:
        print(f"Erro ao buscar dados no banco de dados: {e}")
        # Garante que None seja retornado em caso de erro
        dados_encontrados = None
        print(f"dados encontrados {dados_encontrados}")
        
    finally:
        # Garante que a desconexão sempre ocorra
        DESCONECTA_BD(conn)
        
    print(f"Retorno da busca na tabela {nome_tabela}: {dados_encontrados}")
    return dados_encontrados