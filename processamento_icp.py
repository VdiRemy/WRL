import pyrealsense2 as rs
import numpy as np
import cv2
import open3d as o3d
import argparse
import os
import copy
import math
import time
import sqlite3 as sql
import threading
from pathlib import Path
from ultralytics import YOLO
from datetime import datetime, timedelta # Importação corrigida
import matplotlib.pyplot as plt
import colorama as color # Mantido para mensagens de log

# --- Inicialização do Colorama (se usado nos logs) ---
color.init(autoreset=True)

# --- Definições de Erro ---
class NoDetectionsError(Exception):
    """Exceção personalizada para quando o modelo YOLO não detecta nada."""
    pass

# --- Funções de Diretório (Embutidas) ---
def folder():
    """Retorna o diretório do script atual."""
    # Alterado para usar Pathlib para mais robustez
    return str(Path(__file__).parent.resolve())

def pasta_bd():
    """Retorna o caminho para a pasta do banco de dados (ajuste se necessário)."""
    # Assume que a pasta BD está um nível acima da pasta do script
    return str(Path(__file__).parent.parent.resolve() / "BD")

pasta_base = folder()
db_lock = threading.Lock() # Lock para acesso ao BD

# --- Constantes (Embutidas - Substitua pelos seus valores reais) ---
# Valores de exemplo de config_dados_diametros.py
e_min_bom = 190.0
e_max_bom = 190.0
e_min_extavel = 185.0 # Nome corrigido (era extavel)
e_max_estavel = 195.0
f_min_bom = 30.0
f_max_bom = 30.0
f_min_extavel = 25.0 # Nome corrigido
f_max_estavel = 35.0

MODELO_YOLO_PATH = fr'{pasta_base}\pesos\best.pt'
NUM_FRAMES_ANALISE = 25 # Quantos frames do .bag processar
SKIP_FRAMES_INICIO = 10 # Pular alguns frames iniciais

# [INÍCIO DO NOVO BLOCO DE CÓDIGO]
# Funções para captura ao vivo e gravação de .bag

def exibir_distancia_central(frame, depth_frame, intr):
    """
    Calcula e exibe a distância do pixel central no frame.
    Retorna a distância em metros.
    """
    try:
        # Pega as dimensões do frame de profundidade
        width = intr.width
        height = intr.height
        center_x, center_y = width // 2, height // 2

        # Obtém a distância em metros
        dist_m = depth_frame.get_distance(center_x, center_y)
        
        if dist_m == 0:
            texto = "Distancia: N/A (Aproxime-se)"
        else:
            texto = f"Distancia Central: {dist_m:.2f} m"
        
        # Prepara para desenhar o texto no frame (que pode ser IR ou Color)
        # Converte para BGR se for Gray (Infrared)
        if len(frame.shape) == 2:
            frame_display = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            frame_display = frame.copy()

        # Configurações do texto
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        color_amarelo = (0, 255, 255)
        thickness = 2
        text_size, _ = cv2.getTextSize(texto, font, font_scale, thickness)
        
        # Posição do texto no canto superior esquerdo
        text_x = 10
        text_y = 30
        
        # Adiciona um retângulo de fundo para melhor legibilidade
        cv2.rectangle(frame_display, (text_x - 5, text_y - text_size[1] - 5), 
                      (text_x + text_size[0] + 5, text_y + 5), (0, 0, 0), -1)
        
        cv2.putText(frame_display, texto, (text_x, text_y), font, 
                    font_scale, color_amarelo, thickness)
        
        # Adiciona um marcador central
        cv2.circle(frame_display, (center_x, center_y), 5, color_amarelo, -1)
        cv2.line(frame_display, (center_x - 10, center_y), (center_x + 10, center_y), color_amarelo, 1)
        cv2.line(frame_display, (center_x, center_y - 10), (center_x, center_y + 10), color_amarelo, 1)

        return frame_display, dist_m

    except Exception as e:
        print(f"Erro ao calcular distância central: {e}")
        if len(frame.shape) == 2:
            frame_display = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        else:
            frame_display = frame.copy()
        return frame_display, 0.0


def gravar_sessoes_de_analise(output_dir):
    """
    Abre uma interface de câmera ao vivo para gravar múltiplos arquivos .bag.
    
    - 'r': Inicia a gravação de um arquivo .bag de 3 segundos.
    - 'q': Fecha a câmera e retorna a lista de arquivos gravados.
    
    Args:
        output_dir (Path): O diretório base para salvar os .bag (ex: 'analises_offline').

    Returns:
        list: Uma lista de strings contendo os caminhos completos para os .bag gravados.
    """
    print("\n--- INICIANDO MODO DE CAPTURA AO VIVO ---")
    print("  Pressione 'r' para gravar um clipe de 3 segundos.")
    print("  Pressione 'q' para sair e iniciar a análise.")
    
    lista_arquivos_bag = []
    pipeline_live = None
    intrinsics_live = None
    align_live = None
    
    # --- Configuração inicial para obter intrinsics ---
