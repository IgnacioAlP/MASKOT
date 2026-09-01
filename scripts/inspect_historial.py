from bd import obtener_conexion

EMAIL = 'testcliente@example.com'

def main():
    conn = obtener_conexion()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, cliente_email, evento, descripcion, created_at FROM fidelizacion_historial WHERE cliente_email=%s ORDER BY created_at DESC", (EMAIL,))
        rows = cur.fetchall()
        if not rows:
            print('No rows found for', EMAIL)
            return
        for r in rows:
            print(r)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()