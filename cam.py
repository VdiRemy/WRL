#testar abertura de webcam
import cv2
import tkinter as tk

cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("Erro ao abrir a câmera.")
    exit()
ret, frame = cam.read()
if not ret:
    print("Erro ao capturar o frame.")
    exit()
cv2.imshow("Webcam Teste", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()