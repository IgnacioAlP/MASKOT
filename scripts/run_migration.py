import sys
import os
# Ensure project root is on sys.path so imports like `bd` resolve when running this script
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from bd import obtener_conexion

sql_path = os.path.join(PROJECT_ROOT, 'migrations', '001_create_fidelizacion_tables.sql')
print('Leyendo SQL desde', sql_path)
with open(sql_path,'r',encoding='utf-8') as f:
    sql = f.read()

conn = None
try:
    conn = obtener_conexion()
    cursor = conn.cursor()
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    for stmt in statements:
        print('Ejecutando statement: ', stmt[:60].replace('\n',' '))
        cursor.execute(stmt)
    conn.commit()
    print('Migración ejecutada correctamente')
except Exception as e:
    print('Error ejecutando migración:', e)
    if conn:
        conn.rollback()
finally:
    if conn:
        conn.close()
