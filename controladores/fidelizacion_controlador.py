from bd import obtener_conexion, obtener_tenant_id
import os
from datetime import datetime

try:
    import requests
except Exception:
    requests = None

# Manejo seguro del directorio de logs para compatibilidad con Vercel
if os.environ.get('VERCEL'):
    LOG_DIR = '/tmp/logs'
else:
    LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs'))

try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    pass

LOG_FILE = os.path.join(LOG_DIR, 'fidelizacion.log')
WSP_PHONE = os.environ.get('WSP_PHONE', '+51959703099')

# Configuración opcional de WhatsApp Business API
WSP_API_URL = os.environ.get('WSP_API_URL')
WSP_API_TOKEN = os.environ.get('WSP_API_TOKEN')


def registrar_visita_en_transaccion(cursor, cita_id, cliente_id, tenant_id):
    """Registra un sello una sola vez y abre una nueva cartilla al completar el ciclo."""
    cursor.execute(
        "SELECT id FROM clientes WHERE id = %s AND tenant_id = %s FOR UPDATE",
        (cliente_id, tenant_id)
    )
    if not cursor.fetchone():
        return None

    cursor.execute("""
        SELECT id, nombre, beneficio_nombre, beneficio_descripcion, sellos_objetivo
        FROM fidelizacion_programas
        WHERE tenant_id = %s AND activo = TRUE
        ORDER BY id DESC
        LIMIT 1
    """, (tenant_id,))
    programa = cursor.fetchone()
    if not programa:
        return None

    cursor.execute("""
        SELECT id, sellos
        FROM fidelizacion_cartillas
        WHERE tenant_id = %s AND cliente_id = %s AND estado = 'activa'
        FOR UPDATE
    """, (tenant_id, cliente_id))
    cartilla = cursor.fetchone()
    if not cartilla:
        cursor.execute("""
            INSERT INTO fidelizacion_cartillas (tenant_id, cliente_id)
            VALUES (%s, %s) RETURNING id, sellos
        """, (tenant_id, cliente_id))
        cartilla = cursor.fetchone()

    cursor.execute("""
        INSERT INTO fidelizacion_visitas (tenant_id, cartilla_id, cita_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (cita_id) DO NOTHING
        RETURNING id
    """, (tenant_id, cartilla[0], cita_id))
    if not cursor.fetchone():
        return {'sellos': cartilla[1], 'objetivo': programa[4], 'recompensa': None}

    nuevos_sellos = cartilla[1] + 1
    cursor.execute("""
        UPDATE fidelizacion_cartillas
        SET sellos = %s
        WHERE id = %s AND tenant_id = %s
    """, (nuevos_sellos, cartilla[0], tenant_id))

    recompensa = None
    if nuevos_sellos >= programa[4]:
        cursor.execute("""
            UPDATE fidelizacion_cartillas
            SET estado = 'completada', completed_at = CURRENT_TIMESTAMP
            WHERE id = %s AND tenant_id = %s
        """, (cartilla[0], tenant_id))
        cursor.execute("""
            INSERT INTO fidelizacion_recompensas (
                tenant_id, cliente_id, cartilla_id, beneficio_nombre, beneficio_descripcion
            ) VALUES (%s, %s, %s, %s, %s)
            RETURNING id, beneficio_nombre, beneficio_descripcion
        """, (tenant_id, cliente_id, cartilla[0], programa[2], programa[3]))
        recompensa = cursor.fetchone()
        cursor.execute("""
            INSERT INTO fidelizacion_cartillas (tenant_id, cliente_id)
            VALUES (%s, %s)
        """, (tenant_id, cliente_id))

    return {
        'sellos': 0 if recompensa else nuevos_sellos,
        'objetivo': programa[4],
        'recompensa': recompensa,
    }


