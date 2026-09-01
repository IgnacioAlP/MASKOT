from main import app
from controladores.productos_controlador import obtener_productos

def test_web_form_simulation():
    """Simula exactamente lo que haría el formulario web"""
    try:
        print("=== SIMULACIÓN FORMULARIO WEB ===")
        
        # Buscar producto gato
        productos = obtener_productos()
        producto_gato = None
        for prod in productos:
            if "Gato Adulto 7.5kg" in prod[1]:
                producto_gato = prod
                break
        
        if not producto_gato:
            print("❌ No se encontró el producto")
            return False
            
        print(f"Producto encontrado: ID {producto_gato[0]} - {producto_gato[1]}")
        print(f"Stock mínimo actual: {producto_gato[4]}")
        
        # Simular los datos que envía el formulario
        nuevo_stock_min = producto_gato[4] + 3
        form_data = {
            'id': str(producto_gato[0]),
            'nombre': producto_gato[1],
            'cantidad': str(producto_gato[3]),
            'stock_min': str(nuevo_stock_min),
            'fecha_vencimiento': str(producto_gato[5]) if producto_gato[5] else '',
            'modificar': 'modificar'  # Este es el campo clave
        }
        
        print(f"\nDatos a enviar:")
        for key, value in form_data.items():
            print(f"  {key}: {value}")
        
        print(f"\nCambiando stock mínimo de {producto_gato[4]} a {nuevo_stock_min}")
        
        # Simular request POST usando el contexto de Flask
        with app.test_request_context('/almacen', method='POST', data=form_data):
            # Simular sesión de admin
            from flask import session
            session['usuario_id'] = 1
            session['usuario'] = 'admin_maskot' 
            session['rol'] = 'admin'
            
            # Importar la función almacen directamente
            from main import almacen
            
            try:
                result = almacen()
                print("✅ Función almacen() ejecutada sin errores")
                
                # Verificar si se guardó el cambio
                from controladores.productos_controlador import obtener_producto_por_id
                producto_actualizado = obtener_producto_por_id(producto_gato[0])
                
                print(f"\nVerificación:")
                print(f"  Stock mínimo anterior: {producto_gato[4]}")
                print(f"  Stock mínimo esperado: {nuevo_stock_min}")
                print(f"  Stock mínimo actual: {producto_actualizado[4]}")
                
                if producto_actualizado[4] == nuevo_stock_min:
                    print("  ✅ ¡Stock mínimo se actualizó correctamente!")
                    
                    # Restaurar valor original
                    form_data_restore = form_data.copy()
                    form_data_restore['stock_min'] = str(producto_gato[4])
                    
                    with app.test_request_context('/almacen', method='POST', data=form_data_restore):
                        session['usuario_id'] = 1
                        session['usuario'] = 'admin_maskot'
                        session['rol'] = 'admin'
                        almacen()
                        print("  ✅ Valor original restaurado")
                    
                    return True
                else:
                    print("  ❌ Stock mínimo NO se actualizó")
                    return False
                    
            except Exception as e:
                print(f"❌ Error al ejecutar almacen(): {e}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_web_form_simulation()