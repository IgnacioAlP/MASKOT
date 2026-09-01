#!/usr/bin/env python3
"""
Test para agregar producto nuevo - Simular el formulario de la imagen
"""

import requests

# Datos del formulario según la imagen
form_data = {
    'nombre': 'prueba',
    'tipo': 'stock',  # Stock (Inventario Interno)
    'cantidad': '50',
    'stock_min': '5',
    'fecha_vencimiento': '',  # Vacío en la imagen
    'agregar': 'agregar'  # Campo necesario para el backend
}

url = 'http://127.0.0.1:5000/almacen'

print("🧪 Probando agregar producto nuevo...")
print(f"📝 Datos: {form_data}")

try:
    # Hacer POST al endpoint
    response = requests.post(url, data=form_data, allow_redirects=False)
    
    print(f"\n📊 Respuesta del servidor:")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 302:
        print("✅ Redirección recibida (comportamiento esperado)")
        print(f"Location: {response.headers.get('Location', 'N/A')}")
    elif response.status_code == 200:
        print("⚠️ Respuesta 200 - podría indicar un problema")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        if 'json' in response.headers.get('Content-Type', ''):
            print(f"JSON Response: {response.json()}")
    else:
        print(f"❌ Código de estado inesperado: {response.status_code}")
        print(f"Contenido: {response.text[:500]}")

except Exception as e:
    print(f"❌ Error en la prueba: {e}")

print("\n🔍 Verifica la consola del servidor Flask para ver los logs de debug...")