# --- Configuração inicial para obter intrinsics ---
    try:
        temp_pipe = rs.pipeline()
        temp_cfg = rs.config()
        temp_cfg.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        temp_cfg.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)
        
        # --- LINHAS NOVAS (ADICIONAR AQUI) ---
        pipeline_wrapper = rs.pipeline_wrapper(temp_pipe)
        profile_temp = temp_cfg.resolve(pipeline_wrapper)
        device_temp = profile_temp.get_device()
        device_temp.query_sensors()[0].set_option(rs.option.laser_power, 12) # <-- Defina sua intensidade aqui
        # --- FIM DAS LINHAS NOVAS ---

        profile = temp_pipe.start(temp_cfg)
        depth_profile = profile.get_stream(rs.stream.depth).as_video_stream_profile()
        intrinsics_live = depth_profile.get_intrinsics()
        align_live = rs.align(rs.stream.infrared)
        temp_pipe.stop()
        print("Câmera e intrinsics inicializados.")
    except Exception as e:
        print(f"ERRO: Falha ao inicializar a câmera RealSense. Verifique a conexão. {e}")
        return []

    # --- Loop do Viewfinder Ao Vivo ---
    pipeline_live = rs.pipeline()
    config_live = rs.config()
    config_live.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    config_live.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)
    
    # --- LINHAS NOVAS (ADICIONAR AQUI) ---
    pipeline_wrapper_live = rs.pipeline_wrapper(pipeline_live)
    profile_live_resolved = config_live.resolve(pipeline_wrapper_live)
    device_live = profile_live_resolved.get_device()
    device_live.query_sensors()[0].set_option(rs.option.laser_power, 12) # <-- Defina sua intensidade aqui
    # --- FIM DAS LINHAS NOVAS ---

    pipeline_live.start(config_live) # O start agora usa a config com laser
    
    dist_atual_m = 0.0

    try:
        while True:
            frames = pipeline_live.wait_for_frames()
            aligned_frames = align_live.process(frames)
            
            depth_frame = aligned_frames.get_depth_frame()
            infra_frame = aligned_frames.get_infrared_frame(1) # Usar stream 1
            
            if not depth_frame or not infra_frame:
                continue
                
            infra_image = np.asanyarray(infra_frame.get_data())
            
            # Exibe a distância central
            frame_com_dist, dist_atual_m = exibir_distancia_central(infra_image, depth_frame, intrinsics_live)
            
            cv2.imshow("Captura Ao Vivo - Pressione 'r' para gravar, 'q' para sair", frame_com_dist)
            key = cv2.waitKey(1) & 0xFF

            # --- Sair (q) ---
            if key == ord('q'):
                print("Encerrando captura...")
                break
                
            # --- Gravar (r) ---
            if key == ord('r'):
                print("\nIniciando gravação...")
                # Pausa o stream ao vivo
                pipeline_live.stop()
                cv2.destroyWindow("Captura Ao Vivo - Pressione 'r' para gravar, 'q' para sair")

                # Formata o nome do arquivo
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dist_cm = int(dist_atual_m * 100)
                nome_arquivo = f"captura_dist{dist_cm}cm_{timestamp}.bag"
                caminho_completo_bag = str(output_dir / nome_arquivo)
                
                print(f"Gravando em: {caminho_completo_bag}")
                
                # Configura e inicia a gravação
                pipeline_rec = rs.pipeline()
                config_rec = rs.config()
                # IMPORTANTE: Salva no diretório correto
                config_rec.enable_record_to_file(caminho_completo_bag)
                # Adiciona os mesmos streams
                config_rec.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
                config_rec.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)
                
                pipeline_rec.start(config_rec)
                
                # Grava por 3 segundos
                # (Poderia mostrar um contador, mas time.sleep é mais simples)
                start_time = time.time()
                while time.time() - start_time < 3.0:
                    # Apenas consome frames para manter a gravação ativa
                    pipeline_rec.wait_for_frames()
                
                pipeline_rec.stop()
                print("Gravação concluída.")
                lista_arquivos_bag.append(caminho_completo_bag)
                
                # Reinicia o pipeline ao vivo
                print("Reiniciando visualização ao vivo...")
                pipeline_live.start(config_live)

    finally:
        if pipeline_live:
            pipeline_live.stop()
        cv2.destroyAllWindows()
        print(f"Total de {len(lista_arquivos_bag)} arquivos .bag gravados.")
        
    return lista_arquivos_bag

# [FIM DO NOVO BLOCO DE CÓDIGO]

def visualizar_nuvem_objeto_bruta(mask, depth_frame, depth_intrin, rs_module, class_name, img_index, det_index, visualizar=True):
    """
    Extrai e visualiza a nuvem de pontos 3D "bruta" de uma máscara de segmentação inteira.
    
    Args:
        mask (np.array): A máscara binária (0 ou 255) do objeto (H, W).
        depth_frame (rs.depth_frame): O frame de profundidade alinhado.
        depth_intrin (rs.intrinsics): Parâmetros intrínsecos da câmera.
        rs_module (module): O módulo 'pyrealsense2' (importado como 'rs').
        class_name (str): Nome da classe para o título da janela.
        img_index (int): Índice da imagem no lote (para o título).
        det_index (int): Índice da detecção na imagem (para o título).
        visualizar (bool): Flag para ativar ou desativar a visualização.

    Returns:
        o3d.geometry.PointCloud: A nuvem de pontos Open3D bruta (ou None).
    """
    if not visualizar:
        return None # Não faz nada se a visualização estiver desligada

    print(f"    Visualizando Nuvem Bruta para Img {img_index}, Det {det_index} ({class_name})...")

    # 1. Encontrar todos os pixels (x, y) que pertencem à máscara
    # np.where(mask > 0) retorna (array_de_y, array_de_x)
    pixels_y, pixels_x = np.where(mask > 0)
    
    if pixels_x.size == 0:
        print("    AVISO: Máscara vazia, nada para visualizar.")
        return None

    # 2. Iterar por esses pixels e obter a profundidade
    pontos_3d_mm = []
    for x, y in zip(pixels_x, pixels_y):
        # x e y já são inteiros
        
        # Verificação de limites (segurança extra, embora a máscara deva estar contida)
        if 0 <= x < depth_intrin.width and 0 <= y < depth_intrin.height:
            prof = depth_frame.get_distance(x, y)
            
            # Filtro de profundidade (o mesmo usado no processamento_individual)
            if 0.1 < prof < 1.5: 
                p_3d_m = rs_module.rs2_deproject_pixel_to_point(depth_intrin, [x, y], prof)
                pontos_3d_mm.append([p * 1000 for p in p_3d_m]) # Converte para mm

    if len(pontos_3d_mm) < 10:
        print("    AVISO: Pontos de profundidade insuficientes na nuvem bruta.")
        return None
        
    print(f"    Convertidos {len(pontos_3d_mm)} pixels da máscara em nuvem 3D bruta.")

    # 3. Converter para Open3D
    nuvem_pontos_np = np.array(pontos_3d_mm)
    pcd = converter_para_o3d_pointcloud(nuvem_pontos_np) # Converte para metros

    if pcd is None or not pcd.has_points():
        print("    AVISO: Falha ao criar nuvem Open3D.")
        return None

    # 4. Visualizar
    # Pinta de uma cor padrão (ex: azul) para diferenciar
    pcd.paint_uniform_color([0.0, 0.0, 0.8]) 
    
    visualizar_nuvens(
        [pcd], 
        titulo=f"Nuvem Bruta - Img {img_index} Det {det_index} ({class_name})"
    )

    return pcd # Retorna a nuvem bruta, caso queira usá-la

