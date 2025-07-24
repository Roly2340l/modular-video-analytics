from fastapi import FastAPI, WebSocket, HTTPException, Depends
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt
import requests
import numpy as np
import cv2
import base64
import time
import socket
import threading
import struct
import json
from starlette.websockets import WebSocketDisconnect
from modulos.Yolov5.yolo_detection import procesar_objetos
from modulos.Dmovement.movement_detection import procesar_movimiento
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD
import datetime
from fastapi import FastAPI, WebSocket, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from rdflib import Graph, Namespace
from rdflib.plugins.sparql import prepareQuery
from pathlib import Path

# Configuración de autenticación y cliente OAuth de Google
CLIENT_ID = "AQUI_PON_TU_CLIENT_ID"
CLIENT_SECRET = "AQUI_PON_TU_CLIENT_SECRET"
REDIRECT_URI = "http://localhost:8000/auth/callback"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# Instancia de FastAPI
app = FastAPI()

# Configuración de seguridad OAuth2
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/auth",
    tokenUrl=TOKEN_URL
)

# Ruta para iniciar el proceso de autenticación con Google
@app.get("/auth/login")
async def login():
    # URL de autenticación de Google con parámetros para obtener el código de autorización
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile"
    )
    return {"auth_url": auth_url}

# Callback para obtener el token tras la autenticación
@app.get("/auth/callback")
async def callback(code: str):
    # Canjear el código de autorización por un token de acceso
    response = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
    )
    
    token_data = response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="No se pudo obtener el token de acceso")
    
    # Obtener la información del usuario con el token de acceso
    user_info = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}).json()
    
    return {"access_token": access_token, "user_info": user_info}

# Función auxiliar para verificar el token y obtener información del usuario
def verify_google_token(access_token: str):
    # Solicitar información del usuario a Google usando el access token
    response = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code != 200:
        return None
    return response.json()  # Devuelve la información del usuario si el token es válido

# Lista de módulos de procesamiento
modulos = {
    'objetos': procesar_objetos,
    'movimiento': procesar_movimiento,
    'normal': lambda x: x
}

EX = Namespace("http://example.org/")

# Función para guardar detección en RDF, con usuario como nodo principal
def guardar_deteccion_rdf(user_info, servicio, datos=None):
    g = Graph()

    usuario_id = f"http://example.org/usuario/{user_info['sub']}"
    usuario = URIRef(usuario_id)
    g.add((usuario, RDF.type, EX.Usuario))
    g.add((usuario, EX.nombre, Literal(user_info.get("name"))))
    g.add((usuario, EX.email, Literal(user_info.get("email"))))

    # Generar el timestamp en formato adecuado para el nombre del archivo y el RDF
    timestamp = datetime.datetime.now().isoformat()
    deteccion_id = f"http://example.org/deteccion/{servicio}_{timestamp}"
    deteccion = URIRef(deteccion_id)
    g.add((deteccion, RDF.type, EX.Deteccion))
    g.add((deteccion, EX.realizadaPor, usuario))
    g.add((deteccion, EX.servicio, Literal(servicio)))
    g.add((deteccion, EX.timestamp, Literal(timestamp, datatype=XSD.dateTime)))

    if datos:  # Solo procesar si `datos` no es None
        if isinstance(datos, dict):
            for key, value in datos.items():
                # Si el valor es una lista, se asume que contiene múltiples detecciones o coordenadas
                if isinstance(value, list):
                    for idx, item in enumerate(value):
                        item_uri = URIRef(f"{deteccion_id}/{key}_{idx}")
                        g.add((item_uri, RDF.type, EX.Objeto))
                        g.add((item_uri, EX.deteccionAsociada, deteccion))
                        if isinstance(item, dict):
                            for subkey, subvalue in item.items():
                                g.add((item_uri, EX[subkey], Literal(subvalue)))
                        else:
                            g.add((item_uri, EX.valor, Literal(item)))
                else:
                    g.add((deteccion, EX[key], Literal(value)))
        else:
            print(f"Formato de `datos` inesperado: {type(datos)}")

    # Crear el nombre del archivo RDF con el timestamp
    file_path = f"almacenamiento_rdf/deteccion_{servicio}_{timestamp}.ttl"
    g.serialize(destination=file_path, format="turtle")
    print(f"Detección guardada en RDF en {file_path}")

# En tu servidor, mejorar la consulta en /consultar
@app.get("/consultar")
async def consultar_db(
    email: str = Query(None, description="Email del usuario para filtrar los datos"),
    tipo_servicio: str = Query(None, description="Tipo de servicio, por ejemplo, 'movimiento' o 'objetos'")
):
    g = Graph()
    for file_path in Path("almacenamiento_rdf").glob("*.ttl"):
        g.parse(file_path, format="turtle")

    # Consulta SPARQL mejorada para capturar detalles de detecciones y objetos asociados
    query = """
    SELECT ?timestamp ?servicio ?motion_detected ?valor ?label ?confidence ?coordinates WHERE {
        ?deteccion a ex:Deteccion ;
                   ex:realizadaPor ?usuario ;
                   ex:servicio ?servicio ;
                   ex:timestamp ?timestamp .
        ?usuario ex:email ?email .

        # Captura datos específicos para cada servicio
        OPTIONAL { ?deteccion ex:motion_detected ?motion_detected }
        
        # Relación entre detección y objetos asociados para capturar valor, label, confidence y coordinates
        OPTIONAL {
            ?objeto ex:deteccionAsociada ?deteccion ;
                    ex:valor ?valor .
        }
        OPTIONAL {
            ?objeto ex:deteccionAsociada ?deteccion ;
                    ex:label ?label ;
                    ex:confidence ?confidence ;
                    ex:coordinates ?coordinates .
        }
    """
    if tipo_servicio:
        query += f" FILTER(?servicio = '{tipo_servicio}')"
    query += "} ORDER BY ?timestamp"

    # Preparar y ejecutar la consulta
    q = prepareQuery(query, initNs={"ex": EX})
    results = []
    for row in g.query(q, initBindings={'email': Literal(email)}):
        results.append({
            "timestamp": str(row.timestamp),
            "servicio": str(row.servicio),
            "motion_detected": str(row.motion_detected) if row.motion_detected else "No data",
            "valor": str(row.valor) if row.valor else "No coordenadas",
            "label": str(row.label) if row.label else "No etiqueta",
            "confidence": str(row.confidence) if row.confidence else "No confianza",
            "coordinates": str(row.coordinates) if row.coordinates else "No coordenadas"
        })

    return JSONResponse(content=results)

