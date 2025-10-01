import cv2
import numpy as np
import pyrealsense2 as rs
import math
import os
import pandas as pd
from datetime import datetime
import sqlite3 as sql
from tkinter import messagebox
import colorama as color
from customtkinter import *
from config_dados_diametros import *
from direction import folder, pasta_bd
import threading
from FUNCOES_BD import *
db_lock = threading.Lock()

class NoDetectionsError(Exception):
    """Exceção personalizada para quando o modelo YOLO não detecta nada."""
    pass

pasta = folder()

print("\n\n", color.Fore.GREEN + "Abrindo FUNCOES CAMERA" + color.Style.RESET_ALL)

class DepthCamera:

    def __init__(self):
        print(color.Fore.MAGENTA + "CAMERA INICIALIZADA" + color.Style.RESET_ALL , "\n" )

        self.pipeline = None #LINHA NOVA
        try:
            self.pipeline = rs.pipeline()
            config = rs.config()
            pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
            pipeline_profile = config.resolve(pipeline_wrapper)
            device = pipeline_profile.get_device()
            device.query_sensors()[0].set_option(rs.option.laser_power, 12)
            device_product_line = str(device.get_info(rs.camera_info.product_line))

            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            config.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)
            self.pipeline.start(config)
        except:
            print("AVISO","CONECTA A CAMÊRA")

    def get_simple_infrared(self):
        ret, frames = self.only_get_frame()
        if ret:
            infrared = frames.get_infrared_frame()
            infra_image = np.asanyarray(infrared.get_data())
            return True, infra_image
        else:
            return False, None
                
    def only_get_frame(self):
        frames = self.pipeline.wait_for_frames(timeout_ms=1000) #timeout_ms=2000
        if not frames:
            return False, None
        else:
            return True, frames
    
    
    def turn_in_array(self, frames):
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        infrared = frames.get_infrared_frame()
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        infra_image = np.asanyarray(infrared.get_data())
        if not depth_frame or not color_frame:
            return False, None, None
        return True, depth_frame, depth_image, color_image, infra_image
    
    def get_cp(self, frames):
        #Salva nuvem de pontos e retorna o nome do arquivo
        colorizer = rs.colorizer()
        colorized = colorizer.process(frames)
        carimbo = frames.get_timestamp()
        ply = rs.save_to_ply(f"cloudpoint_{carimbo}.ply")
        ply.set_option(rs.save_to_ply.option_ply_binary, True)
        ply.set_option(rs.save_to_ply.option_ply_normals, False)
        ply.process(colorized)
        print(f"Cloud point saved: cloudpoint_{carimbo}.ply")
        return f"cloudpoint_{carimbo}.ply"
    
    def get_intrin(self, depth_frame):
        depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics
        return depth_intrin
    
    def get_frame(self):      
        frames = self.pipeline.wait_for_frames(timeout_ms=2000) #timeout_ms=2000
        colorizer = rs.colorizer()
        colorized = colorizer.process(frames)
        ply = rs.save_to_ply("1.ply")
        ply.set_option(rs.save_to_ply.option_ply_binary, True)
        ply.set_option(rs.save_to_ply.option_ply_normals, False)
        ply.process(colorized)
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()
        infrared = frames.get_infrared_frame()
        depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics
        Abertura = math.degrees(2*math.atan(depth_intrin.width/(2*depth_intrin.fx)))
        print("Abertura:", Abertura)
        infra_image = np.asanyarray(infrared.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        if not depth_frame or not color_frame:
            return False, None, None
        return True, depth_frame, depth_image, color_image, infra_image, Abertura
        

    def depth(self):
        frames = self.pipeline.wait_for_frames(timeout_ms=2000)
        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())
        if not depth_frame or not color_frame:
            return False, None, None
    
    def get_depth_scale(self):
        self.depth_sensor = self.pipeline.get_active_profile().get_device().first_depth_sensor()
        self.depth_scale = self.depth_sensor.get_depth_scale()
        return self.depth_scale,self.depth_sensor

    def release(self):
        if self.pipeline:
            self.pipeline.stop()
            # Adicione a linha abaixo para zerar o pipeline.
            # Isso garante que a verificação 'if not dc.pipeline:' funcione corretamente.
            self.pipeline = None 
            print(color.Fore.MAGENTA + "CAMERA ENCERRADA" + color.Style.RESET_ALL , "\n" )

def exibir_imagens(foto_app, img_segmentada, img_identificada):
    while True:
        # # Exibições
        cv2.imshow('Imagem Original: ', foto_app)
        cv2.imshow('Imagem segmentada: ', img_segmentada)
        cv2.imshow('Imagem identificada: ', img_identificada)
        
        key = cv2.waitKey(1)
        if key == 27:
            break
    cv2.destroyAllWindows()

