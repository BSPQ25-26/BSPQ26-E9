import os
import sys

# Asegurar que el directorio raíz del servicio está en sys.path
# para que pytest pueda encontrar el módulo 'app'
service_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if service_root not in sys.path:
    sys.path.insert(0, service_root)
