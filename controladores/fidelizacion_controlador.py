from bd import obtener_conexion, obtener_tenant_id
import os
from datetime import datetime

try:
    import requests
except Exception:
    requests = None

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
LOG_DIR = os.path.abspath(LOG_DIR)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'fidelizacion.log')
WSP_PHONE = os.environ.get('WSP_PHONE', '+51959703099')

# Optional WhatsApp Business API configuration via environment variables
WSP_API_URL = os.environ.get('WSP_API_URL')
WSP_API_TOKEN = os.environ.get('WSP_API_TOKEN')


def _log(text):
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{now} | {text}\n")


def _get_fidelizacion_row(cursor, email, tenant_id):
    cursor.execute("SELECT id, cliente_email, cliente_nombre, contador FROM fidelizacion WHERE cliente_email = %s AND tenant_id = %s", (email, tenant_id))
    return cursor.fetchone()


def _create_or_update_fidelizacion(cursor, nombre, email, tenant_id):
    row = _get_fidelizacion_row(cursor, email, tenant_id)
    if row:
        # incrementar contador
        new_count = row[3] + 1
        cursor.execute("UPDATE fidelizacion SET contador = %s, cliente_nombre = %s WHERE id = %s", (new_count, nombre, row[0]))
        return new_count
    else:
        cursor.execute("INSERT INTO fidelizacion (cliente_email, cliente_nombre, contador, tenant_id) VALUES (%s, %s, %s, %s)", (email, nombre, 1, tenant_id))
        return 1


def _insert_historial(cursor, email, evento, descripcion='', tenant_id=1):
    cursor.execute("INSERT INTO fidelizacion_historial (cliente_email, evento, descripcion, tenant_id) VALUES (%s, %s, %s, %s)", (email, evento, descripcion, tenant_id))


def _get_cliente_telefono(cursor, email, tenant_id):
    cursor.execute("SELECT telefono FROM clientes WHERE email = %s AND tenant_id = %s LIMIT 1", (email, tenant_id))
    row = cursor.fetchone()
    if row:
        return row[0]
    return None


def _build_wa_url(message):
    texto = message + "\n\nMensaje automático desde MASKOT."
    encoded = urlencode_text(texto)
    phone_clean = ''.join([c for c in WSP_PHONE if c.isdigit()])
    return f"https://wa.me/{phone_clean}?text={encoded}"


def urlencode_text(text):
    try:
        from urllib.parse import quote_plus
        return quote_plus(text)
    except Exception:
        return text.replace(' ', '%20')