def tirar_foto(color_frame, infra_image, id_bico):
    data = datetime.now()
    lista_arq = []
    # Formatar a data e hora como parte do nome do arquivo

    diretorio_destino_imgBW =  fr'{pasta}\FOTOS_ANALISE'
    diretorio_destino_imgColorida =  fr'{pasta}\FOTOS_REGISTRO'

    nome_arquivo_colorido = data.strftime(f'registro_{id_bico}_%d-%m-%Y_%H.%M.%S') + '.png'
    nome_arquivo_BW = nome_arquivo_colorido

    # VERIFICAR SE DIRETÓRIOS JÁ EXISTEM, CASO NÃO EXISTA, CRIAR PASTAS
    os.makedirs(diretorio_destino_imgBW, exist_ok=True)
    os.makedirs(diretorio_destino_imgColorida, exist_ok=True)

    try:
        caminho_completo_fotografia_BW = os.path.join(diretorio_destino_imgBW, nome_arquivo_BW)
    except:
        os.mkdir(fr'{pasta}\FOTOS_ANALISE')
        print(fr'{pasta}\FOTOS_ANALISE',"criado com sucesso")
        caminho_completo_fotografia_BW = os.path.join(diretorio_destino_imgBW, nome_arquivo_BW)
    
    try:
        caminho_completo_fotografia_colorida = os.path.join(diretorio_destino_imgColorida, nome_arquivo_colorido)
    except:
        os.mkdir(fr'{pasta}\FOTOS_REGISTRO')
        print(fr'{pasta}\FOTOS_REGISTRO',"criado com sucesso")
        caminho_completo_fotografia_colorida = os.path.join(diretorio_destino_imgColorida, nome_arquivo_colorido)

    lista_arq.append(nome_arquivo_colorido)

    print('Salvando foto...')
    cv2.imwrite(caminho_completo_fotografia_BW, infra_image)
    cv2.imwrite(caminho_completo_fotografia_colorida, color_frame)
        
    print(color.Fore.MAGENTA + "Imagem salva" + color.Style.RESET_ALL , "\n" )

    return lista_arq, caminho_completo_fotografia_BW, caminho_completo_fotografia_colorida, nome_arquivo_colorido

