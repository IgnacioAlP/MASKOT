from bd import obtener_conexion, obtener_tenant_id
from datetime import datetime
import json


def generar_numero_venta():
    """Genera un número de venta único"""
    now = datetime.now()
    return f"V{now.strftime('%Y%m%d%H%M%S')}"


def obtener_productos_venta():
    """Obtiene productos disponibles para venta"""
    conexion = obtener_conexion()
    productos = []
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, precio, cantidad, imagen
                FROM productos 
                WHERE activo = 1 AND cantidad > 0 AND tipo = 'venta'
                AND tenant_id = %s
                ORDER BY nombre
            """, (tenant_id,))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos


def procesar_venta(datos_venta):
    """Procesa una venta completa"""
    conexion = obtener_conexion()
    
    try:
        conexion.begin()
        
        with conexion.cursor() as cursor:
            numero_venta = generar_numero_venta()
            # Preparar campos opcionales
            referencia = None
            if 'referencia_pago' in datos_venta and datos_venta.get('referencia_pago'):
                referencia = datos_venta.get('referencia_pago')
            elif datos_venta.get('detalle_multipago'):
                try:
                    referencia = json.dumps(datos_venta.get('detalle_multipago'))
                except Exception:
                    referencia = str(datos_venta.get('detalle_multipago'))

            cliente_nombre = datos_venta.get('cliente_nombre')
            cliente_documento = datos_venta.get('cliente_documento')
            notas = datos_venta.get('notas')

            # Calcular totales si no vienen
            if 'subtotal' not in datos_venta or 'total' not in datos_venta:
                tot = calcular_totales_venta(datos_venta.get('productos', []))
                datos_venta['subtotal'] = tot['subtotal']
                datos_venta['igv'] = tot['igv']
                datos_venta['total'] = tot['total']

            # Antes de insertar, validar stock disponible en productos (no aplica a servicios)
            productos = datos_venta.get('productos', []) or []
            for p in productos:
                if p.get('tipo') == 'servicio':
                    continue  # Los servicios no tienen stock
                pid = p.get('id')
                cantidad = int(p.get('cantidad', p.get('qty', 0)) or 0)
                if cantidad <= 0:
                    conexion.rollback()
                    # Try to include product name if provided
                    nombre_prov = p.get('nombre') or f'id {pid}'
                    return {'success': False, 'error': f'Cantidad inválida para el producto "{nombre_prov}"'}
                # Lock the product row and fetch name + stock
                cursor.execute("SELECT cantidad, nombre FROM productos WHERE id = %s FOR UPDATE", (pid,))
                row = cursor.fetchone()
                if not row:
                    conexion.rollback()
                    return {'success': False, 'error': f'Producto con id {pid} no existe'}
                stock_actual = row[0] or 0
                nombre_db = row[1] or f'id {pid}'
                if stock_actual < cantidad:
                    conexion.rollback()
                    return {'success': False, 'error': f'Stock insuficiente para el producto "{nombre_db}" (disponible {stock_actual})'}

            tenant_id = obtener_tenant_id()
            # Resolver nombre del vendedor para columnas NOT NULL legacy
            vendedor_id = datos_venta.get('vendedor_id')
            vendedor_nombre = None
            if vendedor_id:
                try:
                    cursor.execute("SELECT username FROM usuarios WHERE id = %s", (vendedor_id,))
                    row = cursor.fetchone()
                    vendedor_nombre = row[0] if row else str(vendedor_id)
                except Exception:
                    vendedor_nombre = str(vendedor_id)
            # Insertar venta (incluye referencia_pago y datos de cliente si existen)
            cursor.execute("""
                INSERT INTO ventas (
                    numero_venta, fecha_venta, subtotal, igv, total,
                    metodo_pago, monto_recibido, cambio_entregado, referencia_pago,
                    estado, vendedor_id, vendedor_nombre, productos,
                    cliente_nombre, cliente_documento, notas,
                    tenant_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                numero_venta, datetime.now(), datos_venta['subtotal'],
                datos_venta['igv'], datos_venta['total'], datos_venta['metodo_pago'],
                datos_venta.get('monto_recibido', None), datos_venta.get('cambio_entregado', datos_venta.get('cambio', 0)),
                referencia,
                'completada', vendedor_id, vendedor_nombre, json.dumps(productos),
                cliente_nombre, cliente_documento, notas,
                tenant_id
            ))

            venta_id = cursor.lastrowid

            # Reducir stock de los productos vendidos dentro de la misma transacción (no aplica a servicios)
            for p in productos:
                if p.get('tipo') == 'servicio':
                    continue  # Los servicios no tienen stock que descontar
                pid = p.get('id')
                cantidad = int(p.get('cantidad', p.get('qty', 0)) or 0)
                cursor.execute("UPDATE productos SET cantidad = cantidad - %s WHERE id = %s AND cantidad >= %s", (cantidad, pid, cantidad))
                if cursor.rowcount == 0:
                    # fetch name for friendlier error
                    cursor.execute("SELECT nombre FROM productos WHERE id = %s", (pid,))
                    rname = cursor.fetchone()
                    nombre_db = rname[0] if rname and rname[0] else f'id {pid}'
                    conexion.rollback()
                    return {'success': False, 'error': f'No hay suficiente stock para el producto "{nombre_db}"'}

            conexion.commit()

            total_resp = float(datos_venta.get('total', 0.0))

            return {
                'success': True,
                'venta_id': venta_id,
                'numero_venta': numero_venta,
                'total': total_resp
            }
            
    except Exception as e:
        conexion.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        conexion.close()


