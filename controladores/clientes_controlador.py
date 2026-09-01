from bd import obtener_conexion, obtener_tenant_id
import hashlib

def insertar_cliente(nombre, email, telefono, direccion, documento=None):
    """Inserta un nuevo cliente en la base de datos."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    cliente_id = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                """INSERT INTO clientes (nombre, email, telefono, direccion, documento, fecha_registro, tenant_id) 
                   VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                   RETURNING id""",
                (nombre, email, telefono, direccion, documento, tenant_id)
            )
            cliente_id = cursor.fetchone()[0]
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()
    return cliente_id

def obtener_cliente_por_email(email):
    """Obtiene un cliente por su email."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    cliente = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, nombre, email, telefono, direccion, documento FROM clientes WHERE email = %s AND tenant_id = %s", (email, tenant_id))
            cliente = cursor.fetchone()
    finally:
        conexion.close()
    return cliente

def guardar_tarjeta_cliente(cliente_id, numero_tarjeta, nombre_titular, expiracion, tipo_tarjeta):
    """Guarda una tarjeta para un cliente (con número enmascarado por seguridad)."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        numero_limpio = numero_tarjeta.replace(' ', '').replace('-', '')
        numero_enmascarado = '**** **** **** ' + numero_limpio[-4:]
        numero_hash = hashlib.sha256(numero_limpio.encode()).hexdigest()
        
        with conexion.cursor() as cursor:
            cursor.execute(
                """INSERT INTO tarjetas_cliente (cliente_id, numero_enmascarado, numero_hash, nombre_titular, expiracion, tipo_tarjeta, fecha_registro, tenant_id) 
                   VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)""",
                (cliente_id, numero_enmascarado, numero_hash, nombre_titular, expiracion, tipo_tarjeta, tenant_id)
            )
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()

def obtener_tarjetas_cliente(cliente_id):
    """Obtiene las tarjetas guardadas de un cliente."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    tarjetas = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, numero_enmascarado, nombre_titular, expiracion, tipo_tarjeta FROM tarjetas_cliente WHERE cliente_id = %s AND tenant_id = %s ORDER BY fecha_registro DESC",
                (cliente_id, tenant_id)
            )
            tarjetas = cursor.fetchall()
    finally:
        conexion.close()
    return tarjetas

def obtener_historial_completo():
    """Obtiene el historial completo de clientes con sus citas y pedidos"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    historial = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT 
                    COALESCE(cl.id, 0) as cliente_id,
                    COALESCE(cl.nombre, COALESCE(c.cliente_nombre, 'Cliente sin nombre')) as nombre,
                    COALESCE(cl.email, c.cliente_email) as email,
                    cl.telefono,
                    cl.direccion,
                    cl.fecha_registro,
                    COUNT(DISTINCT c.id) as total_citas,
                    COUNT(DISTINCT p.id) as total_pedidos,
                    COALESCE(SUM(p.total), 0) as total_gastado,
                    MAX(c.fecha::date) as ultima_cita,
                    MAX(p.fecha_pedido::date) as ultimo_pedido
                FROM clientes cl
                LEFT JOIN citas c ON cl.email = c.cliente_email AND c.tenant_id = %s
                LEFT JOIN pedidos p ON cl.id = p.cliente_id
                WHERE cl.tenant_id = %s
                GROUP BY cl.id, cl.nombre, cl.email, cl.telefono, cl.direccion, cl.fecha_registro, c.cliente_nombre
                
                UNION ALL
                
                SELECT DISTINCT 
                    0 as cliente_id,
                    c.cliente_nombre as nombre,
                    c.cliente_email as email,
                    NULL as telefono,
                    NULL as direccion,
                    NULL::timestamp as fecha_registro,
                    COUNT(DISTINCT c.id) as total_citas,
                    0 as total_pedidos,
                    0.0 as total_gastado,
                    MAX(c.fecha::date) as ultima_cita,
                    NULL::date as ultimo_pedido
                FROM citas c
                LEFT JOIN clientes cl ON c.cliente_email = cl.email AND cl.tenant_id = %s
                WHERE cl.id IS NULL AND c.cliente_email IS NOT NULL AND c.tenant_id = %s
                GROUP BY c.cliente_nombre, c.cliente_email
                
                ORDER BY ultima_cita DESC, ultimo_pedido DESC
            """, (tenant_id, tenant_id, tenant_id, tenant_id))
            historial = cursor.fetchall()
    finally:
        conexion.close()
    return historial

