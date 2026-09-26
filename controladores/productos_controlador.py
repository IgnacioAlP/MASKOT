from bd import obtener_conexion, obtener_tenant_id
import os
from datetime import datetime, timedelta


def _normalizar_stock_min(valor, default=5):
    try:
        stock_min = int(valor) if valor is not None else default
    except (TypeError, ValueError):
        stock_min = default
    return max(0, stock_min)


def normalizar_datos_producto_edicion(datos):
    """Normaliza los valores del formulario de edición para evitar mezclar campos por orden."""
    if datos is None:
        datos = {}

    cantidad_raw = datos.get('cantidad', 0)
    precio_raw = datos.get('precio', 0)
    precio_compra_raw = datos.get('precio_compra', None)
    stock_min_raw = datos.get('stock_min', datos.get('stock_minimo', 5))

    try:
        cantidad = int(cantidad_raw) if cantidad_raw not in (None, '') else 0
    except (TypeError, ValueError):
        cantidad = 0

    try:
        precio = float(precio_raw) if precio_raw not in (None, '') else 0.0
    except (TypeError, ValueError):
        precio = 0.0

    try:
        precio_compra = float(precio_compra_raw) if precio_compra_raw not in (None, '') else precio
    except (TypeError, ValueError):
        precio_compra = precio

    stock_min = _normalizar_stock_min(stock_min_raw, 5)

    return {
        'nombre': (datos.get('nombre') or '').strip(),
        'tipo': (datos.get('tipo') or 'stock').strip() or 'stock',
        'cantidad': cantidad,
        'precio': precio,
        'precio_compra': precio_compra,
        'stock_min': stock_min,
        'codigo_barra': (datos.get('codigo_barra') or '').strip() or None,
        'fecha_vencimiento': datos.get('fecha_vencimiento') or None,
    }


def obtener_productos():
    """Obtiene todos los productos del inventario"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                SELECT id, nombre, tipo, cantidad, precio,
                       COALESCE(precio_compra, 0) AS precio_compra,
                       COALESCE(NULLIF(stock_min, 0), NULLIF(stock_minimo, 0), 5) AS stock_min,
                       fecha_vencimiento, codigo_barra, imagen, activo
                FROM productos 
                WHERE tenant_id = %s AND activo = true
                ORDER BY nombre
            """, (tenant_id,))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos

def obtener_productos_mas_vendidos(limit=4):
    """Obtiene los productos más vendidos para mostrar en la tienda"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                SELECT p.id, p.nombre, p.tipo, p.cantidad, p.precio, COALESCE(p.precio_compra, 0),
                       COALESCE(p.stock_min, p.stock_minimo, 5), p.fecha_vencimiento, p.imagen, p.activo
                FROM productos p
                WHERE p.tipo = 'venta' AND p.cantidad > 0 AND p.activo = true AND p.tenant_id = %s
                ORDER BY p.cantidad DESC, p.nombre ASC
                LIMIT %s
            """, (tenant_id, limit))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos

def obtener_producto_por_id(producto_id):
    """Obtiene un producto específico por su ID dentro del tenant actual"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    producto = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                SELECT id, nombre, tipo, cantidad, precio,
                       COALESCE(precio_compra, 0) AS precio_compra,
                       COALESCE(NULLIF(stock_min, 0), NULLIF(stock_minimo, 0), 5) AS stock_min,
                       fecha_vencimiento, imagen, activo
                FROM productos 
                WHERE id = %s AND tenant_id = %s
            """, (producto_id, tenant_id))
            producto = cursor.fetchone()
    finally:
        conexion.close()
    return producto

def obtener_producto_por_codigo_barra(codigo_barra):
    """Busca un producto por su código de barras dentro del tenant actual"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    producto = None
    try:
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                SELECT id, nombre, codigo_barra, tipo, cantidad, precio,
                       COALESCE(precio_compra, 0) AS precio_compra,
                       COALESCE(NULLIF(stock_min, 0), NULLIF(stock_minimo, 0), 5) AS stock_min,
                       fecha_vencimiento, imagen, activo
                FROM productos
                WHERE codigo_barra = %s AND tenant_id = %s AND activo = true
            """, (codigo_barra, tenant_id))
            producto = cursor.fetchone()
    finally:
        conexion.close()
    return producto