def obtener_programa_activo(tenant_id=None):
    conexion = obtener_conexion()
    tenant_id = tenant_id or obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, beneficio_nombre, beneficio_descripcion, sellos_objetivo
                FROM fidelizacion_programas
                WHERE tenant_id = %s AND activo = TRUE
                ORDER BY id DESC LIMIT 1
            """, (tenant_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'id': row[0], 'nombre': row[1], 'beneficio_nombre': row[2],
                'beneficio_descripcion': row[3], 'sellos_objetivo': row[4],
            }
    finally:
        conexion.close()


def guardar_programa(beneficio_nombre, beneficio_descripcion, tenant_id=None):
    conexion = obtener_conexion()
    tenant_id = tenant_id or obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE fidelizacion_programas SET activo = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE tenant_id = %s AND activo = TRUE
            """, (tenant_id,))
            cursor.execute("""
                INSERT INTO fidelizacion_programas (
                    tenant_id, beneficio_nombre, beneficio_descripcion, sellos_objetivo
                ) VALUES (%s, %s, %s, 10)
            """, (tenant_id, beneficio_nombre.strip(), beneficio_descripcion.strip()))
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def _sincronizar_visitas_completadas(cursor, cliente_id, tenant_id):
    cursor.execute("""
        SELECT c.id
        FROM citas c
        LEFT JOIN clientes cl
          ON c.cliente_id IS NULL
         AND LOWER(cl.email) = LOWER(c.cliente_email)
         AND cl.tenant_id = c.tenant_id
        WHERE c.tenant_id = %s
          AND c.estado::text = 'completada'
          AND COALESCE(c.cliente_id, cl.id) = %s
          AND NOT EXISTS (
              SELECT 1 FROM fidelizacion_visitas fv WHERE fv.cita_id = c.id
          )
        ORDER BY c.fecha, c.hora, c.id
    """, (tenant_id, cliente_id))
    for (cita_id,) in cursor.fetchall():
        registrar_visita_en_transaccion(cursor, cita_id, cliente_id, tenant_id)


