from bd import obtener_conexion

def verificar_tablas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    try:
        # Verificar si existe la tabla fidelizacion
        cursor.execute("SHOW TABLES LIKE 'fidelizacion'")
        tabla_existe = bool(cursor.fetchone())
        print(f"Tabla fidelizacion existe: {tabla_existe}")
        
        if tabla_existe:
            cursor.execute("DESCRIBE fidelizacion")
            estructura = cursor.fetchall()
            print("Estructura tabla fidelizacion:")
            for campo in estructura:
                print(f"  {campo}")
        else:
            print("Ejecutando migración...")
            # Ejecutar la migración
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
            from run_migration import ejecutar_migracion
            ejecutar_migracion()
            print("Migración completada")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    verificar_tablas()