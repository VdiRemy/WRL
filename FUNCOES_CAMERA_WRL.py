import cv2
import numpy as np
import pyrealsense2 as rs
import math
import os
import pandas as pd
from datetime import datetime, timedelta
import sqlite3 as sql
from tkinter import messagebox
import colorama as color
from direction import folder, pasta_bd
import threading
from FUNCOES_BD import * # Assume que define CONECTA_BD, DESCONECTA_BD, buscar_registro_por_arquivo
from pathlib import Path # Adicionado para manipulação de caminhos
import open3d as o3d # Adicionado
import copy # Adicionado
import matplotlib.pyplot as plt # Adicionado
# Atenção: Se 'NoDetectionsError' for definida aqui, ótimo. Senão, importe-a se estiver em outro lugar.
# from YOUR_ERROR_MODULE import NoDetectionsError 

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

    def start_recording(self, filename="recording.bag"):
        """Inicia a gravação da câmera em um arquivo .bag"""
        try:
            if self.pipeline:
                self.pipeline.stop()

            # Cria nova pipeline e configuração
            self.pipeline = rs.pipeline()
            config = rs.config()

            # Configura para gravar no arquivo
            # SALVAR DENTRO DA PASTA REGISTROS
            config.enable_record_to_file(filename)

            # Configura os streams desejados
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            config.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)

            # Inicia a pipeline com a gravação ativada
            self.pipeline.start(config)
            print(f"Gravação iniciada no arquivo: {filename}")
        except Exception as e:
            print(f"Erro ao iniciar a gravação: {e}")

    def stop_recording(self):
        """Para a gravação e salva o arquivo .bag."""
        try:
            recorder = self.pipeline.get_active_profile().get_device().as_recorder()
            recorder.pause() # Pausa a gravação
            print("Gravação pausada e arquivo salvo.")
        except Exception as e:
            print(f"Erro ao parar a gravação: {e}")


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
    
    def get_intrinsics(self):
        """Retorna os parâmetros intrínsecos do stream de profundidade."""
        if not self.pipeline:
             print("AVISO: Tentando obter intrinsics sem pipeline ativo.")
             return None
        try:
             profile = self.pipeline.get_active_profile()
             depth_profile = profile.get_stream(rs.stream.depth).as_video_stream_profile()
             return depth_profile.intrinsics
        except Exception as e:
             print(f"ERRO ao obter intrinsics: {e}")
             return None

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



def salvar_frames(dc):
    import pyrealsense2 as rs
    import numpy as np
    import cv2
    import os
    import time 

    data = datetime.now()
    diretorio_destino=  fr'{pasta}\registros'
    nome_arquivo = data.strftime('registro_%d-%m-%Y_%H.%M.%S')

    os.makedirs(diretorio_destino, exist_ok=True)

    try:
        caminho_completo_fotografia = os.path.join(diretorio_destino, nome_arquivo)
    except:
        os.mkdir(fr'{pasta}\registros')
        os.mkdir(fr'{diretorio_destino}\{nome_arquivo}')
        print(fr'{pasta}\registros',"criado com sucesso")
        print(fr'{diretorio_destino}\{nome_arquivo}',"criado com sucesso")
        caminho_completo_fotografia = os.path.join(diretorio_destino, nome_arquivo)
    diretorio_registro = os.path.join(diretorio_destino, nome_arquivo)
    dc.start_recording(filename=diretorio_destino + rf'\{nome_arquivo}.bag')

    time.sleep(3)  # Aguarda 3 segundos para capturar mais frames
    dc.stop_recording()

    if dc:
        try:
            dc.release()
        except:
            pass
        dc = None


    # === CONFIGURAÇÕES ===
    bag_file = diretorio_destino + rf'\{nome_arquivo}.bag'
    output_folder = diretorio_destino + rf'\{nome_arquivo}'

    os.makedirs(output_folder, exist_ok=True)

    # === CONFIGURANDO A LEITURA DO .BAG ===
    pipeline = rs.pipeline()
    config = rs.config()

    # Carrega o .bag para leitura (sem loop)
    config.enable_device_from_file(bag_file, repeat_playback=False)

    # Habilita os streams desejados (igual aos da gravação)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)

    # Inicia o pipeline
    pipeline.start(config)

    # Para obter o controle do playback
    device = pipeline.get_active_profile().get_device()
    playback = device.as_playback()
    playback.set_real_time(False)  # Para não depender do tempo real

    frame_id = 0

    while frame_id < 25:
        frames = pipeline.wait_for_frames()

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        infra_frame = frames.get_infrared_frame()

        if not color_frame or not depth_frame or not infra_frame:
            continue

        # Converte para numpy arrays
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())
        infra_image = np.asanyarray(infra_frame.get_data())

        # === Aqui você trata os frames individualmente ===

        # Exemplo: salva os frames como imagem
        color_path = os.path.join(output_folder, f"color_{frame_id:04d}.png")
        infra_frame_path = os.path.join(output_folder, f"infra_{frame_id:04d}.png")
        
        #salvar nuvem de pontos
        colorizer = rs.pointcloud()
        colorized = colorizer.process(frames)

        ply = rs.save_to_ply(rf"{output_folder}\cloudpoint_{frame_id:04d}.ply")
        ply.set_option(rs.save_to_ply.option_ply_binary, True)
        ply.set_option(rs.save_to_ply.option_ply_normals, False)
        ply.process(colorized)

        cv2.imwrite(color_path, color_image)
        cv2.imwrite(infra_frame_path, infra_image)

        frame_id += 1

    pipeline.stop()
    cv2.destroyAllWindows()
    print(f"Total de frames processados: {frame_id}")

    return output_folder


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

