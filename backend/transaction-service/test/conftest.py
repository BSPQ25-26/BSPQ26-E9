import os
import sys

# Añadir la raíz del servicio al path para que encuentre "app"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
