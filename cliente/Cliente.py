import cv2
import numpy as np
import asyncio
import websockets
import json
import base64
import time
import requests

# Función para intentar conexión y verificar token
async def verificar_conexion(uri):
    try:
        async with websockets.connect(uri) as websocket:
            print("Conectado correctamente al servidor.")
            return True
    except websockets.exceptions.InvalidStatusCode:
        print("Error: Token inválido o conexión denegada.")
        return False
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

# Función para usar el servicio
async def usar_servicio(uri, servicio):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No se pudo abrir la cámara")
        return

    previous_frame_time = time.time()

    async with websockets.connect(uri) as websocket:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Codificar el frame antes de enviarlo
            _, buffer = cv2.imencode('.jpg', frame)

            # Medir el tiempo de ida y vuelta (RTT)
            start_rtt_time = time.time()

            await websocket.send(servicio)  # Enviar el servicio
            await websocket.send(buffer.tobytes())  # Enviar el frame codificado

            try:
                response = await websocket.recv()
                end_rtt_time = time.time()  # Finaliza el tiempo RTT

                # Cálculo de latencia de ida y vuelta (RTT)
                rtt_time = end_rtt_time - start_rtt_time

                # Procesar la respuesta del servidor
                response_data = json.loads(response)
                processing_time_server = response_data["processing_time"]

                # Calcular el tiempo total (RTT + tiempo de procesamiento en el servidor)
                total_time = rtt_time + processing_time_server

                # Decodificar la imagen recibida
                img_data = base64.b64decode(response_data["image"])
                img_array = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                # Calcular los FPS basados en el tiempo entre frames
                time_between_frames = time.time() - previous_frame_time
                previous_frame_time = time.time()

                # Imprimir las métricas
                print(f"FPS: {1 / time_between_frames:.2f}")
                print(f"Latencia de ida y vuelta (RTT): {rtt_time:.4f} s")
                print(f"Tiempo de procesamiento en el servidor: {processing_time_server:.4f} s")
                print(f"Tiempo total (RTT + procesamiento): {total_time:.4f} s")

                # Mostrar el frame procesado
                cv2.imshow("Cliente - Frame Procesado", frame)

            except websockets.exceptions.ConnectionClosedOK:
                print("Conexión cerrada por el servidor")
                break

            # Salir del servicio si se presiona la tecla 'q'
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Saliendo del servicio...")
                break

    cap.release()
    cv2.destroyAllWindows()

# En el cliente, modificar la función de consulta para que permita consultas detalladas
def consultar_db(email, servicio, detalles_especificos=None):
    url = "http://localhost:8000/consultar"
    params = {"email": email, "tipo_servicio": servicio}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        results = response.json()
        if results:
            for result in results:
                print("Fecha y Hora:", result.get("timestamp", ""))
                print("Servicio:", result.get("servicio", ""))
                
                # Mostrar detalles según el tipo de servicio
                if result["servicio"] == "movimiento":
                    print("Movimiento Detectado:", result.get("motion_detected", ""))
                    print("Coordenadas del Movimiento:", result.get("valor", ""))
                
                elif result["servicio"] == "objetos":
                    print("Etiqueta del Objeto:", result.get("label", ""))
                    print("Confianza:", result.get("confidence", ""))
                    print("Coordenadas del Objeto:", result.get("coordinates", ""))
                
                print("-" * 30)
        else:
            print("No se encontraron resultados para los criterios proporcionados.")
    else:
        print("Error al realizar la consulta:", response.text)

# Función para obtener el token
def obtener_token():
    login_url = "http://localhost:8000/auth/login"
    print(f"Visita el siguiente enlace para obtener tu token: {login_url}")

    for intento in range(3):
        raw_token = input("Ingresa el token de autenticación de Google: ")
        token = raw_token.strip().strip('"').strip("'")

        if token:
            print("Token ingresado correctamente.")
            return token
        else:
            print(f"Token no válido. Te quedan {2 - intento} intentos.")

    print("Número de intentos excedido. No se pudo obtener un token válido.")
    return None

# Menú principal
async def menu_principal():
    for intentos in range(3):
        token = obtener_token()
        if not token:
            print("No se pudo obtener el token de autenticación.")
            return

        uri = f"ws://localhost:8000/ws?token={token}"

        if await verificar_conexion(uri):
            break
        else:
            print(f"Intento fallido. Te quedan {2 - intentos} intentos.")
            if intentos == 2:
                print("Número de intentos excedido. No se pudo conectar al servidor.")
                return

    while True:
        print("\n--- Menú Principal ---")
        print("1. Usar servicio")
        print("2. Consultar base de datos")
        print("q. Salir")
        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            print("\n--- Servicios Disponibles ---")
            print("1. Normal")
            print("2. Movimiento")
            print("3. Objetos")
            servicio_opcion = input("Selecciona el servicio: ")

            if servicio_opcion == "1":
                await usar_servicio(uri, "normal")
            elif servicio_opcion == "2":
                await usar_servicio(uri, "movimiento")
            elif servicio_opcion == "3":
                await usar_servicio(uri, "objetos")
            else:
                print("Opción de servicio no válida.")
                continue

        elif opcion == "2":
            print("\n--- Consultar Base de Datos ---")
            email = input("Ingresa tu correo electrónico para la consulta: ")
            servicio = input("Ingresa el tipo de servicio (movimiento, objetos) o déjalo en blanco para consultar todos: ")
            print("\n¿Deseas información detallada? Elige atributos específicos o deja en blanco para todos:")
            print("1. Detalles generales")
            print("2. Coordenadas de movimiento")
            print("3. Etiquetas de objetos")
            print("4. Todos los detalles")
            detalle_opcion = input("Selecciona la opción: ")

            if detalle_opcion == "1":
                consultar_db(email, servicio, ["detalles"])
            elif detalle_opcion == "2":
                consultar_db(email, servicio, ["coordenadas"])
            elif detalle_opcion == "3":
                consultar_db(email, servicio, ["etiqueta"])
            elif detalle_opcion == "4" or detalle_opcion == "":
                consultar_db(email, servicio)  # Sin especificar detalles, muestra todos
            else:
                print("Opción de detalles no válida.")

        elif opcion.lower() == "q":
            print("Saliendo del programa...")
            break
        else:
            print("Opción no válida, por favor intenta de nuevo.")
            continue

if __name__ == "__main__":
    asyncio.run(menu_principal())
