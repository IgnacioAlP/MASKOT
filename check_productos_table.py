#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla productos
"""
import sys
sys.path.append('.')

from bd import obtener_conexion

def check_productos_table():
    print("=== VERIFICANDO ESTRUCTURA DE TABLA PRODUCTOS ===")
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Describir la tabla productos
        cursor.execute("DESCRIBE productos")
        columns = cursor.fetchall()
        
        print("Columnas encontradas en la tabla productos:")
        for column in columns:
            print(f"  {column}")
        
        # Verificar si existe la columna descripcion
        column_names = [col[0] for col in columns]
        if 'descripcion' in column_names:
            print("\n✅ La columna 'descripcion' SÍ existe")
        else:
            print("\n❌ La columna 'descripcion' NO existe")
            print("Columnas disponibles:", column_names)
        
        # Mostrar algunos registros de ejemplo
        cursor.execute("SELECT * FROM productos LIMIT 3")
        productos = cursor.fetchall()
        print(f"\nEjemplos de registros ({len(productos)} encontrados):")
        for producto in productos:
            print(f"  {producto}")
            
    except Exception as e:
        print(f"❌ Error al verificar tabla productos: {e}")
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    check_productos_table()