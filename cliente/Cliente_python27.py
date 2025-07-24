import socket
import base64
import cv2
import struct
import numpy as np
import json
import time

def usar_servicio(conn, servicio):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No se pudo abrir la camara")
        return

    previous_frame_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al leer el frame de la camara")
            break

        start_rtt_time = time.time()

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            print("Error al codificar el frame")
            continue

        img_base64 = base64.b64encode(buffer.tobytes())
        conn.sendall(servicio + '\n')

        data_length = len(img_base64)
        conn.sendall(struct.pack('!I', data_length))
        conn.sendall(img_base64)

        data_length_bytes = conn.recv(4)
        if not data_length_bytes:
            print("Error: No se recibieron datos del servidor")
            break

        data_length = struct.unpack('!I', data_length_bytes)[0]

        response_data = b''
        while len(response_data) < data_length:
            packet = conn.recv(data_length - len(response_data))
            if not packet:
                print("Error: No se recibieron suficientes datos del servidor")
                break
            response_data += packet

        end_rtt_time = time.time()
        rtt_time = end_rtt_time - start_rtt_time

        response = json.loads(response_data)
        processing_time_server = response["processing_time"]
        total_time = rtt_time + processing_time_server

        img_data = base64.b64decode(response["image"])
        nparr = np.frombuffer(img_data, np.uint8)
        frame_procesado = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_procesado is None:
            print("Error: El frame recibido es invalido")
        else:
            cv2.imshow("Frame Procesado", frame_procesado)

        time_between_frames = time.time() - previous_frame_time
        previous_frame_time = time.time()

        print("FPS: {:.2f}".format(1 / time_between_frames))
        print("Latencia de ida y vuelta (RTT): {:.4f} s".format(rtt_time))
        print("Tiempo de procesamiento en el servidor: {:.4f} s".format(processing_time_server))
        print("Tiempo total (RTT + procesamiento): {:.4f} s".format(total_time))

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Saliendo del servicio...")
            break

    cap.release()
    cv2.destroyAllWindows()

def consultar_db(email, servicio):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('127.0.0.1', 9000))

    request = {"email": email, "tipo_servicio": servicio}
    request_json = json.dumps(request).encode('utf-8')
    sock.sendall(struct.pack('!I', len(request_json)))
    sock.sendall(request_json)

    data_length_bytes = sock.recv(4)
    if not data_length_bytes:
        print("Error: No se recibieron datos del servidor")
        sock.close()
        return

    data_length = struct.unpack('!I', data_length_bytes)[0]

    response_data = b''
    while len(response_data) < data_length:
        packet = sock.recv(data_length - len(response_data))
        if not packet:
            print("Error: No se recibieron suficientes datos del servidor")
            sock.close()
            return
        response_data += packet

    response = json.loads(response_data)
    for result in response:
        print("Fecha y Hora:", result.get("timestamp", ""))
        print("Servicio:", result.get("servicio", ""))
        if result["servicio"] == "movimiento":
            print("Movimiento Detectado:", result.get("motion_detected", ""))
            print("Coordenadas del Movimiento:", result.get("valor", ""))
        elif result["servicio"] == "objetos":
            print("Etiqueta del Objeto:", result.get("label", ""))
            print("Confianza:", result.get("confidence", ""))
            print("Coordenadas del Objeto:", result.get("coordinates", ""))
        print("-" * 30)

    sock.close()

def menu_principal():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('192.168.31.79', 9000))

    while True:
        print("\n--- Menu Principal ---")
        print("1. Usar servicio")
        print("2. Consultar base de datos")
        print("q. Salir")
        opcion = raw_input("Selecciona una opcion: ")

        if opcion == "1":
            print("\n--- Servicios Disponibles ---")
            print("1. Normal")
            print("2. Movimiento")
            print("3. Objetos")
            servicio_opcion = raw_input("Selecciona el servicio: ")

            if servicio_opcion == "1":
                usar_servicio(sock, "normal")
            elif servicio_opcion == "2":
                usar_servicio(sock, "movimiento")
            elif servicio_opcion == "3":
                usar_servicio(sock, "objetos")
            else:
                print("Opcion de servicio no valida.")
                continue

        elif opcion == "2":
            email = raw_input("Ingresa tu correo electronico para la consulta: ")
            servicio = raw_input("Ingresa el tipo de servicio (movimiento, objetos) o dejalo en blanco para consultar todos: ")
            consultar_db(email, servicio)

        elif opcion.lower() == "q":
            print("Saliendo del programa...")
            break
        else:
            print("Opcion no valida, por favor intenta de nuevo.")
            continue

    sock.close()

if __name__ == "__main__":
    menu_principal()