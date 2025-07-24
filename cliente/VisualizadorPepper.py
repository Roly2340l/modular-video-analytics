import socket
import numpy as np
import struct
from PIL import Image
import io
import cv2

def main():
    laptop_ip = "192.168.31.79"  # Cambia por la IP de tu laptop
    laptop_port = 9001           # Puerto para recibir los frames

    # Configurar el socket para recibir frames
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((laptop_ip, laptop_port))
    server_socket.listen(1)
    print("Esperando conexion del robot...")

    conn, addr = server_socket.accept()
    print("Conectado al robot en {}:{}".format(addr[0], addr[1]))

    while True:
        # Recibir la longitud del frame
        data_length = conn.recv(4)
        if not data_length:
            break
        length = struct.unpack("!I", data_length)[0]

        # Recibir el frame
        frame_data = b""
        while len(frame_data) < length:
            packet = conn.recv(length - len(frame_data))
            if not packet:
                break
            frame_data += packet

        # Decodificar y mostrar el frame
        image = Image.open(io.BytesIO(frame_data))
        frame = np.array(image)
        cv2.imshow("Stream del Pepper", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    conn.close()
    server_socket.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
