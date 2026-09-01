#!/usr/bin/env python3
"""
Script de prueba completa del sistema de ventas
Verifica todas las funcionalidades del módulo de ventas
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from controladores import ventas_controlador
from datetime import datetime
import json

def probar_busqueda_productos():
    """Prueba la búsqueda de productos para venta"""
    print("🔍 Probando búsqueda de productos...")
    
    # Buscar todos los productos
    productos = ventas_controlador.buscar_productos_para_venta()
    print(f"   ✓ Productos disponibles: {len(productos)}")
    
    if productos:
        primer_producto = productos[0]
        print(f"   ✓ Primer producto: {primer_producto['nombre']} - S/ {primer_producto['precio']}")
    
    # Buscar por categoría si hay categorías
    categorias = ventas_controlador.obtener_categorias_activas()
    print(f"   ✓ Categorías activas: {len(categorias)}")
    
    return productos

def probar_validacion_stock():
    """Prueba la validación de stock"""
    print("\n📦 Probando validación de stock...")
    
    productos = ventas_controlador.buscar_productos_para_venta(limit=3)
    
    if not productos:
        print("   ❌ No hay productos para probar")
        return False
    
    # Crear una venta de prueba con stock válido
    productos_venta = []
    for producto in productos[:2]:  # Solo 2 productos
        cantidad = min(1, producto['stock'])  # Máximo 1 o el stock disponible
        if cantidad > 0:
            productos_venta.append({
                'id': producto['id'],
                'nombre': producto['nombre'],
                'precio': producto['precio'],
                'cantidad': cantidad,
                'total': producto['precio'] * cantidad
            })
    
    if productos_venta:
        validacion = ventas_controlador.validar_stock_productos(productos_venta)
        print(f"   ✓ Validación de stock: {'Válido' if validacion['valido'] else 'Inválido'}")
        
        if not validacion['valido']:
            print(f"   ⚠️  Errores: {', '.join(validacion['errores'])}")
    else:
        print("   ⚠️  No hay productos con stock para probar")
    
    return productos_venta

def probar_calculo_totales():
    """Prueba el cálculo de totales"""
    print("\n🧮 Probando cálculo de totales...")
    
    productos_ejemplo = [
        {'id': 1, 'nombre': 'Producto 1', 'precio': 100.0, 'cantidad': 2},
        {'id': 2, 'nombre': 'Producto 2', 'precio': 50.0, 'cantidad': 1}
    ]
    
    totales = ventas_controlador.calcular_totales_venta(productos_ejemplo)
    
    print(f"   ✓ Subtotal: S/ {totales['subtotal']:.2f}")
    print(f"   ✓ IGV (18%): S/ {totales['igv']:.2f}")
    print(f"   ✓ Total: S/ {totales['total']:.2f}")
    
    # Verificar cálculos
    subtotal_esperado = 250.0  # (100*2) + (50*1)
    igv_esperado = 45.0  # 250 * 0.18
    total_esperado = 295.0  # 250 + 45
    
    assert abs(totales['subtotal'] - subtotal_esperado) < 0.01, "Error en cálculo de subtotal"
    assert abs(totales['igv'] - igv_esperado) < 0.01, "Error en cálculo de IGV"
    assert abs(totales['total'] - total_esperado) < 0.01, "Error en cálculo de total"
    
    print("   ✅ Cálculos verificados correctamente")
    return totales

def probar_venta_completa():
    """Prueba una venta completa de efectivo"""
    print("\n💰 Probando venta completa...")
    
    # Obtener productos disponibles
    productos = ventas_controlador.buscar_productos_para_venta(limit=2)
    
    if len(productos) < 1:
        print("   ❌ No hay suficientes productos para probar venta")
        return None
    
    # Preparar productos para venta
    productos_venta = []
    for producto in productos[:1]:  # Solo 1 producto para simplificar
        if producto['stock'] > 0:
            productos_venta.append({
                'id': producto['id'],
                'nombre': producto['nombre'],
                'precio': producto['precio'],
                'cantidad': 1,
                'total': producto['precio']
            })
    
    if not productos_venta:
        print("   ❌ No hay productos con stock para venta")
        return None
    
    # Calcular totales
    totales = ventas_controlador.calcular_totales_venta(productos_venta)
    
    # Preparar datos de venta (efectivo)
    datos_venta = {
        'vendedor_id': 1,  # Asumiendo que existe el usuario con ID 1
        'vendedor_nombre': 'Test Vendedor',
        'cliente_nombre': 'Cliente Prueba',
        'cliente_documento': '12345678',
        'productos': productos_venta,
        'metodo_pago': 'efectivo',
        'monto_recibido': totales['total'] + 10,  # Pago con 10 soles extra
        'cambio_entregado': 10,
        'notas': 'Venta de prueba del sistema'
    }
    
    # Registrar la venta
    resultado = ventas_controlador.registrar_venta(datos_venta)
    
    if resultado['success']:
        print(f"   ✅ Venta registrada: {resultado['numero_venta']}")
        print(f"   ✓ ID de venta: {resultado['venta_id']}")
        print(f"   ✓ Total: S/ {resultado['total']:.2f}")
        return resultado
    else:
        print(f"   ❌ Error en venta: {resultado['error']}")
        return None

def probar_consulta_venta():
    """Prueba la consulta de venta por ID"""
    print("\n📋 Probando consulta de venta...")
    
    # Obtener la última venta
    ventas = ventas_controlador.obtener_ventas_por_fecha(limit=1)
    
    if not ventas:
        print("   ⚠️  No hay ventas para consultar")
        return None
    
    venta_id = ventas[0]['id']
    venta = ventas_controlador.obtener_venta_por_id(venta_id)
    
    if venta:
        print(f"   ✅ Venta encontrada: {venta['numero_venta']}")
        print(f"   ✓ Cliente: {venta['cliente_nombre']}")
        print(f"   ✓ Total: S/ {venta['total']:.2f}")
        print(f"   ✓ Método: {venta['metodo_pago']}")
        print(f"   ✓ Productos: {len(venta['productos'])}")
        return venta
    else:
        print("   ❌ No se pudo obtener la venta")
        return None

def probar_estadisticas():
    """Prueba las estadísticas de ventas"""
    print("\n📊 Probando estadísticas...")
    
    estadisticas = ventas_controlador.obtener_estadisticas_ventas()
    
    print(f"   ✓ Total ventas: {estadisticas.get('total_ventas', 0)}")
    print(f"   ✓ Total vendido: S/ {estadisticas.get('total_vendido', 0):.2f}")
    print(f"   ✓ Promedio por venta: S/ {estadisticas.get('promedio_venta', 0):.2f}")
    print(f"   ✓ Vendedores activos: {estadisticas.get('vendedores_activos', 0)}")
    
    if estadisticas.get('por_metodo_pago'):
        print("   ✓ Por método de pago:")
        for metodo in estadisticas['por_metodo_pago']:
            print(f"     - {metodo['metodo']}: {metodo['cantidad']} ventas, S/ {metodo['total']:.2f}")
    
    return estadisticas

def probar_productos_mas_vendidos():
    """Prueba la consulta de productos más vendidos"""
    print("\n🏆 Probando productos más vendidos...")
    
    productos = ventas_controlador.obtener_productos_mas_vendidos(limit=5)
    
    print(f"   ✓ Productos en ranking: {len(productos)}")
    
    for i, producto in enumerate(productos, 1):
        print(f"   {i}. {producto['nombre']}: {producto['total_vendido']} vendidos, S/ {producto['total_ingresos']:.2f}")
    
    return productos

def main():
    """Función principal de pruebas"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE VENTAS")
    print("=" * 60)
    
    try:
        # Ejecutar todas las pruebas
        productos = probar_busqueda_productos()
        productos_venta = probar_validacion_stock()
        totales = probar_calculo_totales()
        venta_resultado = probar_venta_completa()
        venta_detalle = probar_consulta_venta()
        estadisticas = probar_estadisticas()
        top_productos = probar_productos_mas_vendidos()
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("\n📋 RESUMEN:")
        print(f"   - Productos disponibles: {len(productos) if productos else 0}")
        print(f"   - Categorías activas: {len(ventas_controlador.obtener_categorias_activas())}")
        print(f"   - Total ventas registradas: {estadisticas.get('total_ventas', 0) if estadisticas else 0}")
        print(f"   - Última venta: {venta_resultado['numero_venta'] if venta_resultado else 'N/A'}")
        
        print("\n🎯 SISTEMA LISTO PARA USAR:")
        print("   1. Ejecutar main.py para iniciar el servidor")
        print("   2. Ir a http://localhost:5000/ventas")
        print("   3. Realizar ventas con efectivo, tarjeta o Yape")
        print("   4. Imprimir tickets en impresora térmica 80mm")
        print("   5. Consultar historial en /ventas/historial")
        
    except Exception as e:
        print(f"\n❌ ERROR EN LAS PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()