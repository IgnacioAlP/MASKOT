from bd import obtener_conexion, obtener_tenant_id

def obtener_citas():
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    citas = []
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.cliente_nombre, c.cliente_email, 
                   GROUP_CONCAT(DISTINCT s.nombre SEPARATOR ', ') as servicios, 
                   c.fecha, c.hora, c.estado,
                   GROUP_CONCAT(DISTINCT m.nombre SEPARATOR ', ') as mascotas,
                   c.precio_total, c.observaciones
            FROM citas c
            LEFT JOIN citas_servicios cs ON c.id = cs.cita_id
            LEFT JOIN servicios s ON cs.servicio_id = s.id
            LEFT JOIN citas_mascotas cm ON c.id = cm.cita_id
            LEFT JOIN mascotas m ON cm.mascota_id = m.id
            WHERE c.tenant_id = %s
            GROUP BY c.id, c.cliente_nombre, c.cliente_email, c.fecha, c.hora, c.estado
            ORDER BY c.fecha, c.hora
        """, (tenant_id,))
        citas = cursor.fetchall()
    conexion.close()
    return citas

def insertar_cita_completa(cliente_nombre, cliente_email, mascotas_data, servicios_ids, fecha, hora, observaciones=''):
    """Inserta una cita con múltiples mascotas y servicios"""
    conexion = obtener_conexion()
    cita_id = None
    try:
        with conexion.cursor() as cursor:
            # Verificar/insertar cliente
            cliente_id = verificar_o_insertar_cliente(cursor, cliente_nombre, cliente_email)
            
            # Insertar cita principal
            tenant_id = obtener_tenant_id()
            cursor.execute("""
                INSERT INTO citas (cliente_id, cliente_nombre, cliente_email, fecha, hora, estado, observaciones, tenant_id) 
                VALUES (%s, %s, %s, %s, %s, 'pendiente', %s, %s)
            """, (cliente_id, cliente_nombre, cliente_email, fecha, hora, observaciones, tenant_id))
            cita_id = cursor.lastrowid
            
            # Insertar mascotas y vincular con la cita
            for mascota_data in mascotas_data:
                mascota_id = insertar_o_obtener_mascota(cursor, cliente_id, mascota_data)
                cursor.execute("INSERT INTO citas_mascotas (cita_id, mascota_id) VALUES (%s, %s)", 
                             (cita_id, mascota_id))
            
            # Vincular servicios con la cita
            precio_total = 0
            for servicio_id in servicios_ids:
                cursor.execute("INSERT INTO citas_servicios (cita_id, servicio_id) VALUES (%s, %s)", 
                             (cita_id, servicio_id))
                # Aquí podrías agregar lógica para calcular precios por servicio
            
            # Actualizar precio total si es necesario
            if precio_total > 0:
                cursor.execute("UPDATE citas SET precio_total = %s WHERE id = %s", (precio_total, cita_id))
        
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()
    return cita_id

def verificar_o_insertar_cliente(cursor, nombre, email, tenant_id=None):
    """Verifica si existe un cliente o lo crea"""
    if tenant_id is None:
        tenant_id = obtener_tenant_id()
    cursor.execute("SELECT id FROM clientes WHERE email = %s AND tenant_id = %s", (email, tenant_id))
    cliente = cursor.fetchone()
    
    if cliente:
        return cliente[0]
    else:
        cursor.execute("INSERT INTO clientes (nombre, email, fecha_registro, tenant_id) VALUES (%s, %s, NOW(), %s)", 
                      (nombre, email, tenant_id))
        return cursor.lastrowid

def insertar_o_obtener_mascota(cursor, cliente_id, mascota_data, tenant_id=None):
    """Inserta o obtiene una mascota existente"""
    if tenant_id is None:
        tenant_id = obtener_tenant_id()
    nombre = mascota_data.get('nombre', '')
    especie = mascota_data.get('especie', '')
    raza = mascota_data.get('raza', '')
    edad = mascota_data.get('edad')
    peso = mascota_data.get('peso')
    
    # Buscar mascota existente
    cursor.execute("""
        SELECT id FROM mascotas 
        WHERE cliente_id = %s AND nombre = %s AND especie = %s AND activo = 1 AND tenant_id = %s
    """, (cliente_id, nombre, especie, tenant_id))
    mascota = cursor.fetchone()
    
    if mascota:
        # Actualizar datos si es necesario
        cursor.execute("""
            UPDATE mascotas 
            SET raza = %s, edad = %s, peso = %s 
            WHERE id = %s
        """, (raza, edad, peso, mascota[0]))
        return mascota[0]
    else:
        # Insertar nueva mascota
        cursor.execute("""
            INSERT INTO mascotas (cliente_id, nombre, especie, raza, edad, peso, fecha_registro, tenant_id) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (cliente_id, nombre, especie, raza, edad, peso, tenant_id))
        return cursor.lastrowid

