"""
Controlador para el manejo de compras e historial de compras (PostgreSQL / Supabase)
"""

import json
from datetime import datetime, date
from bd import obtener_conexion, obtener_tenant_id

def obtener_compras_por_fecha(fecha_inicio=None, fecha_fin=None, cliente_email=None, estado=None, limit=50, offset=0):
    """
    Obtiene las compras filtradas por fecha, cliente y estado
    """
    try:
        conexion = obtener_conexion()
        tenant_id = obtener_tenant_id()
        cursor = conexion.cursor()
        
        query = """
            SELECT 
                c.id,
                c.cliente_nombre,
                c.cliente_email,
                c.cliente_telefono,
                c.total,
                c.metodo_pago,
                c.estado,
                c.fecha_compra,
                COALESCE(jsonb_array_length(c.productos::jsonb), 0) as cantidad_productos
            FROM compras c
            WHERE c.tenant_id = %s
        """
        
        params = [tenant_id]
        
        if fecha_inicio:
            query += " AND c.fecha_compra::date >= %s"
            params.append(fecha_inicio)
            
        if fecha_fin:
            query += " AND c.fecha_compra::date <= %s"
            params.append(fecha_fin)
            
        if cliente_email:
            query += " AND c.cliente_email ILIKE %s"
            params.append(f"%{cliente_email}%")
            
        if estado:
            query += " AND c.estado = %s"
            params.append(estado)
        
        query += " ORDER BY c.fecha_compra DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        cursor.execute(query, params)
        compras = cursor.fetchall()
        
        return compras
        
    except Exception as e:
        print(f"Error al obtener compras: {e}")
        return []
    finally:
        if 'conexion' in locals():
            conexion.close()

def obtener_detalle_compra(compra_id):
    """
    Obtiene los detalles completos de una compra específica
    """
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT 
                c.id,
                c.cliente_nombre,
                c.cliente_email,
                c.cliente_telefono,
                c.productos,
                c.subtotal,
                c.igv,
                c.total,
                c.metodo_pago,
                c.estado,
                c.fecha_compra,
                c.observaciones,
                u.username as vendedor_nombre
            FROM compras c
            LEFT JOIN usuarios u ON c.vendedor_id = u.id
            WHERE c.id = %s
        """, (compra_id,))
        
        compra = cursor.fetchone()
        
        if compra:
            # psycopg2 puede deserializar JSON automáticamente o entregarlo como string
            raw_productos = compra[4]
            if isinstance(raw_productos, str):
                productos_data = json.loads(raw_productos) if raw_productos else []
            elif isinstance(raw_productos, list):
                productos_data = raw_productos
            else:
                productos_data = []
            
            productos_enriquecidos = []
            for producto in productos_data:
                cursor.execute("""
                    SELECT nombre, precio, imagen 
                    FROM productos 
                    WHERE id = %s
                """, (producto.get('id'),))
                
                producto_actual = cursor.fetchone()
                
                if producto_actual:
                    productos_enriquecidos.append({
                        'id': producto.get('id'),
                        'nombre': producto_actual[0],
                        'precio_actual': float(producto_actual[1]),
                        'precio_compra': producto.get('precio', 0),
                        'cantidad': producto.get('cantidad', 1),
                        'subtotal': producto.get('precio', 0) * producto.get('cantidad', 1),
                        'imagen': producto_actual[2]
                    })
                else:
                    productos_enriquecidos.append({
                        'id': producto.get('id'),
                        'nombre': producto.get('nombre', 'Producto no disponible'),
                        'precio_actual': 0,
                        'precio_compra': producto.get('precio', 0),
                        'cantidad': producto.get('cantidad', 1),
                        'subtotal': producto.get('precio', 0) * producto.get('cantidad', 1),
                        'imagen': None
                    })
            
            compra_completa = {
                'id': compra[0],
                'cliente_nombre': compra[1],
                'cliente_email': compra[2],
                'cliente_telefono': compra[3],
                'productos': productos_enriquecidos,
                'subtotal': float(compra[5]) if compra[5] else 0,
                'igv': float(compra[6]) if compra[6] else 0,
                'total': float(compra[7]) if compra[7] else 0,
                'metodo_pago': compra[8],
                'estado': compra[9],
                'fecha_compra': compra[10],
                'observaciones': compra[11],
                'vendedor_nombre': compra[12] or 'No especificado'
            }
            
            return compra_completa
            
        return None
        
    except Exception as e:
        print(f"Error al obtener detalle de compra: {e}")
        return None
    finally:
        if 'conexion' in locals():
            conexion.close()

def registrar_compra(cliente_nombre, cliente_email, cliente_telefono, productos, metodo_pago='efectivo', observaciones=None, vendedor_id=None):
    """
    Registra una nueva compra en el historial
    """
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        subtotal = sum(float(producto['precio']) * int(producto['cantidad']) for producto in productos)
        igv = subtotal * 0.18
        total = subtotal + igv
        
        productos_json = []
        for producto in productos:
            productos_json.append({
                'id': producto['id'],
                'nombre': producto['nombre'],
                'precio': float(producto['precio']),
                'cantidad': int(producto['cantidad'])
            })
        
        cursor.execute("""
            INSERT INTO compras (
                cliente_nombre, cliente_email, cliente_telefono,
                productos, subtotal, igv, total,
                metodo_pago, estado, observaciones, vendedor_id, tenant_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            cliente_nombre,
            cliente_email,
            cliente_telefono,
            json.dumps(productos_json),
            subtotal,
            igv,
            total,
            metodo_pago,
            'pagado',
            observaciones,
            vendedor_id,
            obtener_tenant_id()
        ))
        
        compra_id = cursor.fetchone()[0]
        conexion.commit()
        
        return compra_id
        
    except Exception as e:
        print(f"Error al registrar compra: {e}")
        if 'conexion' in locals():
            conexion.rollback()
        return None
    finally:
        if 'conexion' in locals():
            conexion.close()

