"""
Script de prueba para verificar la integración completa del historial de compras
"""

import sys
sys.path.append('.')

from bd import obtener_conexion
from controladores import compras_controlador
import json

def probar_sistema_completo():
    """Prueba todo el sistema de historial de compras"""
    print("PRUEBA DEL SISTEMA DE HISTORIAL DE COMPRAS")
    print("=" * 50)
    
    # 1. Verificar que la tabla existe
    print("1. Verificando tabla de compras...")
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM compras")
        count = cursor.fetchone()[0]
        print(f"✅ Tabla 'compras' existe con {count} registros")
        conexion.close()
    except Exception as e:
        print(f"❌ Error accediendo a tabla compras: {e}")
        return False
    
    # 2. Probar controlador de compras
    print("\n2. Probando controlador de compras...")
    try:
        # Obtener compras
        compras = compras_controlador.obtener_compras_por_fecha(limit=5)
        print(f"✅ Obtenidas {len(compras)} compras del controlador")
        
        # Obtener estadísticas
        stats = compras_controlador.obtener_estadisticas_compras()
        print(f"✅ Estadísticas: {stats['total_compras']} compras, ${stats['total_vendido']:.2f} vendido")
        
        # Probar obtener detalle si hay compras
        if compras:
            compra_id = compras[0][0]
            detalle = compras_controlador.obtener_detalle_compra(compra_id)
            if detalle:
                print(f"✅ Detalle de compra {compra_id} obtenido correctamente")
                print(f"   Cliente: {detalle['cliente_nombre']}")
                print(f"   Total: ${detalle['total']:.2f}")
                print(f"   Productos: {len(detalle['productos'])}")
            else:
                print(f"⚠️  No se pudo obtener detalle de compra {compra_id}")
        
    except Exception as e:
        print(f"❌ Error en controlador: {e}")
        return False
    
    # 3. Verificar estructura de productos JSON
    print("\n3. Verificando estructura de productos...")
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT productos FROM compras LIMIT 1")
        result = cursor.fetchone()
        if result and result[0]:
            productos_json = json.loads(result[0])
            print(f"✅ JSON de productos válido, {len(productos_json)} productos")
            if productos_json:
                primer_producto = productos_json[0]
                campos_requeridos = ['id', 'nombre', 'precio', 'cantidad']
                tiene_campos = all(campo in primer_producto for campo in campos_requeridos)
                if tiene_campos:
                    print("✅ Estructura de productos correcta")
                else:
                    print(f"⚠️  Faltan campos en productos: {primer_producto}")
        conexion.close()
    except Exception as e:
        print(f"❌ Error verificando JSON: {e}")
    
    # 4. Verificar integración con carrito (simular)
    print("\n4. Probando registro de compra (simulación)...")
    try:
        productos_test = [
            {
                'id': 1,
                'nombre': 'Producto Test',
                'precio': 50.00,
                'cantidad': 2
            }
        ]
        
        compra_id = compras_controlador.registrar_compra(
            cliente_nombre="Cliente Test",
            cliente_email="test@email.com",
            cliente_telefono="555-0123",
            productos=productos_test,
            metodo_pago="efectivo",
            observaciones="Compra de prueba desde script"
        )
        
        if compra_id:
            print(f"✅ Compra test registrada con ID: {compra_id}")
            
            # Verificar que se puede obtener
            detalle_test = compras_controlador.obtener_detalle_compra(compra_id)
            if detalle_test:
                print(f"✅ Compra test recuperada correctamente")
                print(f"   Total calculado: ${detalle_test['total']:.2f}")
            
            # Cambiar estado
            success = compras_controlador.actualizar_estado_compra(compra_id, 'cancelado')
            if success:
                print("✅ Estado de compra cambiado correctamente")
        else:
            print("❌ No se pudo registrar compra test")
            
    except Exception as e:
        print(f"❌ Error en prueba de registro: {e}")
    
    # 5. Verificar métodos de búsqueda
    print("\n5. Probando búsqueda de compras...")
    try:
        resultados = compras_controlador.buscar_compras_por_cliente("test")
        print(f"✅ Búsqueda por cliente funcionando: {len(resultados)} resultados")
        
        # Filtros por estado
        compras_pagadas = compras_controlador.obtener_compras_por_fecha(estado='pagado', limit=3)
        print(f"✅ Filtro por estado 'pagado': {len(compras_pagadas)} resultados")
        
    except Exception as e:
        print(f"❌ Error en búsquedas: {e}")
    
    print("\n" + "=" * 50)
    print("✅ PRUEBA COMPLETADA")
    print("=" * 50)
    print("\nPróximos pasos para probar en la aplicación:")
    print("1. Reiniciar el servidor Flask")
    print("2. Hacer login como admin/empleado/dueño")
    print("3. Ir a 'Gestión' -> 'Historial de Compras'")
    print("4. Realizar una compra desde el carrito")
    print("5. Verificar que aparezca en el historial")
    print("6. Probar generar ticket desde el historial")
    
    return True

def mostrar_configuracion_ticketera():
    """Muestra recordatorio de configuración de ticketera"""
    print("\n" + "=" * 50)
    print("RECORDATORIO: CONFIGURACIÓN DE TICKETERA")
    print("=" * 50)
    print("Para imprimir tickets correctamente:")
    print("1. Configurar papel: 80mm térmico")
    print("2. Orientación: Vertical (Portrait)")
    print("3. Márgenes: Mínimos (1-2mm)")
    print("4. Usar el archivo ticket_prueba.html para probar")
    print("5. Los tickets incluyen:")
    print("   - Información del cliente")
    print("   - Lista detallada de productos")
    print("   - Subtotal, IGV y total")
    print("   - Método de pago")
    print("   - Información de contacto")

if __name__ == "__main__":
    exito = probar_sistema_completo()
    if exito:
        mostrar_configuracion_ticketera()
    else:
        print("\n❌ Hay problemas en el sistema que deben resolverse")