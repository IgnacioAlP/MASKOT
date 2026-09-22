from bd import obtener_conexion, obtener_tenant_id
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def hash_password(password):
    """Genera un hash SHA-256 de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def obtener_usuario_por_nombre(username):
    """Obtiene un usuario por su nombre de usuario (independiente de Mayúsculas/Minúsculas)"""
    username = (username or '').strip()
    conexion = obtener_conexion()
    usuario = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password, rol, activo, tenant_id 
                FROM usuarios 
                WHERE LOWER(username) = LOWER(%s)
            """, (username,))
            usuario = cursor.fetchone()
    except Exception as e:
        logger.error(f"Error al obtener usuario por nombre: {e}")
    finally:
        conexion.close()
    return usuario

def obtener_todos_usuarios(tenant_id=None):
    """
    Obtiene todos los usuarios.
    Si tenant_id es especificado, filtra por ese tenant; si es None, usa el tenant actual.
    Si tenant_id == 'ALL', devuelve todos los usuarios del sistema (modo Superadmin).
    """
    conexion = obtener_conexion()
    if tenant_id is None:
        tenant_id = obtener_tenant_id()
        
    usuarios = []
    try:
        with conexion.cursor() as cursor:
            if tenant_id == 'ALL':
                cursor.execute("""
                    SELECT id, username, rol, activo, created_at, tenant_id
                    FROM usuarios 
                    ORDER BY created_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT id, username, rol, activo, created_at, tenant_id
                    FROM usuarios 
                    WHERE tenant_id = %s
                    ORDER BY created_at DESC
                """, (tenant_id,))
            usuarios = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error al obtener lista de usuarios: {e}")
    finally:
        conexion.close()
    return usuarios

def verificar_credenciales(username, password):
    username = (username or '').strip()
    password = (password or '').strip()

    usuario = obtener_usuario_por_nombre(username)

    if not usuario:
        logger.error(f"[LOGIN FAIL] No se encontró el usuario: '{username}'")
        return {
            'success': False,
            'user': None,
            'message': 'Usuario o contraseña incorrectos'
        }

    # Verificar estado activo
    if not usuario[4]:
        return {
            'success': False,
            'user': None,
            'message': 'La cuenta se encuentra desactivada.'
        }

    # Comparación segura limpiando espacios invisibles de la BD
    password_hash = hash_password(password)
    hash_en_bd = str(usuario[2]).strip() if usuario[2] else ''

    if password_hash == hash_en_bd:
        return {
            'success': True,
            'user': usuario,
            'message': 'Autenticación exitosa'
        }

    logger.error(f"[LOGIN FAIL] Contraseña incorrecta para el usuario: '{username}'")
    return {
        'success': False,
        'user': None,
        'message': 'Usuario o contraseña incorrectos'
    }
    
def insertar_usuario(username, password, rol='empleado', tenant_id=None):
    """Inserta un nuevo usuario (si tenant_id es None, asigna el del contexto actual)"""
    conexion = obtener_conexion()
    if tenant_id is None:
        tenant_id = obtener_tenant_id()
        
    username = (username or '').strip()
    rol = (rol or 'empleado').strip().lower()

    try:
        with conexion.cursor() as cursor:
            password_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO usuarios (username, password, rol, activo, created_at, tenant_id)
                VALUES (%s, %s, %s, true, CURRENT_TIMESTAMP, %s)
                RETURNING id
            """, (username, password_hash, rol, tenant_id))
            user_id = cursor.fetchone()[0]
            conexion.commit()
            return user_id
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al insertar usuario: {e}")
        return None
    finally:
        conexion.close()

def actualizar_password(user_id, nueva_password, tenant_id=None):
    """Actualiza la contraseña de un usuario"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            password_hash = hash_password(nueva_password)
            if tenant_id is not None:
                cursor.execute("""
                    UPDATE usuarios 
                    SET password = %s 
                    WHERE id = %s AND tenant_id = %s
                """, (password_hash, user_id, tenant_id))
            else:
                cursor.execute("""
                    UPDATE usuarios 
                    SET password = %s 
                    WHERE id = %s
                """, (password_hash, user_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al actualizar contraseña: {e}")
        return False
    finally:
        conexion.close()

def desactivar_usuario(user_id, tenant_id=None):
    """Desactiva un usuario del sistema"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            if tenant_id is not None:
                cursor.execute("""
                    UPDATE usuarios 
                    SET activo = false 
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, tenant_id))
            else:
                cursor.execute("""
                    UPDATE usuarios 
                    SET activo = false 
                    WHERE id = %s
                """, (user_id,))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al desactivar usuario: {e}")
        return False
    finally:
        conexion.close()

def activar_usuario(user_id, tenant_id=None):
    """Reactiva un usuario del sistema"""
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            if tenant_id is not None:
                cursor.execute("""
                    UPDATE usuarios 
                    SET activo = true 
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, tenant_id))
            else:
                cursor.execute("""
                    UPDATE usuarios 
                    SET activo = true 
                    WHERE id = %s
                """, (user_id,))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al activar usuario: {e}")
        return False
    finally:
        conexion.close()

def cambiar_rol_usuario(user_id, nuevo_rol, tenant_id=None):
    """Cambia el rol de un usuario"""
    conexion = obtener_conexion()
    nuevo_rol = (nuevo_rol or '').strip().lower()
    try:
        with conexion.cursor() as cursor:
            if tenant_id is not None:
                cursor.execute("""
                    UPDATE usuarios 
                    SET rol = %s 
                    WHERE id = %s AND tenant_id = %s
                """, (nuevo_rol, user_id, tenant_id))
            else:
                cursor.execute("""
                    UPDATE usuarios 
                    SET rol = %s 
                    WHERE id = %s
                """, (nuevo_rol, user_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al cambiar rol: {e}")
        return False
    finally:
        conexion.close()

def existe_usuario(username):
    """Verifica si ya existe un usuario con ese nombre (case-insensitive)"""
    username = (username or '').strip()
    conexion = obtener_conexion()
    existe = False
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM usuarios WHERE LOWER(username) = LOWER(%s)", (username,))
            existe = cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error al consultar existencia de usuario: {e}")
    finally:
        conexion.close()
    return existe

def obtener_usuario_por_id(user_id, tenant_id=None):
    """Obtiene un usuario por su ID"""
    conexion = obtener_conexion()
    usuario = None
    try:
        with conexion.cursor() as cursor:
            if tenant_id is not None:
                cursor.execute("""
                    SELECT id, username, rol, activo, created_at, tenant_id
                    FROM usuarios 
                    WHERE id = %s AND tenant_id = %s
                """, (user_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT id, username, rol, activo, created_at, tenant_id
                    FROM usuarios 
                    WHERE id = %s
                """, (user_id,))
            usuario = cursor.fetchone()
    except Exception as e:
        logger.error(f"Error al obtener usuario por ID: {e}")
    finally:
        conexion.close()
    return usuario

def cambiar_estado_usuario(user_id, estado, tenant_id=None):
    """Cambia el estado activo/inactivo de un usuario (acepta numérico o booleano)"""
    if estado in (1, True, '1', 'true', 'True'):
        return activar_usuario(user_id, tenant_id)
    else:
        return desactivar_usuario(user_id, tenant_id)

def eliminar_usuario(user_id, tenant_id=None):
    """Elimina (desactiva) un usuario del sistema"""
    return desactivar_usuario(user_id, tenant_id)
