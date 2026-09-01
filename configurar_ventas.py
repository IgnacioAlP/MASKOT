#!/usr/bin/env python3
"""
Script para configurar la tabla de ventas en tienda
Este script crea la tabla de ventas con soporte para múltiples métodos de pago
"""

import mysql.connector
from datetime import datetime
import json

def conectar_bd():
    """Conecta a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='veterinaria',
            user='root',
            password='',
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def crear_tabla_ventas():
    """Crea la tabla de ventas si no existe"""
    connection = conectar_bd()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # SQL para crear tabla de ventas
        create_table_query = """
        CREATE TABLE IF NOT EXISTS ventas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            numero_venta VARCHAR(20) UNIQUE NOT NULL,
            vendedor_id INT NOT NULL,
            vendedor_nombre VARCHAR(100) NOT NULL,
            cliente_nombre VARCHAR(100) DEFAULT 'Cliente General',
            cliente_documento VARCHAR(20) DEFAULT NULL,
            productos JSON NOT NULL,
            subtotal DECIMAL(10,2) NOT NULL,
            igv DECIMAL(10,2) NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            metodo_pago ENUM('efectivo', 'tarjeta', 'yape') NOT NULL,
            monto_recibido DECIMAL(10,2) DEFAULT NULL,
            cambio_entregado DECIMAL(10,2) DEFAULT 0.00,
            referencia_pago VARCHAR(100) DEFAULT NULL,
            estado ENUM('completada', 'cancelada', 'pendiente') DEFAULT 'completada',
            notas TEXT DEFAULT NULL,
            fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            INDEX idx_fecha_venta (fecha_venta),
            INDEX idx_vendedor (vendedor_id),
            INDEX idx_metodo_pago (metodo_pago),
            INDEX idx_estado (estado),
            INDEX idx_numero_venta (numero_venta),
            
            FOREIGN KEY (vendedor_id) REFERENCES usuarios(id) ON DELETE RESTRICT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        print("✅ Tabla 'ventas' creada exitosamente")
        
        # Verificar estructura de la tabla
        cursor.execute("DESCRIBE ventas")
        columns = cursor.fetchall()
        print("\n📋 Estructura de la tabla 'ventas':")
        for column in columns:
            print(f"  - {column[0]}: {column[1]}")
            
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Error creando tabla ventas: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def generar_numero_venta():
    """Genera un número de venta único"""
    now = datetime.now()
    return f"V{now.strftime('%Y%m%d')}{now.strftime('%H%M%S')}"