def combinar_e_visualizar_nuvens_finais(nuvens_mescladas_dict, voxel_size_final=0.0005, visualizar=True):
    """
    Combina as nuvens de pontos mescladas do bico e dos furos em uma única nuvem
    e opcionalmente a visualiza.

    Args:
        nuvens_mescladas_dict (dict): Dicionário onde as chaves são 'bico', 'furo_1', etc.,
                                     e os valores são os objetos o3d.geometry.PointCloud
                                     já mesclados (em metros).
        voxel_size_final (float): Tamanho do voxel para um downsample final na nuvem combinada.
        visualizar (bool): Se True, exibe a nuvem combinada em uma janela Open3D.

    Returns:
        o3d.geometry.PointCloud: A nuvem de pontos combinada final, ou None se a entrada for vazia.
    """
    print("\n--- Combinando Nuvens Mescladas Finais ---")
    nuvem_combinada = o3d.geometry.PointCloud()
    nuvens_para_combinar = []
    
    # Adiciona a nuvem do bico, se existir
    if 'bico' in nuvens_mescladas_dict and nuvens_mescladas_dict['bico'] is not None:
        pcd_bico = copy.deepcopy(nuvens_mescladas_dict['bico'])
        # Pinta o bico de vermelho para destaque na visualização combinada
        pcd_bico.paint_uniform_color([1.0, 0.0, 0.0]) 
        nuvens_para_combinar.append(pcd_bico)
        print("  - Adicionando nuvem mesclada do Bico.")

    # Adiciona as nuvens dos furos, se existirem
    chaves_furos = sorted([k for k in nuvens_mescladas_dict if k.startswith('furo_')])
    cmap = plt.get_cmap("viridis") # Colormap para os furos
    
    for i, chave_furo in enumerate(chaves_furos):
        pcd_furo = nuvens_mescladas_dict[chave_furo]
        if pcd_furo is not None:
            pcd_furo_copy = copy.deepcopy(pcd_furo)
            # Pinta cada furo com uma cor do colormap
            color = cmap(i / max(1, len(chaves_furos) - 1))[:3]
            pcd_furo_copy.paint_uniform_color(color)
            nuvens_para_combinar.append(pcd_furo_copy)
            print(f"  - Adicionando nuvem mesclada do {chave_furo.replace('_', ' ').title()}.")

    if not nuvens_para_combinar:
        print("  AVISO: Nenhuma nuvem mesclada válida encontrada para combinar.")
        return None

    # Combina todas as nuvens em uma só
    for pcd in nuvens_para_combinar:
        nuvem_combinada += pcd

    # Aplica um downsample final para uniformizar
    nuvem_combinada_final = nuvem_combinada.voxel_down_sample(voxel_size_final)
    num_pontos_final = len(nuvem_combinada_final.points)
    print(f"  - Nuvem combinada final criada com {num_pontos_final} pontos.")

    # Visualização opcional
    if visualizar and num_pontos_final > 0:
        print("\n--- Abrindo visualizador Open3D: Nuvem Combinada Final ---")
        print("    (Bico em vermelho, Furos em cores variadas)")
        print("    (Feche a janela para finalizar)")
        o3d.visualization.draw_geometries([nuvem_combinada_final], window_name="Nuvem Combinada Final")

    return nuvem_combinada_final    

# --- Funções Auxiliares Open3D (Embutidas) ---


def converter_para_o3d_pointcloud(np_array_mm):
    """Converte um array NumPy (N, 3) em mm para um objeto PointCloud do Open3D em metros."""
    if np_array_mm is None or np_array_mm.size == 0:
        return None
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np_array_mm / 1000.0) # Open3D usa metros
    return pcd

def alinhar_e_mesclar_nuvens(lista_nuvens_o3d, voxel_size=0.0005, max_correspondence_distance=0.001):
    """Alinha uma lista de nuvens de pontos Open3D usando ICP sequencial e as mescla."""
    if not lista_nuvens_o3d or len(lista_nuvens_o3d) < 2:
        return lista_nuvens_o3d[0] if lista_nuvens_o3d else None

    print(f"    - Alinhando {len(lista_nuvens_o3d)} nuvens...")
    nuvens_preparadas = []
    for pcd in lista_nuvens_o3d:
        pcd_down = pcd.voxel_down_sample(voxel_size)
        pcd_down.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30))
        nuvens_preparadas.append(pcd_down)

    nuvem_acumulada_o3d = copy.deepcopy(nuvens_preparadas[0])
    lista_nuvens_originais_transformadas = [copy.deepcopy(lista_nuvens_o3d[0])]

    for i in range(1, len(nuvens_preparadas)):
        source = nuvens_preparadas[i]
        target = nuvem_acumulada_o3d
        trans_init = np.identity(4)
        reg_p2l = o3d.pipelines.registration.registration_icp(
            source, target, max_correspondence_distance, trans_init,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=200))

        print(f"      - Nuvem {i+1} -> Acumulada: Fitness={reg_p2l.fitness:.3f}, RMSE={reg_p2l.inlier_rmse:.3f}")
        
        # Verifica se o alinhamento foi razoável (ajuste os limiares)
        if reg_p2l.fitness < 0.6 or reg_p2l.inlier_rmse > voxel_size * 2 :
             print(f"      AVISO: Alinhamento da nuvem {i+1} pode ter falhado (fitness baixo ou RMSE alto). Ignorando esta nuvem na mesclagem.")
             continue # Pula para a próxima nuvem se o alinhamento for ruim
             
        nuvem_original_para_transformar = copy.deepcopy(lista_nuvens_o3d[i])
        nuvem_original_para_transformar.transform(reg_p2l.transformation)
        lista_nuvens_originais_transformadas.append(nuvem_original_para_transformar)
        
        source.transform(reg_p2l.transformation)
        nuvem_acumulada_o3d += source
        nuvem_acumulada_o3d = nuvem_acumulada_o3d.voxel_down_sample(voxel_size)
        nuvem_acumulada_o3d.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30))

    print("    - Mesclando nuvens alinhadas...")
    nuvem_mesclada = o3d.geometry.PointCloud()
    for pcd in lista_nuvens_originais_transformadas:
        nuvem_mesclada += pcd
        
    nuvem_mesclada_final = nuvem_mesclada.voxel_down_sample(voxel_size)
    print(f"    - Nuvem mesclada final com {len(nuvem_mesclada_final.points)} pontos.")
    return nuvem_mesclada_final

def medir_diametro_o3d(o3d_pointcloud_metros):
    """Calcula o diâmetro de um círculo a partir de uma nuvem de pontos Open3D (em metros)."""
    if o3d_pointcloud_metros is None or not o3d_pointcloud_metros.has_points():
        return 0.0
    pontos_mm = np.asarray(o3d_pointcloud_metros.points) * 1000.0
    if pontos_mm.shape[0] < 10:
        print("    AVISO: Pontos insuficientes na nuvem mesclada para calcular diâmetro.")
        return 0.0
    centroide_3d = np.mean(pontos_mm, axis=0)
    distancias_ao_centro = np.linalg.norm(pontos_mm - centroide_3d, axis=1)
    media_raio = np.mean(distancias_ao_centro)
    std_raio = np.std(distancias_ao_centro)
    raios_filtrados = distancias_ao_centro[abs(distancias_ao_centro - media_raio) < 2.0 * std_raio]
    raio_medio_final = np.mean(raios_filtrados) if raios_filtrados.size > 5 else media_raio
    return raio_medio_final * 2

