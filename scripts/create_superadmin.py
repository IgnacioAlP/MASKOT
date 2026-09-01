"""Script para crear el usuario superadmin en la base de datos."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import hashlib
import pymysql

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

conn = pymysql.connect(host='localhost', port=3306, user='root', password='', db='maskot')
c = conn.cursor()

# Verificar si ya existe
c.execute("SELECT id, username, rol FROM usuarios WHERE rol='superadmin' LIMIT 1")
existing = c.fetchone()

if existing:
    print(f"Superadmin ya existe: id={existing[0]}, username={existing[1]}")
else:
    hashed = hash_password('superadmin123')
    c.execute(
        "INSERT INTO usuarios (username, password, rol, activo, tenant_id) VALUES (%s, %s, %s, %s, %s)",
        ('superadmin', hashed, 'superadmin', 1, 1)
    )
    conn.commit()
    print("Superadmin creado exitosamente:")
    print("  username: superadmin")
    print("  password: superadmin123")
    print("  rol:      superadmin")
    print("  tenant_id: 1")

conn.close()
