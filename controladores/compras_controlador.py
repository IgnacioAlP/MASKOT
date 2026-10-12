"""
Controlador para el manejo de compras e historial de compras (PostgreSQL / Supabase)
"""

import json
from datetime import datetime, date
from bd import obtener_conexion, obtener_tenant_id


def asegurar_tablas_compras_inventario(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compras_inventario (
            id SERIAL PRIMARY KEY,
            proveedor VARCHAR(255) NOT NULL,
            tipo_comprobante VARCHAR(20) NOT NULL DEFAULT 'FC',
            serie VARCHAR(30),
            numero_comprobante VARCHAR(50),
            fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
            fecha_entrega DATE,
            dias_plazo INTEGER NOT NULL DEFAULT 0,
            moneda VARCHAR(5) NOT NULL DEFAULT 'PEN',
            tipo_cambio NUMERIC(12,4) NOT NULL DEFAULT 1,
            local_actual VARCHAR(50),
            almacen_actual VARCHAR(50),
            subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
            descuento NUMERIC(12,2) NOT NULL DEFAULT 0,
            flete NUMERIC(12,2) NOT NULL DEFAULT 0,
            igv NUMERIC(12,2) NOT NULL DEFAULT 0,
            percepcion NUMERIC(12,2) NOT NULL DEFAULT 0,
            total NUMERIC(12,2) NOT NULL DEFAULT 0,
            observaciones TEXT,
            tenant_id INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compras_inventario_detalle (
            id SERIAL PRIMARY KEY,
            compra_id INTEGER NOT NULL REFERENCES compras_inventario(id) ON DELETE CASCADE,
            producto_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
            producto_nombre VARCHAR(255) NOT NULL,
            unidad VARCHAR(30) NOT NULL DEFAULT 'UND',
            factor NUMERIC(12,3) NOT NULL DEFAULT 1,
            cantidad INTEGER NOT NULL,
            precio_unitario NUMERIC(12,2) NOT NULL,
            descuento_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
            igv_pct NUMERIC(6,2) NOT NULL DEFAULT 18,
            total NUMERIC(12,2) NOT NULL DEFAULT 0
        )
    """)


def registrar_compra_inventario(documento, items, tenant_id=None):
    """Guarda un documento de proveedor y actualiza existencias en una transacción."""
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    tenant_id = tenant_id if tenant_id is not None else obtener_tenant_id()
    if not documento.get('proveedor') or not items:
        return {'success': False, 'error': 'Indica el proveedor y agrega al menos un producto.'}

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_compras_inventario(cursor)
            lineas = []
            subtotal = Decimal('0')
            descuento_total = Decimal('0')
            igv_total = Decimal('0')

            for item in items:
                producto_id = int(item.get('producto_id') or 0)
                cantidad = int(item.get('cantidad') or 0)
                factor = Decimal(str(item.get('factor') or 1))
                precio = Decimal(str(item.get('precio_unitario') or 0))
                descuento_pct = Decimal(str(item.get('descuento_pct') or 0))
                igv_pct = Decimal(str(item.get('igv_pct') or 0))
                if cantidad <= 0 or factor <= 0 or precio < 0 or not 0 <= descuento_pct <= 100 or igv_pct < 0:
                    raise ValueError('Revisa cantidad, factor, precio, descuento e IGV de los productos.')

                cursor.execute("""
                    SELECT nombre FROM productos
                    WHERE id = %s AND tenant_id = %s AND activo = TRUE
                    FOR UPDATE
                """, (producto_id, tenant_id))
                producto = cursor.fetchone()
                if not producto:
                    raise ValueError('Uno de los productos ya no existe o no pertenece a este local.')

                bruto = (Decimal(cantidad) * factor * precio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                descuento = (bruto * descuento_pct / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                base = bruto - descuento
                igv = (base * igv_pct / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                subtotal += bruto
                descuento_total += descuento
                igv_total += igv
                lineas.append({
                    'producto_id': producto_id,
                    'nombre': producto[0],
                    'unidad': str(item.get('unidad') or 'UND')[:30],
                    'factor': factor,
                    'cantidad': cantidad,
                    'precio': precio,
                    'descuento_pct': descuento_pct,
                    'igv_pct': igv_pct,
                    'total': base + igv,
                })

            flete = Decimal(str(documento.get('flete') or 0))
            percepcion = Decimal(str(documento.get('percepcion') or 0))
            if flete < 0 or percepcion < 0:
                raise ValueError('Flete y percepción no pueden ser negativos.')
            total = subtotal - descuento_total + igv_total + flete + percepcion
            tipo_cambio = Decimal(str(documento.get('tipo_cambio') or 1))
            if tipo_cambio <= 0:
                raise ValueError('El tipo de cambio debe ser mayor a cero.')

            cursor.execute("""
                INSERT INTO compras_inventario (
                    proveedor, tipo_comprobante, serie, numero_comprobante,
                    fecha_emision, fecha_entrega, dias_plazo, moneda, tipo_cambio,
                    local_actual, almacen_actual, subtotal, descuento, flete, igv,
                    percepcion, total, observaciones, tenant_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                documento.get('proveedor').strip(), documento.get('tipo_comprobante') or 'FC',
                documento.get('serie') or None, documento.get('numero_comprobante') or None,
                documento.get('fecha_emision') or date.today(), documento.get('fecha_entrega') or None,
                int(documento.get('dias_plazo') or 0), documento.get('moneda') or 'PEN',
                tipo_cambio, documento.get('local_actual') or '01', documento.get('almacen_actual') or '01',
                subtotal, descuento_total, flete, igv_total, percepcion, total,
                documento.get('observaciones') or None, tenant_id
            ))
            compra_id = cursor.fetchone()[0]

            for linea in lineas:
                cursor.execute("""
                    INSERT INTO compras_inventario_detalle (
                        compra_id, producto_id, producto_nombre, unidad, factor, cantidad,
                        precio_unitario, descuento_pct, igv_pct, total
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    compra_id, linea['producto_id'], linea['nombre'], linea['unidad'], linea['factor'],
                    linea['cantidad'], linea['precio'], linea['descuento_pct'], linea['igv_pct'], linea['total']
                ))
                cantidad_inventario = Decimal(linea['cantidad']) * linea['factor']
                if cantidad_inventario != cantidad_inventario.to_integral_value():
                    raise ValueError('El factor debe generar unidades enteras de inventario.')
                stock_agregado = int(cantidad_inventario)
                if stock_agregado <= 0:
                    raise ValueError('El factor y la cantidad deben generar al menos una unidad de inventario.')
                cursor.execute("""
                    UPDATE productos
                    SET cantidad = cantidad + %s, precio_compra = %s
                    WHERE id = %s AND tenant_id = %s
                """, (stock_agregado, linea['precio'], linea['producto_id'], tenant_id))

            conexion.commit()
            return {'success': True, 'compra_id': compra_id, 'total': float(total)}
    except (ValueError, InvalidOperation) as e:
        conexion.rollback()
        return {'success': False, 'error': str(e)}
    except Exception as e:
        conexion.rollback()
        print(f"Error al registrar compra de proveedor: {e}")
        return {'success': False, 'error': 'No se pudo guardar la compra. Revisa el documento y vuelve a intentarlo.'}
    finally:
        conexion.close()


def obtener_compras_inventario(tenant_id=None, limit=50):
    tenant_id = tenant_id if tenant_id is not None else obtener_tenant_id()
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_compras_inventario(cursor)
            cursor.execute("""
                SELECT c.id, c.proveedor, c.tipo_comprobante, c.serie, c.numero_comprobante,
                       c.fecha_emision, c.total, c.moneda, COUNT(d.id)
                FROM compras_inventario c
                LEFT JOIN compras_inventario_detalle d ON d.compra_id = c.id
                WHERE c.tenant_id = %s
                GROUP BY c.id
                ORDER BY c.fecha_emision DESC, c.id DESC
                LIMIT %s
            """, (tenant_id, limit))
            return cursor.fetchall()
    finally:
        conexion.close()


def obtener_detalle_compra_inventario(compra_id, tenant_id=None):
    tenant_id = tenant_id if tenant_id is not None else obtener_tenant_id()
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_compras_inventario(cursor)
            cursor.execute("""
                SELECT id, proveedor, tipo_comprobante, serie, numero_comprobante, fecha_emision,
                       fecha_entrega, dias_plazo, moneda, tipo_cambio, local_actual, almacen_actual,
                       subtotal, descuento, flete, igv, percepcion, total, observaciones
                FROM compras_inventario WHERE id = %s AND tenant_id = %s
            """, (compra_id, tenant_id))
            compra = cursor.fetchone()
            if not compra:
                return None
            cursor.execute("""
                SELECT producto_nombre, unidad, factor, cantidad, precio_unitario, descuento_pct, igv_pct, total
                FROM compras_inventario_detalle WHERE compra_id = %s ORDER BY id
            """, (compra_id,))
            return {'compra': compra, 'items': cursor.fetchall()}
    finally:
        conexion.close()

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

def registrar_entrada_inventario(producto_id, cantidad, precio_compra, proveedor=None, observaciones=None,
                               tipo_comprobante='BC', serie=None, numero_comprobante=None):
    """Registra una entrada al inventario y actualiza el costo de compra del producto."""
    try:
        conexion = obtener_conexion()
        tenant_id = obtener_tenant_id()
        cursor = conexion.cursor()

        detalle_comprobante = []
        tipo_comp = (tipo_comprobante or 'BC').strip().upper() if tipo_comprobante else 'BC'
        if tipo_comp:
            detalle_comprobante.append(f"Tipo: {tipo_comp}")
        if serie:
            detalle_comprobante.append(f"Serie: {serie}")
        if numero_comprobante:
            detalle_comprobante.append(f"N°: {numero_comprobante}")

        observacion_final = observaciones.strip() if observaciones else ''
        if detalle_comprobante:
            detalle_texto = ' | '.join(detalle_comprobante)
            observacion_final = f"{observacion_final} | {detalle_texto}".strip(' | ')

        cursor.execute("""
            SELECT cantidad, precio, COALESCE(precio_compra, 0)
            FROM productos
            WHERE id = %s AND tenant_id = %s
        """, (producto_id, tenant_id))
        row = cursor.fetchone()
        if not row:
            return False

        stock_actual = int(row[0] or 0)
        precio_venta = float(row[1] or 0)
        costo_actual = float(row[2] or 0)
        cantidad = int(cantidad or 0)
        costo_compra = float(precio_compra or 0)

        if cantidad <= 0 or costo_compra < 0:
            return False

        nuevo_stock = stock_actual + cantidad
        nuevo_costo = costo_compra if costo_actual == 0 else costo_compra

        cursor.execute("""
            UPDATE productos
            SET cantidad = %s,
                precio_compra = %s,
                precio = COALESCE(%s, precio)
            WHERE id = %s AND tenant_id = %s
        """, (nuevo_stock, nuevo_costo, precio_venta, producto_id, tenant_id))

        cursor.execute("""
            INSERT INTO compras (cliente_nombre, cliente_email, cliente_telefono, productos, subtotal, igv, total,
                                metodo_pago, estado, observaciones, vendedor_id, tenant_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            proveedor or 'Proveedor Interno',
            '',
            '',
            json.dumps([{
                'id': producto_id,
                'nombre': 'Entrada de inventario',
                'precio': costo_compra,
                'cantidad': cantidad,
                'tipo': 'compra_inventario'
            }]),
            costo_compra * cantidad,
            0,
            costo_compra * cantidad,
            'efectivo',
            'pagado',
            observacion_final or f'Entrada de inventario para producto ID {producto_id}',
            None,
            tenant_id
        ))

        conexion.commit()
        return True
    except Exception as e:
        print(f"Error al registrar entrada de inventario: {e}")
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