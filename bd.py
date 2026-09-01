import pymysql

def obtener_conexion():
    return pymysql.connect(host='MASKOT.mysql.pythonanywhere-services.com',
                           user='MASKOT',
                           password='J161402i',
                           db='MASKOT$Veterinaria')
