#!/usr/bin/env python3
"""
Script de prueba para verificar los tipos de datos que devuelven las funciones de clientes
"""
import sys
sys.path.append('.')

from controladores.clientes_controlador import obtener_todos_clientes, obtener_historial_completo, obtener_detalles_cliente

def test_tipos_datos():
    print("=== TESTING TIPOS DE DATOS ===")
    
    print("\n1. Probando obtener_todos_clientes():")
    try:
        clientes = obtener_todos_clientes()
        if clientes:
            for i, cliente in enumerate(clientes[:3]):  # Solo primeros 3
                print(f"Cliente {i+1}:")
                for j, campo in enumerate(cliente):
                    tipo = type(campo).__name__
                    print(f"  Campo {j}: {campo} (tipo: {tipo})")
                print()
        else:
            print("No hay clientes")
    except Exception as e:
        print(f"Error en obtener_todos_clientes(): {e}")
    
    print("\n2. Probando obtener_historial_completo():")
    try:
        historial = obtener_historial_completo()
        if historial:
            for i, cliente in enumerate(historial[:2]):  # Solo primeros 2
                print(f"Historial {i+1}:")
                for j, campo in enumerate(cliente):
                    tipo = type(campo).__name__
                    print(f"  Campo {j}: {campo} (tipo: {tipo})")
                print()
        else:
            print("No hay historial")
    except Exception as e:
        print(f"Error en obtener_historial_completo(): {e}")
    
    print("\n3. Probando obtener_detalles_cliente():")
    try:
        # Probar con el primer cliente disponible
        clientes = obtener_todos_clientes()
        if clientes:
            cliente_id = clientes[0][0]
            detalles = obtener_detalles_cliente(cliente_id=cliente_id)
            
            if detalles.get('cliente'):
                print("Información del cliente:")
                for j, campo in enumerate(detalles['cliente']):
                    tipo = type(campo).__name__
                    print(f"  Campo {j}: {campo} (tipo: {tipo})")
                
            if detalles.get('citas'):
                print("Primera cita:")
                cita = detalles['citas'][0]
                for j, campo in enumerate(cita):
                    tipo = type(campo).__name__
                    print(f"  Campo {j}: {campo} (tipo: {tipo})")
        else:
            print("No hay clientes para probar detalles")
    except Exception as e:
        print(f"Error en obtener_detalles_cliente(): {e}")

if __name__ == "__main__":
    test_tipos_datos()