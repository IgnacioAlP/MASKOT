import os
import psycopg2

def obtener_conexion():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
        port=os.environ.get("DB_PORT", "6543"),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres.zpgwjgslescslwlwrwdw"),
        password=os.environ.get("DB_PASSWORD"),
        sslmode="require"
    )
    with conn.cursor() as cursor:
        cursor.execute("SET TIME ZONE 'America/Lima';")
    
    return conn

def obtener_tenant_id():
    """Retorna el tenant_id de la sesión Flask activa. Siempre devuelve un int."""
    try:
        from flask import session
        tid = session.get('tenant_id', 1)
        return int(tid) if tid else 1
    except Exception:
        return 1