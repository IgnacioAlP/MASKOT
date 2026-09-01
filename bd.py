import os
import psycopg2
from psycopg2.extras import RealDictCursor

def obtener_conexion():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
        port=os.environ.get("DB_PORT", "6543"),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres.zpgwjgslescslwlwrwdw"),
        password=os.environ.get("DB_PASSWORD"),
        sslmode="require",
        cursor_factory=RealDictCursor
    )

def obtener_tenant_id():
    try:
        from flask import session
        tid = session.get('tenant_id', 1)
        return int(tid) if tid else 1
    except Exception:
        return 1