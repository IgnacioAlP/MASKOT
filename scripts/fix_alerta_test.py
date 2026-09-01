from bd import obtener_conexion

email='testcliente@example.com'
conn = obtener_conexion()
cur = conn.cursor()
try:
    nombre='Cliente Test'
    telefono='sin teléfono'
    nuevo = f"¡Increíble! El {nombre} ha acumulado 10 citas. Tiene un 20% de descuento en su próximo baño. Contactarse a ({telefono})"
    cur.execute("SELECT id FROM fidelizacion_historial WHERE cliente_email=%s AND evento='alerta_10' ORDER BY created_at DESC LIMIT 1", (email,))
    r=cur.fetchone()
    print('found', r)
    if r:
        cur.execute("UPDATE fidelizacion_historial SET descripcion=%s, created_at=NOW() WHERE id=%s", (nuevo, r[0]))
        conn.commit()
        print('updated')
    else:
        cur.execute("INSERT INTO fidelizacion_historial (cliente_email, evento, descripcion, created_at) VALUES (%s,%s,%s,NOW())", (email,'alerta_10',nuevo))
        conn.commit()
        print('inserted')
finally:
    cur.close()
    conn.close()