def processamento_individual(i, result, mascaras, depth_frame, depth_intrin, rs, visualizar_passos=False):
    """Processa uma detecção (bico ou furo) e calcula seu diâmetro 3D."""

    try:
        class_id = int(result.boxes.cls[i])
        class_name = result.names[class_id]

        print(f"    Processando detecção {i+1}: Classe '{class_name}'")

        mask = mascaras[i].astype(np.uint8)

        # Usar apenas a borda é mais eficiente e preciso para medir o diâmetro.
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            print(f"AVISO: Nenhuma borda encontrada para a detecção {class_name} ({i+1}). Pulando.")
            return None

        # Usamos o maior contorno encontrado para garantir
        contour = max(contours, key=cv2.contourArea)

        contour = contour.squeeze() # Remove dimensões desnecessárias
        
        num_pontos_contorno = contour.shape[0]
        print(f"Contorno para '{class_name}': {num_pontos_contorno} pontos encontrados.")

        '''
        # Se o contorno não for 2D (ex: um único ponto ou linha), pular
        if contour.ndim != 2 or contour.shape[0] < 2:
            print(f"AVISO: Contorno inválido para a detecção {class_name} ({i+1}). Pulando.")
            return 
        '''    
        pixeis_pulados = 0
        pontos_3d_mm = []
        for pixel_coords in contour:
            x, y = int(pixel_coords[0]), int(pixel_coords[1])

            # Verifica se as coordenadas estão dentro dos limites da imagem de profundidade
            if 0 <= x < depth_intrin.width and 0 <= y < depth_intrin.height:
                profundidade_metros = depth_frame.get_distance(x, y)

                if 0.1 < profundidade_metros < 1: # (Ex: entre 10cm e 1m - ajuste conforme necessário)
                        ponto_3d_metros = rs.rs2_deproject_pixel_to_point(depth_intrin, [x, y], profundidade_metros)
                        pontos_3d_mm.append([p * 1000 for p in ponto_3d_metros]) # Converte para mm
                else:
                    pixeis_pulados += 1
                    pass # Ignora pixels fora da imagem
        
        if len(pontos_3d_mm) < 10: # Se tivermos muito poucos pontos 3D, a medição não é confiável
            print(f"AVISO: Pontos de profundidade insuficientes ({len(pontos_3d_mm)}) para a detecção {i+1}. Pulando.")
            return None

        print(f"Convertidos {len(pontos_3d_mm)} pixels da borda para uma nuvem de pontos 3D.")
 
        # Abordagem robusta: calcular o diâmetro médio a partir do centroide dos pontos 3D.

        nuvem_pontos = np.array(pontos_3d_mm)
        nuvem_o3d = converter_para_o3d_pointcloud(nuvem_pontos) # Converte para metros para Open3D
        

        if visualizar_passos and nuvem_o3d:
            visualizar_nuvens([nuvem_o3d], f"Nuvem Individual - {class_name} {i+1}")

        # ---   FILTRAR OUTLIERS DA NUVEM DE PONTOS ---

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


        # ---  CALCULAR O DIÂMETRO (agora com a nuvem filtrada) ---
        centroide_3d = np.mean(nuvem_pontos, axis=0)
        distancias_ao_centro = np.linalg.norm(nuvem_pontos - centroide_3d, axis=1)
        diametro_mm = np.mean(distancias_ao_centro) * 2

        print(f"Medição concluída para '{class_name}': Diâmetro = {diametro_mm:.2f} mm ({len(nuvem_pontos)} pts)")

        return {
            'classe': class_name,
            'diametro_mm': diametro_mm,
            'centroide_3d': centroide_3d,
            'nuvem_pontos': nuvem_pontos # Retorna a nuvem para poder retornar na função principal
        }

    except Exception as e:
        print(f"ERRO inesperado no processamento individual da detecção {i+1}: {e}")
        import traceback
        traceback.print_exc() # Imprime detalhes do erro para depuração
        return None

