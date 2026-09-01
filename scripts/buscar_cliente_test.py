from bd import obtener_conexion

EMAIL = 'testcliente@example.com'

def main():
    conn = obtener_conexion()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nombre, email, telefono FROM clientes WHERE email=%s LIMIT 1", (EMAIL,))
        row = cur.fetchone()
        print(row)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