# Modificación en `websocket_endpoint` para incluir guardado RDF
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        user_info = verify_google_token(token)
        if not user_info:
            print("Token inválido")
            await websocket.close()
            return

        await websocket.accept()
        print(f"Conexión permitida para el usuario: {user_info.get('name', 'Desconocido')}")

        while True:
            servicio = await websocket.receive_text()
            if servicio not in modulos:
                print("Servicio no reconocido")
                continue

            try:
                data = await websocket.receive_bytes()
                nparr = np.frombuffer(data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                start_processing_time = time.time()
                frame_procesado, datos = modulos[servicio](frame)
                processing_time = time.time() - start_processing_time

                guardar_deteccion_rdf(user_info, servicio, datos)

                _, img_encoded = cv2.imencode('.jpg', frame_procesado)
                img_base64 = base64.b64encode(img_encoded).decode('utf-8')
                response = {
                    "processing_time": processing_time,
                    "image": img_base64
                }
                await websocket.send_json(response)

            except Exception as e:
                print(f"Error en el procesamiento de frame: {e}")
                break
    except Exception as e:
        if isinstance(e, WebSocketDisconnect) and e.code == 1000:
            print("Conexión cerrada limpiamente por el cliente.")
        else:
            print(f"Error inesperado: {e}")
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            print("Conexión ya cerrada.")

# Manejo de clientes TCP para Python 2.7
def handle_tcp_connection(conn, addr):
    print(f"Conexión establecida con {addr}")
    try:
        while True:
            # Recibir el servicio seleccionado
            servicio = b''
            while not servicio.endswith(b'\n'):
                part = conn.recv(1)
                if not part:
                    print(f"Cliente {addr} desconectado.")
                    return
                servicio += part

            servicio = servicio.decode('utf-8').strip()

            if servicio not in modulos:
                print(f"Servicio no reconocido: {servicio}")
                continue

            # Recibir la longitud del frame
            data_length_bytes = conn.recv(4)
            if not data_length_bytes:
                print(f"No se pudo recibir la longitud del frame de {addr}.")
                break

            data_length = struct.unpack('!I', data_length_bytes)[0]

            # Recibir los datos del frame
            data = b''
            while len(data) < data_length:
                packet = conn.recv(data_length - len(data))
                if not packet:
                    print(f"No se recibieron todos los datos del cliente {addr}.")
                    return
                data += packet

            try:
                img_data = base64.b64decode(data)
                nparr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    print(f"El frame recibido de {addr} no es válido.")
                    continue

                # Procesar el frame según el servicio
                start_processing_time = time.time()
                frame_procesado, datos = modulos[servicio](frame)
                processing_time = time.time() - start_processing_time

                # Guardar la detección en RDF (sin autenticación, usando dirección como identificador)
                user_info = {
                    "sub": addr[0],  # IP del cliente como identificador
                    "name": f"Cliente {addr}",
                    "email": f"cliente_{addr[0].replace('.', '_')}@example.com"
                }
                guardar_deteccion_rdf(user_info, servicio, datos)

                # Codificar la imagen procesada
                _, img_encoded = cv2.imencode('.jpg', frame_procesado)
                img_base64 = base64.b64encode(img_encoded).decode('utf-8')

                # Crear la respuesta JSON
                response = {
                    "processing_time": processing_time,
                    "image": img_base64,
                    "datos": datos  # Incluye datos adicionales sobre detecciones
                }

                # Convertir a bytes y enviar la longitud seguida del contenido
                response_json = json.dumps(response).encode('utf-8')
                response_length = struct.pack('!I', len(response_json))
                conn.sendall(response_length)
                conn.sendall(response_json)

            except Exception as e:
                print(f"Error procesando el frame de {addr}: {e}")
                continue

    except Exception as e:
        print(f"Error en la conexión con {addr}: {e}")
    finally:
        print(f"Conexión cerrada con {addr}")
        conn.close()

# Iniciar servidor TCP
def start_tcp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 9000))
    server_socket.listen(5)
    print("Servidor TCP en ejecución...")

    try:
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_tcp_connection, args=(conn, addr)).start()
    except KeyboardInterrupt:
        print("Servidor TCP detenido")
    finally:
        server_socket.close()

# Ejecutar ambos servidores (FastAPI y TCP)
if __name__ == "__main__":
    import uvicorn
    tcp_thread = threading.Thread(target=start_tcp_server)
    tcp_thread.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)
