"""
Script para probar la consulta de detalles de cita y verificar los índices
"""

import sys
sys.path.append('.')

from bd import obtener_conexion

def probar_consulta_detalle_cita(cita_id=3):
    """Prueba la consulta de detalles de cita"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        print(f"Probando consulta para cita ID: {cita_id}")
        print("=" * 50)
        
        # Primero, verificar que la cita existe
        cursor.execute("SELECT COUNT(*) FROM citas WHERE id = %s", (cita_id,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(f"❌ No existe una cita con ID {cita_id}")
            # Mostrar las citas disponibles
            cursor.execute("SELECT id, cliente_nombre, fecha FROM citas LIMIT 5")
            citas = cursor.fetchall()
            print("\nCitas disponibles:")
            for cita in citas:
                print(f"  - ID: {cita[0]}, Cliente: {cita[1]}, Fecha: {cita[2]}")
            return
        
        print(f"✅ Cita {cita_id} existe")
        
        # Consulta corregida
        cursor.execute("""
            SELECT 
                c.id,
                c.cliente_nombre,
                c.cliente_email,
                s.nombre as servicio_nombre,
                c.fecha,
                c.hora,
                c.estado,
                c.created_at,
                c.observaciones,
                c.mascota_nombre,
                c.mascota_especie,
                c.mascota_raza,
                c.mascota_edad,
                c.mascota_peso,
                c.cliente_telefono,
                c.precio_total
            FROM citas c
            LEFT JOIN servicios s ON c.servicio_id = s.id
            WHERE c.id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        
        if cita:
            print("✅ Consulta ejecutada exitosamente")
            print("\nDatos obtenidos:")
            print("-" * 30)
            
            campos = [
                'id', 'cliente_nombre', 'cliente_email', 'servicio_nombre',
                'fecha', 'hora', 'estado', 'created_at', 'observaciones',
                'mascota_nombre', 'mascota_especie', 'mascota_raza', 
                'mascota_edad', 'mascota_peso', 'cliente_telefono', 'precio_total'
            ]
            
            for i, valor in enumerate(cita):
                print(f"[{i}] {campos[i]}: {valor}")
            
            print("\n" + "=" * 50)
            print("VERIFICACIÓN DE ÍNDICES PARA TEMPLATE:")
            print("=" * 50)
            print(f"cita[0] (ID): {cita[0]}")
            print(f"cita[1] (Cliente): {cita[1]}")
            print(f"cita[2] (Email): {cita[2]}")
            print(f"cita[3] (Servicio): {cita[3]}")
            print(f"cita[4] (Fecha): {cita[4]}")
            print(f"cita[5] (Hora): {cita[5]}")
            print(f"cita[6] (Estado): {cita[6]}")
            print(f"cita[7] (Created_at): {cita[7]}")
            print(f"cita[8] (Observaciones): {cita[8]}")
            
            # Información de mascotas
            print("\nInformación de Mascotas:")
            print(f"cita[9] (Mascota nombre): {cita[9]}")
            print(f"cita[10] (Mascota especie): {cita[10]}")
            print(f"cita[11] (Mascota raza): {cita[11]}")
            print(f"cita[12] (Mascota edad): {cita[12]}")
            print(f"cita[13] (Mascota peso): {cita[13]}")
            
            print(f"\ncita[14] (Teléfono): {cita[14]}")
            print(f"cita[15] (Precio total): {cita[15]}")
            
        else:
            print("❌ No se obtuvieron datos de la consulta")
            
    except Exception as e:
        print(f"❌ Error en la consulta: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("PRUEBA DE CONSULTA DE DETALLES DE CITA")
    print("=" * 50)
    
    # Probar con diferentes IDs de cita
    for cita_id in [1, 2, 3]:
        probar_consulta_detalle_cita(cita_id)
        print("\n" + "=" * 70 + "\n")