# ---> SUBSTITUA SUA FUNÇÃO 'analisar_imagem' POR ESTA <---
def analisar_imagem_lote_comparativo(model, nome, depth_frames_lote, lista_imagens, output_folder, depth_intrin, visualizar_passos=False):
    """
    Analisa um lote de imagens, calcula diâmetros individualmente e usando ICP para mesclar nuvens.
    Retorna ambos os resultados para comparação.
    """
    print("--- INICIANDO ANÁLISE DE IMAGEM COMPARATIVA (LOTE + ICP) ---")
    
    if not nome.lower().endswith(('.png', '.jpg', '.jpeg')): nome += '.png'
    
    # --- 1. Execução do Modelo YOLO ---
    try:
        results_lote = model(lista_imagens, device='cpu', retina_masks=True, save=True, save_crop=True,
                             project=fr"{output_folder}\resultados", name=nome, conf=0.80)
        if not results_lote: raise NoDetectionsError("Modelo YOLO não retornou resultados.")
    except Exception as e:
        print(f"ERRO CRÍTICO no modelo YOLO: {e}"); return None, None, None, None, None # Adapte o retorno de erro

    # --- 2. Processamento Individual e Coleta de Nuvens ---
    resultados_individuais_lote = [] 
    nuvens_por_objeto = {'bico': [], 'furos': {}} # {furo_id: {'nuvens': [], 'centroides': []}}
    
    # Variáveis para guardar informações da última imagem processada com sucesso
    last_valid_result = None
    last_valid_masks_data = None
    last_valid_caminho_segmentada = None
    last_valid_nuvem_geral = np.array([]) # Inicializa como array vazio

    if len(results_lote) != len(depth_frames_lote):
         print(f"ERRO: Inconsistência entre resultados ({len(results_lote)}) e depth frames ({len(depth_frames_lote)}).")
         return None, None, None, None, None # Adapte o retorno de erro

    for k, (result, depth_frame) in enumerate(zip(results_lote, depth_frames_lote)):
        print(f"\n--- Processando Imagem {k+1}/{len(results_lote)}) ---")
        
        # Validações básicas do resultado
        if not result.masks or not hasattr(result.masks, 'data') or result.masks.data is None or not result.boxes:
            print(f"Imagem {k+1}: Dados de detecção inválidos ou ausentes. Pulando.")
            continue
            
        mascaras = result.masks.data.cpu().numpy()
        lista_medicoes_imagem = []
        nuvem_geral_imagem_k = np.array([]) # Nuvem geral desta imagem k

        # Salva imagem segmentada (exemplo da primeira)
        caminho_segmentada_atual = None
        if k == 0:
            try:
                img_segmentada = result.plot(masks=True, boxes=False)
                dir_destino_base = fr'{pasta}\FOTOS_SEGMENTADA'
                os.makedirs(dir_destino_base, exist_ok=True)
                nome_base, ext = os.path.splitext(nome)
                caminho_segmentada_atual = os.path.join(dir_destino_base, f"{nome_base}_lote_seg{ext}")
                cv2.imwrite(caminho_segmentada_atual, img_segmentada)
            except Exception as e: print(f"AVISO: Falha ao salvar imagem segmentada: {e}")

        # Processa cada detecção na imagem k
        imagem_teve_sucesso = False
        for i in range(len(result.boxes)):
            medicao = processamento_individual(i, result, mascaras, depth_frame, depth_intrin, rs, visualizar_passos)
            if medicao and medicao.get('nuvem_pontos_o3d') is not None:
                imagem_teve_sucesso = True
                lista_medicoes_imagem.append(medicao)
                
                # Coleta nuvens O3D
                classe = medicao['classe']
                nuvem_o3d = medicao['nuvem_pontos_o3d']
                centroide = medicao.get('centroide_3d')
                
                # Acumula nuvem geral da imagem k (em mm)
                if nuvem_geral_imagem_k.size == 0:
                     nuvem_geral_imagem_k = medicao['nuvem_pontos_np']
                else:
                     nuvem_geral_imagem_k = np.vstack((nuvem_geral_imagem_k, medicao['nuvem_pontos_np']))

                if classe.lower() == 'bico':
                    nuvens_por_objeto['bico'].append(nuvem_o3d)
                elif classe.lower() == 'furo' and centroide is not None:
                    # Agrupamento simples por proximidade de centroides (ajuste a tolerância)
                    furo_id_encontrado = None
                    for f_id, f_data in nuvens_por_objeto['furos'].items():
                         if f_data['centroides']:
                             dist = np.linalg.norm(centroide - np.mean(f_data['centroides'], axis=0))
                             if dist < 15.0: # Tolerância em mm
                                 furo_id_encontrado = f_id
                                 break
                    if furo_id_encontrado is not None:
                         nuvens_por_objeto['furos'][furo_id_encontrado]['nuvens'].append(nuvem_o3d)
                         nuvens_por_objeto['furos'][furo_id_encontrado]['centroides'].append(centroide)
                    else:
                        novo_id = len(nuvens_por_objeto['furos'])
                        nuvens_por_objeto['furos'][novo_id] = {'nuvens': [nuvem_o3d], 'centroides': [centroide]}

        # Organiza e armazena resultados individuais da imagem k
        if lista_medicoes_imagem:
            bico_info = next((m for m in lista_medicoes_imagem if m['classe'].lower() == 'bico'), None)
            furos_info = sorted([m for m in lista_medicoes_imagem if m['classe'].lower() == 'furo'], key=lambda f: f.get('centroide_3d', [0,0,0])[0])
            resultados_individuais_lote.append({'bico': bico_info, 'furos': furos_info})
            
            # ---> Guarda informações da última imagem válida <---
            last_valid_result = result
            last_valid_masks_data = result.masks.data # Guarda o tensor original
            last_valid_caminho_segmentada = caminho_segmentada_atual if k == 0 else last_valid_caminho_segmentada # Mantém o da primeira imagem
            last_valid_nuvem_geral = nuvem_geral_imagem_k # Guarda a nuvem NumPy (mm) desta imagem

    # --- 3. Cálculo das Estatísticas Individuais ---
    # (Código como fornecido anteriormente, sem alterações)
    dados_agregados_individuais = {'bico': [], 'furos': {}}
    for res_img in resultados_individuais_lote:
        if res_img['bico']: dados_agregados_individuais['bico'].append(res_img['bico']['diametro_mm'])
        for i, f_info in enumerate(res_img['furos']): dados_agregados_individuais['furos'].setdefault(i, []).append(f_info['diametro_mm'])
    estatisticas_individuais = {}
    if dados_agregados_individuais['bico']:
        meds = dados_agregados_individuais['bico']
        estatisticas_individuais['bico'] = {'media': np.mean(meds), 'desvio_padrao': np.std(meds), 'n': len(meds)}
    for i, lista_diams in dados_agregados_individuais['furos'].items():
        if lista_diams:
            chave = f'furo_{i+1}'
            estatisticas_individuais[chave] = {'media': np.mean(lista_diams), 'desvio_padrao': np.std(lista_diams), 'n': len(lista_diams)}

    # --- 4. Processamento ICP e Análise Mesclada ---
    resultados_mesclados = {}
    nuvens_mescladas_vis = []
    # Mescla Bico
    if nuvens_por_objeto['bico']:
        print("\n--- Alinhando e Mesclando Nuvens do Bico ---")
        if visualizar_passos: visualizar_nuvens(nuvens_por_objeto['bico'], "Nuvens Individuais - Bico")
        nuvem_bico_m = alinhar_e_mesclar_nuvens(nuvens_por_objeto['bico'])
        if nuvem_bico_m:
            if visualizar_passos: visualizar_nuvens([nuvem_bico_m], "Nuvem Mesclada - Bico")
            diam_bico_m = medir_diametro_o3d(nuvem_bico_m)
            resultados_mesclados['bico'] = {'diametro_mm': diam_bico_m}
            if visualizar_passos: nuvens_mescladas_vis.append(copy.deepcopy(nuvem_bico_m).paint_uniform_color([1,0,0]))
    # Mescla Furos
    ids_furos_ord = sorted(nuvens_por_objeto['furos'].keys())
    for i, f_id in enumerate(ids_furos_ord):
        nuvens_f = nuvens_por_objeto['furos'][f_id]['nuvens']
        if nuvens_f:
            print(f"\n--- Alinhando e Mesclando Nuvens do Furo {i+1} ---")
            if visualizar_passos: visualizar_nuvens(nuvens_f, f"Nuvens Individuais - Furo {i+1}")
            nuvem_f_m = alinhar_e_mesclar_nuvens(nuvens_f)
            if nuvem_f_m:
                if visualizar_passos: visualizar_nuvens([nuvem_f_m], f"Nuvem Mesclada - Furo {i+1}")
                diam_f_m = medir_diametro_o3d(nuvem_f_m)
                chave = f'furo_{i+1}'
                resultados_mesclados[chave] = {'diametro_mm': diam_f_m}
                if visualizar_passos:
                     color = plt.cm.get_cmap("viridis")(i / max(1, len(ids_furos_ord)-1))[:3]
                     nuvens_mescladas_vis.append(copy.deepcopy(nuvem_f_m).paint_uniform_color(color))

    # --- 5. Apresentação Comparativa ---
    # (Código como fornecido anteriormente, sem alterações)
    print("\n\n" + "="*75)
    print("             RESULTADOS COMPARATIVOS (mm)")
    print("="*75)
    print(f"{'Classe':<10} | {'Média Individual':>18} | {'Desvio Padrão':>15} | {'Resultado Mesclado (ICP)':>25}")
    print("-" * 75)
    todas_classes = set(estatisticas_individuais.keys()) | set(resultados_mesclados.keys())
    classes_ordenadas = sorted(list(todas_classes), key=lambda x: (x != 'bico', x))
    for classe in classes_ordenadas:
        m_ind = f"{estatisticas_individuais[classe]['media']:.2f}" if classe in estatisticas_individuais else "N/A"
        s_ind = f"{estatisticas_individuais[classe]['desvio_padrao']:.3f}" if classe in estatisticas_individuais else "N/A"
        r_mesc = f"{resultados_mesclados[classe]['diametro_mm']:.2f}" if classe in resultados_mesclados else "Falhou/N/A"
        nome_fmt = classe.replace('_', ' ').title()
        print(f"{nome_fmt:<10} | {m_ind:>18} | {s_ind:>15} | {r_mesc:>25}")
    print("=" * 75)

    # --- 6. Visualização Final Agregada ---
    if visualizar_passos and nuvens_mescladas_vis:
        visualizar_nuvens(nuvens_mescladas_vis, "Nuvens Mescladas Finais (Bico Vermelho)")

    # --- 7. Preparar Retorno (Compatível com o código antigo) ---
    lista_diametros_final = [] # Usa a média individual para compatibilidade
    if 'bico' in estatisticas_individuais:
        lista_diametros_final.append(round(estatisticas_individuais['bico']['media'], 2))
    # Ordena as chaves dos furos para garantir a ordem correta
    chaves_furos_individuais = sorted([k for k in estatisticas_individuais if k.startswith('furo_')], key=lambda x: int(x.split('_')[1]))
    for chave in chaves_furos_individuais:
         lista_diametros_final.append(round(estatisticas_individuais[chave]['media'], 2))

    # ---> RETORNO AJUSTADO <---
    # Retorna a lista de diâmetros médios e os dados da ÚLTIMA imagem válida processada
    return (lista_diametros_final, 
            last_valid_masks_data, 
            last_valid_result, 
            last_valid_caminho_segmentada, 
            last_valid_nuvem_geral, 
            estatisticas_individuais, # Retorna também as estatísticas completas
            resultados_mesclados)   # E os resultados do ICP

