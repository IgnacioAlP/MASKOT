import os
import re

class PostgresCursorWrapper:
    """Wrapper para cursores de PostgreSQL que adapta GROUP_CONCAT y lastrowid para compatibilidad total con MySQL."""
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, query, vars=None):
        sql = query
        
        # Traducir GROUP_CONCAT de MySQL a STRING_AGG de PostgreSQL
        if 'GROUP_CONCAT' in sql.upper():
            sql = re.sub(
                r'GROUP_CONCAT\s*\(\s*(DISTINCT\s+)?(.*?)\s+SEPARATOR\s+([\'"].*?[\'"])\s*\)',
                r'STRING_AGG(\1\2, \3)',
                sql,
                flags=re.IGNORECASE
            )
            sql = re.sub(
                r'GROUP_CONCAT\s*\(\s*(DISTINCT\s+)?(.*?)\s*\)',
                r"STRING_AGG(\1\2, ', ')",
                sql,
                flags=re.IGNORECASE
            )

        # Capturar id generado en INSERT usando RETURNING id
        is_insert = sql.strip().upper().startswith('INSERT')
        if is_insert and 'RETURNING' not in sql.upper():
            sql_with_returning = sql.rstrip('; \n\r\t') + ' RETURNING id;'
            try:
                self._cursor.execute(sql_with_returning, vars)
                res = self._cursor.fetchone()
                if res:
                    self.lastrowid = res[0]
                return
            except Exception:
                # Si la tabla no usa columna 'id', ejecutar query original
                pass

        self._cursor.execute(sql, vars)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    def close(self):
        return self._cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cursor.close()


class PostgresConnectionWrapper:
    """Wrapper para la conexión PostgreSQL."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        cursor = self._conn.cursor(*args, **kwargs)
        return PostgresCursorWrapper(cursor)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()


def obtener_conexion():
    """
    Obtiene una conexión a la base de datos Supabase (PostgreSQL) o MySQL según la configuración.
    Prioriza PostgreSQL via psycopg2 / psycopg2-binary para Supabase en Vercel.
    """
    db_url = os.environ.get('DATABASE_URL')
    
    # Credenciales por defecto para Supabase
    host = os.environ.get('DB_HOST', 'db.zpgwjgslescslwlwrwdw.supabase.co')
    port = int(os.environ.get('DB_PORT', 5432))
    database = os.environ.get('DB_NAME', 'postgres')
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', '')

    # 1. Intentar con DATABASE_URL si está definida (ej. en Vercel/Supabase)
    if db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url, sslmode='require')
            return PostgresConnectionWrapper(conn)
        except Exception:
            pass

    # 2. Intentar conexión PostgreSQL con psycopg2
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
            sslmode=os.environ.get('DB_SSLMODE', 'require')
        )
        return PostgresConnectionWrapper(conn)
    except ImportError:
        pass

    # 3. Fallback a PyMySQL (para desarrollo local previo o fallback)
    try:
        import pymysql
        mysql_host = os.environ.get('MYSQL_HOST', 'MASKOT.mysql.pythonanywhere-services.com')
        mysql_user = os.environ.get('MYSQL_USER', 'MASKOT')
        mysql_password = os.environ.get('MYSQL_PASSWORD', 'J161402i')
        mysql_db = os.environ.get('MYSQL_DB', 'MASKOT$Veterinaria')
        return pymysql.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            db=mysql_db
        )
    except Exception as e:
        raise Exception(f"No se pudo establecer conexión a la base de datos. Instale psycopg2-binary o configure DB_PASSWORD. Detalle: {e}")


