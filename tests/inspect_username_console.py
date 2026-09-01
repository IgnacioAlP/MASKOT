import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bd import obtener_conexion
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('inspect_username')

USERNAME = 'admin_maskot'

try:
    conn = obtener_conexion()
    with conn.cursor() as cursor:
        # Consultar exactamente con WHERE
        cursor.execute("SELECT id, username, password, rol, activo, HEX(username) as hex_user FROM usuarios WHERE username = %s", (USERNAME,))
        row = cursor.fetchone()
        logger.info('Resultado de SELECT con WHERE: %s', row)

        # Listar todos los usuarios con HEX(username)
        cursor.execute("SELECT id, username, HEX(username) as hex_user FROM usuarios ORDER BY id")
        rows = cursor.fetchall()
        logger.info('Todos los usuarios (id, username, hex):')
        for r in rows:
            logger.info(r)
    conn.close()
except Exception as e:
    logger.exception('Error al inspeccionar usernames: %s', e)

print('Inspección finalizada')
