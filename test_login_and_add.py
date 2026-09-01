#!/usr/bin/env python3
"""
Test completo: login + agregar producto
"""

import requests

# Crear una sesión para mantener las cookies
session = requests.Session()

# Paso 1: Hacer login
login_url = 'http://127.0.0.1:5000/login'
login_data = {
    'username': 'admin_maskot',
    'password': 'admin2024'  # Contraseña por defecto
}

print("🔐 Haciendo login...")
login_response = session.post(login_url, data=login_data, allow_redirects=False)
print(f"Login Status: {login_response.status_code}")

if login_response.status_code == 302:
    print("✅ Login exitoso, redirigido")
else:
    print("❌ Error en login")
    print(f"Response: {login_response.text[:500]}")
    exit(1)

# Paso 2: Agregar producto
almacen_url = 'http://127.0.0.1:5000/almacen'
product_data = {
    'nombre': 'prueba',
    'tipo': 'stock',  # Stock (Inventario Interno)
    'cantidad': '50',
    'stock_min': '5',
    'fecha_vencimiento': '',  # Vacío
    'agregar': 'agregar'
}

print("\n📦 Agregando producto...")
print(f"Datos: {product_data}")

response = session.post(almacen_url, data=product_data, allow_redirects=False)
print(f"\nStatus Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")

if response.status_code == 302:
    print("✅ Redirección recibida - producto probablemente agregado")
    location = response.headers.get('Location', '')
    print(f"Redirigido a: {location}")
elif response.status_code == 200:
    print("⚠️ Respuesta 200 - revisar contenido")
    if 'json' in response.headers.get('Content-Type', ''):
        print(f"JSON: {response.json()}")
    else:
        print("HTML response (revisar servidor)")
else:
    print(f"❌ Error: {response.status_code}")
    print(f"Content: {response.text[:500]}")

print("\n🔍 Revisar logs del servidor Flask para más detalles...")