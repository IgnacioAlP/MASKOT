from bd import obtener_conexion, obtener_tenant_id

def _asegurar_columnas(cursor):
    """Garantiza la presencia de columnas precio y duracion en PostgreSQL sin usar DESCRIBE o AFTER."""
    cursor.execute("ALTER TABLE servicios ADD COLUMN IF NOT EXISTS precio DECIMAL(10,2) DEFAULT 0.00")
    cursor.execute("ALTER TABLE servicios ADD COLUMN IF NOT EXISTS duracion INT DEFAULT 30")

def obtener_servicios():
    """Obtiene todos los servicios disponibles con datos completos para la gestión"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    servicios = []
    try:
        with conexion.cursor() as cursor:
            _asegurar_columnas(cursor)
            conexion.commit()
            
            cursor.execute("""
                SELECT s.id, s.nombre, 
                       COALESCE(s.precio, 0.00) as precio,
                       COALESCE(s.duracion, 30) as duracion,
                       s.descripcion,
                       s.activo,
                       CURRENT_TIMESTAMP as fecha_creacion,
                       s.max_citas_dia,
                       COUNT(c.id) as total_citas
                FROM servicios s
                LEFT JOIN citas c ON s.id = c.servicio_id AND c.tenant_id = %s
                WHERE s.activo = true AND s.tenant_id = %s
                GROUP BY s.id, s.nombre, s.precio, s.duracion, s.descripcion, s.activo, s.max_citas_dia
                ORDER BY s.nombre ASC
            """, (tenant_id, tenant_id))
            servicios = cursor.fetchall()
    except Exception as e:
        print(f"Error en obtener_servicios: {e}")
    finally:
        conexion.close()
    return servicios

def obtener_servicios_activos():
    """Alias para obtener_servicios() - obtiene todos los servicios activos"""
    return obtener_servicios()

def obtener_servicios_destacados(limit=3):
    """Obtiene los servicios más destacados (máximo especificado para mostrar en inicio)"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    servicios = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.nombre, s.descripcion, s.max_citas_dia, COUNT(c.id) as total_citas
                FROM servicios s
                LEFT JOIN citas c ON s.id = c.servicio_id AND c.tenant_id = %s
                WHERE s.activo = true AND s.tenant_id = %s
                GROUP BY s.id, s.nombre, s.descripcion, s.max_citas_dia
                ORDER BY total_citas DESC, s.id ASC
                LIMIT %s
            """, (tenant_id, tenant_id, limit))
            servicios = cursor.fetchall()
    finally:
        conexion.close()
    return servicios

def obtener_servicio_por_id(servicio_id):
    """Obtiene un servicio específico por su ID"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    servicio = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, descripcion, precio, duracion, max_citas_dia 
                FROM servicios 
                WHERE id = %s AND activo = true AND tenant_id = %s
            """, (servicio_id, tenant_id))
            servicio = cursor.fetchone()
    finally:
        conexion.close()
    return servicio

def obtener_max_citas_dia(servicio_id):
    """Obtiene el máximo de citas por día para un servicio específico"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    max_citas = 0
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT max_citas_dia 
                FROM servicios 
                WHERE id = %s AND activo = true AND tenant_id = %s
            """, (servicio_id, tenant_id))
            resultado = cursor.fetchone()
            if resultado:
                max_citas = resultado[0]
    finally:
        conexion.close()
    return max_citas

def insertar_servicio(nombre, descripcion, max_citas_dia, precio=0.00, duracion=30):
    """Inserta un nuevo servicio"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            _asegurar_columnas(cursor)
            
            cursor.execute("""
                INSERT INTO servicios (nombre, descripcion, precio, duracion, max_citas_dia, activo, tenant_id) 
                VALUES (%s, %s, %s, %s, %s, true, %s)
                RETURNING id
            """, (nombre, descripcion, precio, duracion, max_citas_dia, tenant_id))
            servicio_id = cursor.fetchone()[0]
            conexion.commit()
            return servicio_id
    except Exception as e:
        conexion.rollback()
        print(f"Error al insertar servicio: {e}")
        return False
    finally:
        conexion.close()

def actualizar_servicio(servicio_id, nombre, descripcion, max_citas_dia, precio=0.00, duracion=30):
    """Actualiza un servicio existente"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            _asegurar_columnas(cursor)
            
            cursor.execute("""
                UPDATE servicios 
                SET nombre = %s, descripcion = %s, precio = %s, duracion = %s, max_citas_dia = %s 
                WHERE id = %s AND tenant_id = %s
            """, (nombre, descripcion, precio, duracion, max_citas_dia, servicio_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar servicio: {e}")
        return False
    finally:
        conexion.close()

def desactivar_servicio(servicio_id):
    """Desactiva un servicio (no lo elimina completamente)"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE servicios SET activo = false WHERE id = %s AND tenant_id = %s", (servicio_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al desactivar servicio: {e}")
        return False
    finally:
        conexion.close()

def activar_servicio(servicio_id):
    """Reactiva un servicio desactivado"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE servicios SET activo = true WHERE id = %s AND tenant_id = %s", (servicio_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al activar servicio: {e}")
        return False
    finally:
        conexion.close()

def obtener_servicios_completos():
    """Obtiene todos los servicios (activos e inactivos) para administración"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    servicios = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.nombre, s.descripcion, s.max_citas_dia, s.activo,
                       COUNT(c.id) as total_citas,
                       COALESCE(MAX(c.fecha)::date::text, 'Nunca') as ultima_cita
                FROM servicios s
                LEFT JOIN citas c ON s.id = c.servicio_id AND c.tenant_id = %s
                WHERE s.tenant_id = %s
                GROUP BY s.id, s.nombre, s.descripcion, s.max_citas_dia, s.activo
                ORDER BY s.activo DESC, total_citas DESC, s.nombre ASC
            """, (tenant_id, tenant_id))
            servicios = cursor.fetchall()
    finally:
        conexion.close()
    return servicios