def analisar_imagem(model, imagem, nome, depth_frame, depth_image, Abertura):
    """
    Analisa a imagem para detectar o bico e os furos, e calcula seus diâmetros reais
    usando uma abordagem de nuvem de pontos 3D.

    Args:
        model: O modelo YOLO treinado.
        imagem: A imagem de infravermelho (como um array NumPy BGR).
        nome: O nome do arquivo para salvar os resultados.
        depth_frame: O frame de profundidade da câmera RealSense.
        depth_image: A imagem de profundidade (array NumPy).
        Abertura: O ângulo de abertura da câmera (não mais usado diretamente no cálculo,
                  mas mantido para compatibilidade com a chamada da função).

    Returns:
        Uma tupla contendo:
        - lista_diametros (list): Lista com os diâmetros calculados em mm.
        - mascaras (torch.Tensor): As máscaras de segmentação originais.
        - results (ultralytics.engine.results.Results): Os resultados completos do YOLO.
        - caminho_completo_fotografia_segmentada (str): Caminho para a imagem salva com as máscaras.
    """
    print("--- INICIANDO ANÁLISE DE IMAGEM (FLUXO 3D) ---")

    try:
        # --- 1. EXECUÇÃO DO MODELO YOLO ---
        results = model(imagem, device='cpu', retina_masks=True, save=True, save_crop=True, project=fr"{pasta}\resultados", name=nome, conf=0.80)

        if not results or len(results[0].boxes) == 0:
            raise NoDetectionsError("Nenhum objeto (bico ou furo) foi detectado na imagem.")
                

        result = results[0]  # Trabalhamos com o primeiro (e único) resultado

        # --- SALVAR IMAGEM SEGMENTADA (VISUALIZAÇÃO) ---
        img_segmentada = result.plot(masks=True, boxes=False)
        diretorio_destino_imgSegmentada = fr'{pasta}\FOTOS_SEGMENTADA'
        os.makedirs(diretorio_destino_imgSegmentada, exist_ok=True)
        caminho_completo_fotografia_segmentada = os.path.join(diretorio_destino_imgSegmentada, nome)
        cv2.imwrite(caminho_completo_fotografia_segmentada, img_segmentada)

        # --- 2. PREPARAÇÃO PARA CONVERSÃO 3D ---
        # Obter os parâmetros intrínsecos da câmera. Isso é crucial para a conversão de pixel para ponto 3D.
        # Estes são os "dados de fábrica" da lente da câmera.
        try:
            depth_intrin = depth_frame.profile.as_video_stream_profile().intrinsics
            
        except AttributeError:
             raise AttributeError("O 'depth_frame' fornecido não é válido ou não tem perfil de stream. Use um frame real da câmera.")


        print(f"Parâmetros da câmera (Intrinsics) carregados. Dimensões: {depth_intrin.width}x{depth_intrin.height}")

        lista_medicoes = []
        mascaras = result.masks.data.cpu().numpy()

        # --- 3. PROCESSAMENTO INDIVIDUAL DE CADA DETECÇÃO ---
        # Iteramos por cada objeto que o YOLO encontrou.
        for i in range(len(result.boxes)):
            class_id = int(result.boxes.cls[i])
            class_name = result.names[class_id]

            # Pega a máscara binária para a detecção atual
            mask = mascaras[i].astype(np.uint8)

            # --- 4. ENCONTRAR O CONTORNO (A BORDA) DA MÁSCARA ---
            # Usar apenas a borda é mais eficiente e preciso para medir o diâmetro.
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
            if not contours:
                print(f"AVISO: Nenhuma borda encontrada para a detecção {i+1}. Pulando.")
                continue

            # Usamos o maior contorno encontrado para garantir
            contour = max(contours, key=cv2.contourArea)
            contour = contour.squeeze() # Remove dimensões desnecessárias

            # --- 5. CONVERTER PIXELS DO CONTORNO PARA PONTOS 3D ---
            pontos_3d_mm = []
            for pixel_coords in contour:
                x, y = int(pixel_coords[0]), int(pixel_coords[1])

                # Pega a distância (profundidade) em metros para este pixel específico.
                profundidade_metros = depth_frame.get_distance(x, y)

                # Filtro para ignorar pixels sem informação de profundidade válida
                if 0.1 < profundidade_metros < 1.5:  # (Ex: entre 10cm e 1.5m)
                    # A MÁGICA ACONTECE AQUI: Converte o pixel 2D (x, y) + profundidade para um ponto 3D (X, Y, Z)
                    ponto_3d_metros = rs.rs2_deproject_pixel_to_point(depth_intrin, [x, y], profundidade_metros)
                    
                    # Converte de metros para milímetros e adiciona à nossa lista
                    pontos_3d_mm.append([p * 1000 for p in ponto_3d_metros])
            
            # if len(pontos_3d_mm) < 10: # Se tivermos muito poucos pontos 3D, a medição não é confiável
            #     print(f"AVISO: Pontos de profundidade insuficientes ({len(pontos_3d_mm)}) para a detecção {i+1}. Pulando.")
            #     continue

            print(f"Convertidos {len(pontos_3d_mm)} pixels da borda para uma nuvem de pontos 3D.")

            # --- 6. CALCULAR O DIÂMETRO A PARTIR DA NUVEM DE PONTOS 3D ---
            # Abordagem robusta: calcular o diâmetro médio a partir do centroide dos pontos 3D.
            nuvem_pontos = np.array(pontos_3d_mm)
            
            # --- 6a. FILTRAR OUTLIERS DA NUVEM DE PONTOS ---
            if len(nuvem_pontos) > 10: # Só filtra se tivermos pontos suficientes
                # a. Calcular o centroide e as distâncias (raios)
                centroide_3d_inicial = np.mean(nuvem_pontos, axis=0)
                distancias_iniciais = np.linalg.norm(nuvem_pontos - centroide_3d_inicial, axis=1)
                
                # b. Calcular a média e o desvio padrão dos raios
                media_raio = np.mean(distancias_iniciais)
                desvio_padrao_raio = np.std(distancias_iniciais)
                
                # c. Definir um critério: manter apenas pontos dentro de, por exemplo, 1.5 desvios padrão da média
                limite_aceitacao = 1.5 
                
                # d. Criar a nova nuvem de pontos filtrada
                nuvem_pontos_filtrada = nuvem_pontos[abs(distancias_iniciais - media_raio) < limite_aceitacao * desvio_padrao_raio]
                
                if len(nuvem_pontos_filtrada) > 5:
                    print(f"Filtro de outliers: {len(nuvem_pontos)} -> {len(nuvem_pontos_filtrada)} pontos.")
                    nuvem_pontos = nuvem_pontos_filtrada # Usa a nuvem filtrada para o cálculo
                else:
                    print("AVISO: Filtro de outliers removeu pontos demais. Usando nuvem original.")


            # --- 6b. CALCULAR O DIÂMETRO (agora com a nuvem filtrada) ---
            centroide_3d = np.mean(nuvem_pontos, axis=0)
            distancias_ao_centro = np.linalg.norm(nuvem_pontos - centroide_3d, axis=1)
            diametro_mm = np.mean(distancias_ao_centro) * 2

            # a. Encontrar o centro da nuvem de pontos
            centroide_3d = np.mean(nuvem_pontos, axis=0)

            # b. Calcular a distância de cada ponto da borda até o centro (raios)
            distancias_ao_centro = np.linalg.norm(nuvem_pontos - centroide_3d, axis=1)

            # c. O diâmetro é duas vezes o raio médio
            diametro_mm = np.mean(distancias_ao_centro) * 2

            print(f"Medição concluída para '{class_name}': Diâmetro = {diametro_mm:.2f} mm")

            # Armazena o resultado de forma estruturada
            lista_medicoes.append({
                'classe': class_name,
                'diametro_mm': diametro_mm,
                'centroide_3d': centroide_3d
            })

        # --- 7. ORGANIZAR OS RESULTADOS FINAIS ---
        # Separa o bico dos furos e monta a lista final na ordem esperada pelo resto do código.
        diametro_bico = 0
        furos = []
        for medicao in lista_medicoes:
            if medicao['classe'].lower() == 'bico':
                diametro_bico = medicao['diametro_mm']
            elif medicao['classe'].lower() == 'furo':
                furos.append(medicao)
        
        # AQUI você pode adicionar uma lógica para ordenar os furos se necessário,
        # por exemplo, usando as coordenadas X e Y do 'centroide_3d'.
        # Por enquanto, vamos apenas adicionar os diâmetros.
        
        lista_diametros = [float(round(diametro_bico, 2))]
        for furo in furos:
            lista_diametros.append(float(round(furo['diametro_mm'], 2)))

        print(f"\n--- ANÁLISE CONCLUÍDA ---")
        print(f"Lista de diâmetros final (mm): {lista_diametros}")
        
        return lista_diametros, result.masks.data, results, caminho_completo_fotografia_segmentada

    except Exception as e:
        if 'Nenhum objeto (bico ou furo) foi detectado na imagem.' in str(e):
            raise NoDetectionsError("Nenhum objeto (bico ou furo) foi detectado na imagem.")
        else:
            print(f"ERRO CRÍTICO na função analisar_imagem: {e}")
            # Retorna None para indicar falha e permitir que o código que chamou a função trate o erro.
            return None, None, None, None
    


