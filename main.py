import pyrealsense2 as rs
import numpy as np
import cv2
import os

# === CONFIGURAÇÕES ===
bag_file = "registro_1759778131134.35.bag"  # Nome do arquivo .bag salvo anteriormente
output_folder = "frames_extraidos"

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
print(f"Lendo: {bag_file}")

# Para obter o controle do playback
device = pipeline.get_active_profile().get_device()
playback = device.as_playback()
playback.set_real_time(False)  # Para não depender do tempo real

frame_id = 0

try:
    while True:
        frames = pipeline.wait_for_frames()
        
        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            continue

        # Converte para numpy arrays
        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())

        # === Aqui você trata os frames individualmente ===

        # Exemplo: salva os frames como imagem
        color_path = os.path.join(output_folder, f"color_{frame_id:04d}.png")
        depth_path = os.path.join(output_folder, f"depth_{frame_id:04d}.png")

        cv2.imwrite(color_path, color_image)

        # Escala e aplica colormap para visualização
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
        )
        cv2.imwrite(depth_path, depth_colormap)

        # Mostra na tela (opcional)
        cv2.imshow("Color", color_image)
        cv2.imshow("Depth", depth_colormap)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_id += 1

except RuntimeError:
    print("Todos os frames foram processados.")

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    print(f"Total de frames processados: {frame_id}")