def obtener_detalles_cliente(cliente_id=None, email=None):
    """Obtiene los detalles completos de un cliente específico con sus citas y pedidos"""
    conexion = obtener_conexion()
    detalles = {}
    try:
        with conexion.cursor() as cursor:
            if cliente_id:
                cursor.execute(
                    "SELECT id, nombre, email, telefono, direccion, fecha_registro FROM clientes WHERE id = %s",
                    (cliente_id,)
                )
            elif email:
                cursor.execute(
                    "SELECT id, nombre, email, telefono, direccion, fecha_registro FROM clientes WHERE email = %s",
                    (email,)
                )
            else:
                return detalles
            
            cliente_info = cursor.fetchone()
            if cliente_info:
                detalles['cliente'] = cliente_info
                cliente_email = cliente_info[2]
            else:
                cliente_email = email
                detalles['cliente'] = None
            
            # Citas del cliente
            if cliente_email:
                cursor.execute("""
                    SELECT c.id, c.cliente_nombre, c.cliente_email, s.nombre as servicio, 
                           c.fecha::date as fecha, 
                           TO_CHAR(c.hora::time, 'HH24:MI') as hora,
                           c.estado, c.created_at,
                           c.mascota_nombre, c.mascota_especie, c.mascota_raza, c.mascota_edad, c.mascota_peso
                    FROM citas c
                    LEFT JOIN servicios s ON c.servicio_id = s.id
                    WHERE c.cliente_email = %s
                    ORDER BY c.fecha DESC, c.hora DESC
                """, (cliente_email,))
                detalles['citas'] = cursor.fetchall()
            
            # Pedidos del cliente
            if cliente_id:
                cursor.execute("""
                    SELECT p.id, p.subtotal, p.igv, p.total, p.metodo_pago, p.estado,
                           p.fecha_pedido, p.fecha_pago, p.fecha_entrega,
                           COUNT(dp.id) as total_productos
                    FROM pedidos p
                    LEFT JOIN detalle_pedidos dp ON p.id = dp.pedido_id
                    WHERE p.cliente_id = %s
                    GROUP BY p.id, p.subtotal, p.igv, p.total, p.metodo_pago, p.estado, p.fecha_pedido, p.fecha_pago, p.fecha_entrega
                    ORDER BY p.fecha_pedido DESC
                """, (cliente_id,))
                detalles['pedidos'] = cursor.fetchall()
            
            # Detalles de productos de los pedidos más recientes
            if cliente_id:
                cursor.execute("""
                    SELECT dp.pedido_id, pr.nombre, dp.cantidad, dp.precio_unitario, dp.subtotal
                    FROM detalle_pedidos dp
                    JOIN productos pr ON dp.producto_id = pr.id
                    JOIN pedidos p ON dp.pedido_id = p.id
                    WHERE p.cliente_id = %s
                    ORDER BY p.fecha_pedido DESC
                    LIMIT 20
                """, (cliente_id,))
                detalles['productos_recientes'] = cursor.fetchall()
            
    finally:
        conexion.close()
    return detalles

def insertar_pedido(cliente_id, items, total_final, metodo_pago, subtotal=None, igv=None, estado='pendiente'):
    """Inserta un nuevo pedido en la base de datos con cálculo de IGV."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    pedido_id = None
    try:
        if subtotal is None or igv is None:
            subtotal = round(total_final / 1.18, 2)
            igv = round(total_final - subtotal, 2)
        
        with conexion.cursor() as cursor:
            cursor.execute(
                """INSERT INTO pedidos (cliente_id, subtotal, igv, total, metodo_pago, estado, fecha_pedido, tenant_id) 
                   VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                   RETURNING id""",
                (cliente_id, subtotal, igv, total_final, metodo_pago, estado, tenant_id)
            )
            pedido_id = cursor.fetchone()[0]
            
            for item in items:
                cursor.execute(
                    """INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario, subtotal, tenant_id) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (pedido_id, item['id'], item['qty'], item['precio_unitario'], item['subtotal'], tenant_id)
                )
        
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()
    return pedido_id

def obtener_todos_clientes():
    """Obtiene todos los clientes únicos tanto de la tabla clientes como de citas"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    clientes = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    nombre,
                    email,
                    telefono,
                    direccion,
                    fecha_registro,
                    total_citas
                FROM (
                    SELECT DISTINCT 
                        cl.nombre as nombre,
                        cl.email as email,
                        cl.telefono,
                        cl.direccion,
                        cl.fecha_registro,
                        COUNT(DISTINCT c.id) as total_citas
                    FROM clientes cl
                    LEFT JOIN citas c ON cl.email = c.cliente_email AND c.tenant_id = %s
                    WHERE cl.tenant_id = %s
                    GROUP BY cl.id, cl.nombre, cl.email, cl.telefono, cl.direccion, cl.fecha_registro
                    
                    UNION
                    
                    SELECT DISTINCT 
                        c.cliente_nombre as nombre,
                        c.cliente_email as email,
                        NULL as telefono,
                        NULL as direccion,
                        NULL::timestamp as fecha_registro,
                        COUNT(DISTINCT c.id) as total_citas
                    FROM citas c
                    LEFT JOIN clientes cl ON c.cliente_email = cl.email AND cl.tenant_id = %s
                    WHERE cl.id IS NULL AND c.cliente_email IS NOT NULL AND c.tenant_id = %s
                    GROUP BY c.cliente_nombre, c.cliente_email
                ) AS todos_clientes
                ORDER BY nombre ASC
            """, (tenant_id, tenant_id, tenant_id, tenant_id))
            clientes = cursor.fetchall()
    finally:
        conexion.close()
    return clientes

def actualizar_cliente(email_anterior, nuevo_email, telefono='', direccion=''):
    """Actualiza la información de un cliente (excepto el nombre)"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM clientes WHERE email = %s AND tenant_id = %s", (email_anterior, tenant_id))
            cliente = cursor.fetchone()
            
            if cliente:
                cursor.execute("""
                    UPDATE clientes 
                    SET email = %s, telefono = %s, direccion = %s 
                    WHERE email = %s AND tenant_id = %s
                """, (nuevo_email, telefono, direccion, email_anterior, tenant_id))
            else:
                cursor.execute("SELECT DISTINCT cliente_nombre FROM citas WHERE cliente_email = %s AND tenant_id = %s LIMIT 1", (email_anterior, tenant_id))
                cita_info = cursor.fetchone()
                if cita_info:
                    cursor.execute("""
                        INSERT INTO clientes (nombre, email, telefono, direccion, fecha_registro, tenant_id) 
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                    """, (cita_info[0], nuevo_email, telefono, direccion, tenant_id))
            
            if email_anterior != nuevo_email:
                cursor.execute("""
                    UPDATE citas 
                    SET cliente_email = %s 
                    WHERE cliente_email = %s AND tenant_id = %s
                """, (nuevo_email, email_anterior, tenant_id))
        
        conexion.commit()
    except Exception as e:
        conexion.rollback()
        raise e
    finally:
        conexion.close()