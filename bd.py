import os
import psycopg2


def obtener_conexion():
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    dbname = os.environ.get("DB_NAME")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")

    missing = [
        key for key, value in {
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_NAME": dbname,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items() if not value
    ]

    if missing:
        raise RuntimeError(
            "Faltan variables de entorno de Supabase: " + ", ".join(missing) +
            ". Configúralas en Vercel o en tu entorno local antes de usar la base de datos."
        )

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        sslmode="require"
    )

    with conn.cursor() as cursor:
        cursor.execute("SET TIME ZONE 'America/Lima';")
    conn.commit()

    return conn

def obtener_tenant_id():
    """Retorna el tenant_id de la sesión Flask activa. Soporta numéricos y 'ALL' para superadmin."""
    try:
        from flask import session
        tid = session.get('tenant_id', 1)
        if str(tid).upper() == 'ALL':
            return 'ALL'
        return int(tid) if tid is not None else 1
    except Exception:
        return 1
