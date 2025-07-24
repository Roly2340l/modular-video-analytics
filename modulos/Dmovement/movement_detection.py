import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from vision import check_motion_v1
import cv2 as cv

prev_frame = None

def procesar_movimiento(frame):
    global prev_frame
    data = {}

    if prev_frame is not None:
        motion_detected, frame_with_motion, _, Coordenadas = check_motion_v1(prev_frame, frame)
        data["motion_detected"] = motion_detected
        data["coordenadas"] = Coordenadas
        prev_frame = frame
        return frame_with_motion, data
    else:
        prev_frame = frame
        return frame, data  # Devuelve siempre un diccionario vacío si no hay detecciones