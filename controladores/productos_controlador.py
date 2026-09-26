from bd import obtener_conexion, obtener_tenant_id
import os
from datetime import datetime, timedelta

def obtener_productos():
    """Obtiene todos los productos del inventario"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    productos = []
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, tipo, cantidad, precio, COALESCE(precio_compra, 0), stock_min,
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
            cursor.execute("""
                SELECT p.id, p.nombre, p.tipo, p.cantidad, p.precio, COALESCE(p.precio_compra, 0), p.stock_min,
                       p.fecha_vencimiento, p.imagen, p.activo
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
            cursor.execute("""
                SELECT id, nombre, tipo, cantidad, precio, COALESCE(precio_compra, 0), stock_min,
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
            cursor.execute("""
                SELECT id, nombre, codigo_barra, tipo, cantidad, precio, COALESCE(precio_compra, 0), stock_min,
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
            termino = f"%{query.strip()}%" if query else "%"
            cursor.execute("""
                SELECT id, nombre, codigo_barra, tipo, cantidad, precio, COALESCE(precio_compra, 0), stock_min, imagen
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


def insertar_producto(nombre, tipo='stock', cantidad=0, precio=0.00, stock_min=0,
                      fecha_vencimiento=None, imagen=None, codigo_barra=None, precio_compra=None):
    """Inserta un nuevo producto en el inventario"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        if precio_compra is None:
            precio_compra = precio
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO productos (nombre, codigo_barra, tipo, cantidad, precio, precio_compra, stock_min,
                                     fecha_vencimiento, imagen, activo, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s)
                RETURNING id
            """, (nombre, codigo_barra or None, tipo, cantidad, precio, precio_compra, stock_min,
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
                        stock_min=0, fecha_vencimiento=None, codigo_barra=None, precio_compra=None):
    """Actualiza un producto existente"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        if precio_compra is None:
            precio_compra = precio
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE productos 
                SET nombre = %s, tipo = %s, cantidad = %s, precio = %s,
                    precio_compra = %s, stock_min = %s, fecha_vencimiento = %s, codigo_barra = %s
                WHERE id = %s AND tenant_id = %s
            """, (nombre, tipo, cantidad, precio, precio_compra, stock_min, fecha_vencimiento, codigo_barra or None, producto_id, tenant_id))
            conexion.commit()
            return True
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
            cursor.execute("""
                SELECT id, nombre, cantidad, precio, stock_min, tipo
                FROM productos 
                WHERE cantidad <= stock_min AND activo = true AND tenant_id = %s
                ORDER BY (cantidad - stock_min) ASC
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
                SELECT id, nombre, tipo, cantidad, precio, COALESCE(precio_compra, 0), stock_min,
                       fecha_vencimiento, codigo_barra, imagen, activo
                FROM productos 
                WHERE tipo = %s AND activo = true AND tenant_id = %s
                ORDER BY nombre
            """, (tipo, tenant_id))
            productos = cursor.fetchall()
    finally:
        conexion.close()
    return productos