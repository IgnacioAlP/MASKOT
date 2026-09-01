import os
import sys
from bd import obtener_conexion

def test():
    print("--- Probando conexion a la base de datos ---")
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")
            res = cursor.fetchone()
            print(f"[OK] Conexion exitosa. Respuesta del servidor: {res}")
            
            # Intentar verificar si las tablas existen
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = cursor.fetchall()
            print(f"[INFO] Tablas encontradas en Supabase ({len(tables)}): {[t[0] for t in tables]}")
            
        conn.close()
    except Exception as e:
        print(f"[ERROR] Error de conexion: {e}")

if __name__ == '__main__':
    test()

