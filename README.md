# Modular Video Analytics

Este proyecto implementa un sistema modular de análisis de video en tiempo real.  
Permite procesar video proveniente de diferentes clientes (webcam local, robot Pepper u otros) mediante módulos personalizables, devolviendo resultados en tiempo real y almacenando detecciones en un modelo semántico RDF.

## Características

- Procesamiento de video en tiempo real.
- Arquitectura modular: puedes añadir nuevos módulos fácilmente.
- Soporte para clientes WebSocket (con autenticación Google OAuth2) y TCP (clientes legacy o Pepper).
- Almacenamiento semántico RDF de cada detección (consultable por SPARQL).
- Integración con el robot Pepper vía SDK `qi`.

## Estructura

```
modular-video-analytics/
├── servidor/
│   ├── Servidor.py
│   ├── modulos/
│   │   ├── Dmovement/
│   │   │   ├── movement_detection.py
│   │   │   └── utils.py
│   │   └── Yolov5/
│   │       └── yolo_detection.py
│   └── almacenamiento_rdf/
│       └── .gitkeep
├── clientes/
│   ├── Cliente.py
│   ├── Cliente_python27.py
│   ├── Pepper.py
│   └── VisualizadorPepper.py
├── requirements.txt
└── README.md
```

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/TU_USUARIO/modular-video-analytics.git
cd modular-video-analytics
```

2. Crea un entorno virtual e instálalo:
```bash
python -m venv venv
source venv/bin/activate   # En Linux/Mac
venv\Scripts\activate      # En Windows
pip install -r requirements.txt
```

> **Nota:**  
> En el robot Pepper es necesario tener instalado el SDK `qi` en su entorno NAOqi. No se instala con `pip`, sino desde el software del robot.

## Ejecución

### 1. Servidor (en la laptop)
Inicia el servidor principal que escucha WebSocket y TCP:
```bash
cd servidor
python Servidor.py
```

- WebSocket disponible en `ws://<IP_LAPTOP>:8000/ws`
- TCP disponible en `<IP_LAPTOP>:9000`

### 2. Cliente WebSocket (en la laptop)
Permite autenticarse con Google y usar la webcam local:
```bash
cd clientes
python Cliente.py
```

### 3. Cliente TCP legacy (en la laptop)
Prueba de cliente TCP compatible con Python 2.7:
```bash
cd clientes
python Cliente_python27.py
```

### 4. Robot Pepper (cliente TCP)
En el robot (o dispositivo con SDK `qi`):
```bash
cd clientes
python Pepper.py
```

### 5. Visualizador Pepper (en la laptop)
Para mostrar los frames procesados que Pepper reenvía:
```bash
cd clientes
python VisualizadorPepper.py
```

## 📊 Consultas RDF

Puedes consultar las detecciones almacenadas usando el endpoint HTTP:

```
GET http://<IP_LAPTOP>:8000/consultar?email=<EMAIL>&tipo_servicio=<movimiento|objetos>
```

Devuelve resultados en JSON con timestamp, servicio y datos asociados (objetos detectados, coordenadas, etc.).

## Agregar nuevos módulos

Para agregar un nuevo módulo de procesamiento:
1. Crea un archivo en `servidor/modulos/` que defina una función:
```python
def procesar(frame):
    # Procesa y devuelve frame procesado y datos
    return frame, {}
```
2. Regístralo en el diccionario `modulos` dentro de `Servidor.py`:
```python
modulos = {
    'objetos': procesar_objetos,
    'movimiento': procesar_movimiento,
    'normal': lambda x: (x, {}),
    'tu_modulo': procesar_tu_modulo
}
```

## Requerimientos

Ver `requirements.txt` para dependencias principales:
```
fastapi
uvicorn
websockets
opencv-python
numpy
requests
rdflib
python-jose
pillow
torch
torchvision
ultralytics
```

## Notas finales

- Asegúrate de que la laptop y el robot estén en la misma red.
- Abre los puertos 8000 (HTTP/WebSocket) y 9000 (TCP) en el firewall de la laptop.
- Para pruebas sin Pepper, puedes usar únicamente `Cliente.py`.
