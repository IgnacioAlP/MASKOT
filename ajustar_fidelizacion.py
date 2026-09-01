#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script directo para ajustar contadores de fidelización y generar alertas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bd import obtener_conexion
from datetime import datetime

def ajustar_contadores_fidelizacion():
    """Ajustar contadores directamente en la base de datos"""
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    try:
        # Obtener clientes de prueba
        cursor.execute("SELECT id, nombre, email FROM clientes WHERE nombre LIKE 'Cliente Prueba%'")
        clientes = cursor.fetchall()
        
        if len(clientes) < 2:
            print("No se encontraron suficientes clientes de prueba")
            return
        
        cliente_1 = clientes[0]  # 5 citas -> 10% descuento
        cliente_2 = clientes[1]  # 10 citas -> 20% descuento + reset
        
        print(f"Cliente 1: {cliente_1[1]} ({cliente_1[2]})")
        print(f"Cliente 2: {cliente_2[1]} ({cliente_2[2]})")
        
        # Limpiar registros existentes
        cursor.execute("DELETE FROM fidelizacion WHERE cliente_email IN (%s, %s)", (cliente_1[2], cliente_2[2]))
        cursor.execute("DELETE FROM fidelizacion_historial WHERE cliente_email IN (%s, %s)", (cliente_1[2], cliente_2[2]))
        
        # Insertar cliente 1 con 5 citas (activará alerta de 10%)
        cursor.execute("""
            INSERT INTO fidelizacion (cliente_email, cliente_nombre, contador, fecha_inicio)
            VALUES (%s, %s, %s, %s)
        """, (cliente_1[2], cliente_1[1], 5, datetime.now()))
        
        # Insertar cliente 2 con 10 citas (activará alerta de 20% y reset)
        cursor.execute("""
            INSERT INTO fidelizacion (cliente_email, cliente_nombre, contador, fecha_inicio)
            VALUES (%s, %s, %s, %s)
        """, (cliente_2[2], cliente_2[1], 10, datetime.now()))
        
        # Generar alertas en el historial
        # Para cliente 1 (5 citas = 10% descuento)
        cursor.execute("""
            INSERT INTO fidelizacion_historial (cliente_email, evento, descripcion, created_at)
            VALUES (%s, %s, %s, %s)
        """, (
            cliente_1[2], 
            'descuento_10', 
            f'¡{cliente_1[1]} ha completado 5 citas! Descuento del 10% disponible.',
            datetime.now()
        ))
        
        # Para cliente 2 (10 citas = 20% descuento + reset)
        cursor.execute("""
            INSERT INTO fidelizacion_historial (cliente_email, evento, descripcion, created_at)
            VALUES (%s, %s, %s, %s)
        """, (
            cliente_2[2], 
            'descuento_20', 
            f'¡{cliente_2[1]} ha completado 10 citas! Descuento del 20% disponible. Contador reseteado.',
            datetime.now()
        ))
        
        # Reset del contador para cliente 2 (simulando el reset automático)
        cursor.execute("UPDATE fidelizacion SET contador = 0 WHERE cliente_email = %s", (cliente_2[2],))
        
        conn.commit()
        
        print("\n✅ Contadores ajustados exitosamente!")
        print("- Cliente 1: 5 citas → Alerta de 10% descuento")
        print("- Cliente 2: 10 citas → Alerta de 20% descuento + reset a 0")
        
        # Verificar estado final
        cursor.execute("SELECT cliente_email, cliente_nombre, contador FROM fidelizacion")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]} citas")
        
        print("\nAhora puedes ver las alertas en el dashboard!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    ajustar_contadores_fidelizacion()