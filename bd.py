import pymysql

def obtener_conexion():
    return pymysql.connect(host='MASKOT.mysql.pythonanywhere-services.com',
                           user='MASKOT',
                           password='J161402i',
                           db='MASKOT$NC')

def obtener_tenant_id():
    """Retorna el tenant_id de la sesión Flask activa. Siempre devuelve un int."""
    try:
        from flask import session
        tid = session.get('tenant_id', 1)
        return int(tid) if tid else 1
    except Exception:
        return 1