def insertar_datos_prueba():
    """Inserta datos de prueba en la tabla de ventas"""
    connection = conectar_bd()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Obtener un usuario existente para usar como vendedor
        cursor.execute("SELECT id, username FROM usuarios WHERE rol IN ('admin', 'empleado', 'dueño') LIMIT 1")
        vendedor = cursor.fetchone()
        
        if not vendedor:
            print("❌ No se encontró ningún usuario para usar como vendedor")
            return False
        
        vendedor_id, vendedor_nombre = vendedor
        
        # Obtener algunos productos para la venta de prueba
        cursor.execute("SELECT id, nombre, precio FROM productos WHERE activo = 1 LIMIT 3")
        productos_disponibles = cursor.fetchall()
        
        if not productos_disponibles:
            print("❌ No se encontraron productos activos para la venta de prueba")
            return False
        
        # Crear venta de prueba con efectivo
        productos_venta = []
        subtotal = 0
        
        for i, (prod_id, nombre, precio) in enumerate(productos_disponibles):
            cantidad = i + 1  # 1, 2, 3 productos respectivamente
            total_producto = float(precio) * cantidad
            subtotal += total_producto
            
            productos_venta.append({
                'id': prod_id,
                'nombre': nombre,
                'precio': float(precio),
                'cantidad': cantidad,
                'total': total_producto
            })
        
        igv = round(subtotal * 0.18, 2)
        total = round(subtotal + igv, 2)
        
        # Venta en efectivo
        numero_venta_efectivo = generar_numero_venta()
        monto_recibido = total + 10  # Cliente paga con 10 soles más
        cambio = monto_recibido - total
        
        insert_venta_efectivo = """
        INSERT INTO ventas (
            numero_venta, vendedor_id, vendedor_nombre, cliente_nombre,
            productos, subtotal, igv, total, metodo_pago,
            monto_recibido, cambio_entregado, estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_venta_efectivo, (
            numero_venta_efectivo, vendedor_id, vendedor_nombre, 'Ana García',
            json.dumps(productos_venta), subtotal, igv, total, 'efectivo',
            monto_recibido, cambio, 'completada'
        ))
        
        # Venta con tarjeta
        numero_venta_tarjeta = generar_numero_venta() + "T"
        
        insert_venta_tarjeta = """
        INSERT INTO ventas (
            numero_venta, vendedor_id, vendedor_nombre, cliente_nombre,
            productos, subtotal, igv, total, metodo_pago,
            referencia_pago, estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_venta_tarjeta, (
            numero_venta_tarjeta, vendedor_id, vendedor_nombre, 'Carlos Mendoza',
            json.dumps(productos_venta), subtotal, igv, total, 'tarjeta',
            'VISA ***1234 - Auth: 123456', 'completada'
        ))
        
        # Venta con Yape
        numero_venta_yape = generar_numero_venta() + "Y"
        
        insert_venta_yape = """
        INSERT INTO ventas (
            numero_venta, vendedor_id, vendedor_nombre, cliente_nombre,
            productos, subtotal, igv, total, metodo_pago,
            referencia_pago, estado
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_venta_yape, (
            numero_venta_yape, vendedor_id, vendedor_nombre, 'María López',
            json.dumps(productos_venta), subtotal, igv, total, 'yape',
            'Yape - Op: 987654321', 'completada'
        ))
        
        connection.commit()
        print(f"✅ Datos de prueba insertados exitosamente")
        print(f"   - Venta efectivo: {numero_venta_efectivo}")
        print(f"   - Venta tarjeta: {numero_venta_tarjeta}")
        print(f"   - Venta yape: {numero_venta_yape}")
        print(f"   - Vendedor: {vendedor_nombre}")
        print(f"   - Total por venta: S/ {total}")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Error insertando datos de prueba: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def verificar_tabla():
    """Verifica que la tabla se haya creado correctamente"""
    connection = conectar_bd()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM ventas")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total de ventas en la tabla: {count}")
        
        # Mostrar últimas ventas
        cursor.execute("""
        SELECT numero_venta, vendedor_nombre, cliente_nombre, 
               total, metodo_pago, fecha_venta 
        FROM ventas 
        ORDER BY fecha_venta DESC 
        LIMIT 5
        """)
        
        ventas = cursor.fetchall()
        print("\n🧾 Últimas ventas registradas:")
        for venta in ventas:
            numero, vendedor, cliente, total, metodo, fecha = venta
            print(f"  - {numero}: {cliente} - S/ {total} ({metodo}) - {vendedor}")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Error verificando tabla: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def main():
    """Función principal"""
    print("🚀 Configurando sistema de ventas en tienda...")
    print("=" * 60)
    
    # Crear tabla
    if crear_tabla_ventas():
        print("\n🎯 Insertando datos de prueba...")
        if insertar_datos_prueba():
            print("\n🔍 Verificando configuración...")
            verificar_tabla()
            print("\n✅ ¡Sistema de ventas configurado correctamente!")
            print("\n📋 Próximos pasos:")
            print("   1. Ejecutar el servidor Flask")
            print("   2. Ir a 'Ventas' en el menú principal") 
            print("   3. Realizar una venta de prueba")
            print("   4. Imprimir ticket en impresora térmica")
        else:
            print("\n❌ Error insertando datos de prueba")
    else:
        print("\n❌ Error creando tabla de ventas")

if __name__ == "__main__":
    main()