def visualizar_nuvens(lista_nuvens_o3d, titulo="Visualização de Nuvens de Pontos"):
    """Exibe uma lista de nuvens de pontos Open3D em uma janela interativa, colorindo-as."""
    if not lista_nuvens_o3d:
        print("Nenhuma nuvem para visualizar.")
        return
    
    nuvens_para_plotar = []
    num_nuvens_validas = sum(1 for pcd in lista_nuvens_o3d if pcd is not None and pcd.has_points())
    idx_valido = 0
    cmap = plt.get_cmap("viridis") # Define o colormap fora do loop
    for pcd in lista_nuvens_o3d:
        if pcd is not None and pcd.has_points():
            pcd_copy = copy.deepcopy(pcd)
            if not pcd_copy.has_colors():
                 # Usa get_cmap em vez de cm.get_cmap
                 color = cmap(idx_valido / max(1, num_nuvens_validas - 1))[:3]
                 pcd_copy.paint_uniform_color(color)
            nuvens_para_plotar.append(pcd_copy)
            idx_valido += 1

    if nuvens_para_plotar:
        print(f"\n--- Abrindo visualizador Open3D: {titulo} ---")
        print("    (Feche a janela para continuar a execução)")
        o3d.visualization.draw_geometries(nuvens_para_plotar, window_name=titulo)
    else:
        print("Nenhuma nuvem válida encontrada para visualizar.")

# --- Funções de Processamento de Imagem e Dados (Embutidas) ---
def processamento_individual(i, result, mascaras, depth_frame, depth_intrin, rs_module, visualizar_passos=False):
    """ Processa uma única detecção, calcula diâmetro e retorna nuvens NP e O3D. """
    try:
        class_id = int(result.boxes.cls[i])
        class_name = result.names[class_id]
        mask = mascaras[i].astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours: return None
        contour = max(contours, key=cv2.contourArea).squeeze()
        
        # Verifica se o contorno é válido antes de prosseguir
        if contour.ndim != 2 or contour.shape[0] < 3:
             print(f"    AVISO: Contorno inválido para detecção {i+1} ({class_name}). Pulando.")
             return None

        pontos_3d_mm = []
        for px, py in contour:
            x, y = int(px), int(py)
            if 0 <= x < depth_intrin.width and 0 <= y < depth_intrin.height:
                prof = depth_frame.get_distance(x, y)
                if 0.1 < prof < 1.5: # Aumentado o limite superior para 1.5m
                    p_3d_m = rs_module.rs2_deproject_pixel_to_point(depth_intrin, [x, y], prof)
                    pontos_3d_mm.append([p * 1000 for p in p_3d_m])
        if len(pontos_3d_mm) < 10: return None

        nuvem_pontos_np = np.array(pontos_3d_mm)
        nuvem_o3d = converter_para_o3d_pointcloud(nuvem_pontos_np)

        if visualizar_passos and nuvem_o3d:
            visualizar_nuvens([nuvem_o3d], f"Nuvem Individual - {class_name} {i+1}")

        # --- 6a. FILTRAR OUTLIERS DA NUVEM DE PONTOS ---
        nuvem_pontos_np_original_para_vis = None # Guarda a nuvem original para visualização
        indices_validos = np.ones(len(nuvem_pontos_np), dtype=bool) # Assume todos válidos inicialmente

        if len(nuvem_pontos_np) > 10: # Só filtra se tivermos pontos suficientes
            # Guarda a nuvem original ANTES de filtrar, SE for visualizar
            if visualizar_passos:
                 nuvem_pontos_np_original_para_vis = copy.deepcopy(nuvem_pontos_np)

            # a. Calcular o centroide e as distâncias (raios)
            centroide_3d_inicial = np.mean(nuvem_pontos_np, axis=0)
            distancias_iniciais = np.linalg.norm(nuvem_pontos_np - centroide_3d_inicial, axis=1)

            # b. Calcular a média e o desvio padrão dos raios
            media_raio = np.mean(distancias_iniciais)
            desvio_padrao_raio = np.std(distancias_iniciais)

            # c. Definir um critério (Ex: 2.0 desvios padrão)
            limite_aceitacao = 2.0 # Você pode ajustar este valor!
            indices_validos = abs(distancias_iniciais - media_raio) < limite_aceitacao * desvio_padrao_raio
            num_removidos = np.sum(~indices_validos)

            # ---> INÍCIO DA VISUALIZAÇÃO DO FILTRO <---
            if visualizar_passos and nuvem_pontos_np_original_para_vis is not None:
                print(f"    Visualizando Filtro: {num_removidos} outliers potenciais.")
                pcd_vis = converter_para_o3d_pointcloud(nuvem_pontos_np_original_para_vis)
                if pcd_vis:
                    # Cria um array de cores (Verde para mantidos, Vermelho para removidos)
                    cores_vis = np.array([[0.0, 0.8, 0.0]] * len(nuvem_pontos_np_original_para_vis)) # Verde
                    cores_vis[~indices_validos] = [1.0, 0.0, 0.0] # Vermelho

                    pcd_vis.colors = o3d.utility.Vector3dVector(cores_vis)

                    # Chama o visualizador diretamente para mostrar a nuvem colorida
                    print(f"\n--- Abrindo visualizador Open3D: Filtro Outliers - {class_name} {i+1} ---")
                    print("    (Verde = Mantido, Vermelho = Removido)")
                    print("    (Feche a janela para continuar)")
                    o3d.visualization.draw_geometries([pcd_vis], window_name=f"Filtro Outliers - {class_name} {i+1}")
            # ---> FIM DA VISUALIZAÇÃO DO FILTRO <---

            # d. Criar a nova nuvem de pontos filtrada
            nuvem_pontos_filtrada = nuvem_pontos_np[indices_validos]

            if len(nuvem_pontos_filtrada) > 5:
                print(f"    Filtro de outliers: {len(nuvem_pontos_np)} -> {len(nuvem_pontos_filtrada)} pontos ({num_removidos} removidos).")
                nuvem_pontos_np = nuvem_pontos_filtrada # Usa a nuvem filtrada para o cálculo
            else:
                print(f"    AVISO: Filtro de outliers removeu pontos demais ({num_removidos}). Usando nuvem original.")
                # Neste caso, nuvem_pontos_np permanece inalterada
        
        # Cálculo do diâmetro
        centroide = np.mean(nuvem_pontos_np, axis=0)
        raios = np.linalg.norm(nuvem_pontos_np - centroide, axis=1)
        diametro_mm = np.mean(raios) * 2
        print(f"    Medição concluída para '{class_name}': Diâmetro = {diametro_mm:.2f} mm")

        return {
            'classe': class_name, 'diametro_mm': diametro_mm, 'centroide_3d': centroide,
            'nuvem_pontos_o3d': nuvem_o3d, 'nuvem_pontos_np': nuvem_pontos_np
        }
    except Exception as e:
        print(f"ERRO no processamento individual da detecção {i+1}: {e}")
        return None