# Mantener funciones de compatibilidad hacia atrás
def insertar_cita(cliente_nombre, cliente_email, servicio_id, fecha, hora, 
                  mascota_nombre, mascota_especie, mascota_raza=None, mascota_edad=None, mascota_peso=None):
    """Función de compatibilidad para una sola mascota y servicio"""
    mascotas_data = [{
        'nombre': mascota_nombre,
        'especie': mascota_especie,
        'raza': mascota_raza,
        'edad': mascota_edad,
        'peso': mascota_peso
    }]
    return insertar_cita_completa(cliente_nombre, cliente_email, mascotas_data, [servicio_id], fecha, hora)

def eliminar_cita(id):
    conexion = obtener_conexion()
    with conexion.cursor() as cursor:
        # Las tablas relacionadas se eliminan automáticamente por CASCADE
        cursor.execute("DELETE FROM citas WHERE id = %s", (id,))
    conexion.commit()
    conexion.close()

def cambiar_estado_cita(id, estado):
    """Cambia el estado de una cita ('pendiente', 'completada', 'cancelada')."""
    conexion = obtener_conexion()
    with conexion.cursor() as cursor:
        cursor.execute("UPDATE citas SET estado = %s WHERE id = %s", (estado, id))
    conexion.commit()
    conexion.close()

def obtener_cita_por_id(id):
    conexion = obtener_conexion()
    cita = None
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.cliente_nombre, c.cliente_email, c.fecha, c.hora, c.estado,
                   c.observaciones, c.precio_total,
                   GROUP_CONCAT(DISTINCT CONCAT(m.nombre, '|', m.especie, '|', COALESCE(m.raza, ''), '|', 
                                              COALESCE(m.edad, ''), '|', COALESCE(m.peso, '')) SEPARATOR ';') as mascotas,
                   GROUP_CONCAT(DISTINCT CONCAT(s.id, '|', s.nombre) SEPARATOR ';') as servicios
            FROM citas c
            LEFT JOIN citas_mascotas cm ON c.id = cm.cita_id
            LEFT JOIN mascotas m ON cm.mascota_id = m.id
            LEFT JOIN citas_servicios cs ON c.id = cs.cita_id
            LEFT JOIN servicios s ON cs.servicio_id = s.id
            WHERE c.id = %s
            GROUP BY c.id
        """, (id,))
        cita = cursor.fetchone()
    conexion.close()
    return cita

def contar_citas_por_servicio_y_fecha(servicio_id, fecha):
    """Cuenta el número de citas para un servicio en una fecha específica."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(DISTINCT c.id) FROM citas c
            JOIN citas_servicios cs ON c.id = cs.cita_id
            WHERE cs.servicio_id = %s AND c.fecha = %s AND c.estado = 'pendiente' AND c.tenant_id = %s
        """, (servicio_id, fecha, tenant_id))
        count = cursor.fetchone()[0]
    conexion.close()
    return count

def contar_citas_pendientes(servicio_id, fecha):
    """Cuenta el número de citas para un servicio en una fecha específica."""
    return contar_citas_por_servicio_y_fecha(servicio_id, fecha)

def obtener_citas_por_fecha(fecha):
    """Obtiene todas las citas para una fecha específica."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT c.id, c.cliente_nombre, c.cliente_email, c.fecha, c.hora, c.estado,
                   GROUP_CONCAT(DISTINCT s.nombre SEPARATOR ', ') as servicios,
                   GROUP_CONCAT(DISTINCT m.nombre SEPARATOR ', ') as mascotas,
                   c.observaciones, c.precio_total
            FROM citas c 
            LEFT JOIN citas_servicios cs ON c.id = cs.cita_id
            LEFT JOIN servicios s ON cs.servicio_id = s.id
            LEFT JOIN citas_mascotas cm ON c.id = cm.cita_id
            LEFT JOIN mascotas m ON cm.mascota_id = m.id
            WHERE c.fecha=%s AND c.tenant_id = %s
            GROUP BY c.id, c.cliente_nombre, c.cliente_email, c.fecha, c.hora, c.estado
            ORDER BY c.hora
        """, (fecha, tenant_id))
        citas = cursor.fetchall()
    conexion.close()
    return citas

def actualizar_cita(id, cliente_nombre, cliente_email, servicio_id, fecha, hora, estado):
    conexion = obtener_conexion()
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE citas SET cliente_nombre = %s, cliente_email = %s, fecha = %s, hora = %s, estado = %s WHERE id = %s",
            (cliente_nombre, cliente_email, fecha, hora, estado, id)
        )
        # Actualizar servicio (simplificado para compatibilidad)
        cursor.execute("DELETE FROM citas_servicios WHERE cita_id = %s", (id,))
        cursor.execute("INSERT INTO citas_servicios (cita_id, servicio_id) VALUES (%s, %s)", (id, servicio_id))
    conexion.commit()
    conexion.close()
