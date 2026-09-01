import os
import psycopg2
from psycopg2.extras import RealDictCursor

def obtener_conexion():
    connection = psycopg2.connect(
        host=os.environ.get("DB_HOST", "db.zpgwjgslescslwlwrwdw.supabase.co"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD"),
        cursor_factory=RealDictCursor
    )
    return connection

def obtener_tenant_id():
    """Retorna el tenant_id de la sesión Flask activa. Siempre devuelve un int."""
    try:
        from flask import session
        tid = session.get('tenant_id', 1)
        return int(tid) if tid else 1
    except Exception:
        return 1