def analisar_imagem(model, nome, depth_frame, lista_imagens, output_folder, depth_intrin):
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
    lista_de_resultados_do_lote = [] 

    # Garante que o nome do arquivo tenha extensão
    if not nome.lower().endswith(('.png', '.jpg', '.jpeg')):
        nome = nome + '.png'  # ou .jpg
        
    # --- Execução do Modelo YOLO no Lote ---
    try:
        results_lote  = model(lista_imagens, device='cpu', retina_masks=True, save=True, save_crop=True,
                project=fr"{output_folder}\resultados", name=nome, conf=0.80)

        if not results_lote :
            raise NoDetectionsError("Nenhum objeto (bico ou furo) foi detectado na imagem.")
    except Exception as e:
        if 'Nenhum objeto (bico ou furo) foi detectado na imagem.' in str(e):
            raise NoDetectionsError("Nenhum objeto (bico ou furo) foi detectado na imagem.")
        else:
            print(f"ERRO CRÍTICO na função analisar_imagem: {e}")
            # Retorna None para indicar falha e permitir que o código que chamou a função trate o erro.
            return None, None, None, None

    resultados_individuais_lote = [] # Guarda os dicionários de medição de cada imagem
    nuvens_por_objeto = {'bico': [], 'furos': {}} # Coleta nuvens Open3D para ICP


    for k, result in enumerate(results_lote):

        if not result.boxes or len(result.boxes) == 0:
            print(f"Imagem {k+1}: Nenhuma detecção válida. Pulando.")
            continue
        
        if not hasattr(result.masks, 'data') or result.masks.data is None:
            print(f"Imagem {k+1}: Objeto de máscaras inválido. Pulando.")
            continue

        if not result.masks:
            print(f"Imagem {k+1}: Sem máscaras detectadas. Pulando.")
            continue

        lista_medicoes = []
        nuvem_pontos_imagem = np.array([])
        mascaras = result.masks.data.cpu().numpy()     


            
        print(f"\n--- Processando Imagem {k+1}/{len(results_lote)}) ---")

        if k == 0:
            # --- SALVAR IMAGEM SEGMENTADA (VISUALIZAÇÃO) ---
            img_segmentada = result.plot(masks=True, boxes=False)

            try:
                diretorio_destino_imgSegmentada = fr'{pasta}\FOTOS_SEGMENTADA\{nome}'
                print(diretorio_destino_imgSegmentada)
            except:
                os.mkdir(fr'{pasta}\FOTOS_SEGMENTADA\{nome}')
                print(fr'{pasta}\FOTOS_SEGMENTADA\{nome}',"criado com sucesso")
            os.makedirs(diretorio_destino_imgSegmentada, exist_ok=True)
            caminho_completo_fotografia_segmentada = os.path.join(diretorio_destino_imgSegmentada, nome)
            cv2.imwrite(caminho_completo_fotografia_segmentada, img_segmentada)
            print(f"Imagem segmentada salva em: {caminho_completo_fotografia_segmentada}")

        # --- 2. PREPARAÇÃO PARA CONVERSÃO 3D ---
        # Obter os parâmetros intrínsecos da câmera. Isso é crucial para a conversão de pixel para ponto 3D.
        # Estes são os "dados de fábrica" da lente da câmera.

        print(f"Parâmetros da câmera (Intrinsics) carregados. Dimensões: {depth_intrin.width}x{depth_intrin.height}")


        for i in range(len(result.boxes)):
            medicao = processamento_individual(i, result, mascaras, depth_frame, depth_intrin, rs, visualizar_passos)
            if medicao is not None:
                lista_medicoes.append(medicao)
                # Acumula as nuvens de pontos para a imagem (apenas para o retorno, se necessário)
                if nuvem_pontos_imagem.size == 0:
                    nuvem_pontos_imagem = medicao['nuvem_pontos']
                else:
                    nuvem_pontos_imagem = np.vstack((nuvem_pontos_imagem, medicao['nuvem_pontos']))
        # Organizar e ordenar os resultados desta imagem
        diametro_bico_info = None
        furos_info = []
        for medicao in lista_medicoes:
            if medicao['classe'].lower() == 'bico':
                diametro_bico_info = medicao
            elif medicao['classe'].lower() == 'furo':
                furos_info.append(medicao)

        # Lógica crucial de ordenação (seu código original, que está correto)
        if furos_info:
            furos_info.sort(key=lambda f: f['centroide_3d'][0])

        resultado_da_imagem = {
            'bico': diametro_bico_info,
            'furos': furos_info
        }

        print(f"\n--- ANÁLISE CONCLUÍDA ---")
        # Armazena o resultado da imagem atual
        lista_de_resultados_do_lote.append({
            'medicoes': resultado_da_imagem,
            'mascaras': result.masks.data,
            'resultado_modelo': result,
            'caminho_imagem': caminho_completo_fotografia_segmentada,
            'nuvem_geral': nuvem_pontos_imagem
        })

    if not lista_de_resultados_do_lote:
        print("AVISO: Nenhuma medição válida foi obtida de nenhuma imagem no lote.")
        return None, None, None, None, None
        
    dados_agregados = {'bico': [], 'furos': {}}

    # Iterar sobre os resultados de cada imagem e preencher a estrutura
    for resultado in lista_de_resultados_do_lote:
        medicoes = resultado['medicoes']
        if medicoes['bico']:
            dados_agregados['bico'].append(medicoes['bico']['diametro_mm'])
        
        for i, furo_info in enumerate(medicoes['furos']):
            if i not in dados_agregados['furos']:
                dados_agregados['furos'][i] = []
            dados_agregados['furos'][i].append(furo_info['diametro_mm'])

    # Calcular as estatísticas finais (média, desvio padrão, contagem)
    estatisticas_finais = {}

    if dados_agregados['bico']:
        medicoes_bico = dados_agregados['bico']
        estatisticas_finais['bico'] = {
            'media': np.mean(medicoes_bico),
            'desvio_padrao': np.std(medicoes_bico),
            'total_medicoes': len(medicoes_bico),
            'medicoes': medicoes_bico
        }

    for i, lista_diams_furo in dados_agregados['furos'].items():
        if lista_diams_furo:
            chave = f'furo_{i+1}'
            estatisticas_finais[chave] = {
                'media': np.mean(lista_diams_furo),
                'desvio_padrao': np.std(lista_diams_furo),
                'total_medicoes': len(lista_diams_furo),
                'medicoes': lista_diams_furo
            }

    # Apresentar os resultados finais
    print("\n======================================")
    print("   ANÁLISE FINAL DO LOTE DE IMAGENS")
    print("======================================")
    for classe, dados in estatisticas_finais.items():
        print(f"  Classe: {classe.replace('_', ' ').title()}")
        print(f"    - Média do Diâmetro: {dados['media']:.2f} mm")
        print(f"    - Desvio Padrão:     {dados['desvio_padrao']:.3f} mm")
        print(f"    - Total de Medições: {dados['total_medicoes']}")

    lista_diametros = []
    if 'bico' in estatisticas_finais:
        lista_diametros.append(float(round(estatisticas_finais['bico']['media'], 2)))
    for i in range(len(estatisticas_finais) - 1):  # -1 porque 'bico' não é furo
        chave = f'furo_{i+1}'
        if chave in estatisticas_finais:
            lista_diametros.append(float(round(estatisticas_finais[chave]['media'], 2)))
    #CONCERTAR RETORNO, ESTOU RECEBENDO APENAS O ULTIMO RESULTADO DO LOTE, SENDO SOMENTE O BICO DE BOX
    return lista_diametros, result.masks.data, result, caminho_completo_fotografia_segmentada, nuvem_pontos_imagem
    


