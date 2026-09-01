#!/usr/bin/env python3
"""
Script para agregar datos de ejemplo a las tablas existentes
"""

from bd import obtener_conexion

def agregar_datos_para_recibo():
    """Agrega datos a las tablas existentes para poder generar recibos"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        print("🔧 Agregando datos para recibos...")
        
        # Obtener una cita de prueba
        cursor.execute("SELECT id FROM citas WHERE estado = 'completada' LIMIT 1")
        cita_result = cursor.fetchone()
        
        if not cita_result:
            # Si no hay citas completadas, usar cualquier cita
            cursor.execute("SELECT id FROM citas LIMIT 1")
            cita_result = cursor.fetchone()
            
            if cita_result:
                # Marcar como completada para poder generar recibo
                cursor.execute("UPDATE citas SET estado = 'completada' WHERE id = %s", (cita_result[0],))
                print(f"🔄 Cita {cita_result[0]} marcada como completada")
        
        if not cita_result:
            print("⚠️ No hay citas disponibles")
            return False
            
        cita_id = cita_result[0]
        print(f"📋 Usando cita ID: {cita_id}")
        
        # Verificar si hay servicios
        cursor.execute("SELECT COUNT(*) FROM servicios")
        servicios_count = cursor.fetchone()[0]
        
        if servicios_count == 0:
            # Crear algunos servicios de ejemplo
            cursor.execute("""
                INSERT INTO servicios (nombre, descripcion, precio) VALUES
                ('Consulta General', 'Consulta veterinaria básica', 50.00),
                ('Vacunación', 'Aplicación de vacunas', 30.00),
                ('Baño y Corte', 'Servicio de grooming completo', 40.00)
            """)
            print("💉 Servicios de ejemplo creados")
        
        # Verificar si ya hay datos de mascotas para esta cita
        cursor.execute("SELECT COUNT(*) FROM citas_mascotas WHERE cita_id = %s", (cita_id,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Agregar una mascota de ejemplo
            cursor.execute("""
                INSERT INTO citas_mascotas (cita_id, nombre, especie, raza, edad, peso)
                VALUES (%s, 'Firulais', 'perro', 'Labrador', 3, 25.5)
            """, (cita_id,))
            print("🐕 Mascota de ejemplo agregada a citas_mascotas")
        
        # Agregar servicio a la cita
        cursor.execute("SELECT COUNT(*) FROM citas_servicios WHERE cita_id = %s", (cita_id,))
        servicios_cita_count = cursor.fetchone()[0]
        
        if servicios_cita_count == 0:
            cursor.execute("SELECT id FROM servicios LIMIT 1")
            servicio_result = cursor.fetchone()
            if servicio_result:
                cursor.execute("""
                    INSERT INTO citas_servicios (cita_id, servicio_id)
                    VALUES (%s, %s)
                """, (cita_id, servicio_result[0]))
                print("🛠️ Servicio vinculado a la cita en citas_servicios")
        
        conexion.commit()
        print("✅ Datos para recibo creados exitosamente")
        print(f"🎯 Ahora puedes generar el recibo para la cita ID: {cita_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("🚀 Configurando datos para recibos...")
    agregar_datos_para_recibo()