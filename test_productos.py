#!/usr/bin/env python3
"""
Script para probar el controlador de productos corregido
"""
import sys
sys.path.append('.')

try:
    from controladores.productos_controlador import obtener_productos_mas_vendidos
    
    print("=== PROBANDO CONTROLADOR DE PRODUCTOS ===")
    
    productos = obtener_productos_mas_vendidos(4)
    print(f"✅ Productos más vendidos obtenidos: {len(productos)}")
    
    for i, producto in enumerate(productos, 1):
        print(f"  {i}. {producto[1]} - Stock: {producto[4]} - Tipo: {producto[6]}")
    
    print("\n✅ Controlador de productos funciona correctamente")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()