def extrair_data_e_hora(nome_arquivo):
    lista = nome_arquivo.split("_")

    data_original = lista[1]
    hora_original = lista[2]

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

def enumerar_furos(lista_pontos, qtd_furos, img, nome_arquivo, lista_diametros=None, output_folder=None):

    # Definir o ponto central (suposição: centro da imagem localizada em resultados)
    path_resultados = os.path.join(output_folder, 'resultados')

    nome_pasta_dinamica = os.listdir(path_resultados)[0]

    # 3. Construir o caminho para a pasta de crops do bico
    path_crops_bico = os.path.join(path_resultados, nome_pasta_dinamica, 'crops', 'Bico')

    # 4. Listar todas as imagens, ordená-las e pegar a última
    lista_de_imagens_crop = sorted(os.listdir(path_crops_bico))
    nome_ultima_imagem = lista_de_imagens_crop[-1] # Pega o último item da lista ordenada
    print("nome_ultima_imagem", nome_ultima_imagem)
    # 5. Construir o caminho final completo e carregar a imagem
    caminho_final_crop = os.path.join(path_crops_bico, nome_ultima_imagem)

    bico_crop = cv2.imread(caminho_final_crop)

    # Agora a variável 'bico_crop' contém a imagem correta.
    if bico_crop is not None:
        print("Imagem carregada com sucesso!")
        # cv2.imshow("Crop do Bico", bico_crop)
        # cv2.waitKey(0)
    else:
        print("Falha ao carregar a imagem.")

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
            caminho = os.path.join(diretorio_guias, nome_ultima_imagem)
            print("Caminho para salvar imagem com furos numerados:", caminho)
            cv2.imwrite(caminho, img)
            
            return numbered_holes, caminho
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
    lista_completa.append(dados_arquivo)
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
        if k == 0:
            aux = 0
            lista_registro = dados_colunas + [regioes[k], dados_diametros[k], estados[aux], estado_bico[0]]
        else:
            lista_registro = dados_colunas + [regioes[k], dados_diametros[k], estados[k-1], estado_bico[0]]
        
        # Passo 2: Montar o comando SQL dinamicamente usando o nome da tabela
        comando = f'INSERT INTO {nome_tabela} VALUES {placeholders}'
        
        # Verifica se o número de itens na lista corresponde ao número de placeholders
        if len(lista_registro) != placeholders.count('?'):
            print(f"ERRO: Incompatibilidade de colunas para a tabela {nome_tabela}.")
            print(f"Esperado: {placeholders.count('?')}, Recebido: {len(lista_registro)}")
            continue # Pula para a próxima iteração

        cursor.execute(comando, tuple(lista_registro))
    
    print(f'Comandos de desgaste para a tabela {nome_tabela} executados.')