def obtener_productos_por_busqueda(query, limite=20):
    """Busca productos por nombre o código de barras para registrar compras o ventas."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            termino = f"%{query.strip()}%" if query else "%"
            cursor.execute("""
                SELECT id, nombre, codigo_barra, tipo, cantidad, precio,
                       COALESCE(precio_compra, 0) AS precio_compra,
                       COALESCE(NULLIF(stock_min, 0), NULLIF(stock_minimo, 0), 5) AS stock_min,
                       imagen
                FROM productos
                WHERE tenant_id = %s AND activo = true
                  AND (
                    nombre ILIKE %s OR COALESCE(codigo_barra::text, '') ILIKE %s OR TRIM(COALESCE(codigo_barra::text, '')) = %s
                  )
                ORDER BY nombre ASC
                LIMIT %s
            """, (tenant_id, termino, termino, query.strip() if query else '', limite))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos


def insertar_producto(nombre, tipo='stock', cantidad=0, precio=0.00, stock_min=5,
                      fecha_vencimiento=None, imagen=None, codigo_barra=None, precio_compra=None):
    """Inserta un nuevo producto en el inventario"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        stock_min = _normalizar_stock_min(stock_min, 5)
        if precio_compra is None:
            precio_compra = precio
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                INSERT INTO productos (nombre, codigo_barra, tipo, cantidad, precio, precio_compra, stock_min, stock_minimo,
                                     fecha_vencimiento, imagen, activo, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s)
                RETURNING id
            """, (nombre, codigo_barra or None, tipo, cantidad, precio, precio_compra, stock_min, stock_min,
                  fecha_vencimiento, imagen, tenant_id))
            producto_id = cursor.fetchone()[0]
            conexion.commit()
            return producto_id
    except Exception as e:
        conexion.rollback()
        print(f"Error al insertar producto: {e}")
        return None
    finally:
        conexion.close()

def actualizar_producto(producto_id, nombre, tipo='stock', cantidad=0, precio=0.00,
                        stock_min=5, fecha_vencimiento=None, codigo_barra=None, precio_compra=None):
    """Actualiza un producto existente"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        stock_min = _normalizar_stock_min(stock_min, 5)
        if precio_compra is None:
            precio_compra = precio
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                UPDATE productos 
                SET nombre = %s, tipo = %s, cantidad = %s, precio = %s,
                    precio_compra = %s, stock_min = %s, stock_minimo = %s,
                    fecha_vencimiento = %s, codigo_barra = %s
                WHERE id = %s AND tenant_id = %s
            """, (nombre, tipo, cantidad, precio, precio_compra, stock_min, stock_min,
                  fecha_vencimiento, codigo_barra or None, producto_id, tenant_id))
            conexion.commit()
            return cursor.rowcount > 0
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar producto: {e}")
        return False
    finally:
        conexion.close()

def eliminar_producto(producto_id):
    """Elimina un producto del inventario (desactivación lógica)"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE productos SET activo = false WHERE id = %s AND tenant_id = %s", (producto_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al eliminar producto: {e}")
        return False
    finally:
        conexion.close()

def obtener_productos_bajo_stock():
    """Obtiene productos con stock bajo"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_min INTEGER DEFAULT 5")
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 5")
            cursor.execute("""
                SELECT id, nombre, cantidad, precio, COALESCE(stock_min, stock_minimo, 5), tipo
                FROM productos 
                WHERE cantidad <= COALESCE(stock_min, stock_minimo, 5) AND activo = true AND tenant_id = %s
                ORDER BY (cantidad - COALESCE(stock_min, stock_minimo, 5)) ASC
            """, (tenant_id,))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos

def obtener_productos_por_vencer():
    """Obtiene productos próximos a vencer (en los próximos 30 días)"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            fecha_limite = datetime.now() + timedelta(days=30)
            cursor.execute("""
                SELECT id, nombre, fecha_vencimiento, cantidad, precio, tipo
                FROM productos 
                WHERE fecha_vencimiento IS NOT NULL 
                AND fecha_vencimiento <= %s 
                AND activo = true
                AND tenant_id = %s
                ORDER BY fecha_vencimiento ASC
            """, (fecha_limite, tenant_id))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos

def actualizar_stock_producto(producto_id, nueva_cantidad):
    """Actualiza el stock de un producto específico"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE productos 
                SET cantidad = %s
                WHERE id = %s AND tenant_id = %s
            """, (nueva_cantidad, producto_id, tenant_id))
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar stock: {e}")
        return False
    finally:
        conexion.close()

def reducir_stock_producto(producto_id, cantidad_vendida):
    """Reduce el stock de un producto después de una venta"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE productos 
                SET cantidad = cantidad - %s
                WHERE id = %s AND tenant_id = %s AND cantidad >= %s
            """, (cantidad_vendida, producto_id, tenant_id, cantidad_vendida))
            
            if cursor.rowcount == 0:
                return False
                
            conexion.commit()
            return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al reducir stock: {e}")
        return False
    finally:
        conexion.close()

def obtener_productos_tienda():
    """Obtiene productos disponibles para la tienda online (solo tipo venta)"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, tipo as descripcion, precio, cantidad, imagen, tipo
                FROM productos 
                WHERE tipo = 'venta'
                AND cantidad > 0 
                AND activo = true
                AND tenant_id = %s
                ORDER BY nombre
            """, (tenant_id,))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos

def obtener_productos_por_tipo(tipo):
    """Obtiene productos filtrados por tipo específico"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, tipo, cantidad, precio, COALESCE(precio_compra, 0), COALESCE(stock_min, 0),
                       fecha_vencimiento, codigo_barra, imagen, activo
                FROM productos 
                WHERE tipo = %s AND activo = true AND tenant_id = %s
                ORDER BY nombre
            """, (tipo, tenant_id))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos