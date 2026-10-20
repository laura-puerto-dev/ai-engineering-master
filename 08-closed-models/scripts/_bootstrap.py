# GUÍA DE LECTURA · scripts/_bootstrap.py
# Permite ejecutar scripts desde la terminal con python scripts/archivo.py.
# Añade la raíz del proyecto a las rutas donde Python busca el paquete curso.
# No instala dependencias ni modifica los archivos del proyecto.

# Path permite construir rutas, comprobar archivos y leer/escribir sin concatenar separadores a mano.
from pathlib import Path

# Gestiona rutas de importación y el intérprete actual de Python.
import sys

# Añade la raíz al principio de sys.path para importar el paquete curso desde un script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