def salvar_registro_principal(cursor, lista_completa, qtd_furos, data_hora):
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

    index_insercao = 9  # antes do 'data' e 'hora'

    lista_completa = lista_completa[:index_insercao] + data_hora + lista_completa[index_insercao:]


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
            salvar_registro_principal(cursor_wrl, lista_completa, qtd_furos,extrair_data_e_hora(lista_completa[8]))
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

# ---> CORREÇÃO 3: Lógica de Processamento Lendo Arquivos <---
def tarefa_de_processamento_independente(dados_entrada):
    """
    Executa a lógica de negócio lendo os frames extraídos da pasta.
    """
    try:
        # Desempacota os dados de entrada
        model = dados_entrada["model"]
        nome_base_arquivo = dados_entrada["nome"]
        output_folder = Path(dados_entrada["output_folder"]) # Converte para Path
        depth_intrin = dados_entrada["depth_intrin"]
        lista_APP = dados_entrada["lista_APP"]
        qtd_furos = dados_entrada["qtd_furos"]

        print(f"Iniciando processamento para: {nome_base_arquivo}")
        print(f"Lendo frames de: {output_folder}")

        # 1. Encontra os arquivos de imagem extraídos (infravermelho)
        lista_caminhos_infra = sorted(list(output_folder.glob("infra_*.png")))
        if not lista_caminhos_infra:
            raise ValueError(f"Nenhuma imagem infra encontrada em {output_folder}")
        
        # 2. Carrega as imagens infravermelhas
        lista_imagens_infra = [cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) for p in lista_caminhos_infra]
        # Converte para BGR para o modelo YOLO
        lista_imagens_bgr = [cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) for img in lista_imagens_infra]

        # 3. SIMULAÇÃO DOS DEPTH FRAMES (DESAFIO!)
        # Ler os depth frames *como objetos rs.depth_frame* de arquivos NÃO É DIRETO.
        # O SDK não oferece uma função simples para isso.
        # SOLUÇÃO PRAGMÁTICA: Usar UM ÚNICO depth_frame (lido do .bag) para APROXIMAR.
        # Isso assume que a câmera não se moveu muito durante a gravação.

        depth_frame_unico = None
        bag_file = output_folder.parent / (output_folder.name + ".bag") # Reconstrói o caminho do .bag
        if bag_file.exists():
            print(f"Lendo depth frame do arquivo .bag: {bag_file}")
            pipe_leitura = rs.pipeline()
            cfg_leitura = rs.config()
            try:
                cfg_leitura.enable_device_from_file(str(bag_file), repeat_playback=False)
                profile = pipe_leitura.start(cfg_leitura)
                # Tenta pegar um frame do meio da gravação
                playback = profile.get_device().as_playback()
                duration = playback.get_duration().total_seconds()
                seek_time_ns = int((duration / 2) * 1e9) # Metade da duração em nanossegundos
                playback.seek(timedelta(seconds=seek_time_ns / 1e9))

                frames = pipe_leitura.wait_for_frames(5000) # Espera até 5s
                if frames:
                    depth_frame_unico = frames.get_depth_frame()
                    print("Depth frame lido do .bag com sucesso.")
                else:
                    print("AVISO: Não foi possível ler um depth frame do .bag.")
            except Exception as e_read:
                 print(f"AVISO: Erro ao ler depth frame do .bag: {e_read}")
            finally:
                 pipe_leitura.stop()
        else:
            print(f"AVISO: Arquivo .bag não encontrado em {bag_file}. Usando depth_frame simulado.")
            # Se não encontrar o .bag, não podemos fazer a análise 3D real.
            # Retornar erro ou usar dados simulados? Vamos retornar erro por segurança.
            raise FileNotFoundError(f"Arquivo .bag não encontrado: {bag_file}")


        if depth_frame_unico is None:
             raise ValueError("Não foi possível obter um depth_frame válido para análise.")
             
        # Cria uma lista replicando o depth_frame único para corresponder às imagens
        depth_frames_lote_simulado = [depth_frame_unico] * len(lista_imagens_bgr)


        # --- Chamada da Função de Análise (Versão Lote) ---
        # Passamos a lista de imagens lidas e a lista simulada de depth frames
        retorno_analise = analisar_imagem_lote_comparativo(
            model, nome_base_arquivo, depth_frames_lote_simulado, lista_imagens_bgr,
            str(output_folder.parent), # Passa a pasta PAI (onde a pasta 'resultados' será criada)
            depth_intrin, visualizar_passos=False
        )

        # Desempacota o retorno
        (lista_diametros_media, last_masks_data, last_result,
         last_caminho_segmentada, last_nuvem_geral,
         estatisticas_individuais, resultados_mesclados) = retorno_analise

        if lista_diametros_media is None:
            raise ValueError("Falha na análise (analisar_imagem_lote_comparativo retornou None).")

        # --- Continua com a lógica de salvar e retornar ---
        nome_arquivo_compat = nome_base_arquivo + '.png'
        # (Adapte a lógica de 'extrair_coordenadas_centro' e 'enumerar_furos' se necessário)
        # ... (seu código para extrair pontos, enumerar, reunir dados, salvar no BD) ...

        # *** CUIDADO com 'enumerar_furos' ***
        # Ela precisa encontrar o CROP do bico. O caminho agora é diferente.
        # Exemplo de como encontrar o crop:
        # caminho_crop_bico_estimado = output_folder.parent / "resultados" / nome_base_arquivo / "crops" / "Bico"
        # Procure o arquivo de imagem mais recente lá dentro. Adapte a função.

        # Chamada adaptada (requer modificação em enumerar_furos)
        img_para_enumerar_path = last_caminho_segmentada # Caminho da primeira imagem segmentada
        img_enum = cv2.imread(str(img_para_enumerar_path)) if img_para_enumerar_path and os.path.exists(img_para_enumerar_path) else np.zeros_like(lista_imagens_bgr[0])

        # A lógica para obter 'lista_pontos' precisa ser robusta
        lista_pontos = []
        if last_result:
            try:
                caixas = last_result.boxes.data.cpu().numpy()
                nomes = last_result.names
                lista_pontos = extrair_coordenadas_centro(caixas, nomes)
                centro_compat = (lista_imagens_bgr[-1].shape[1]//2, lista_imagens_bgr[-1].shape[0]//2)
                lista_pontos = filtrar_ponto_central(lista_pontos, centro_compat)
            except Exception as e_pts:
                print(f"AVISO: Não foi possível extrair pontos da última imagem: {e_pts}")

        # Modifique enumerar_furos para aceitar output_folder.parent (pasta 'registros')
        furos_numerados, caminho_foto_enumerada = enumerar_furos(
             lista_pontos, qtd_furos, img_enum, nome_base_arquivo,
             lista_diametros_media, str(output_folder.parent) # Passa a pasta pai
        )

        diametros_ordenados = lista_diametros_media
        lista_dh = extrair_data_e_hora(nome_arquivo_compat)
        lista_completa = reunir_dados(lista_APP, nome_arquivo_compat, diametros_ordenados)
        estados = identificar_estados(lista_completa)
        estado_bico = estado_geral_bico(estados)

        dados_para_desgaste = (lista_completa, estados, diametros_ordenados, estado_bico)
        dados_para_registro_principal = (lista_completa, qtd_furos)

        sucesso_bd = processar_e_salvar_analise_completa(dados_para_desgaste, dados_para_registro_principal)

        if not sucesso_bd:
            return {"sucesso": False, "mensagem_erro": "Falha ao salvar no banco de dados."}

        return {
            "sucesso": True, "dados": lista_completa, "arquivo": nome_arquivo_compat,
            "resultados_icp": resultados_mesclados
        }

    except ValueError as e:
            msg_erro = str(e).lower()
            imagem_erro_path = None # Inicializa como None

            # Tenta construir o caminho para a imagem de erro salva pelo YOLO
            try:
                # 1. Recria o nome da pasta de resultados usada pelo YOLO (com extensão)
                nome_resultado_folder = nome_base_arquivo + '.png' 
                
                # 2. Constrói o caminho completo
                #    output_folder é a pasta com frames extraídos (ex: .../registros/registro_...)
                #    A pasta 'resultados' está um nível acima dela.
                caminho_base_resultados = output_folder.parent # Vai para a pasta 'registros'
                imagem_erro_path = os.path.join(
                    str(caminho_base_resultados), # Converte Path para string
                    "resultados", 
                    nome_resultado_folder, 
                    "image0.jpg"
                )
                
                # Verifica se o arquivo realmente existe
                if not os.path.exists(imagem_erro_path):
                    print(f"AVISO: Imagem de debug YOLO não encontrada em: {imagem_erro_path}")
                    imagem_erro_path = None # Define como None se não existir

            except Exception as e_path:
                # Se houver erro ao montar o caminho (ex: variável não definida), apenas avisa.
                print(f"AVISO: Erro ao tentar construir caminho para imagem de erro: {e_path}")
                imagem_erro_path = None

            # Verifica a mensagem de erro específica
            if "não podemos identificar os" in msg_erro:
                print(f"Erro específico de identificação: {e}")
                if imagem_erro_path:
                    print(f"Retornando com imagem de erro: {imagem_erro_path}")
                return {
                    "sucesso": False,
                    "mensagem_erro": str(e),
                    "imagem_erro": imagem_erro_path # Retorna o caminho ou None
                }
            else:
                # Se for outro ValueError, retorna a mensagem genérica
                print(f"ValueError genérico: {e}")
                return {
                    "sucesso": False,
                    "mensagem_erro": str(e)
                    # Não retorna imagem_erro para erros genéricos, a menos que você queira
                }



def converter_para_o3d_pointcloud(np_array_mm):
    """Converte um array NumPy (N, 3) em mm para um objeto PointCloud do Open3D em metros."""
    if np_array_mm is None or np_array_mm.size == 0:
        return None
    pcd = o3d.geometry.PointCloud()
    # Open3D espera coordenadas em metros, então dividimos por 1000.0
    pcd.points = o3d.utility.Vector3dVector(np_array_mm / 1000.0) 
    return pcd

def alinhar_e_mesclar_nuvens(lista_nuvens_o3d, voxel_size=0.0005, max_correspondence_distance=0.001):
    """
    Alinha uma lista de nuvens de pontos Open3D usando ICP sequencial e as mescla.
    Args:
        lista_nuvens_o3d (list): Lista de o3d.geometry.PointCloud (em metros).
        voxel_size (float): Tamanho do voxel para downsampling e mesclagem (em metros).
        max_correspondence_distance (float): Distância máxima para correspondência no ICP (em metros).
    Returns:
        o3d.geometry.PointCloud: Nuvem de pontos mesclada e alinhada, ou None se falhar.
    """
    if not lista_nuvens_o3d or len(lista_nuvens_o3d) < 2:
        return lista_nuvens_o3d[0] if lista_nuvens_o3d else None

    print(f"    - Alinhando {len(lista_nuvens_o3d)} nuvens...")
    
    # Prepara as nuvens (downsampling e cálculo de normais são cruciais para ICP ponto-a-plano)
    nuvens_preparadas = []
    for pcd in lista_nuvens_o3d:
        pcd_down = pcd.voxel_down_sample(voxel_size)
        pcd_down.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30))
        nuvens_preparadas.append(pcd_down)

    # Inicia com a primeira nuvem como referência acumulada
    nuvem_acumulada_o3d = copy.deepcopy(nuvens_preparadas[0])
    lista_nuvens_originais_transformadas = [copy.deepcopy(lista_nuvens_o3d[0])] # Guarda as originais transformadas

    # ICP Sequencial: Alinha cada nuvem (source) com a nuvem acumulada anterior (target)
    for i in range(1, len(nuvens_preparadas)):
        source = nuvens_preparadas[i]
        target = nuvem_acumulada_o3d # Usa a nuvem acumulada *downsampled* como alvo para eficiência

        # Estimativa inicial da transformação (matriz identidade)
        trans_init = np.identity(4)

        # Executa o ICP ponto-a-plano (geralmente mais robusto que ponto-a-ponto)
        reg_p2l = o3d.pipelines.registration.registration_icp(
            source, target, max_correspondence_distance, trans_init,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=200)) # Aumentar iterações se precisar

        print(f"      - Nuvem {i+1} -> Acumulada: Fitness={reg_p2l.fitness:.3f}, RMSE={reg_p2l.inlier_rmse:.3f}")

        # Aplica a transformação encontrada à nuvem original (sem downsampling) para manter detalhes
        nuvem_original_para_transformar = copy.deepcopy(lista_nuvens_o3d[i])
        nuvem_original_para_transformar.transform(reg_p2l.transformation)
        lista_nuvens_originais_transformadas.append(nuvem_original_para_transformar)
        
        # Atualiza a nuvem acumulada (usando a versão downsampled transformada)
        source.transform(reg_p2l.transformation)
        nuvem_acumulada_o3d += source
        # Faz downsample na acumulada para manter o próximo ICP eficiente
        nuvem_acumulada_o3d = nuvem_acumulada_o3d.voxel_down_sample(voxel_size) 
        # Recalcula normais para o próximo ICP
        nuvem_acumulada_o3d.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30))


    # Mescla final usando todas as nuvens originais já transformadas
    print("    - Mesclando nuvens alinhadas...")
    nuvem_mesclada = o3d.geometry.PointCloud()
    for pcd in lista_nuvens_originais_transformadas:
        nuvem_mesclada += pcd
        
    # Downsample final para limpar a nuvem mesclada e torná-la uniforme
    nuvem_mesclada_final = nuvem_mesclada.voxel_down_sample(voxel_size)
    
    print(f"    - Nuvem mesclada final com {len(nuvem_mesclada_final.points)} pontos.")
    return nuvem_mesclada_final