def extrair_data_e_hora(nome_arquivo):
    lista = nome_arquivo.split("_")

    data_original = lista[2]
    hora_original = lista[3]
    hora_original = hora_original[:5]

    data = data_original.replace("-", "/")
    hora = hora_original.replace(".", ":")

    lista_data_hora = []
    lista_data_hora.append(data)
    lista_data_hora.append(hora)

    return lista_data_hora



def extrair_dados(resultado, mascaras, nome):
    """
    Extrai as caixas de detecção completas (xyxy, conf, cls) e nomes de classes dos resultados do YOLO.
    Retorna duas listas vazias em caso de erro.
    """
    try:
        if resultado is None or resultado[0].boxes is None:
            print("AVISO em extrair_dados: 'resultado' inválido ou sem 'boxes'. Retornando listas vazias.")
            return [], []

        resultado = resultado[0]
        resultado.masks.xyn
        # Extrair nomes das classes
        nomes_classes = resultado.names.values()
        # Extrair caixas delimitadoras
        caixas_detectadas = resultado.boxes.data
        resultado.masks.xy
        caixas_detectadas.shape
        # Extrair classes a partir das caixas identificadas
        infos_classes = caixas_detectadas[:, -1].int().tolist()
        # Armazenando as mascaras por classes
        mascaras_por_classe = {name: [] for name in resultado.names.values()}
        # Iterar pelas mascaras e rotulos de classe
        for mask, class_id in zip(mascaras, infos_classes):
            nome_classe = resultado.names[class_id] 
            mascaras_por_classe[nome_classe].append(mask.cpu().numpy())
        
        lista_proprs = []
        i = -1
        # Iterar por todas as classes
        for nome_classe, masks in mascaras_por_classe.items():
            for mask in masks:
                i+=1
                if i == 0:
                    lista_proprs.append({'Classe': f'{nome_classe}','Arquivo': nome})
                else:
                    lista_proprs.append({'Classe': f'{nome_classe} {i}','Arquivo': nome})
        
        # Armazenando os nomes das classes em uma lista
        nomes_classes = list(resultado[0].names.values())

        return caixas_detectadas, nomes_classes

    except Exception as e:
        print(f"AVISO: Erro dentro de extrair_dados (mascarado): {e}")
        print("--- MASCARANDO ERRO: Retornando listas vazias para caixas e nomes. ---")
        return [], []
    