def obtener_detalle_venta(venta_id):
    """Obtiene el detalle de una venta"""
    conexion = obtener_conexion()
    venta = None
    
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT v.id, v.numero_venta, v.fecha_venta, v.subtotal, v.igv, v.total,
                       v.metodo_pago, v.monto_recibido, v.cambio_entregado, v.estado,
                       v.productos, u.username as vendedor_nombre,
                       v.cliente_nombre, v.cliente_documento, v.notas, v.referencia_pago,
                       v.created_at, v.updated_at
                FROM ventas v
                LEFT JOIN usuarios u ON v.vendedor_id = u.id
                WHERE v.id = %s
            """, (venta_id,))
            
            resultado = cursor.fetchone()
            
            if resultado:
                # Construir venta con valores por defecto para evitar claves faltantes
                productos = []
                try:
                    productos = json.loads(resultado[10]) if resultado[10] else []
                except Exception:
                    productos = []
                # Normalizar cada producto: asegurar precio, cantidad y total
                productos_normalizados = []
                for p in productos:
                    try:
                        precio = float(p.get('precio', p.get('precio_unitario', p.get('unit_price', p.get('price', 0)))))
                    except Exception:
                        try:
                            precio = float(p.get('price', 0))
                        except Exception:
                            precio = 0.0
                    try:
                        cantidad = int(p.get('cantidad', p.get('qty', p.get('cantidad_vendida', 0))))
                    except Exception:
                        cantidad = int(p.get('qty', 0) or 0)
                    total_producto = round(precio * cantidad, 2)
                    pn = dict(p)
                    pn['precio'] = precio
                    pn['cantidad'] = cantidad
                    pn['total'] = total_producto
                    productos_normalizados.append(pn)

                # Intentar deserializar referencia_pago como detalle de multipago si aplica
                referencia_pago = resultado[15] if len(resultado) > 15 else None
                detalle_multipago = None
                if referencia_pago:
                    try:
                        maybe = json.loads(referencia_pago)
                        # Normalize into list of {metodo, monto}
                        if isinstance(maybe, dict):
                            normalized = []
                            # Case A: keys like metodo1/monto1
                            i = 1
                            found_indexed = False
                            while True:
                                key_met = f'metodo{i}'
                                key_mon = f'monto{i}'
                                if key_met in maybe or key_mon in maybe:
                                    found_indexed = True
                                    met = maybe.get(key_met)
                                    mon = maybe.get(key_mon, 0)
                                    try:
                                        mon_val = float(mon or 0)
                                    except Exception:
                                        mon_val = 0.0
                                    if met:
                                        normalized.append({'metodo': str(met), 'monto': round(mon_val,2)})
                                    i += 1
                                    # safety cap
                                    if i > 20:
                                        break
                                    continue
                                break

                            if not found_indexed:
                                # Case B: dict where keys are method names and values are amounts
                                for kkk, vvv in maybe.items():
                                    try:
                                        vv = float(vvv or 0)
                                    except Exception:
                                        vv = 0.0
                                    normalized.append({'metodo': str(kkk), 'monto': round(vv,2)})

                            detalle_multipago = normalized if normalized else None
                    except Exception:
                        detalle_multipago = None

                venta = {
                    'id': resultado[0],
                    'numero_venta': resultado[1] or '',
                    'fecha_venta': resultado[2] if resultado[2] else None,
                    'subtotal': float(resultado[3]) if resultado[3] is not None else 0.0,
                    'igv': float(resultado[4]) if resultado[4] is not None else 0.0,
                    'total': float(resultado[5]) if resultado[5] is not None else 0.0,
                    'metodo_pago': resultado[6] or '',
                    'monto_recibido': float(resultado[7]) if resultado[7] is not None else 0.0,
                    'cambio_entregado': float(resultado[8]) if resultado[8] is not None else 0.0,
                    'cambio': float(resultado[8]) if resultado[8] is not None else 0.0,
                    'estado': resultado[9] or 'desconocido',
                    'productos': productos_normalizados,
                    'vendedor_nombre': resultado[11] or '',
                    'cliente_nombre': resultado[12] or '',
                    'cliente_documento': resultado[13] or '',
                    'notas': resultado[14] or '',
                    'referencia_pago': referencia_pago or '',
                    'detalle_multipago': detalle_multipago,
                    'created_at': resultado[16],
                    'updated_at': resultado[17]
                }
                
    finally:
        conexion.close()
    
    return venta


def obtener_venta_por_id(venta_id):
    """Alias para compatibilidad: devuelve detalle de venta por id"""
    return obtener_detalle_venta(venta_id)


def registrar_venta(data):
    """Alias simple para compatibilidad con main.py (usa procesar_venta)."""
    return procesar_venta(data)


def obtener_ventas_por_fecha(fecha_inicio=None, fecha_fin=None, vendedor_id=None,
                            metodo_pago=None, estado=None, limit=50, offset=0):
    """Devuelve lista de ventas filtradas por rango de fechas y otros parámetros.
    Los parámetros fecha_inicio/fecha_fin deben estar en formato 'YYYY-MM-DD' o None.
    """
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            where = ['tenant_id = %s']
            params = [tenant_id]
            if fecha_inicio:
                where.append('DATE(fecha_venta) >= %s')
                params.append(fecha_inicio)
            if fecha_fin:
                where.append('DATE(fecha_venta) <= %s')
                params.append(fecha_fin)
            if vendedor_id:
                where.append('vendedor_id = %s')
                params.append(vendedor_id)
            if metodo_pago:
                where.append('metodo_pago = %s')
                params.append(metodo_pago)
            if estado:
                where.append('estado = %s')
                params.append(estado)

            where_clause = (' WHERE ' + ' AND '.join(where)) if where else ''

            # also fetch referencia_pago so we can detect detalle_multipago (multipago) for display
            sql = f"SELECT id, numero_venta, fecha_venta, subtotal, igv, total, metodo_pago, referencia_pago, estado, vendedor_id, productos FROM ventas {where_clause} ORDER BY fecha_venta DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            resultados = []
            for r in rows:
                try:
                    productos = json.loads(r[9]) if r[9] else []
                except Exception:
                    productos = []
                # r[7] is referencia_pago (may contain JSON with detalle_multipago)
                referencia_pago = r[7]
                detalle_multipago = None
                if referencia_pago:
                    try:
                        maybe = json.loads(referencia_pago)
                        if isinstance(maybe, dict):
                            normalized = []
                            i = 1
                            found_indexed = False
                            while True:
                                key_met = f'metodo{i}'
                                key_mon = f'monto{i}'
                                if key_met in maybe or key_mon in maybe:
                                    found_indexed = True
                                    met = maybe.get(key_met)
                                    mon = maybe.get(key_mon, 0)
                                    try:
                                        mon_val = float(mon or 0)
                                    except Exception:
                                        mon_val = 0.0
                                    if met:
                                        normalized.append({'metodo': str(met), 'monto': round(mon_val,2)})
                                    i += 1
                                    if i > 20:
                                        break
                                    continue
                                break

                            if not found_indexed:
                                for kkk, vvv in maybe.items():
                                    try:
                                        vv = float(vvv or 0)
                                    except Exception:
                                        vv = 0.0
                                    normalized.append({'metodo': str(kkk), 'monto': round(vv,2)})

                            detalle_multipago = normalized if normalized else None
                    except Exception:
                        detalle_multipago = None

                resultados.append({
                    'id': r[0],
                    'numero_venta': r[1],
                    'fecha_venta': r[2],
                    'subtotal': float(r[3]) if r[3] is not None else 0.0,
                    'igv': float(r[4]) if r[4] is not None else 0.0,
                    'total': float(r[5]) if r[5] is not None else 0.0,
                    'metodo_pago': r[6],
                    'detalle_multipago': detalle_multipago,
                    'estado': r[8],
                    'vendedor_id': r[9],
                    'productos': productos
                })
            return resultados
    finally:
        conexion.close()


def calcular_totales_venta(productos):
    """Calcula subtotal, igv (18%) y total para una lista de productos.
    Cada producto debe tener 'precio' y 'cantidad'. Devuelve dict con subtotal, igv, total.
    """
    try:
        subtotal = 0.0
        for p in productos:
            precio = float(p.get('precio', p.get('total', 0)) or 0)
            cantidad = int(p.get('cantidad', p.get('qty', 1)) or 0)
            subtotal += precio * cantidad
        subtotal = round(subtotal, 2)
        igv = round(subtotal * 0.18, 2)
        total = round(subtotal + igv, 2)
        return {'subtotal': subtotal, 'igv': igv, 'total': total}
    except Exception:
        return {'subtotal': 0.0, 'igv': 0.0, 'total': 0.0}


def obtener_estadisticas_ventas(fecha_inicio=None, fecha_fin=None):
    """Devuelve estadísticas básicas de ventas en un rango de fechas."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            where = ['tenant_id = %s']
            params = [tenant_id]
            if fecha_inicio:
                where.append('DATE(fecha_venta) >= %s')
                params.append(fecha_inicio)
            if fecha_fin:
                where.append('DATE(fecha_venta) <= %s')
                params.append(fecha_fin)
            where_clause = ' WHERE ' + ' AND '.join(where)

            # Total de ventas y suma total vendida
            cursor.execute(f"SELECT COUNT(*) as cnt, COALESCE(SUM(total),0) as total_vendido FROM ventas {where_clause}", tuple(params))
            row = cursor.fetchone()
            total_ventas = int(row[0]) if row else 0
            total_vendido = float(row[1]) if row else 0.0

            promedio = (total_vendido / total_ventas) if total_ventas > 0 else 0.0

            # Por método de pago
            # We aggregate in Python so we can account for detalle_multipago stored in referencia_pago
            cursor.execute(f"SELECT metodo_pago, referencia_pago, total FROM ventas {where_clause}", tuple(params))
            rows_pm = cursor.fetchall()
            agg = {}
            for r in rows_pm:
                metodo_pago = r[0] or ''
                referencia_pago = r[1]
                total_venta = float(r[2] or 0)

                # Try to parse referencia_pago as multipago detail
                used_multipago = False
                if referencia_pago:
                    try:
                        maybe = json.loads(referencia_pago)
                        # normalize into list of {metodo,monto}
                        normalized = []
                        if isinstance(maybe, dict):
                            # metodo1/monto1 pattern
                            i = 1
                            found_indexed = False
                            while True:
                                mk = f'metodo{i}'
                                nk = f'monto{i}'
                                if mk in maybe or nk in maybe:
                                    found_indexed = True
                                    met = maybe.get(mk)
                                    mon = maybe.get(nk, 0)
                                    try:
                                        mon_val = float(mon or 0)
                                    except Exception:
                                        mon_val = 0.0
                                    if met:
                                        normalized.append({'metodo': str(met).strip(), 'monto': round(mon_val,2)})
                                    i += 1
                                    if i > 20:
                                        break
                                    continue
                                break
                            if not found_indexed:
                                for kkk, vvv in maybe.items():
                                    try:
                                        vv = float(vvv or 0)
                                    except Exception:
                                        vv = 0.0
                                    normalized.append({'metodo': str(kkk).strip(), 'monto': round(vv,2)})
                        # If we have a normalized multipago list, add amounts per method
                        if normalized:
                            used_multipago = True
                            for mp in normalized:
                                meth = (mp.get('metodo') or '').strip()
                                if not meth:
                                    continue
                                monto = float(mp.get('monto') or 0)
                                key = meth.lower()
                                if key not in agg:
                                    agg[key] = {'metodo': key, 'cantidad': 0, 'total': 0.0}
                                # For multipago we count the sale toward each method used
                                agg[key]['cantidad'] += 1
                                agg[key]['total'] += monto
                    except Exception:
                        pass

                if not used_multipago:
                    # No multipago detail: attribute the entire sale total to metodo_pago
                    meth = metodo_pago.strip() if metodo_pago else ''
                    if not meth:
                        # skip anonymous/empty method entries
                        continue
                    key = meth.lower()
                    if key not in agg:
                        agg[key] = {'metodo': key, 'cantidad': 0, 'total': 0.0}
                    agg[key]['cantidad'] += 1
                    agg[key]['total'] += total_venta

            por_metodo = []
            for v in agg.values():
                # Round totals
                por_metodo.append({'metodo': v['metodo'], 'cantidad': int(v['cantidad']), 'total': round(float(v['total']),2)})

            # Vendedores activos
            cursor.execute(f"SELECT COUNT(DISTINCT vendedor_id) FROM ventas {where_clause}", tuple(params))
            vendedores_activos = int(cursor.fetchone()[0] or 0)

            return {
                'total_ventas': total_ventas,
                'total_vendido': round(total_vendido,2),
                'promedio_venta': round(promedio,2),
                'por_metodo_pago': por_metodo,
                'vendedores_activos': vendedores_activos
            }
    finally:
        conexion.close()