def medir_diametro_o3d(o3d_pointcloud_metros):
    """Calcula o diâmetro de um círculo a partir de uma nuvem de pontos Open3D (em metros)."""
    if o3d_pointcloud_metros is None or not o3d_pointcloud_metros.has_points():
        return 0.0
        
    # Converte de volta para NumPy array em milímetros para o cálculo
    pontos_mm = np.asarray(o3d_pointcloud_metros.points) * 1000.0
    
    if pontos_mm.shape[0] < 10:
        print("    AVISO: Pontos insuficientes na nuvem mesclada para calcular diâmetro.")
        return 0.0

    # Usa a mesma lógica robusta de cálculo de diâmetro que já tínhamos
    centroide_3d = np.mean(pontos_mm, axis=0)
    distancias_ao_centro = np.linalg.norm(pontos_mm - centroide_3d, axis=1)
    
    # Adicionar filtro de outlier nos raios aqui pode ser útil
    media_raio = np.mean(distancias_ao_centro)
    std_raio = np.std(distancias_ao_centro)
    raios_filtrados = distancias_ao_centro[abs(distancias_ao_centro - media_raio) < 2.0 * std_raio] # Filtro de 2 desvios padrão
    
    if raios_filtrados.size > 5:
        raio_medio_final = np.mean(raios_filtrados)
    else:
        raio_medio_final = media_raio # Usa a média original se o filtro removeu demais
        
    diametro = raio_medio_final * 2
    return diametro

