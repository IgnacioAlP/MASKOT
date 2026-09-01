from bd import obtener_conexion, obtener_tenant_id
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def hash_password(password):
    """Genera un hash SHA-256 de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def obtener_usuario_por_nombre(username):
    """Obtiene un usuario por su nombre de usuario"""
    conexion = obtener_conexion()
    usuario = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password, rol, activo, tenant_id 
                FROM usuarios 
                WHERE username = %s
            """, (username,))
            usuario = cursor.fetchone()
    finally:
        conexion.close()
    return usuario

def obtener_todos_usuarios():
    """Obtiene todos los usuarios del tenant actual"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    usuarios = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, rol, activo, created_at
                FROM usuarios 
                WHERE tenant_id = %s
                ORDER BY created_at DESC
            """, (tenant_id,))
            usuarios = cursor.fetchall()
    finally:
        conexion.close()
    return usuarios

def verificar_credenciales(username, password):
    """Verifica las credenciales de un usuario"""
    usuario = obtener_usuario_por_nombre(username)
    if usuario and usuario[4]:  # usuario activo
        password_hash = hash_password(password)
        if password_hash == usuario[2]:  # comparar hash
            return {
                'success': True,
                'user': usuario,  # tupla: (id, username, password, rol, activo, tenant_id)
                'message': 'Autenticación exitosa'
            }
    
    return {
        'success': False,
        'user': None,
        'message': 'Credenciales inválidas'
    }

def insertar_usuario(username, password, rol='empleado'):
    """Inserta un nuevo usuario en el tenant actual"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
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

def actualizar_password(user_id, nueva_password):
    """Actualiza la contraseña de un usuario"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            password_hash = hash_password(nueva_password)
            cursor.execute("""
                UPDATE usuarios 
                SET password = %s 
                WHERE id = %s AND tenant_id = %s
            """, (password_hash, user_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al actualizar contraseña: {e}")
        return False
    finally:
        conexion.close()

def desactivar_usuario(user_id):
    """Desactiva un usuario del sistema"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE usuarios 
                SET activo = false 
                WHERE id = %s AND tenant_id = %s
            """, (user_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al desactivar usuario: {e}")
        return False
    finally:
        conexion.close()

def activar_usuario(user_id):
    """Reactiva un usuario del sistema"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE usuarios 
                SET activo = true 
                WHERE id = %s AND tenant_id = %s
            """, (user_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al activar usuario: {e}")
        return False
    finally:
        conexion.close()

def cambiar_rol_usuario(user_id, nuevo_rol):
    """Cambia el rol de un usuario"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE usuarios 
                SET rol = %s 
                WHERE id = %s AND tenant_id = %s
            """, (nuevo_rol, user_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error al cambiar rol: {e}")
        return False
    finally:
        conexion.close()

def existe_usuario(username):
    """Verifica si ya existe un usuario con ese nombre"""
    conexion = obtener_conexion()
    existe = False
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            existe = cursor.fetchone() is not None
    finally:
        conexion.close()
    return existe

def obtener_usuario_por_id(user_id):
    """Obtiene un usuario por su ID"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    usuario = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, rol, activo, created_at
                FROM usuarios 
                WHERE id = %s AND tenant_id = %s
            """, (user_id, tenant_id))
            usuario = cursor.fetchone()
    finally:
        conexion.close()
    return usuario

def cambiar_estado_usuario(user_id, estado):
    """Cambia el estado activo/inactivo de un usuario (acepta numérico o booleano)"""
    if estado in (1, True, '1', 'true'):
        return activar_usuario(user_id)
    else:
        return desactivar_usuario(user_id)

def eliminar_usuario(user_id):
    """Elimina (desactiva) un usuario del sistema"""
    return desactivar_usuario(user_id)