def _send_via_whatsapp_business(phone, message):
    """Opcional: enviar via WhatsApp Business API si está configurado WSP_API_URL y WSP_API_TOKEN."""
    if not (WSP_API_URL and WSP_API_TOKEN and requests):
        return False, 'WSP API no configurada o requests no disponible'

    headers = {'Authorization': f'Bearer {WSP_API_TOKEN}', 'Content-Type': 'application/json'}
    payload = {
        'to': phone,
        'type': 'text',
        'text': {'body': message}
    }
    try:
        resp = requests.post(WSP_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            return True, resp.text
        else:
            return False, f'Status {resp.status_code}: {resp.text}'
    except Exception as e:
        return False, str(e)


def obtener_alertas_recientes(limit=10):
    """Obtiene las alertas de fidelización más recientes para mostrar en el dashboard"""
    conexion = obtener_conexion()
    alertas = []
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
                # Unir con la tabla clientes para obtener teléfono y nombre real cuando esté disponible.
                cursor.execute("""
                    SELECT 
                        COALESCE(c.nombre, fh.cliente_email) as cliente_nombre,
                        c.telefono as cliente_telefono,
                        fh.evento,
                        fh.descripcion,
                        fh.created_at
                    FROM fidelizacion_historial fh
                    LEFT JOIN clientes c ON fh.cliente_email = c.email AND c.tenant_id = fh.tenant_id
                    WHERE fh.evento IN ('alerta_5', 'alerta_10') AND fh.tenant_id = %s
                    ORDER BY fh.created_at DESC
                    LIMIT %s
                """, (tenant_id, limit))
                alertas = cursor.fetchall()
    finally:
        conexion.close()
    return alertas


def sincronizar_fidelizacion_desde_citas():
    """Sincroniza la tabla `fidelizacion` leyendo las citas completadas por cliente (por email).
    - Cuenta las citas con estado 'completada' por cliente_email en `citas`.
    - Actualiza o inserta la fila en `fidelizacion` con el contador correcto.
    - Inserta en `fidelizacion_historial` eventos de alerta cuando se alcanzan 5 o 10 citas.
    - Reinicia el contador a 0 si alcanza 10 y registra el reinicio.
    Esta función es idempotente y puede ejecutarse periódicamente.
    """
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            # Contar citas completadas agrupadas por cliente_email
            cursor.execute("""
                SELECT cliente_email, cliente_nombre, COUNT(*) as total
                FROM citas
                WHERE estado = 'completada' AND cliente_email IS NOT NULL AND tenant_id = %s
                GROUP BY cliente_email, cliente_nombre
            """, (tenant_id,))
            resultados = cursor.fetchall()

            for row in resultados:
                email = row[0]
                nombre = row[1] or email
                total = int(row[2] or 0)

                # Obtener fila existente
                cursor.execute("SELECT id, contador FROM fidelizacion WHERE cliente_email = %s AND tenant_id = %s", (email, tenant_id))
                existente = cursor.fetchone()

                if existente:
                    fid_id, contador_actual = existente[0], int(existente[1] or 0)
                    if contador_actual != total:
                        cursor.execute("UPDATE fidelizacion SET contador = %s, cliente_nombre = %s WHERE id = %s", (total, nombre, fid_id))
                else:
                    cursor.execute("INSERT INTO fidelizacion (cliente_email, cliente_nombre, contador, tenant_id) VALUES (%s, %s, %s, %s)", (email, nombre, total, tenant_id))

                # Generar alertas si corresponde: insertar en historial cuando se cruza 5 o 10
                # Verificar si ya existe alerta_5/alerta_10 reciente para evitar duplicados
                if total >= 5:
                    # Inssert or update alerta_5 para este email con el mensaje actualizado
                    telefono = _get_cliente_telefono(cursor, email, tenant_id) or 'sin teléfono'
                    mensaje_5 = f"¡Increíble! El {nombre} ha acumulado {total} citas. Tiene un 10% de descuento en su próximo baño. Contactarse a ({telefono})"
                    cursor.execute("SELECT id FROM fidelizacion_historial WHERE cliente_email=%s AND evento='alerta_5' AND tenant_id=%s ORDER BY created_at DESC LIMIT 1", (email, tenant_id))
                    row_alerta5 = cursor.fetchone()
                    if row_alerta5:
                        cursor.execute("UPDATE fidelizacion_historial SET descripcion=%s, created_at=NOW() WHERE id=%s", (mensaje_5, row_alerta5[0]))
                    else:
                        _insert_historial(cursor, email, 'alerta_5', mensaje_5, tenant_id)

                if total >= 10:
                    telefono = _get_cliente_telefono(cursor, email, tenant_id) or 'sin teléfono'
                    mensaje_10 = f"¡Increíble! El {nombre} ha acumulado {total} citas. Tiene un 20% de descuento en su próximo baño. Contactarse a ({telefono})"
                    cursor.execute("SELECT id FROM fidelizacion_historial WHERE cliente_email=%s AND evento='alerta_10' AND tenant_id=%s ORDER BY created_at DESC LIMIT 1", (email, tenant_id))
                    row_alerta10 = cursor.fetchone()
                    if row_alerta10:
                        cursor.execute("UPDATE fidelizacion_historial SET descripcion=%s, created_at=NOW() WHERE id=%s", (mensaje_10, row_alerta10[0]))
                    else:
                        _insert_historial(cursor, email, 'alerta_10', mensaje_10, tenant_id)
                    # Reiniciar contador a 0 después de otorgar el beneficio
                    cursor.execute("UPDATE fidelizacion SET contador = 0 WHERE cliente_email = %s AND tenant_id = %s", (email, tenant_id))
                    _insert_historial(cursor, email, 'reinicio', f'contador reiniciado tras alcanzar {total}', tenant_id)

            conexion.commit()
    finally:
        conexion.close()


def procesar_fidelizacion_para_cliente(cliente_nombre, cliente_email, enviar_automatico=False):
    """Procesa la fidelización incrementando contador en DB, registrando historial y devolviendo info.
    - Si el contador alcanza 5 o 10, se inserta un historial y se construye una URL de WA.
    - Si enviar_automatico=True y la API está configurada, intentará enviar el mensaje.
    Retorna: dict { total_citas, wa_url (optional), sent (bool), send_info }
    """
    result = {'total_citas': 0, 'wa_url': None, 'sent': False, 'send_info': None}

    if not cliente_email:
        return result

    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            # Incrementar contador en la tabla fidelizacion
            total = _create_or_update_fidelizacion(cursor, cliente_nombre, cliente_email, tenant_id)
            _insert_historial(cursor, cliente_email, 'incremento', f'contador ahora {total}', tenant_id)

            # Commit temporal para persistir cambios
            conexion.commit()

            result['total_citas'] = total

            mensaje = None
            if total == 5:
                telefono = _get_cliente_telefono(cursor, cliente_email, tenant_id) or 'sin teléfono'
                mensaje = f"¡Increíble! El {cliente_nombre} ha acumulado {total} citas. Tiene un 10% de descuento en su próximo baño. Contactarse a ({telefono})"
                _insert_historial(cursor, cliente_email, 'alerta_5', mensaje, tenant_id)
            elif total >= 10:
                telefono = _get_cliente_telefono(cursor, cliente_email, tenant_id) or 'sin teléfono'
                mensaje = f"¡Increíble! El {cliente_nombre} ha acumulado {total} citas. Tiene un 20% de descuento en su próximo baño. Contactarse a ({telefono})"
                _insert_historial(cursor, cliente_email, 'alerta_10', mensaje, tenant_id)

                # Reiniciar contador a 0 automáticamente
                cursor.execute("UPDATE fidelizacion SET contador = 0 WHERE cliente_email = %s AND tenant_id = %s", (cliente_email, tenant_id))
                _insert_historial(cursor, cliente_email, 'reinicio', f'contador reiniciado tras alcanzar {total}', tenant_id)
                conexion.commit()
                result['total_citas'] = 0

            # Registrar en log de archivos
            _log(f"{cliente_email} | {cliente_nombre} | total_citas={total} | mensaje_needed={'yes' if mensaje else 'no'}")

            if mensaje:
                wa_url = _build_wa_url(mensaje)
                result['wa_url'] = wa_url

                # Intentar envío automático si se pidió y la API está configurada
                if enviar_automatico and WSP_API_URL and WSP_API_TOKEN:
                    sent, info = _send_via_whatsapp_business('+' + ''.join([c for c in WSP_PHONE if c.isdigit()]), mensaje)
                    result['sent'] = sent
                    result['send_info'] = info
                    _log(f"envio_automatico | {cliente_email} | sent={sent} | info={info}")

    finally:
        conexion.close()

    return result