def analisar_imagem_lote_comparativo(model, nome, depth_frames_lote, lista_imagens, output_folder_base, depth_intrin, visualizar_passos=False):
    """ Analisa um lote de imagens, calcula diâmetros individualmente e usando ICP para mesclar nuvens. """
    print("--- INICIANDO ANÁLISE DE IMAGEM COMPARATIVA (LOTE + ICP) ---")
    
    # Define a pasta específica para os resultados desta execução
    output_folder_results = Path(output_folder_base) / "resultados" / nome
    output_folder_results.mkdir(parents=True, exist_ok=True) # Cria a pasta
    nome_arquivo_base_com_ext = nome + '.png' # Adiciona extensão para salvar a imagem
    nuvens_mescladas_final_dict = {}
    # --- 1. Execução do Modelo YOLO ---
    try:
        # Salva resultados na pasta específica criada acima
        results_lote = model(lista_imagens, device='cpu', retina_masks=True, save=True, save_crop=True,
                             project=str(Path(output_folder_base) / "resultados"), # Pasta base para 'project'
                             name=nome, # Nome da subpasta específica
                             conf=0.80)
        if not results_lote: raise NoDetectionsError("Modelo YOLO não retornou resultados.")
    except Exception as e:
        print(f"ERRO CRÍTICO no modelo YOLO: {e}"); return None, None, None, None, None, None, None

    # --- 2. Processamento Individual e Coleta de Nuvens ---
    resultados_individuais_lote = []
    nuvens_por_objeto = {'bico': [], 'furos': {}}
    last_valid_result = None
    last_valid_masks_data = None
    last_valid_caminho_segmentada = None
    last_valid_nuvem_geral = np.array([])

    if len(results_lote) != len(depth_frames_lote):
         print(f"ERRO: Inconsistência entre resultados ({len(results_lote)}) e depth frames ({len(depth_frames_lote)}).")
         return None, None, None, None, None, None, None

    for k, (result, depth_frame) in enumerate(zip(results_lote, depth_frames_lote)):
        print(f"\n--- Processando Imagem {k+1}/{len(results_lote)}) ---")
        if not result.masks or not hasattr(result.masks, 'data') or result.masks.data is None or not result.boxes:
            print(f"Imagem {k+1}: Dados inválidos. Pulando."); continue
            
        mascaras = result.masks.data.cpu().numpy()
        lista_medicoes_imagem = []
        nuvem_geral_imagem_k = np.array([])
        caminho_segmentada_atual = None

        # Salva imagem segmentada (agora dentro da pasta de resultados específica)
        if k == 0: # Salva apenas a primeira como exemplo
            try:
                img_segmentada = result.plot(masks=True, boxes=False)
                # Salva na pasta 'resultados/nome_base_analise/'
                caminho_segmentada_atual = str(output_folder_results / f"{nome}_seg.png")
                cv2.imwrite(caminho_segmentada_atual, img_segmentada)
                print(f"Imagem segmentada salva em: {caminho_segmentada_atual}")
            except Exception as e: print(f"AVISO: Falha ao salvar imagem segmentada: {e}")

        # Processa cada detecção
        imagem_teve_sucesso = False
        for i in range(len(result.boxes)):
            '''
            # ---> INÍCIO DA NOVA ETAPA: Visualização da Nuvem Bruta <---
            try:
                # Pega a máscara e o nome da classe
                current_mask = mascaras[i].astype(np.uint8)
                current_class_id = int(result.boxes.cls[i])
                current_class_name = result.names[current_class_id]

                # Chama a nova função de visualização
                # (Passa k+1 e i+1 para indexação amigável)


                visualizar_nuvem_objeto_bruta(
                    current_mask, 
                    depth_frame, 
                    depth_intrin, 
                    rs, # Passa o módulo 'rs'
                    current_class_name, 
                    k+1, # Índice da Imagem
                    i+1, # Índice da Deteção
                    visualizar=visualizar_passos
                )

                
            except Exception as e_vis:
                 print(f"    AVISO: Erro durante a visualização da nuvem bruta: {e_vis}")
            # --- FIM DA NOVA ETAPA ---
            '''

            medicao = processamento_individual(i, result, mascaras, depth_frame, depth_intrin, rs, visualizar_passos)
            if medicao and medicao.get('nuvem_pontos_o3d') is not None:
                lista_medicoes_imagem.append(medicao)
                classe = medicao['classe']
                nuvem_o3d = medicao['nuvem_pontos_o3d']
                centroide = medicao.get('centroide_3d')
                
                # Acumula nuvem geral da imagem
                nuvem_np = medicao['nuvem_pontos_np']
                if nuvem_np is not None and nuvem_np.size > 0:
                    if nuvem_geral_imagem_k.size == 0: nuvem_geral_imagem_k = nuvem_np
                    else: nuvem_geral_imagem_k = np.vstack((nuvem_geral_imagem_k, nuvem_np))

                # Coleta nuvens para ICP
                if classe.lower() == 'bico':
                    nuvens_por_objeto['bico'].append(nuvem_o3d)
                elif classe.lower() == 'furo' and centroide is not None:
                    furo_id_encontrado = None
                    for f_id, f_data in nuvens_por_objeto['furos'].items():
                         if f_data['centroides']:
                             dist = np.linalg.norm(centroide - np.mean(f_data['centroides'], axis=0))
                             if dist < 15.0: furo_id_encontrado = f_id; break
                    if furo_id_encontrado is not None:
                         nuvens_por_objeto['furos'][furo_id_encontrado]['nuvens'].append(nuvem_o3d)
                         nuvens_por_objeto['furos'][furo_id_encontrado]['centroides'].append(centroide)
                    else:
                        novo_id = len(nuvens_por_objeto['furos'])
                        nuvens_por_objeto['furos'][novo_id] = {'nuvens': [nuvem_o3d], 'centroides': [centroide]}

        # Armazena resultados individuais da imagem
        if lista_medicoes_imagem:
            bico_info = next((m for m in lista_medicoes_imagem if m['classe'].lower() == 'bico'), None)
            furos_info = sorted([m for m in lista_medicoes_imagem if m['classe'].lower() == 'furo'], key=lambda f: f.get('centroide_3d', [0,0,0])[0])
            resultados_individuais_lote.append({'bico': bico_info, 'furos': furos_info})
            last_valid_result = result
            last_valid_masks_data = result.masks.data
            last_valid_caminho_segmentada = caminho_segmentada_atual if k == 0 else last_valid_caminho_segmentada
            last_valid_nuvem_geral = nuvem_geral_imagem_k

    # --- 3. Cálculo das Estatísticas Individuais ---
    dados_agregados_individuais = {'bico': [], 'furos': {}}
    for res_img in resultados_individuais_lote:
        if res_img.get('bico') and res_img['bico'].get('diametro_mm') is not None: 
             dados_agregados_individuais['bico'].append(res_img['bico']['diametro_mm'])
        for i, f_info in enumerate(res_img.get('furos', [])): 
             if f_info and f_info.get('diametro_mm') is not None:
                 dados_agregados_individuais['furos'].setdefault(i, []).append(f_info['diametro_mm'])

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
        # if visualizar_passos: visualizar_nuvens(nuvens_por_objeto['bico'], "Nuvens Individuais - Bico")
        nuvem_bico_m = alinhar_e_mesclar_nuvens(nuvens_por_objeto['bico'])
        if nuvem_bico_m:
            nuvens_mescladas_final_dict['bico'] = nuvem_bico_m # Armazena o objeto
            
            # if visualizar_passos: visualizar_nuvens([nuvem_bico_m], "Nuvem Mesclada - Bico")
            
            diam_bico_m = medir_diametro_o3d(nuvem_bico_m)
            resultados_mesclados['bico'] = {'diametro_mm': diam_bico_m}
            if visualizar_passos: nuvens_mescladas_vis.append(copy.deepcopy(nuvem_bico_m).paint_uniform_color([1,0,0]))
    # Mescla Furos
    ids_furos_ord = sorted(nuvens_por_objeto['furos'].keys())
    for i, f_id in enumerate(ids_furos_ord):
        nuvens_f = nuvens_por_objeto['furos'][f_id]['nuvens']
        if nuvens_f:
            print(f"\n--- Alinhando e Mesclando Nuvens do Furo {i+1} ---")
            # if visualizar_passos: visualizar_nuvens(nuvens_f, f"Nuvens Individuais - Furo {i+1}")
            nuvem_f_m = alinhar_e_mesclar_nuvens(nuvens_f)
            if nuvem_f_m:
                chave = f'furo_{i+1}'
                nuvens_mescladas_final_dict[chave] = nuvem_f_m # Armazena o objeto
                
                # if visualizar_passos: visualizar_nuvens([nuvem_f_m], f"Nuvem Mesclada - Furo {i+1}")
                
                diam_f_m = medir_diametro_o3d(nuvem_f_m)
                chave = f'furo_{i+1}'
                resultados_mesclados[chave] = {'diametro_mm': diam_f_m}
                if visualizar_passos:
                     cmap = plt.get_cmap("viridis")
                     color = cmap(i / max(1, len(ids_furos_ord)-1))[:3]
                     nuvens_mescladas_vis.append(copy.deepcopy(nuvem_f_m).paint_uniform_color(color))

    # --- 5. Preparar Retorno ---
    lista_diametros_final = []
    if 'bico' in estatisticas_individuais:
        lista_diametros_final.append(round(estatisticas_individuais['bico']['media'], 2))
    chaves_furos_individuais = sorted([k for k in estatisticas_individuais if k.startswith('furo_')], key=lambda x: int(x.split('_')[1]))
    for chave in chaves_furos_individuais:
         lista_diametros_final.append(round(estatisticas_individuais[chave]['media'], 2))

    # Retorna múltiplos valores
    return (lista_diametros_final, last_valid_masks_data, last_valid_result,
        last_valid_caminho_segmentada, last_valid_nuvem_geral,
        estatisticas_individuais, resultados_mesclados, 
        nuvens_mescladas_final_dict,
        nuvens_por_objeto) # <-- Novo item retornado

