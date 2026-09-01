#!/usr/bin/env python3
"""
Script para agregar citas de prueba con diferentes estados
"""

from bd import obtener_conexion
from datetime import date, time

def agregar_citas_prueba():
    """Agrega citas de prueba con diferentes estados"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        print("🔧 Agregando citas de prueba...")
        
        hoy = date.today()
        
        # Citas de prueba con diferentes estados
        citas_prueba = [
            ("Juan Pérez", "juan@email.com", hoy, "09:00:00", "pendiente"),
            ("María González", "maria@email.com", hoy, "10:00:00", "confirmada"),
            ("Carlos López", "carlos@email.com", hoy, "11:00:00", "en_progreso"),
            ("Ana Silva", "ana@email.com", hoy, "12:00:00", "completada"),
            ("Luis García", "luis@email.com", hoy, "13:00:00", "cancelada"),
        ]
        
        for nombre, email, fecha, hora, estado in citas_prueba:
            cursor.execute("""
                INSERT INTO citas (cliente_nombre, cliente_email, fecha, hora, estado, observaciones)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, email, fecha, hora, estado, f"Cita de prueba - Estado: {estado}"))
            print(f"✅ Cita agregada: {nombre} - {estado}")
        
        conexion.commit()
        
        print(f"\n🎉 Se agregaron {len(citas_prueba)} citas de prueba para hoy ({hoy})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al agregar citas: {e}")
        return False
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("🚀 Agregando citas de prueba...")
    agregar_citas_prueba()