def actualizar_estado_compra(compra_id, nuevo_estado):
    """
    Actualiza el estado de una compra
    """
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            UPDATE compras 
            SET estado = %s 
            WHERE id = %s
        """, (nuevo_estado, compra_id))
        
        if cursor.rowcount > 0:
            conexion.commit()
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error al actualizar estado de compra: {e}")
        if 'conexion' in locals():
            conexion.rollback()
        return False
    finally:
        if 'conexion' in locals():
            conexion.close()

def obtener_estadisticas_compras(fecha_inicio=None, fecha_fin=None):
    """
    Obtiene estadísticas de compras para un período
    """
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        where_clause = ""
        params = []
        
        if fecha_inicio:
            where_clause += " AND c.fecha_compra::date >= %s"
            params.append(fecha_inicio)
            
        if fecha_fin:
            where_clause += " AND c.fecha_compra::date <= %s"
            params.append(fecha_fin)
        
        # Total de ventas
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_compras,
                SUM(total) as total_vendido,
                AVG(total) as promedio_venta,
                SUM(CASE WHEN estado = 'pagado' THEN total ELSE 0 END) as total_pagado
            FROM compras c
            WHERE 1=1 {where_clause}
        """, params)
        
        estadisticas = cursor.fetchone()
        
        # Ventas por método de pago
        cursor.execute(f"""
            SELECT 
                metodo_pago,
                COUNT(*) as cantidad,
                SUM(total) as total
            FROM compras c
            WHERE estado = 'pagado' {where_clause}
            GROUP BY metodo_pago
            ORDER BY total DESC
        """, params)
        
        ventas_por_metodo = cursor.fetchall()
        
        # Productos más vendidos desplegando el arreglo JSON
        cursor.execute(f"""
            SELECT 
                elem->>'nombre' as producto_nombre,
                SUM((elem->>'cantidad')::numeric) as total_vendido
            FROM compras c,
            LATERAL jsonb_array_elements(c.productos::jsonb) as elem
            WHERE c.estado = 'pagado' {where_clause}
            GROUP BY elem->>'nombre'
            ORDER BY total_vendido DESC
            LIMIT 10
        """, params)
        
        productos_populares = cursor.fetchall()
        
        return {
            'total_compras': estadisticas[0] or 0,
            'total_vendido': float(estadisticas[1]) if estadisticas[1] else 0.0,
            'promedio_venta': float(estadisticas[2]) if estadisticas[2] else 0.0,
            'total_pagado': float(estadisticas[3]) if estadisticas[3] else 0.0,
            'ventas_por_metodo': ventas_por_metodo,
            'productos_populares': productos_populares
        }
        
    except Exception as e:
        print(f"Error al obtener estadísticas: {e}")
        return {
            'total_compras': 0,
            'total_vendido': 0.0,
            'promedio_venta': 0.0,
            'total_pagado': 0.0,
            'ventas_por_metodo': [],
            'productos_populares': []
        }
    finally:
        if 'conexion' in locals():
            conexion.close()

def buscar_compras_por_cliente(termino_busqueda, limit=20):
    """
    Busca compras por nombre o email del cliente
    """
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            SELECT 
                c.id,
                c.cliente_nombre,
                c.cliente_email,
                c.total,
                c.fecha_compra,
                c.estado
            FROM compras c
            WHERE c.cliente_nombre ILIKE %s 
               OR c.cliente_email ILIKE %s
            ORDER BY c.fecha_compra DESC
            LIMIT %s
        """, (f"%{termino_busqueda}%", f"%{termino_busqueda}%", limit))
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Error al buscar compras: {e}")
        return []
    finally:
        if 'conexion' in locals():
            conexion.close()