def analisar_arquivo_bag(bag_filepath, num_frames_processar, visualizar, model, output_dir_analise):
    """
    Função refatorada que analisa um ÚNICO arquivo .bag.
    Contém a lógica principal da sua 'main' original.
    """
    print(f"\n--- Processando arquivo .bag: {bag_filepath} ---")
    bag_path = Path(bag_filepath)
    if not bag_path.exists():
        print(f"ERRO: Arquivo .bag não encontrado em '{bag_filepath}'")
        return None, None, None

    # --- Configurar Pipeline RealSense (Lógica da sua main original) ---
    pipeline = rs.pipeline()
    config = rs.config()
    align = None
    depth_intrinsics = None
    profile = None 

    try:
        config.enable_device_from_file(str(bag_path), repeat_playback=False)
        profile = pipeline.start(config)
        
        dev_check = profile.get_device()
        playback_check = dev_check.as_playback() 
        if playback_check is None:
            print(f"ERRO CRÍTICO: Dispositivo do {bag_path.name} não suporta playback.")
            pipeline.stop()
            return None, None, None

        depth_profile = profile.get_stream(rs.stream.depth).as_video_stream_profile()
        depth_intrinsics = depth_profile.intrinsics
        align = rs.align(rs.stream.infrared)
        pipeline.stop()
        profile = None 
        
        profile = pipeline.start(config) 
        playback_dev = profile.get_device()
        playback = playback_dev.as_playback() 
        if playback is None:
            print(f"ERRO CRÍTICO: Falha ao obter playback na 2ª leitura de {bag_path.name}.")
            pipeline.stop()
            return None, None, None
            
        playback.set_real_time(False)
    except Exception as e:
        print(f"!!! ERRO GERAL ao configurar a pipeline para {bag_path.name}: {e}")
        if pipeline: 
            try: pipeline.stop(); 
            except: pass
        return None, None, None

    # --- Extração e Preparação dos Frames (Lógica da sua main original) ---
    lista_imagens_bgr = []
    lista_depth_frames = []
    frames_lidos = 0
    frames_processados_validos = 0
    max_wait_attempts = 10
    wait_attempts = 0

    try:
        while frames_processados_validos < num_frames_processar:
            success, frames = pipeline.try_wait_for_frames(2000)
            if not success:
                wait_attempts += 1
                if wait_attempts >= max_wait_attempts: break 
                continue 
            wait_attempts = 0
            frames_lidos += 1
            if frames_lidos <= SKIP_FRAMES_INICIO: continue
            
            aligned_frames = align.process(frames)
            if not aligned_frames: continue
            
            depth_frame = aligned_frames.get_depth_frame()
            infra_frame = aligned_frames.get_infrared_frame()
            if not depth_frame or not infra_frame: continue

            infra_image = np.asanyarray(infra_frame.get_data())
            infra_bgr = cv2.cvtColor(infra_image, cv2.COLOR_GRAY2BGR)
            
            lista_depth_frames.append(depth_frame)
            lista_imagens_bgr.append(infra_bgr)
            frames_processados_validos += 1
            
    except RuntimeError as e:
        if "Frames did not arrive within" in str(e):
             print(f"Fim do arquivo {bag_path.name} alcançado.")
        else:
             print(f"ERRO de Runtime durante a leitura de {bag_path.name}: {e}")
    finally:
        pipeline.stop()

    if frames_processados_validos == 0: 
        print(f"ERRO: Nenhum frame válido extraído de {bag_path.name}.")
        return None, None, None

    # --- Execução da Análise (Lógica da sua main original) ---
    print(f"Iniciando análise YOLO + ICP em {frames_processados_validos} frames de {bag_path.name}...")
    nome_base_analise = bag_path.stem
    
    try:
        retorno_analise = analisar_imagem_lote_comparativo(
            model, nome_base_analise, lista_depth_frames, lista_imagens_bgr,
            str(output_dir_analise), depth_intrinsics, visualizar_passos=visualizar
        )
        if retorno_analise[0] is None: 
            print(f"ERRO: Análise de {bag_path.name} falhou.")
            return None, None, None
        
        # Desempacota (agora com o 9º item)
        (lista_diametros_media, _, _, _, _, 
         estatisticas_individuais, resultados_mesclados, 
         nuvens_mescladas_dict, nuvens_por_objeto_brutas) = retorno_analise
             
        # --- Apresenta Resultados Finais (Lógica da sua main original) ---
        print("\n" + "="*80)
        print(f"     RESULTADOS INDIVIDUAIS PARA: {nome_base_analise}")
        print("="*80)
        print(f"{'Classe':<10} | {'Média Individual':>18} | {'Desvio Padrão':>15} ({'N':>2}) | {'Resultado Mesclado (ICP)':>25}")
        print("-" * 80)
        todas_classes = set(estatisticas_individuais.keys()) | set(resultados_mesclados.keys())
        classes_ordenadas = sorted(list(todas_classes), key=lambda x: (x != 'bico', x))
        for classe in classes_ordenadas:
            n_ind = estatisticas_individuais[classe]['n'] if classe in estatisticas_individuais else 0
            m_ind = f"{estatisticas_individuais[classe]['media']:.2f}" if classe in estatisticas_individuais else "N/A"
            s_ind = f"{estatisticas_individuais[classe]['desvio_padrao']:.3f}" if classe in estatisticas_individuais else "N/A"
            r_mesc = f"{resultados_mesclados[classe]['diametro_mm']:.2f}" if classe in resultados_mesclados else "Falhou/N/A"
            nome_fmt = classe.replace('_', ' ').title()
            print(f"{nome_fmt:<10} | {m_ind:>18} | {s_ind:>15} ({n_ind:>2}) | {r_mesc:>25}")
        print("=" * 80)

        # Retorna os dados para agregação
        return nuvens_mescladas_dict, nuvens_por_objeto_brutas, nome_base_analise

    except NoDetectionsError as e: print(f"ERRO DE ANÁLISE em {bag_path.name}: {e}")
    except Exception as e: print(f"ERRO CRÍTICO durante a análise de {bag_path.name}: {e}"); import traceback; traceback.print_exc()
    
    return None, None, None


