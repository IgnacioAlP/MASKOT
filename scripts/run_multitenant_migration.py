"""
Script para ejecutar la migración multitenant localmente.
Ejecutar una sola vez: python scripts/run_multitenant_migration.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

def get_conn():
    return pymysql.connect(host='localhost', port=3306, user='root', password='', db='maskot')

def run():
    conn = get_conn()
    c = conn.cursor()

    # 1. Tabla de tenants
    c.execute("""CREATE TABLE IF NOT EXISTS tenants (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        slug VARCHAR(50) NOT NULL UNIQUE,
        activo TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""")
    print("[OK] Tabla tenants creada o ya existe")

    # 2. Tenant por defecto
    c.execute("SELECT id FROM tenants WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO tenants (id, nombre, slug) VALUES (1, 'MASKOT', 'maskot')")
    conn.commit()
    print("[OK] Tenant por defecto asegurado")

    # 3. Agregar rol superadmin
    try:
        c.execute("ALTER TABLE usuarios MODIFY COLUMN rol ENUM('cliente','dueño','admin','empleado','superadmin') NOT NULL")
        conn.commit()
        print("[OK] Rol superadmin agregado")
    except Exception as e:
        print(f"[INFO] rol already updated: {e}")

    # Tablas a las que agregar tenant_id
    tables = [
        'usuarios', 'clientes', 'mascotas', 'citas', 'servicios',
        'productos', 'personal', 'asistencia', 'pedidos', 'detalle_pedidos',
        'tarjetas_cliente', 'citas_mascotas', 'citas_servicios',
        'compras', 'ventas', 'fidelizacion', 'fidelizacion_historial'
    ]

    # 4. Agregar tenant_id a cada tabla
    for table in tables:
        # Verificar si la tabla existe
        c.execute("SHOW TABLES LIKE %s", (table,))
        if not c.fetchone():
            print(f"[SKIP] Tabla {table} no existe")
            continue
        # Verificar si ya tiene tenant_id
        c.execute(f"SHOW COLUMNS FROM `{table}` LIKE 'tenant_id'")
        if c.fetchone():
            print(f"[SKIP] {table}.tenant_id ya existe")
            continue
        try:
            c.execute(f"ALTER TABLE `{table}` ADD COLUMN tenant_id INT DEFAULT 1")
            conn.commit()
            print(f"[OK] tenant_id agregado a {table}")
        except Exception as e:
            print(f"[ERROR] {table}: {e}")

    # 5. Índices
    for table in tables:
        c.execute("SHOW TABLES LIKE %s", (table,))
        if not c.fetchone():
            continue
        c.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = 'idx_tenant'")
        if c.fetchone():
            print(f"[SKIP] índice idx_tenant en {table} ya existe")
            continue
        try:
            c.execute(f"ALTER TABLE `{table}` ADD INDEX idx_tenant (tenant_id)")
            conn.commit()
            print(f"[OK] índice idx_tenant creado en {table}")
        except Exception as e:
            print(f"[ERROR] índice {table}: {e}")

    # 6. Foreign keys (opcionales, se ignoran si fallan)
    fk_tables = [
        'usuarios', 'clientes', 'mascotas', 'citas', 'servicios',
        'productos', 'personal', 'asistencia', 'pedidos', 'detalle_pedidos',
        'tarjetas_cliente', 'citas_mascotas', 'citas_servicios'
    ]
    for table in fk_tables:
        c.execute("SHOW TABLES LIKE %s", (table,))
        if not c.fetchone():
            continue
        fk_name = f"fk_{table}_tenant"
        # Verificar si ya existe la FK
        c.execute("""
            SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS 
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s 
            AND CONSTRAINT_TYPE = 'FOREIGN KEY' AND CONSTRAINT_NAME = %s
        """, (table, fk_name))
        if c.fetchone():
            print(f"[SKIP] FK {fk_name} ya existe")
            continue
        try:
            c.execute(f"ALTER TABLE `{table}` ADD CONSTRAINT `{fk_name}` FOREIGN KEY (tenant_id) REFERENCES tenants(id)")
            conn.commit()
            print(f"[OK] FK {fk_name} creada")
        except Exception as e:
            print(f"[WARN] FK {fk_name}: {e}")

    conn.close()
    print("\n[DONE] Migración multitenant completada.")

if __name__ == '__main__':
    run()