# Função para ordenar os pontos em sentido horário
def sort_points_clockwise(pts):
    print("Ordenando pontos em sentido horário")
    # print("pontos antes de ordenar", pts)
    center = np.mean(pts, axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    sorted_pts = pts[np.argsort(angles)]
    # print("pontos após ordenar", sorted_pts)
    return sorted_pts

# Função para filtrar o ponto central
def filtrar_ponto_central(pontos, ponto_central, threshold=10):
    """
    Filtra um ponto central de uma lista de pontos.
    Mascarada para lidar com segurança com entradas None.
    """
    # Se a lista de pontos ou o ponto central forem nulos, retorna uma lista vazia
    if pontos is None or ponto_central is None:
        print("AVISO em filtrar_ponto_central: 'pontos' ou 'ponto_central' é None. Retornando lista vazia.")
        return []
    
    try:
        pontos_filtrados = [p for p in pontos if not (abs(p[0] - ponto_central[0]) < threshold and abs(p[1] - ponto_central[1]) < threshold)]
        print("Pontos: ", pontos)
        print("Pontos filtrados: ", pontos_filtrados)
        return pontos_filtrados
    
    except (TypeError, IndexError) as e:
        # Se ocorrer um erro inesperado (ex: um ponto não tem 2 coordenadas), retorna a lista original sem filtrar
        print(f"AVISO: Erro ao filtrar pontos (mascarado): {e}. Retornando lista não filtrada.")
        return pontos
    
# Função para extrair as coordenadas e centro das caixas delimitadoras
def extrair_coordenadas_centro(detected_boxes, classes_nomes):
    """
    Extrai os centros das caixas de detecção.
    Mascarada para ignorar caixas com formato de dados inesperado.
    """
    coordenadas_caixas = []
    pontos = []

    # Verifica se a entrada é válida antes de iterar
    if detected_boxes is None:
        print("AVISO em extrair_coordenadas_centro: 'detected_boxes' é None. Retornando lista vazia.")
        return []

    for box in detected_boxes:
        try:
            # Tenta desempacotar 6 valores
            x1, y1, x2, y2, conf, classe = box
            
            # Converte para int, pois podem vir como float
            centro_x = int((x1 + x2) / 2)
            centro_y = int((y1 + y2) / 2)
            ponto = (centro_x, centro_y)
            pontos.append(ponto)
            
            coordenadas_caixas.append({
                'Classe': classes_nomes[int(classe)],
                'Centro': {'x': centro_x, 'y': centro_y}
            })
        except (ValueError, TypeError) as e:
            # Se o desempacotamento falhar, avisa no console e continua
            print(f"AVISO: Ignorando uma caixa de detecção com formato inválido. Erro: {e}")
            print("dados obtidos:")
            print(box)
            continue

    return pontos

def enumerar_furos(lista_pontos, qtd_furos, img, nome_arquivo, lista_diametros=None):
    # Definir o ponto central (suposição: centro da imagem localizada em resultados)
    bico_crop = cv2.imread(os.path.join(fr'{pasta}\resultados', fr'{nome_arquivo}\crops\Bico\image0.jpg'))
    altura, largura = bico_crop.shape[:2]
    print("altura, largura", altura, largura)
    ponto_central = definir_centro(altura, largura)
    print("lista_pontos em enumerar furos", lista_pontos)
    # Filtrar o ponto central
    lista_pontos = filtrar_ponto_central(lista_pontos, ponto_central, threshold=10)
    print("\nlista_pontos em enumerar furos pós filtrar ponto central\n", lista_pontos)
    # Se lista_diametros não for fornecida, não filtra pelo diâmetro
    if lista_diametros is not None and len(lista_diametros) == len(lista_pontos):
        print("lista com diâmetros fornecida, filtrando pelo diâmetro do bico.")
        # O primeiro elemento de lista_diametros é o bico (maior diâmetro)
        # Remover o ponto correspondente ao bico (maior diâmetro)
        idx_bico = np.argmax(lista_diametros)
        # O bico está sempre no início da lista_diametros, então removemos o ponto correspondente

        pontos_furos = []
        # Itera sobre os pontos e seus índices
        for i, p in enumerate(lista_pontos):
            if i != idx_bico:  # Filtra o ponto do bico
                pontos_furos.append(p)
        print("pontos_furos", pontos_furos)
    else:
        print("lista com diâmetros não fornecida ou tamanho incompatível, não filtrando pelo diâmetro do bico.")
        pontos_furos = lista_pontos
        print("pontos_furos", pontos_furos)  

    if len(pontos_furos) < qtd_furos:
        print("(fun_cam)Não foram detectados pontos suficientes.")
        print("dados obtidos:")
        print(pontos_furos)
        print("tamanho: ", len(pontos_furos))
        return []
    else:
        # Quando tem mais pontos do que o necessário, seleciona do começo da lista até a quantidade de furos 
        # o ideal seria selecionar os mais próximos do centro
        furos = pontos_furos[:qtd_furos]

        if furos:
            print("Furos detectados:", furos)
            furos_array = np.array(furos)
            print("Furos array:\n", furos_array)
            # Ordenar os furos pela posição mais alta e depois em sentido horário
            sorted_holes = sort_points_clockwise(furos_array)
            print("Furos ordenados:\n", sorted_holes)
            # Numerar os furos e criar lista ordenada
            numbered_holes = [(i+1, (x, y)) for i, (x, y) in enumerate(sorted_holes)]
            for i, (x, y) in enumerate(sorted_holes, start=1):
                cv2.putText(img, str(i), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            diretorio_guias = fr'{pasta}\FOTOS_GUIA'
            caminho = os.path.join(diretorio_guias, nome_arquivo)
            cv2.imwrite(caminho, img)
            return numbered_holes
        else:
            return []

def definir_centro(altura, largura):
    mid_x, mid_y = largura // 2, altura // 2
    ponto = (mid_x, mid_y)
    return ponto
###################################################

def reunir_dados(dados_app, dados_arquivo, dados_diametros):
    lista_completa = []
    
    # Inserir os dados vindos do app
    for dado in dados_app:
        lista_completa.append(dado)
    # Inserir os dados vindos do app
    for dado in dados_arquivo:
        lista_completa.append(dado)
    # Inserir os dados dos diametros
    for dado in dados_diametros:
        lista_completa.append(dado)
    print("DADOS REUNIDOS:", lista_completa)
    return lista_completa

def organizar_dados_app(lista):

    #lista -> furos, grupo, site, BOF, tipo, ID, funcionário, vida
    #['6'(0), 'MINERADORA/BH/BRASIL'(1), 'Bloco 1'(2), '1'(3), '30/5'(4), '3'(5), 'JULIA'(6), '140(7)']
    # lista_APP = [furos, grupo, site, bof, tipo, id, usuário, vida] |
    lista_APP = [lista[0], lista[1], lista[2], lista[3], lista[4], lista[5], lista[6], lista[7]]
    qtd_furos = int(lista[0])
    id = '00' + str(lista[5])
        
    return lista_APP, id, qtd_furos

def sobrepor_molde(infra_image):
    frame = infra_image.copy()
    # Obtenha as dimensões do frame
    height, width = frame.shape
    # Calcule o centro do frame
    center_x = width // 2
    center_y = height // 2
    cv2.circle(frame, (center_x, center_y), 140, (0, 255, 255),2, 1)

    # back_frame = cv2.cvtColor(back_frame, cv2.COLOR_GRAY2RGB)
    # molde = cv2.imread(fr'{pasta}\ICONES_FOTOS\MOLDE.png')
    # # Redimensionar a imagem para o tamanho do frame
    # molde_resized = cv2.resize(molde, (infra_image.shape[1], infra_image.shape[0]))
    # # Definir a região de interesse onde a imagem será sobreposta
    # roi = back_frame[0:molde_resized.shape[0], 0:molde_resized.shape[1]]
    # # Sobrepor a imagem na região de interesse (roi)
    # for c in range(0, 2):
    #     roi[:, :, c] = molde_resized[:, :, c] * (molde_resized[:, :, 2] / 255.0) + roi[:, :, c] * (1.0 - molde_resized[:, :, 2] / 255.0)
    
    return frame
    
##  FUNÇÕES DO SITE - APENAS PARA O BICO DE 6 FUROS ##
def identificar_estados(lista_completa):
    # Lista de diâmetros (EXTERNO até FURO_N)
    diametros = lista_completa[11:]
    print("tamanho lista_completa:", len(lista_completa))
    ESTADOS = []
    for diametro in diametros:
        if diametro >= 100:
            if e_min_bom <= diametro <= e_max_bom:
                ESTADOS.append('Bom')
            elif e_max_bom < diametro <= e_max_estavel or e_min_extavel <= diametro < e_min_bom:
                ESTADOS.append('Estável')
            elif diametro < e_min_extavel or diametro > e_max_estavel:
                ESTADOS.append('Crítico')
            else:
                print(f'Não foi possível analisar o diâmetro {diametro}')

        else:
            if f_min_bom <= diametro <= f_max_bom:
                ESTADOS.append('Bom')
            elif f_max_bom < diametro <= f_max_estavel or f_min_extavel <= diametro < f_min_bom:
                ESTADOS.append('Estável')
            elif diametro < f_min_extavel or diametro > f_max_estavel:
                ESTADOS.append('Crítico')
            else:
                print(f'Não foi possível analisar o diâmetro {diametro}')
    return ESTADOS


def estado_geral_bico(lista_diametros):
    print("lista_diametros:", lista_diametros)
    lista = lista_diametros[1:]
    estado_bico = []
    contagem_furos_bom = lista.count('Bom')
    contagem_furos_estavel = lista.count('Estável')
    contagem_furos_critico = lista.count('Crítico')

    if contagem_furos_critico >= 2:
        estado_bico.append('Crítico')
    elif contagem_furos_estavel >= 3 and contagem_furos_bom <= contagem_furos_estavel:
        estado_bico.append('Estável')
    elif contagem_furos_bom >= 3:
        estado_bico.append('Bom')
    else:
        print('Não foi possível analisar o estado da lança estado geral_bico')
        estado_bico.append('Indefinido')
    return estado_bico

def salvar_registros_desgaste(cursor, lista_completa, estados, dados_diametros, estado_bico, qtd_furos):
    """
    Salva os registros de desgaste na tabela correta (B4 ou B6)
    baseado na quantidade de furos.
    """
    print("Dados recebidos para salvar_registros_desgaste:")
    print("lista_completa:", lista_completa)
    print("estados:", estados)
    print("dados_diametros:", dados_diametros)
    print("estado_bico:", estado_bico)
    print("qtd_furos:", qtd_furos)

    # Passo 1: Determinar o nome da tabela com base no novo parâmetro 'qtd_furos'
    if qtd_furos == 4:
        nome_tabela = 'B4'
        # O número de colunas para B4 deve ser 11. Ajuste se for diferente.
        placeholders = '(?,?,?,?,?,?,?,?,?,?,?)' 
    elif qtd_furos == 6:
        nome_tabela = 'B6'
        # O número de colunas para B6 deve ser 11. Ajuste se for diferente.
        placeholders = '(?,?,?,?,?,?,?,?,?,?,?)'
    else:
        # Lida com um caso inesperado, impedindo o crash
        print(f"ERRO: Número de furos não suportado ({qtd_furos}). Nenhum dado de desgaste foi salvo.")
        return # Para a execução da função se o número de furos for inválido

    # O resto da sua lógica continua igual
    dados_diametros = dados_diametros[1:]
    dados_colunas = [lista_completa[0], lista_completa[1], lista_completa[2], lista_completa[4], lista_completa[5], lista_completa[7], lista_completa[8]]

    regioes = []
    for i in range(len(dados_diametros)):
        regiao = 'EXTERNO' if i == 0 else f'FURO_{i}'
        regioes.append(regiao)

    for k in range(len(dados_diametros)):
        lista_registro = dados_colunas + [regioes[k], dados_diametros[k], estados[k], estado_bico[0]]
        
        # Passo 2: Montar o comando SQL dinamicamente usando o nome da tabela
        comando = f'INSERT INTO {nome_tabela} VALUES {placeholders}'
        
        # Verifica se o número de itens na lista corresponde ao número de placeholders
        if len(lista_registro) != placeholders.count('?'):
            print(f"ERRO: Incompatibilidade de colunas para a tabela {nome_tabela}.")
            print(f"Esperado: {placeholders.count('?')}, Recebido: {len(lista_registro)}")
            continue # Pula para a próxima iteração

        cursor.execute(comando, tuple(lista_registro))
    
    print(f'Comandos de desgaste para a tabela {nome_tabela} executados.')

def salvar_registro_principal(cursor, lista_completa, qtd_furos):
    """
    Insere o registro principal na tabela B4 ou B6 dentro de REGISTROS_WRL.db.
    """
    # Determina a tabela e o número de colunas
    if qtd_furos == 4:
        nome_tabela = 'B4'
        # Adapte o número de '?' para corresponder às colunas da sua tabela B4
        placeholders = '(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' # 16 colunas
    elif qtd_furos == 6:
        nome_tabela = 'B6'
        # Adapte para a tabela B6
        placeholders = '(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' # 18 colunas
    else:
        raise ValueError(f"Quantidade de furos inválida para salvar registro principal: {qtd_furos}")

    # Monta o comando de forma segura
    comando = f"INSERT INTO {nome_tabela} VALUES {placeholders}"
    comando_vida = "UPDATE DADOS_EMPRESAS SET ULTIMA_VIDA = ? WHERE ID = ?"
    # Garante que a lista de dados tenha o mesmo tamanho que os placeholders
    if len(lista_completa) != placeholders.count('?'):
        print(f"ERRO: Incompatibilidade de dados para a tabela {nome_tabela}.")
        print(f"Esperado: {placeholders.count('?')}, Recebido: {len(lista_completa)}")
        print("Dados recebidos:", lista_completa)
        raise ValueError(f"Não podemos identificar os {qtd_furos} furos. Tire a foto novamente.")

    

    print(f"Salvando registro principal na tabela {nome_tabela} com dados: {lista_completa}")
    cursor.execute(comando, tuple(lista_completa))
    cursor.execute(comando_vida, (lista_completa[7], lista_completa[5]))
    print(f"Comando de inserção na tabela {nome_tabela} executado.")


def processar_e_salvar_analise_completa(dados_desgaste, dados_vida):
    """
    Orquestra o salvamento em AMBOS os bancos de dados:
    1. Salva os registros de desgaste detalhados em REGISTROS_DESGASTE.db.
    2. Salva o registro principal da inspeção em REGISTROS_WRL.db.
    """
    # Desempacota os dados que serão usados
    lista_completa, estados, dados_diametros, estado_bico = dados_desgaste
    _, qtd_furos = dados_vida  # Usamos num2 como qtd_furos para clareza

    # --- TRANSAÇÃO 1: SALVAR EM REGISTROS_DESGASTE.DB ---
    banco_desgaste = None
    with db_lock:
        try:
            caminho_bd_desgaste = fr'{pasta_bd()}\REGISTROS_DESGASTE.db'
            banco_desgaste = sql.connect(caminho_bd_desgaste, timeout=10)
            cursor_desgaste = banco_desgaste.cursor()
            
            # Chama a função que salva os detalhes do desgaste
            salvar_registros_desgaste(cursor_desgaste, lista_completa, estados, dados_diametros, estado_bico, qtd_furos)
            
            banco_desgaste.commit()
            print("Dados de DESGASTE inseridos com sucesso.")
            
        except sql.Error as e:
            print(f"ERRO NO BANCO DE DADOS [DESGASTE]: {e}. Revertendo transação.")
            if banco_desgaste:
                banco_desgaste.rollback()
            return False  # Falha na primeira transação, para tudo
            
        finally:
            if banco_desgaste:
                banco_desgaste.close()

    # --- TRANSAÇÃO 2: SALVAR EM REGISTROS_WRL.DB ---
    banco_wrl = None
    with db_lock:
        try:
            caminho_bd_wrl = fr'{pasta_bd()}\REGISTROS_WRL.db'
            banco_wrl = sql.connect(caminho_bd_wrl, timeout=10)
            cursor_wrl = banco_wrl.cursor()

            # Chama a função que salva o registro principal
            # (Você pode precisar de uma função 'salvar_registros' similar à de desgaste)
            # Vamos assumir que existe uma fun2.salvar_registro_principal
            lista_completa, qtd_furos = dados_vida
            salvar_registro_principal(cursor_wrl, lista_completa, qtd_furos)
            banco_wrl.commit()
            print("Dados PRINCIPAIS inseridos com sucesso.")
            
        except sql.Error as e:
            print(f"ERRO NO BANCO DE DADOS [WRL]: {e}. Revertendo transação.")
            if banco_wrl:
                banco_wrl.rollback()
            return False # Falha na segunda transação
            
        finally:
            if banco_wrl:
                banco_wrl.close()

    # Se ambas as transações foram bem-sucedidas
    print("DADOS INSERIDOS COM SUCESSO EM AMBAS AS OPERAÇÕES!")
    return True

def tarefa_de_processamento_independente(dados_entrada):
    """
    Executa toda a lógica de negócio de forma independente da UI.
    Recebe um dicionário com todos os dados e retorna um dicionário com o resultado.
    """
    try:
        # Desempacota os dados de entrada
        model = dados_entrada["model"]
        caminho_fotoBW = dados_entrada["caminho_fotoBW"]
        nome_arquivo = dados_entrada["nome_arquivo"]
        depth_frame = dados_entrada["depth_frame"]        
        depth_image = dados_entrada["depth_image"]
        Abertura = dados_entrada["Abertura"]
        nome_arquivo_BW = dados_entrada["nome_arquivo_BW"]
        centro = dados_entrada["centro"]
        lista_APP = dados_entrada["lista_APP"]
        qtd_furos = dados_entrada["qtd_furos"]

        # --- Início da sua lógica de processamento ---
        lista_dh = extrair_data_e_hora(nome_arquivo[0])
        lista_diametros, mascaras, resultados, caminho_fotoSegmentada = analisar_imagem(model, cv2.imread(caminho_fotoBW), nome_arquivo[0], depth_frame, depth_image, Abertura)
        if lista_diametros is None:
            raise ValueError("Não podemos identificar os furos. Tire a foto novamente.")
        caixas_detectadas, nomes_classes = extrair_dados(resultados, mascaras, nome_arquivo_BW)
        lista_pontos = extrair_coordenadas_centro(caixas_detectadas, nomes_classes)
        lista_pontos = filtrar_ponto_central(lista_pontos, centro)

        # Obter furos numerados e ordenados
        furos_numerados = enumerar_furos(lista_pontos, qtd_furos, cv2.imread(caminho_fotoSegmentada), nome_arquivo[0], lista_diametros)
        for dado in lista_dh: nome_arquivo.append(dado)

        # Sincronizar diametros com ordem dos furos numerados
        diametros_ordenados = []
        if furos_numerados and len(lista_diametros) > 1:
            # O primeiro item de lista_diametros é o externo, os demais são furos
            diametros_ordenados.append(lista_diametros[0]) # externo
            # Mapear furos numerados para diametros
            for idx, (num, coords) in enumerate(furos_numerados):
                if idx+1 < len(lista_diametros):
                    diametros_ordenados.append(lista_diametros[idx+1])
        else:
            diametros_ordenados = lista_diametros

        print("Dados a serem unidos por reunir_dados: lista_APP", lista_APP)
        print("nome_arquivo: ", nome_arquivo)
        print("diametros_ordenados: ", diametros_ordenados)
        lista_completa = reunir_dados(lista_APP, nome_arquivo, diametros_ordenados)
        print("pós lista completa linhas 687 funcoes camera: ", lista_completa)
        estados = identificar_estados(lista_completa)
        estado_bico = estado_geral_bico(estados)

        dados_para_desgaste = (lista_completa, estados, diametros_ordenados, estado_bico)
        dados_para_registro_principal = (lista_completa, qtd_furos)

        sucesso_bd = processar_e_salvar_analise_completa(dados_para_desgaste, dados_para_registro_principal)

        if not sucesso_bd:
             return {"sucesso": False, "mensagem_erro": "Falha ao salvar no banco de dados."}

        # Se tudo deu certo, retorna os dados para a próxima tela
        return {
            "sucesso": True,
            "dados": lista_completa,
            "arquivo": nome_arquivo[0]
        }
    except ValueError as e:
        msg_erro = str(e).lower()
        if "não podemos identificar os" in msg_erro:  # seu erro específico
            # Retorna também a imagem (caminho)
            print(rf"{pasta}\resultados\{nome_arquivo[0]}\image0.jpg")
            return {
                "sucesso": False,
                "mensagem_erro": str(e),
                "imagem_erro": os.path.join(pasta, "resultados", nome_arquivo[0], "image0.jpg")
            }
        else:
            return {
                "sucesso": False,
                "mensagem_erro": str(e)
            }
    except Exception as e:
        return {"sucesso": False, "mensagem_erro": str(e)}