from bd import obtener_conexion
import os
from datetime import datetime

try:
    import requests
except Exception:
    requests = None

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
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


def _get_fidelizacion_row(cursor, email):
    cursor.execute("SELECT id, cliente_email, cliente_nombre, contador FROM fidelizacion WHERE cliente_email = %s", (email,))
    return cursor.fetchone()


def _create_or_update_fidelizacion(cursor, nombre, email):
    row = _get_fidelizacion_row(cursor, email)
    if row:
        # incrementar contador
        new_count = row[3] + 1
        cursor.execute("UPDATE fidelizacion SET contador = %s, cliente_nombre = %s WHERE id = %s", (new_count, nombre, row[0]))
        return new_count
    else:
        cursor.execute("INSERT INTO fidelizacion (cliente_email, cliente_nombre, contador) VALUES (%s, %s, %s)", (email, nombre, 1))
        return 1


def _insert_historial(cursor, email, evento, descripcion=''):
    cursor.execute("INSERT INTO fidelizacion_historial (cliente_email, evento, descripcion) VALUES (%s, %s, %s)", (email, evento, descripcion))


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


def procesar_fidelizacion_para_cliente(cliente_nombre, cliente_email, enviar_automático=False):
    """Procesa la fidelización incrementando contador en DB, registrando historial y devolviendo info.
    - Si el contador alcanza 5 o 10, se inserta un historial y se construye una URL de WA.
    - Si enviar_automático=True y la API está configurada, intentará enviar el mensaje.
    Retorna: dict { total_citas, wa_url (optional), sent (bool), send_info }
    """
    result = {'total_citas': 0, 'wa_url': None, 'sent': False, 'send_info': None}

    if not cliente_email:
        return result

    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            # Incrementar contador en la tabla fidelizacion
            total = _create_or_update_fidelizacion(cursor, cliente_nombre, cliente_email)
            _insert_historial(cursor, cliente_email, 'incremento', f'contador ahora {total}')

            # Commit temporal para persistir cambios
            conexion.commit()

            result['total_citas'] = total

            mensaje = None
            if total == 5:
                mensaje = f"Hola {cliente_nombre}, ¡felicidades! Has acumulado {total} citas. Tienes un 10% de descuento en tu próximo baño."
                _insert_historial(cursor, cliente_email, 'alerta_5', mensaje)
            elif total >= 10:
                mensaje = f"Hola {cliente_nombre}, ¡increíble! Has acumulado {total} citas. Tienes un 20% de descuento en tu próximo baño. Tu tarjeta de fidelización se reinicia a 0 citas."
                _insert_historial(cursor, cliente_email, 'alerta_10', mensaje)

                # Reiniciar contador a 0 automáticamente
                cursor.execute("UPDATE fidelizacion SET contador = 0 WHERE cliente_email = %s", (cliente_email,))
                _insert_historial(cursor, cliente_email, 'reinicio', f'contador reiniciado tras alcanzar {total}')
                conexion.commit()
                result['total_citas'] = 0

            # Registrar en log de archivos
            _log(f"{cliente_email} | {cliente_nombre} | total_citas={total} | mensaje_needed={'yes' if mensaje else 'no'}")

            if mensaje:
                wa_url = _build_wa_url(mensaje)
                result['wa_url'] = wa_url

                # Intentar envío automático si se pidió y la API está configurada
                if enviar_automático and WSP_API_URL and WSP_API_TOKEN:
                    sent, info = _send_via_whatsapp_business('+' + ''.join([c for c in WSP_PHONE if c.isdigit()]), mensaje)
                    result['sent'] = sent
                    result['send_info'] = info
                    _log(f"envio_automatico | {cliente_email} | sent={sent} | info={info}")

    finally:
        conexion.close()

    return result

