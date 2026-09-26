import os
import urllib.parse
import psycopg2


def _get_env_value(*names):
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ''):
            return value
    return None


def construir_config_db():
    """Resuelve la configuración de conexión aceptando varias convenciones de Supabase/Vercel."""
    db_url = _get_env_value(
        'DATABASE_URL',
        'DB_URL',
        'POSTGRES_URL',
        'POSTGRES_PRISMA_URL',
        'SUPABASE_URL',
        'SUPABASE_DB_URL'
    )
    if db_url:
        return {'url': db_url}

    host = _get_env_value('DB_HOST', 'PGHOST', 'SUPABASE_HOST')
    port = _get_env_value('DB_PORT', 'PGPORT', 'SUPABASE_PORT', '5432')
    dbname = _get_env_value('DB_NAME', 'PGDATABASE', 'SUPABASE_DB_NAME', 'POSTGRES_DB')
    user = _get_env_value('DB_USER', 'PGUSER', 'SUPABASE_USER', 'POSTGRES_USER')
    password = _get_env_value('DB_PASSWORD', 'PGPASSWORD', 'SUPABASE_PASSWORD', 'POSTGRES_PASSWORD')

    missing = [
        key for key, value in {
            'DB_HOST': host,
            'DB_PORT': port,
            'DB_NAME': dbname,
            'DB_USER': user,
            'DB_PASSWORD': password,
        }.items() if not value
    ]

    if missing:
        raise RuntimeError(
            'Faltan variables de entorno de Supabase: ' + ', '.join(missing) +
            '. Configúralas en Vercel o en tu entorno local antes de usar la base de datos.'
        )

    return {
        'host': host,
        'port': port,
        'dbname': dbname,
        'user': user,
        'password': password,
        'sslmode': 'require'
    }


def obtener_conexion():
    db_cfg = construir_config_db()

    if 'url' in db_cfg:
        conn = psycopg2.connect(db_cfg['url'])
    else:
        conn = psycopg2.connect(
            host=db_cfg['host'],
            port=db_cfg['port'],
            dbname=db_cfg['dbname'],
            user=db_cfg['user'],
            password=db_cfg['password'],
            sslmode=db_cfg.get('sslmode', 'require')
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