def visualizar_nuvens(lista_nuvens_o3d, titulo="Visualização de Nuvens de Pontos"):
    """Exibe uma lista de nuvens de pontos Open3D em uma janela interativa, colorindo-as."""
    if not lista_nuvens_o3d:
        print("Nenhuma nuvem para visualizar.")
        return
    
    nuvens_para_plotar = []
    num_nuvens_validas = sum(1 for pcd in lista_nuvens_o3d if pcd is not None and pcd.has_points())
    
    idx_valido = 0
    for pcd in lista_nuvens_o3d:
        if pcd is not None and pcd.has_points():
            pcd_copy = copy.deepcopy(pcd)
            # Pinta cada nuvem com uma cor diferente se não tiver cor
            if not pcd_copy.has_colors():
                 # Usar um colormap garante cores distintas
                color = plt.cm.get_cmap("viridis")(idx_valido / max(1, num_nuvens_validas - 1))[:3]
                pcd_copy.paint_uniform_color(color)
            nuvens_para_plotar.append(pcd_copy)
            idx_valido += 1

    if nuvens_para_plotar:
        print(f"\n--- Abrindo visualizador Open3D: {titulo} ---")
        print("    (Feche a janela para continuar a execução)")
        o3d.visualization.draw_geometries(nuvens_para_plotar, window_name=titulo)
    else:
        print("Nenhuma nuvem válida encontrada para visualizar.")