def criar_legenda_3d(texto, posicao, cor, escala_fonte=0.005):
    """
    Cria um objeto de geometria 3D (esfera) para atuar como uma legenda.
    O Open3D padrão (draw_geometries) não suporta texto, então usamos esferas coloridas
    e imprimimos a legenda no console.
    """
    # Cria uma esfera pequena no local do centroide
    raio_esfera = escala_fonte * 5 # Raio da esfera
    legenda_esfera = o3d.geometry.TriangleMesh.create_sphere(radius=raio_esfera)
    
    # Desloca a esfera para ficar ligeiramente "acima" do furo (eixo Z)
    posicao_deslocada = np.array(posicao) + [0, 0, raio_esfera * 4] 
    legenda_esfera.translate(posicao_deslocada)
    legenda_esfera.paint_uniform_color(cor)
    return legenda_esfera


def visualizar_analise_agregada(resultados_agregados, visualizar, output_dir_analise):
    """
    Combina os resultados de TODAS as análises de .bag e exibe
    as duas visualizações 3D solicitadas (Bruta e Pós-ICP).
    """
    if not resultados_agregados:
        print("Nenhum resultado de análise para agregar.")
        return

    print("\n\n" + "="*80)
    print("  INICIANDO AGREGAÇÃO E VISUALIZAÇÃO FINAL")
    print("="*80)
    
    geometrias_brutas_agregadas = []
    geometrias_icp_agregadas = []
    
    # Dicionários para acumular as nuvens
    nuvens_brutas_bico = o3d.geometry.PointCloud()
    nuvens_brutas_furos = {} # {0: PointCloud, 1: PointCloud, ...}
    
    nuvens_icp_bico = o3d.geometry.PointCloud()
    nuvens_icp_furos = {} # {'furo_1': PointCloud, 'furo_2': PointCloud, ...}

    # --- 1. Acumular todas as nuvens ---
    for nuvens_icp_dict, nuvens_brutas_dict, nome_base in resultados_agregados:
        print(f"Agregando dados de: {nome_base}")
        
        # Acumula Brutas
        if 'bico' in nuvens_brutas_dict:
            for pcd in nuvens_brutas_dict['bico']:
                nuvens_brutas_bico += pcd
        for f_id, f_data in nuvens_brutas_dict['furos'].items():
            if f_id not in nuvens_brutas_furos:
                nuvens_brutas_furos[f_id] = o3d.geometry.PointCloud()
            for pcd in f_data['nuvens']:
                nuvens_brutas_furos[f_id] += pcd

        # Acumula Pós-ICP
        if 'bico' in nuvens_icp_dict:
            nuvens_icp_bico += nuvens_icp_dict['bico']
        chaves_furos_icp = sorted([k for k in nuvens_icp_dict if k.startswith('furo_')])
        for chave_furo in chaves_furos_icp:
            if chave_furo not in nuvens_icp_furos:
                nuvens_icp_furos[chave_furo] = o3d.geometry.PointCloud()
            nuvens_icp_furos[chave_furo] += nuvens_icp_dict[chave_furo]

    cmap = plt.get_cmap("viridis") # Colormap para os furos

    # --- 2. Preparar Visualização Bruta (Sua Solicitação) ---
    print("\nPreparando Visualização 1: Nuvens Brutas Agregadas (Sem ICP)")
    nuvens_brutas_bico.paint_uniform_color([1.0, 0.0, 0.0]) # Bico em Vermelho
    geometrias_brutas_agregadas.append(nuvens_brutas_bico)
    
    ids_furos_brutos = sorted(nuvens_brutas_furos.keys())
    for i, f_id in enumerate(ids_furos_brutos):
        pcd_furo_bruto = nuvens_brutas_furos[f_id]
        color = cmap(i / max(1, len(ids_furos_brutos) - 1))[:3]
        pcd_furo_bruto.paint_uniform_color(color)
        geometrias_brutas_agregadas.append(pcd_furo_bruto)
    
    if visualizar and geometrias_brutas_agregadas:
        print("  -> Abrindo Visualizador (Bruto)... Feche para continuar.")
        o3d.visualization.draw_geometries(
            geometrias_brutas_agregadas, 
            window_name="Visualizacao Agregada - Nuvens Brutas (Sem Alinhamento)"
        )
    
    # --- 3. Preparar Visualização Pós-ICP com Legendas (Sua Solicitação) ---
    print("\nPreparando Visualização 2: Nuvens Finais Pós-ICP (Com Legendas)")
    print("\n--- LEGENDA DA VISUALIZACAO FINAL (PÓS-ICP) ---")
    
    nuvens_icp_bico.paint_uniform_color([1.0, 0.0, 0.0]) # Bico em Vermelho
    geometrias_icp_agregadas.append(nuvens_icp_bico)
    print(f"  - Bico = Vermelho")

    chaves_furos_icp = sorted(nuvens_icp_furos.keys())
    for i, chave_furo in enumerate(chaves_furos_icp):
        pcd_furo_icp = nuvens_icp_furos[chave_furo]
        if not pcd_furo_icp.has_points(): continue
        
        color = cmap(i / max(1, len(chaves_furos_icp) - 1))[:3]
        pcd_furo_icp.paint_uniform_color(color)
        geometrias_icp_agregadas.append(pcd_furo_icp)
        
        # Adiciona a "Legenda" (Esfera 3D)
        centroide_furo = pcd_furo_icp.get_center()
        nome_furo_legivel = chave_furo.replace('_', ' ').title()
        
        # Adiciona a esfera de legenda
        legenda_esfera = criar_legenda_3d(nome_furo_legivel, centroide_furo, color)
        geometrias_icp_agregadas.append(legenda_esfera)
        
        print(f"  - {nome_furo_legivel} = Cor {color} (marcado com esfera)")
    
    print("="*50)

    # Salva a nuvem combinada final Pós-ICP
    if geometrias_icp_agregadas:
        nuvem_combinada_final = o3d.geometry.PointCloud()
        for geo in geometrias_icp_agregadas:
            if isinstance(geo, o3d.geometry.PointCloud):
                nuvem_combinada_final += geo
        
        # Remove outliers e faz downsample
        nuvem_combinada_final, _ = nuvem_combinada_final.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        nuvem_combinada_final = nuvem_combinada_final.voxel_down_sample(voxel_size=0.0005) # Voxel de 0.5mm
        
        # Salva o .ply
        caminho_ply_final = output_dir_analise / "analise_agregada_final.ply"
        o3d.io.write_point_cloud(str(caminho_ply_final), nuvem_combinada_final)
        print(f"\nNuvem de pontos Pós-ICP agregada salva em: {caminho_ply_final}")
        
        # Substitui as geometrias pela nuvem limpa (mas sem as esferas)
        # Para a visualização final, é melhor mostrar com as legendas
        # geometrias_icp_agregadas = [nuvem_combinada_final] # Descomente se quiser ver SÓ a nuvem limpa

    if visualizar and geometrias_icp_agregadas:
        print("  -> Abrindo Visualizador (Pós-ICP com Legendas)... Feche para finalizar.")
        o3d.visualization.draw_geometries(
            geometrias_icp_agregadas, 
            window_name="Visualizacao Agregada - FINAL Pós-ICP (Com Legendas)"
        )

