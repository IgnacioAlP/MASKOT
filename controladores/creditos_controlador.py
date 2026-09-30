"""
Controlador para el manejo y gestión de créditos (cuentas por cobrar)
MASKOT - Petshop y Veterinaria
"""

from bd import obtener_conexion, obtener_tenant_id
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)


def asegurar_tablas_credito(cursor):
    """Crea las tablas de crédito y abonos si aún no existen."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credito (
            id SERIAL PRIMARY KEY,
            venta_id INT NULL REFERENCES ventas(id) ON DELETE SET NULL,
            cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            cliente_nombre VARCHAR(255) NOT NULL,
            cliente_documento VARCHAR(50),
            monto_total NUMERIC(12,2) NOT NULL DEFAULT 0.00,
            monto_pagado NUMERIC(12,2) NOT NULL DEFAULT 0.00,
            saldo_pendiente NUMERIC(12,2) NOT NULL DEFAULT 0.00,
            fecha_credito TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            fecha_vencimiento DATE,
            estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
            notas TEXT,
            tenant_id INT DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credito_abonos (
            id SERIAL PRIMARY KEY,
            credito_id INT NOT NULL REFERENCES credito(id) ON DELETE CASCADE,
            monto NUMERIC(12,2) NOT NULL,
            metodo_pago VARCHAR(50) DEFAULT 'efectivo',
            notas TEXT,
            usuario_nombre VARCHAR(100),
            fecha_abono TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            tenant_id INT DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)


def crear_credito(cliente_id, cliente_nombre, cliente_documento=None, monto_total=0.0,
                  venta_id=None, fecha_vencimiento=None, notas=None, tenant_id=None):
    """Crea un nuevo registro de crédito para un cliente."""
    conexion = obtener_conexion()
    if tenant_id is None:
        tenant_id = obtener_tenant_id()

    monto_total = float(monto_total or 0.0)
    estado = 'pagado' if monto_total <= 0 else 'pendiente'
    saldo_pendiente = 0.0 if monto_total <= 0 else monto_total

    if not fecha_vencimiento:
        fecha_vencimiento = (datetime.now() + timedelta(days=30)).date()

    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_credito(cursor)
            cursor.execute("""
                INSERT INTO credito (
                    venta_id, cliente_id, cliente_nombre, cliente_documento,
                    monto_total, monto_pagado, saldo_pendiente,
                    fecha_credito, fecha_vencimiento, estado, notas, tenant_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s)
                RETURNING id
            """, (
                venta_id, cliente_id, cliente_nombre, cliente_documento,
                monto_total, 0.0, saldo_pendiente,
                fecha_vencimiento, estado, notas, tenant_id
            ))
            credito_id = cursor.fetchone()[0]
            conexion.commit()
            return {'success': True, 'credito_id': credito_id}
    except Exception as e:
        conexion.rollback()
        logger.error(f"Error creando crédito: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        conexion.close()


def obtener_creditos(filtros=None, tenant_id=None):
    """Obtiene lista de créditos con filtros opcionales y datos del cliente."""
    if filtros is None:
        filtros = {}
    if tenant_id is None:
        tenant_id = obtener_tenant_id()

    conexion = obtener_conexion()
    creditos = []

    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_credito(cursor)

            # Auto-actualizar créditos vencidos
            cursor.execute("""
                UPDATE credito 
                SET estado = 'vencido', updated_at = CURRENT_TIMESTAMP
                WHERE estado IN ('pendiente', 'parcial') 
                  AND fecha_vencimiento < CURRENT_DATE
                  AND tenant_id = %s
            """, (tenant_id,))
            conexion.commit()

            where_clauses = ["cr.tenant_id = %s"]
            params = [tenant_id]

            # Filtro por estado
            estado = filtros.get('estado')
            if estado and estado != 'todos':
                if estado == 'vencido':
                    where_clauses.append("(cr.estado = 'vencido' OR (cr.estado IN ('pendiente', 'parcial') AND cr.fecha_vencimiento < CURRENT_DATE))")
                else:
                    where_clauses.append("cr.estado = %s")
                    params.append(estado)

            # Filtro por búsqueda (cliente nombre o documento)
            busqueda = filtros.get('busqueda', '').strip()
            if busqueda:
                where_clauses.append("(cr.cliente_nombre ILIKE %s OR cr.cliente_documento ILIKE %s OR cl.telefono ILIKE %s)")
                param_b = f"%{busqueda}%"
                params.extend([param_b, param_b, param_b])

            # Filtro por fechas
            fecha_inicio = filtros.get('fecha_inicio')
            if fecha_inicio:
                where_clauses.append("cr.fecha_credito::date >= %s")
                params.append(fecha_inicio)

            fecha_fin = filtros.get('fecha_fin')
            if fecha_fin:
                where_clauses.append("cr.fecha_credito::date <= %s")
                params.append(fecha_fin)

            where_str = " AND ".join(where_clauses)

            query = f"""
                SELECT 
                    cr.id,
                    cr.venta_id,
                    cr.cliente_id,
                    cr.cliente_nombre,
                    COALESCE(cr.cliente_documento, cl.documento, '') AS documento,
                    COALESCE(cl.telefono, '') AS telefono,
                    COALESCE(cl.email, '') AS email,
                    cr.monto_total,
                    cr.monto_pagado,
                    cr.saldo_pendiente,
                    cr.fecha_credito,
                    cr.fecha_vencimiento,
                    cr.estado,
                    COALESCE(cr.notas, '') AS notas,
                    COALESCE(v.numero_venta, '') AS numero_venta
                FROM credito cr
                LEFT JOIN clientes cl ON cr.cliente_id = cl.id
                LEFT JOIN ventas v ON cr.venta_id = v.id
                WHERE {where_str}
                ORDER BY cr.fecha_credito DESC
            """

            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                f_credito = row[10]
                f_venc = row[11]
                hoy = date.today()
                dias_restantes = (f_venc - hoy).days if f_venc else None

                creditos.append({
                    'id': row[0],
                    'venta_id': row[1],
                    'cliente_id': row[2],
                    'cliente_nombre': row[3],
                    'cliente_documento': row[4],
                    'cliente_telefono': row[5],
                    'cliente_email': row[6],
                    'monto_total': float(row[7] or 0.0),
                    'monto_pagado': float(row[8] or 0.0),
                    'saldo_pendiente': float(row[9] or 0.0),
                    'fecha_credito': f_credito,
                    'fecha_vencimiento': f_venc,
                    'estado': row[12],
                    'notas': row[13],
                    'numero_venta': row[14],
                    'dias_restantes': dias_restantes
                })

    except Exception as e:
        logger.error(f"Error obteniendo créditos: {e}")
    finally:
        conexion.close()

    return creditos


def obtener_credito_por_id(credito_id, tenant_id=None):
    """Obtiene los detalles completos de un crédito y sus abonos."""
    if tenant_id is None:
        tenant_id = obtener_tenant_id()

    conexion = obtener_conexion()
    credito = None

    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_credito(cursor)
            cursor.execute("""
                SELECT 
                    cr.id,
                    cr.venta_id,
                    cr.cliente_id,
                    cr.cliente_nombre,
                    COALESCE(cr.cliente_documento, cl.documento, '') AS documento,
                    COALESCE(cl.telefono, '') AS telefono,
                    COALESCE(cl.email, '') AS email,
                    cr.monto_total,
                    cr.monto_pagado,
                    cr.saldo_pendiente,
                    cr.fecha_credito,
                    cr.fecha_vencimiento,
                    cr.estado,
                    COALESCE(cr.notas, '') AS notas,
                    COALESCE(v.numero_venta, '') AS numero_venta,
                    v.productos AS venta_productos
                FROM credito cr
                LEFT JOIN clientes cl ON cr.cliente_id = cl.id
                LEFT JOIN ventas v ON cr.venta_id = v.id
                WHERE cr.id = %s AND cr.tenant_id = %s
            """, (credito_id, tenant_id))

            row = cursor.fetchone()
            if row:
                f_credito = row[10]
                f_venc = row[11]
                hoy = date.today()
                dias_restantes = (f_venc - hoy).days if f_venc else None

                credito = {
                    'id': row[0],
                    'venta_id': row[1],
                    'cliente_id': row[2],
                    'cliente_nombre': row[3],
                    'cliente_documento': row[4],
                    'cliente_telefono': row[5],
                    'cliente_email': row[6],
                    'monto_total': float(row[7] or 0.0),
                    'monto_pagado': float(row[8] or 0.0),
                    'saldo_pendiente': float(row[9] or 0.0),
                    'fecha_credito': f_credito,
                    'fecha_vencimiento': f_venc,
                    'estado': row[12],
                    'notas': row[13],
                    'numero_venta': row[14],
                    'venta_productos': row[15],
                    'dias_restantes': dias_restantes,
                    'abonos': []
                }

                # Cargar historial de abonos
                cursor.execute("""
                    SELECT id, monto, metodo_pago, COALESCE(notas, ''), usuario_nombre, fecha_abono
                    FROM credito_abonos
                    WHERE credito_id = %s AND tenant_id = %s
                    ORDER BY fecha_abono DESC
                """, (credito_id, tenant_id))

                for ab in cursor.fetchall():
                    credito['abonos'].append({
                        'id': ab[0],
                        'monto': float(ab[1] or 0.0),
                        'metodo_pago': ab[2],
                        'notas': ab[3],
                        'usuario_nombre': ab[4] or 'Usuario',
                        'fecha_abono': ab[5]
                    })

    except Exception as e:
        logger.error(f"Error obteniendo detalle de crédito: {e}")
    finally:
        conexion.close()

    return credito


def registrar_abono(credito_id, monto, metodo_pago='efectivo', notas=None, usuario_nombre=None, tenant_id=None):
    """Registra un pago/abono al crédito y actualiza los saldos."""
    if tenant_id is None:
        tenant_id = obtener_tenant_id()

    monto = float(monto or 0.0)
    if monto <= 0:
        return {'success': False, 'error': 'El monto del abono debe ser mayor a 0'}

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_credito(cursor)

            cursor.execute("""
                SELECT monto_total, monto_pagado, saldo_pendiente, estado
                FROM credito
                WHERE id = %s AND tenant_id = %s
                FOR UPDATE
            """, (credito_id, tenant_id))

            row = cursor.fetchone()
            if not row:
                conexion.rollback()
                return {'success': False, 'error': 'Crédito no encontrado'}

            monto_total = float(row[0] or 0.0)
            monto_pagado_actual = float(row[1] or 0.0)
            saldo_actual = float(row[2] or 0.0)

            if saldo_actual <= 0:
                conexion.rollback()
                return {'success': False, 'error': 'Este crédito ya ha sido cancelado en su totalidad'}

            # Si el abono supera el saldo, se ajusta al saldo pendiente
            monto_abono = min(monto, saldo_actual)
            nuevo_pagado = round(monto_pagado_actual + monto_abono, 2)
            nuevo_saldo = round(max(0.0, saldo_actual - monto_abono), 2)
            nuevo_estado = 'pagado' if nuevo_saldo <= 0 else 'parcial'

            # 1. Insertar abono en historial
            cursor.execute("""
                INSERT INTO credito_abonos (
                    credito_id, monto, metodo_pago, notas, usuario_nombre, fecha_abono, tenant_id
                ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                RETURNING id
            """, (
                credito_id, monto_abono, metodo_pago, notas, usuario_nombre or 'Cajero', tenant_id
            ))
            abono_id = cursor.fetchone()[0]

            # 2. Actualizar estado y saldos del crédito
            cursor.execute("""
                UPDATE credito
                SET monto_pagado = %s,
                    saldo_pendiente = %s,
                    estado = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
            """, (nuevo_pagado, nuevo_saldo, nuevo_estado, credito_id, tenant_id))

            conexion.commit()

            return {
                'success': True,
                'abono_id': abono_id,
                'monto_abonado': monto_abono,
                'saldo_pendiente': nuevo_saldo,
                'nuevo_estado': nuevo_estado
            }

    except Exception as e:
        conexion.rollback()
        logger.error(f"Error registrando abono: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        conexion.close()


def obtener_resumen_creditos(tenant_id=None):
    """Obtiene métricas y estadísticas para el panel superior del módulo de créditos."""
    if tenant_id is None:
        tenant_id = obtener_tenant_id()

    conexion = obtener_conexion()
    resumen = {
        'total_otorgado': 0.0,
        'total_pendiente': 0.0,
        'total_cobrado': 0.0,
        'conteo_pendientes': 0,
        'conteo_vencidos': 0,
        'conteo_pagados': 0,
        'total_creditos': 0
    }

    try:
        with conexion.cursor() as cursor:
            asegurar_tablas_credito(cursor)

            cursor.execute("""
                SELECT 
                    COALESCE(SUM(monto_total), 0) AS total_otorgado,
                    COALESCE(SUM(monto_pagado), 0) AS total_cobrado,
                    COALESCE(SUM(saldo_pendiente), 0) AS total_pendiente,
                    COUNT(id) AS total_creditos,
                    COUNT(CASE WHEN estado IN ('pendiente', 'parcial') AND (fecha_vencimiento >= CURRENT_DATE OR fecha_vencimiento IS NULL) THEN 1 END) AS pendientes,
                    COUNT(CASE WHEN estado = 'vencido' OR (estado IN ('pendiente', 'parcial') AND fecha_vencimiento < CURRENT_DATE) THEN 1 END) AS vencidos,
                    COUNT(CASE WHEN estado = 'pagado' THEN 1 END) AS pagados
                FROM credito
                WHERE tenant_id = %s
            """, (tenant_id,))

            row = cursor.fetchone()
            if row:
                resumen['total_otorgado'] = float(row[0] or 0.0)
                resumen['total_cobrado'] = float(row[1] or 0.0)
                resumen['total_pendiente'] = float(row[2] or 0.0)
                resumen['total_creditos'] = int(row[3] or 0)
                resumen['conteo_pendientes'] = int(row[4] or 0)
                resumen['conteo_vencidos'] = int(row[5] or 0)
                resumen['conteo_pagados'] = int(row[6] or 0)

    except Exception as e:
        logger.error(f"Error obteniendo resumen de créditos: {e}")
    finally:
        conexion.close()

    return resumen
