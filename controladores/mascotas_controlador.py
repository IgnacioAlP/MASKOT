"""
Controlador para la gestión de mascotas (PostgreSQL / Supabase)
"""

from bd import obtener_conexion, obtener_tenant_id

def obtener_mascotas():
    """Obtiene todas las mascotas activas registradas en el tenant actual"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    mascotas = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.nombre, 
                    m.especie, 
                    m.raza, 
                    m.edad, 
                    m.peso, 
                    m.cliente_id, 
                    c.nombre as cliente_nombre,
                    c.email as cliente_email,
                    m.fecha_registro
                FROM mascotas m
                LEFT JOIN clientes c ON m.cliente_id = c.id
                WHERE m.activo = true AND m.tenant_id = %s
                ORDER BY m.nombre ASC
            """, (tenant_id,))
            mascotas = cursor.fetchall()
    finally:
        conexion.close()
    return mascotas

def obtener_mascotas_por_cliente(cliente_id):
    """Obtiene todas las mascotas activas pertenecientes a un cliente específico"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    mascotas = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, especie, raza, edad, peso, fecha_registro
                FROM mascotas
                WHERE cliente_id = %s AND activo = true AND tenant_id = %s
                ORDER BY nombre ASC
            """, (cliente_id, tenant_id))
            mascotas = cursor.fetchall()
    finally:
        conexion.close()
    return mascotas

def obtener_mascota_por_id(mascota_id):
    """Obtiene el detalle de una mascota específica por su ID"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    mascota = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.nombre, 
                    m.especie, 
                    m.raza, 
                    m.edad, 
                    m.peso, 
                    m.cliente_id, 
                    c.nombre as cliente_nombre,
                    c.email as cliente_email,
                    m.fecha_registro,
                    m.activo
                FROM mascotas m
                LEFT JOIN clientes c ON m.cliente_id = c.id
                WHERE m.id = %s AND m.tenant_id = %s
            """, (mascota_id, tenant_id))
            mascota = cursor.fetchone()
    finally:
        conexion.close()
    return mascota

def insertar_mascota(cliente_id, nombre, especie, raza=None, edad=None, peso=None):
    """Inserta una nueva mascota en la base de datos"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    mascota_id = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO mascotas (cliente_id, nombre, especie, raza, edad, peso, activo, fecha_registro, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, true, CURRENT_TIMESTAMP, %s)
                RETURNING id
            """, (cliente_id, nombre, especie, raza, edad, peso, tenant_id))
            mascota_id = cursor.fetchone()[0]
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()
    return mascota_id

def actualizar_mascota(mascota_id, nombre, especie, raza=None, edad=None, peso=None):
    """Actualiza la información de una mascota"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE mascotas
                SET nombre = %s, especie = %s, raza = %s, edad = %s, peso = %s
                WHERE id = %s AND tenant_id = %s
            """, (nombre, especie, raza, edad, peso, mascota_id, tenant_id))
        conexion.commit()
        return True
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()

def eliminar_mascota(mascota_id, deshabilitacion_logica=True):
    """Deshabilita lógicamente o elimina permanentemente una mascota"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            if deshabilitacion_logica:
                cursor.execute("""
                    UPDATE mascotas 
                    SET activo = false 
                    WHERE id = %s AND tenant_id = %s
                """, (mascota_id, tenant_id))
            else:
                cursor.execute("""
                    DELETE FROM mascotas 
                    WHERE id = %s AND tenant_id = %s
                """, (mascota_id, tenant_id))
        conexion.commit()
        return True
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()

def buscar_mascotas(termino, limit=20):
    """Busca mascotas por nombre, especie, raza o nombre del dueño"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    mascotas = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    m.id, 
                    m.nombre, 
                    m.especie, 
                    m.raza, 
                    m.edad, 
                    m.peso, 
                    m.cliente_id, 
                    c.nombre as cliente_nombre
                FROM mascotas m
                LEFT JOIN clientes c ON m.cliente_id = c.id
                WHERE m.activo = true 
                  AND m.tenant_id = %s
                  AND (m.nombre ILIKE %s OR m.especie ILIKE %s OR m.raza ILIKE %s OR c.nombre ILIKE %s)
                ORDER BY m.nombre ASC
                LIMIT %s
            """, (tenant_id, f"%{termino}%", f"%{termino}%", f"%{termino}%", f"%{termino}%", limit))
            mascotas = cursor.fetchall()
    finally:
        conexion.close()
    return mascotas