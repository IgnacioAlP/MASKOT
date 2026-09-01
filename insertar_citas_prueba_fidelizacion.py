#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para insertar citas de prueba para demostrar el programa de fidelización
Cliente 1: 5 citas (activará alerta de 10% descuento)
Cliente 2: 10 citas (activará alerta de 20% descuento y reset del contador)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bd import obtener_conexion
from datetime import datetime, timedelta
import random

def crear_citas_prueba():
    """Crear citas de prueba para demostrar la funcionalidad de fidelización"""
    
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existen clientes de prueba
        cursor.execute("SELECT id, nombre FROM clientes WHERE nombre LIKE 'Cliente Prueba%' ORDER BY id LIMIT 2")
        clientes_existentes = cursor.fetchall()
        
        if len(clientes_existentes) < 2:
            print("Creando clientes de prueba...")
            
            # Crear clientes de prueba si no existen
            clientes_datos = [
                ('Cliente Prueba Fidelidad 1', '999111000', 'cliente1@prueba.com', 'Av. Prueba 123'),
                ('Cliente Prueba Fidelidad 2', '999222000', 'cliente2@prueba.com', 'Av. Prueba 456')
            ]
            
            for nombre, telefono, email, direccion in clientes_datos:
                cursor.execute("""
                    INSERT INTO clientes (nombre, telefono, email, direccion, fecha_registro)
                    VALUES (%s, %s, %s, %s, %s)
                """, (nombre, telefono, email, direccion, datetime.now()))
            
            conn.commit()
            
            # Obtener los IDs de los clientes recién creados
            cursor.execute("SELECT id, nombre FROM clientes WHERE nombre LIKE 'Cliente Prueba%' ORDER BY id ASC LIMIT 2")
            clientes_existentes = cursor.fetchall()
        
        cliente_1_id, cliente_1_nombre = clientes_existentes[0]
        cliente_2_id, cliente_2_nombre = clientes_existentes[1]
        
        print(f"Cliente 1: {cliente_1_nombre} (ID: {cliente_1_id})")
        print(f"Cliente 2: {cliente_2_nombre} (ID: {cliente_2_id})")
        
        # Verificar servicios disponibles
        cursor.execute("SELECT id, nombre FROM servicios LIMIT 5")
        servicios = cursor.fetchall()
        
        if not servicios:
            print("No hay servicios disponibles. Creando servicio de prueba...")
            cursor.execute("""
                INSERT INTO servicios (nombre, precio, descripcion)
                VALUES ('Consulta General', 50.00, 'Consulta veterinaria general')
            """)
            conn.commit()
            
            cursor.execute("SELECT id, nombre FROM servicios LIMIT 1")
            servicios = cursor.fetchall()
        
        servicio_id = servicios[0][0]
        servicio_nombre = servicios[0][1]
        print(f"Usando servicio: {servicio_nombre} (ID: {servicio_id})")
        
        # Limpiar citas existentes de estos clientes para empezar desde cero
        print("Limpiando citas existentes de clientes de prueba...")
        cursor.execute("DELETE FROM citas WHERE cliente_id IN (%s, %s)", (cliente_1_id, cliente_2_id))
        
        # Para fidelización, necesitamos usar email en lugar de cliente_id
        cursor.execute("SELECT email FROM clientes WHERE id = %s", (cliente_1_id,))
        cliente_1_email = cursor.fetchone()[0]
        cursor.execute("SELECT email FROM clientes WHERE id = %s", (cliente_2_id,))
        cliente_2_email = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM fidelizacion WHERE cliente_email IN (%s, %s)", (cliente_1_email, cliente_2_email))
        cursor.execute("DELETE FROM fidelizacion_historial WHERE cliente_email IN (%s, %s)", (cliente_1_email, cliente_2_email))
        conn.commit()
        
        # Crear 5 citas para el cliente 1
        print(f"\nCreando 5 citas para {cliente_1_nombre}...")
        fecha_base = datetime.now() - timedelta(days=30)
        
        for i in range(5):
            fecha_cita = fecha_base + timedelta(days=i*6)  # Una cita cada 6 días
            
            cursor.execute("""
                INSERT INTO citas (cliente_id, servicio_id, fecha, hora, estado, observaciones)
                VALUES (%s, %s, %s, %s, 'completada', %s)
            """, (
                cliente_1_id,
                servicio_id,
                fecha_cita.date(),
                '10:00',
                f'Cita de prueba #{i+1} para programa de fidelización'
            ))
            
            print(f"  - Cita {i+1}: {fecha_cita.strftime('%Y-%m-%d')} a las 10:00")
        
        # Crear 10 citas para el cliente 2
        print(f"\nCreando 10 citas para {cliente_2_nombre}...")
        
        for i in range(10):
            fecha_cita = fecha_base + timedelta(days=i*3)  # Una cita cada 3 días
            
            cursor.execute("""
                INSERT INTO citas (cliente_id, servicio_id, fecha, hora, estado, observaciones)
                VALUES (%s, %s, %s, %s, 'completada', %s)
            """, (
                cliente_2_id,
                servicio_id,
                fecha_cita.date(),
                '14:00',
                f'Cita de prueba #{i+1} para programa de fidelización'
            ))
            
            print(f"  - Cita {i+1}: {fecha_cita.strftime('%Y-%m-%d')} a las 14:00")
        
        conn.commit()
        
        # Procesar fidelización para ambos clientes
        print("\nProcesando programa de fidelización...")
        
        # Importar y usar el controlador de fidelización
        from controladores.fidelizacion_controlador import procesar_fidelizacion_para_cliente
        
        # Procesar cada cita del cliente 1
        print(f"Procesando {cliente_1_nombre}...")
        for i in range(5):
            resultado = procesar_fidelizacion_para_cliente(cliente_1_nombre, cliente_1_email)
            print(f"  Cita {i+1}: {resultado.get('contador', 0)} citas totales")
        
        # Procesar cada cita del cliente 2
        print(f"Procesando {cliente_2_nombre}...")
        for i in range(10):
            resultado = procesar_fidelizacion_para_cliente(cliente_2_nombre, cliente_2_email)
            print(f"  Cita {i+1}: {resultado.get('contador', 0)} citas totales")
            if resultado.get('alertas'):
                for alerta in resultado['alertas']:
                    print(f"    ⚠️ ALERTA: {alerta['mensaje']}")
        
        # Obtener resultado final
        resultado_cliente_1 = procesar_fidelizacion_para_cliente(cliente_1_nombre, cliente_1_email, enviar_automatico=False)
        resultado_cliente_2 = procesar_fidelizacion_para_cliente(cliente_2_nombre, cliente_2_email, enviar_automatico=False)
        
        print(f"\nResultado Cliente 1 ({cliente_1_nombre}):")
        print(f"  - Total citas: {resultado_cliente_1.get('total_citas', 0)}")
        print(f"  - Alertas generadas: {len(resultado_cliente_1.get('alertas', []))}")
        for alerta in resultado_cliente_1.get('alertas', []):
            print(f"    * {alerta['mensaje']}")
        
        print(f"\nResultado Cliente 2 ({cliente_2_nombre}):")
        print(f"  - Total citas: {resultado_cliente_2.get('total_citas', 0)}")
        print(f"  - Alertas generadas: {len(resultado_cliente_2.get('alertas', []))}")
        for alerta in resultado_cliente_2.get('alertas', []):
            print(f"    * {alerta['mensaje']}")
        
        # Mostrar estado de fidelización
        print("\nEstado actual de fidelización:")
        cursor.execute("""
            SELECT cliente_email, contador, fecha_inicio
            FROM fidelizacion 
            WHERE cliente_email IN (%s, %s)
        """, (cliente_1_email, cliente_2_email))
        
        for row in cursor.fetchall():
            email, contador, fecha = row
            nombre_cliente = cliente_1_nombre if email == cliente_1_email else cliente_2_nombre
            print(f"  - {nombre_cliente}: {contador} citas completadas")
        
        print("\n✅ Citas de prueba creadas exitosamente!")
        print("Ahora puedes ir al dashboard para ver las alertas de fidelización.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    crear_citas_prueba()