def obtener_cartillas_admin(tenant_id=None):
    conexion = obtener_conexion()
    tenant_id = tenant_id or obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT COALESCE(c.cliente_id, cl.id)
                FROM citas c
                LEFT JOIN clientes cl
                  ON c.cliente_id IS NULL
                 AND LOWER(cl.email) = LOWER(c.cliente_email)
                 AND cl.tenant_id = c.tenant_id
                WHERE c.tenant_id = %s AND c.estado::text = 'completada'
                  AND COALESCE(c.cliente_id, cl.id) IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM fidelizacion_visitas fv WHERE fv.cita_id = c.id
                  )
            """, (tenant_id,))
            clientes_pendientes = [row[0] for row in cursor.fetchall()]
            for cliente_id in clientes_pendientes:
                _sincronizar_visitas_completadas(cursor, cliente_id, tenant_id)

            cursor.execute("""
                SELECT cl.id, cl.nombre, cl.email, cl.telefono,
                       COALESCE(fc.sellos, 0), COALESCE(fp.sellos_objetivo, 10),
                       (SELECT COUNT(*) FROM fidelizacion_recompensas fr
                        WHERE fr.cliente_id = cl.id AND fr.tenant_id = cl.tenant_id
                          AND fr.estado = 'disponible'),
                       fc.created_at
                FROM clientes cl
                LEFT JOIN fidelizacion_cartillas fc
                  ON fc.cliente_id = cl.id AND fc.tenant_id = cl.tenant_id AND fc.estado = 'activa'
                LEFT JOIN fidelizacion_programas fp
                  ON fp.tenant_id = cl.tenant_id AND fp.activo = TRUE
                WHERE cl.tenant_id = %s AND COALESCE(cl.activo, TRUE) = TRUE
                ORDER BY cl.nombre
            """, (tenant_id,))
            cartillas = cursor.fetchall()

            cursor.execute("""
                SELECT fr.id, cl.nombre, fr.beneficio_nombre, fr.beneficio_descripcion,
                       fr.created_at, fr.estado
                FROM fidelizacion_recompensas fr
                JOIN clientes cl ON cl.id = fr.cliente_id AND cl.tenant_id = fr.tenant_id
                WHERE fr.tenant_id = %s
                ORDER BY fr.created_at DESC
            """, (tenant_id,))
            recompensas = cursor.fetchall()
            cursor.execute("""
                SELECT fc.id, cl.nombre, fc.sellos, fc.estado, fc.created_at,
                       fc.completed_at, COUNT(fv.id)
                FROM fidelizacion_cartillas fc
                JOIN clientes cl ON cl.id = fc.cliente_id AND cl.tenant_id = fc.tenant_id
                LEFT JOIN fidelizacion_visitas fv ON fv.cartilla_id = fc.id
                WHERE fc.tenant_id = %s
                GROUP BY fc.id, cl.nombre
                ORDER BY fc.created_at DESC
            """, (tenant_id,))
            historial_cartillas = cursor.fetchall()
            resultado = cartillas, recompensas, historial_cartillas
        conexion.commit()
        return resultado
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def obtener_cartilla_cliente(cliente_id, tenant_id=None):
    conexion = obtener_conexion()
    tenant_id = tenant_id or obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT nombre, sellos_objetivo
                FROM fidelizacion_programas
                WHERE tenant_id = %s AND activo = TRUE
                ORDER BY id DESC LIMIT 1
            """, (tenant_id,))
            programa = cursor.fetchone()
            _sincronizar_visitas_completadas(cursor, cliente_id, tenant_id)
            cursor.execute("""
                SELECT fc.sellos, COALESCE(fp.sellos_objetivo, 10), fp.nombre
                FROM fidelizacion_cartillas fc
                LEFT JOIN fidelizacion_programas fp
                  ON fp.tenant_id = fc.tenant_id AND fp.activo = TRUE
                WHERE fc.cliente_id = %s AND fc.tenant_id = %s AND fc.estado = 'activa'
            """, (cliente_id, tenant_id))
            actual = cursor.fetchone() or (0, 10, 'Cartilla de visitas')
            cursor.execute("""
                SELECT beneficio_nombre, beneficio_descripcion, estado, created_at
                FROM fidelizacion_recompensas
                WHERE cliente_id = %s AND tenant_id = %s
                ORDER BY created_at DESC
            """, (cliente_id, tenant_id))
            recompensas = cursor.fetchall()
            cartilla = {
                'sellos': actual[0], 'objetivo': actual[1], 'nombre': actual[2],
                'recompensas': recompensas, 'programa_activo': programa is not None,
            }
        conexion.commit()
        return cartilla
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def canjear_recompensa(recompensa_id, tenant_id=None):
    conexion = obtener_conexion()
    tenant_id = tenant_id or obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE fidelizacion_recompensas
                SET estado = 'canjeada', redeemed_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s AND estado = 'disponible'
                RETURNING id
            """, (recompensa_id, tenant_id))
            actualizada = cursor.fetchone() is not None
        conexion.commit()
        return actualizada
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def _log(text):
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"{now} | {text}\n"
    print(log_msg, end='')
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg)
    except Exception:
        pass


def _get_fidelizacion_row(cursor, email, tenant_id):
    cursor.execute("SELECT id, cliente_email, cliente_nombre, contador FROM fidelizacion WHERE cliente_email = %s AND tenant_id = %s", (email, tenant_id))
    return cursor.fetchone()


def _create_or_update_fidelizacion(cursor, nombre, email, tenant_id):
    row = _get_fidelizacion_row(cursor, email, tenant_id)
    if row:
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


def urlencode_text(text):
    try:
        from urllib.parse import quote_plus
        return quote_plus(text)
    except Exception:
        return text.replace(' ', '%20')


def _build_wa_url(message):
    texto = message + "\n\nMensaje automático desde MASKOT."
    encoded = urlencode_text(texto)
    phone_clean = ''.join([c for c in WSP_PHONE if c.isdigit()])
    return f"https://wa.me/{phone_clean}?text={encoded}"


def _send_via_whatsapp_business(phone, message):
    """Opcional: enviar vía WhatsApp Business API si está configurado WSP_API_URL y WSP_API_TOKEN."""
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
    """Sincroniza la tabla `fidelizacion` leyendo las citas completadas por cliente (por email)."""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
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

                cursor.execute("SELECT id, contador FROM fidelizacion WHERE cliente_email = %s AND tenant_id = %s", (email, tenant_id))
                existente = cursor.fetchone()

                if existente:
                    fid_id, contador_actual = existente[0], int(existente[1] or 0)
                    if contador_actual != total:
                        cursor.execute("UPDATE fidelizacion SET contador = %s, cliente_nombre = %s WHERE id = %s", (total, nombre, fid_id))
                else:
                    cursor.execute("INSERT INTO fidelizacion (cliente_email, cliente_nombre, contador, tenant_id) VALUES (%s, %s, %s, %s)", (email, nombre, total, tenant_id))

                # Generar alertas si corresponde
                if total >= 5:
                    telefono = _get_cliente_telefono(cursor, email, tenant_id) or 'sin teléfono'
                    mensaje_5 = f"¡Increíble! El {nombre} ha acumulado {total} citas. Tiene un 10% de descuento en su próximo baño. Contactarse a ({telefono})"
                    cursor.execute("SELECT id FROM fidelizacion_historial WHERE cliente_email=%s AND evento='alerta_5' AND tenant_id=%s ORDER BY created_at DESC LIMIT 1", (email, tenant_id))
                    row_alerta5 = cursor.fetchone()
                    if row_alerta5:
                        cursor.execute("UPDATE fidelizacion_historial SET descripcion=%s, created_at=CURRENT_TIMESTAMP WHERE id=%s", (mensaje_5, row_alerta5[0]))
                    else:
                        _insert_historial(cursor, email, 'alerta_5', mensaje_5, tenant_id)

                if total >= 10:
                    telefono = _get_cliente_telefono(cursor, email, tenant_id) or 'sin teléfono'
                    mensaje_10 = f"¡Increíble! El {nombre} ha acumulado {total} citas. Tiene un 20% de descuento en su próximo baño. Contactarse a ({telefono})"
                    cursor.execute("SELECT id FROM fidelizacion_historial WHERE cliente_email=%s AND evento='alerta_10' AND tenant_id=%s ORDER BY created_at DESC LIMIT 1", (email, tenant_id))
                    row_alerta10 = cursor.fetchone()
                    if row_alerta10:
                        cursor.execute("UPDATE fidelizacion_historial SET descripcion=%s, created_at=CURRENT_TIMESTAMP WHERE id=%s", (mensaje_10, row_alerta10[0]))
                    else:
                        _insert_historial(cursor, email, 'alerta_10', mensaje_10, tenant_id)
                    
                    cursor.execute("UPDATE fidelizacion SET contador = 0 WHERE cliente_email = %s AND tenant_id = %s", (email, tenant_id))
                    _insert_historial(cursor, email, 'reinicio', f'contador reiniciado tras alcanzar {total}', tenant_id)

            conexion.commit()
    finally:
        conexion.close()


def procesar_fidelizacion_para_cliente(cliente_nombre, cliente_email, enviar_automatico=False):
    """Procesa la fidelización incrementando contador en DB, registrando historial y devolviendo info."""
    result = {'total_citas': 0, 'wa_url': None, 'sent': False, 'send_info': None}

    if not cliente_email:
        return result

    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        with conexion.cursor() as cursor:
            total = _create_or_update_fidelizacion(cursor, cliente_nombre, cliente_email, tenant_id)
            _insert_historial(cursor, cliente_email, 'incremento', f'contador ahora {total}', tenant_id)
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

                cursor.execute("UPDATE fidelizacion SET contador = 0 WHERE cliente_email = %s AND tenant_id = %s", (cliente_email, tenant_id))
                _insert_historial(cursor, cliente_email, 'reinicio', f'contador reiniciado tras alcanzar {total}', tenant_id)
                conexion.commit()
                result['total_citas'] = 0

            _log(f"{cliente_email} | {cliente_nombre} | total_citas={total} | mensaje_needed={'yes' if mensaje else 'no'}")

            if mensaje:
                wa_url = _build_wa_url(mensaje)
                result['wa_url'] = wa_url

                if enviar_automatico and WSP_API_URL and WSP_API_TOKEN:
                    sent, info = _send_via_whatsapp_business('+' + ''.join([c for c in WSP_PHONE if c.isdigit()]), mensaje)
                    result['sent'] = sent
                    result['send_info'] = info
                    _log(f"envio_automatico | {cliente_email} | sent={sent} | info={info}")

    finally:
        conexion.close()

    return result