"""
Script de prueba para el módulo de ventas en tienda
Crea datos de prueba y valida el funcionamiento del sistema
"""

import sys
import os
sys.path.append('c:/Users/alonz/OneDrive/Documents/VETERINARIA')

from controladores import ventas_controlador
from bd import obtener_conexion
import json
from datetime import datetime

def probar_sistema_ventas():
    """Prueba completa del sistema de ventas"""
    print("=== PROBANDO SISTEMA DE VENTAS ===")
    
    try:
        # 1. Probar obtener productos para venta
        print("\n1. Obteniendo productos disponibles para venta...")
        productos = ventas_controlador.obtener_productos_venta()
        print(f"✅ Productos encontrados: {len(productos)}")
        
        if productos:
            print("   Primeros 3 productos:")
            for i, producto in enumerate(productos[:3]):
                print(f"   - {producto[1]}: S/ {producto[2]} (Stock: {producto[3]})")
        
        # 2. Crear venta de prueba
        print("\n2. Creando venta de prueba...")
        
        if not productos:
            print("❌ No hay productos disponibles para crear venta de prueba")
            return
        
        # Usar el primer producto disponible
        producto_prueba = productos[0]
        
        datos_venta = {
            'productos': [
                {
                    'id': producto_prueba[0],
                    'nombre': producto_prueba[1],
                    'precio': float(producto_prueba[2]),
                    'cantidad': 2
                }
            ],
            'subtotal': float(producto_prueba[2]) * 2,
            'igv': (float(producto_prueba[2]) * 2) * 0.18,
            'total': (float(producto_prueba[2]) * 2) * 1.18,
            'metodo_pago': 'efectivo',
            'monto_recibido': 100.00,
            'cambio': 100.00 - ((float(producto_prueba[2]) * 2) * 1.18),
            'vendedor_id': 7  # admin_maskot
        }
        
        resultado = ventas_controlador.procesar_venta(datos_venta)
        
        if resultado['success']:
            print(f"✅ Venta creada exitosamente: {resultado['numero_venta']}")
            venta_id = resultado['venta_id']
            
            # 3. Probar obtener detalle de venta
            print("\n3. Obteniendo detalle de la venta...")
            detalle = ventas_controlador.obtener_detalle_venta(venta_id)
            
            if detalle:
                print(f"✅ Detalle obtenido:")
                print(f"   - Número: {detalle['numero_venta']}")
                print(f"   - Total: S/ {detalle['total']:.2f}")
                print(f"   - Método de pago: {detalle['metodo_pago']}")
                print(f"   - Productos: {len(detalle['productos'])}")
                print(f"   - Vendedor: {detalle['vendedor_nombre']}")
            else:
                print("❌ No se pudo obtener el detalle de la venta")
        else:
            print(f"❌ Error al crear venta: {resultado.get('error', 'Error desconocido')}")
        
        print("\n=== PRUEBA COMPLETADA ===")
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    probar_sistema_ventas()