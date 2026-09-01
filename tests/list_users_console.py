import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from controladores import usuarios_controlador
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('list_users')

try:
    usuarios = usuarios_controlador.obtener_usuarios()
    logger.info('Usuarios obtenidos: %s', usuarios)
    print('Total usuarios:', len(usuarios))
    for u in usuarios:
        print(u)
except Exception as e:
    logger.exception('Error al obtener usuarios: %s', e)

print('Fin listado usuarios')
