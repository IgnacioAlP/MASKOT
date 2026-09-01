import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from controladores import usuarios_controlador
from bd import obtener_conexion
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('reset_password')

if len(sys.argv) < 3:
    print('Usage: reset_password.py <username> <new_password>')
    sys.exit(1)

username = sys.argv[1]
new_password = sys.argv[2]

hashed = usuarios_controlador.hash_password(new_password)

try:
    conn = obtener_conexion()
    with conn.cursor() as cursor:
        cursor.execute('UPDATE usuarios SET password = %s WHERE username = %s', (hashed, username))
        affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected:
        logger.info('Password updated for user: %s', username)
    else:
        logger.warning('No user updated. Username may not exist: %s', username)
except Exception as e:
    logger.exception('Error updating password: %s', e)
    sys.exit(2)
