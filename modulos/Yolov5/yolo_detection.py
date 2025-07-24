# yolo_detection.py
import torch
import cv2

modelo_yolo = torch.hub.load('ultralytics/yolov5', 'custom', path='modulos/Yolov5/yolov5s.pt')

def procesar_objetos(frame):
    results = modelo_yolo(frame)
    data = {
        "detecciones": []
    }

    for result in results.xyxy[0].cpu().numpy():
        x_min, y_min, x_max, y_max, conf, cls = result
        label = modelo_yolo.names[int(cls)]
        cv2.rectangle(frame, (int(x_min), int(y_min)), (int(x_max), int(y_max)), (0, 255, 0), 2)
        cv2.putText(frame, label, (int(x_min), int(y_min) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        data["detecciones"].append({
            "label": label,
            "confidence": float(conf),
            "coordinates": [int(x_min), int(y_min), int(x_max), int(y_max)]
        })

    return frame, data