def obtener_productos_mas_vendidos(fecha_inicio=None, fecha_fin=None, limit=10):
    """Agrega los productos desde el campo JSON 'productos' de las ventas y retorna los más vendidos."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            where = ['tenant_id = %s']
            params = [tenant_id]
            if fecha_inicio:
                where.append('DATE(fecha_venta) >= %s')
                params.append(fecha_inicio)
            if fecha_fin:
                where.append('DATE(fecha_venta) <= %s')
                params.append(fecha_fin)
            where_clause = ' WHERE ' + ' AND '.join(where)

            cursor.execute(f"SELECT productos FROM ventas {where_clause}", tuple(params))
            agregados = {}
            for row in cursor.fetchall():
                try:
                    items = json.loads(row[0]) if row[0] else []
                except Exception:
                    items = []
                for it in items:
                    pid = it.get('id')
                    nombre = it.get('nombre') or it.get('title') or str(pid)
                    cantidad = int(it.get('cantidad', it.get('qty', 1)) or 0)
                    total_ingresos = float(it.get('precio', it.get('total', 0))) * cantidad
                    if pid not in agregados:
                        agregados[pid] = {'id': pid, 'nombre': nombre, 'cantidad': 0, 'total_ingresos': 0.0}
                    agregados[pid]['cantidad'] += cantidad
                    agregados[pid]['total_ingresos'] += total_ingresos

            # Ordenar por cantidad vendida
            lista = sorted(agregados.values(), key=lambda x: x['cantidad'], reverse=True)
            return lista[:limit]
    finally:
        conexion.close()


def validar_stock_productos(productos):
    """Valida si hay stock suficiente para la lista de productos.
    Devuelve dict con 'valido' y 'errores' (lista de strings) y 'errores_obj' (lista de objects {id,nombre,msg}).
    """
    errores = []
    errores_obj = []
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            for p in productos:
                pid = p.get('id')
                cantidad = int(p.get('cantidad', p.get('qty', 0)) or 0)
                nombre_prov = p.get('nombre') or None
                if cantidad <= 0:
                    msg = f'Cantidad inválida para el producto "{nombre_prov or pid}"'
                    errores.append(msg)
                    errores_obj.append({'id': pid, 'nombre': nombre_prov or '', 'msg': msg})
                    continue
                cursor.execute("SELECT cantidad, nombre FROM productos WHERE id = %s", (pid,))
                row = cursor.fetchone()
                if not row:
                    msg = f'Producto "{nombre_prov or pid}" no existe'
                    errores.append(msg)
                    errores_obj.append({'id': pid, 'nombre': nombre_prov or '', 'msg': msg})
                    continue
                stock_actual = row[0] or 0
                nombre_db = row[1] or nombre_prov or ''
                if stock_actual < cantidad:
                    msg = f'Stock insuficiente para el producto "{nombre_db}" (disponible {stock_actual})'
                    errores.append(msg)
                    errores_obj.append({'id': pid, 'nombre': nombre_db, 'msg': msg, 'disponible': stock_actual})
    finally:
        conexion.close()

    return {'valido': len(errores) == 0, 'errores': errores, 'errores_obj': errores_obj}


def cancelar_venta(venta_id, motivo=None, usuario_id=None):
    """Marca una venta como cancelada y repone el stock de los productos vendidos.
    Devuelve {'success': True} o {'success': False, 'error': msg}
    """
    conexion = obtener_conexion()
    try:
        conexion.begin()
        with conexion.cursor() as cursor:
            # Obtener venta y sus productos
            cursor.execute("SELECT id, estado, productos FROM ventas WHERE id = %s FOR UPDATE", (venta_id,))
            row = cursor.fetchone()
            if not row:
                conexion.rollback()
                return {'success': False, 'error': 'Venta no encontrada'}
            estado_actual = row[1]
            productos_json = row[2]
            if estado_actual == 'cancelada':
                conexion.rollback()
                return {'success': False, 'error': 'Venta ya está cancelada'}

            try:
                productos = json.loads(productos_json) if productos_json else []
            except Exception:
                productos = []

            # Reponer stock
            for p in productos:
                pid = p.get('id')
                cantidad = int(p.get('cantidad', p.get('qty', 0)) or 0)
                if pid and cantidad > 0:
                    cursor.execute("UPDATE productos SET cantidad = cantidad + %s WHERE id = %s", (cantidad, pid))

            # Marcar venta como cancelada y opcionalmente guardar motivo
            cursor.execute("UPDATE ventas SET estado = 'cancelada', notas = CONCAT(IFNULL(notas, ''), %s) WHERE id = %s", (f'\nCANCELADA: {motivo or ""}', venta_id))
            conexion.commit()
            return {'success': True}
    except Exception as e:
        conexion.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        conexion.close()