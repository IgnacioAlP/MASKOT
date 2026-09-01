#!/usr/bin/env python3
"""
Script para actualizar los estados de las citas en la base de datos
"""

from bd import obtener_conexion

def actualizar_estados_citas():
    """Actualiza los estados disponibles en la tabla citas"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        print("🔧 Actualizando estados de la tabla citas...")
        
        # Actualizar el enum de estados
        cursor.execute("""
            ALTER TABLE `citas` 
            MODIFY `estado` enum('pendiente','confirmada','en_progreso','completada','cancelada') 
            DEFAULT 'pendiente'
        """)
        
        conexion.commit()
        
        print("✅ Estados actualizados exitosamente!")
        print("Estados disponibles: pendiente, confirmada, en_progreso, completada, cancelada")
        
        # Verificar la estructura
        cursor.execute("DESCRIBE citas")
        columns = cursor.fetchall()
        
        for column in columns:
            if column[0] == 'estado':
                print(f"📋 Campo estado: {column[1]}")
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Error al actualizar estados: {e}")
        return False
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("🚀 Actualizando estructura de base de datos...")
    actualizar_estados_citas()