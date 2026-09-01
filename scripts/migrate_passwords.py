#!/usr/bin/env python3
"""Script seguro para migrar contraseñas en texto plano a SHA256.
- Crea un respaldo de la tabla `usuarios` en un archivo SQL (simple dump SELECT INTO).
- Convierte las contraseñas que no tienen formato de SHA256 a su hash.

USO:
    .venv\Scripts\python.exe scripts\migrate_passwords.py

NOTA: Revisa el respaldo antes de aplicar en producción.
"""
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bd import obtener_conexion
from controladores import usuarios_controlador
import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('migrate_passwords')

BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

HEX64_RE = re.compile(r'^[0-9a-fA-F]{64}$')

def dump_users_to_file(conn, path):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, username, password, rol, activo, created_at FROM usuarios")
        rows = cursor.fetchall()
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(str(r) + '\n')


def main():
    logger.info('Iniciando migración de contraseñas')
    conn = obtener_conexion()
    try:
        # Backup simple
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(BACKUP_DIR, f'usuarios_backup_{now}.txt')
        logger.info('Creando respaldo en %s', backup_path)
        dump_users_to_file(conn, backup_path)

        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, password FROM usuarios")
            users = cursor.fetchall()

            for user in users:
                uid, uname, pwd = user
                if pwd is None:
                    continue
                if isinstance(pwd, bytes):
                    try:
                        pwd = pwd.decode('utf-8')
                    except:
                        continue

                if HEX64_RE.match(pwd.strip()):
                    logger.debug('User %s id=%s already hashed', uname, uid)
                    continue

                # No parece un hash; migrar
                new_hash = usuarios_controlador.hash_password(pwd)
                logger.info('Migrando contraseña para user=%s id=%s', uname, uid)
                cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", (new_hash, uid))

        conn.commit()
        logger.info('Migración completada correctamente')
    except Exception as e:
        logger.exception('Error durante la migración: %s', e)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