# --- Função Main e Argument Parser (como no original) ---
def main(num_frames_processar, visualizar):
    """
    Função principal ORQUESTRADORA.
    1. Chama a gravação ao vivo.
    2. Itera pelos .bag gravados e chama a análise individual.
    3. Chama a visualização agregada final.
    """
    
    # --- 0. Define o diretório de saída ---
    output_dir_analise = Path(pasta_base) / "analises_offline"
    output_dir_analise.mkdir(exist_ok=True)
    
    # --- 1. Gravar Sessões .bag ---
    # Esta função abre a câmera ao vivo e retorna uma lista de arquivos .bag
    lista_arquivos_bag = gravar_sessoes_de_analise(output_dir_analise)
    
    if not lista_arquivos_bag:
        print("Nenhum arquivo .bag foi gravado. Encerrando.")
        return

    # --- 2. Carregar Modelo YOLO (uma única vez) ---
    try:
        model = YOLO(MODELO_YOLO_PATH)
        print("Modelo YOLO carregado com sucesso.")
    except Exception as e: 
        print(f"ERRO CRÍTICO ao carregar o modelo YOLO: {e}"); return

    # --- 3. Analisar cada .bag gravado ---
    resultados_agregados = [] # Lista para guardar os resultados de cada .bag
    
    for bag_file_path in lista_arquivos_bag:
        # Chama a função de análise refatorada
        retorno = analisar_arquivo_bag(
            bag_file_path, 
            num_frames_processar, 
            visualizar, 
            model,
            output_dir_analise
        )
        
        nuvens_icp_dict, nuvens_brutas_dict, nome_base = retorno
        
        if nuvens_icp_dict is not None and nuvens_brutas_dict is not None:
            resultados_agregados.append((nuvens_icp_dict, nuvens_brutas_dict, nome_base))
        else:
            print(f"AVISO: Análise do arquivo {bag_file_path} falhou e será ignorada na agregação.")

    # --- 4. Visualização Agregada Final ---
    if resultados_agregados:
        visualizar_analise_agregada(resultados_agregados, visualizar, output_dir_analise)
    else:
        print("Nenhuma análise foi bem-sucedida. Não há nada para agregar.")

    print("\n--- Processo Concluído ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processa um arquivo .bag RealSense para análise 3D com ICP.")
    
    # Argumentos originais, mas agora 'bag_file' não é mais usado
    parser.add_argument("-n", "--num_frames", type=int, default=NUM_FRAMES_ANALISE,
                        help=f"Número de frames a serem extraídos e analisados (padrão: {NUM_FRAMES_ANALISE}).")
    parser.add_argument("-v", "--visualize", action="store_true",
                        help="Habilita a visualização das nuvens de pontos Open3D durante o processo.")
    
    # Removemos o argumento obrigatório 'bag_file'
    # parser.add_argument(fr"bag_file", help="Caminho para o arquivo .bag a ser processado.")
    
    args = parser.parse_args()
    
    # Chama a nova main orquestradora
    main(args.num_frames, args.visualize)