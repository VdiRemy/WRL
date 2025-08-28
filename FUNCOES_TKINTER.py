import tkinter as tk
from PIL import Image, ImageTk

def CRIAR_FRAME(inp_frame, inp_bg, inp_light = None):
    frame = tk.Frame(inp_frame,
                    bg= inp_bg,
                    highlightbackground= inp_light)
    return frame

def CRIAR_BOTAO(inp_frame, inp_texto, inp_bg, inp_fg, inp_borda = None,inp_tamanho= None, inp_style = None, inp_cursor = None, inp_comando = None, inp_imagem=None, imagem_posicao='left'):
    imagem = None
    
    if inp_imagem:
        try:
            imagem = Image.open(inp_imagem)
            imagem = imagem.resize((100, 100))  # Redimensionar a imagem se necessário
            imagem = ImageTk.PhotoImage(imagem)
        except Exception as e:
            print(f"Erro ao carregar a imagem: {e}")
            imagem = None
            
    botao = tk.Button(  inp_frame, # frame
                        text = inp_texto, # texto
                        bg = inp_bg, # background
                        fg = inp_fg, # 
                        bd = inp_borda, #borda do botão
                        font= ("calibri", inp_tamanho ,inp_style), #fonte, tamanho, style
                        cursor = inp_cursor, # estilo do cursor
                        command = inp_comando,
                        relief='groove',
                        image= imagem,  # imagem no botão
                        compound = imagem_posicao  # posição da imagem em relação ao texto
                     )
    botao.imagem = imagem 
    return botao
    
def CRIAR_LABEL(inp_frame, inp_texto, inp_bg, inp_fg, inp_fonte = None, inp_tam_fonte = None, inp_style = None):
    label = tk.Label(inp_frame, # frame
                    text = inp_texto, # texto
                    bg = inp_bg, # background
                    fg = inp_fg, # cor da letra
                    font = (inp_fonte, inp_tam_fonte, inp_style))#fonte, tamanho, style
    return label

def BOTAO_VOLTAR(aba_1, aba_2): #sai da aba atual e volta para a anterior
    aba_1.deiconify()  # Exiba a janela anterior
    aba_2.destroy()  # Destrua a janela atual