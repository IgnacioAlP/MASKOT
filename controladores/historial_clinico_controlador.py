"""Consultas y registros del historial clínico de mascotas."""

from bd import obtener_conexion, obtener_tenant_id


def asegurar_tabla_historial(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_clinico (
            id SERIAL PRIMARY KEY,
            mascota_id INTEGER NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
            fecha_visita DATE NOT NULL DEFAULT CURRENT_DATE,
            servicio VARCHAR(255) NOT NULL,
            diagnostico TEXT,
            tratamiento TEXT,
            indicaciones TEXT,
            proxima_cita DATE,
            tenant_id INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)


def obtener_mascotas_con_alertas(tenant_id=None):
    tenant_id = tenant_id if tenant_id is not None else obtener_tenant_id()
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT m.id, m.nombre, m.especie, COALESCE(m.raza, ''),
                                             COALESCE(c.nombre, 'Sin dueño'), COALESCE(c.telefono, ''),
                                             (SELECT MIN(proxima.fecha)
                                                FROM (
                                                        SELECT ci.fecha
                                                        FROM citas ci
                                                        LEFT JOIN citas_mascotas cm ON cm.cita_id = ci.id
                                                        WHERE ci.tenant_id = m.tenant_id
                                                            AND (cm.mascota_id = m.id OR
                                                                     (cm.mascota_id IS NULL AND ci.mascota_nombre = m.nombre
                                                                        AND (ci.cliente_id IS NULL OR ci.cliente_id = m.cliente_id)))
                                                            AND ci.fecha >= CURRENT_DATE
                                                            AND ci.estado::text NOT IN ('cancelada', 'completada')
                                                        UNION ALL
                                                        SELECT hc.proxima_cita
                                                        FROM historial_clinico hc
                                                        WHERE hc.mascota_id = m.id AND hc.tenant_id = m.tenant_id
                                                            AND hc.proxima_cita >= CURRENT_DATE
                                                ) proxima),
                       (SELECT COUNT(*) FROM historial_clinico hc
                        WHERE hc.mascota_id = m.id AND hc.tenant_id = m.tenant_id)
                                                 + (SELECT COUNT(DISTINCT ci.id) FROM citas ci
                                                        LEFT JOIN citas_mascotas cm ON cm.cita_id = ci.id
                                                        WHERE ci.tenant_id = m.tenant_id
                                                            AND (cm.mascota_id = m.id OR
                                                                     (cm.mascota_id IS NULL AND ci.mascota_nombre = m.nombre
                                                                        AND (ci.cliente_id IS NULL OR ci.cliente_id = m.cliente_id)))
                                                            AND ci.fecha <= CURRENT_DATE AND ci.estado::text <> 'cancelada')
                FROM mascotas m
                LEFT JOIN clientes c ON c.id = m.cliente_id
                WHERE m.tenant_id = %s AND m.activo = TRUE
                ORDER BY m.nombre
            """, (tenant_id,))
            return cursor.fetchall()
    finally:
        conexion.close()


def obtener_mascota_historial(mascota_id, tenant_id=None):
    tenant_id = tenant_id if tenant_id is not None else obtener_tenant_id()
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT m.id, m.nombre, m.especie, COALESCE(m.raza, ''),
                       COALESCE(m.edad, 0), COALESCE(m.peso, 0),
                       COALESCE(c.nombre, 'Sin dueño'), COALESCE(c.telefono, '')
                FROM mascotas m
                LEFT JOIN clientes c ON c.id = m.cliente_id
                WHERE m.id = %s AND m.tenant_id = %s AND m.activo = TRUE
            """, (mascota_id, tenant_id))
            mascota = cursor.fetchone()
            if not mascota:
                return None, []

            cursor.execute("""
                SELECT fecha_visita, servicio, diagnostico, tratamiento, indicaciones,
                       proxima_cita, created_at
                FROM historial_clinico
                WHERE mascota_id = %s AND tenant_id = %s
                ORDER BY fecha_visita DESC, id DESC
            """, (mascota_id, tenant_id))
            visitas = [{
                'fecha': row[0], 'servicio': row[1], 'diagnostico': row[2] or '',
                'tratamiento': row[3] or '', 'indicaciones': row[4] or '',
                'proxima_cita': row[5], 'origen': 'Registro clínico'
            } for row in cursor.fetchall()]

            cursor.execute("""
                SELECT ci.fecha, ci.hora,
                       COALESCE(string_agg(DISTINCT s.nombre, ', '), MAX(servicio_principal.nombre), 'Sin servicio'),
                       COALESCE(ci.observaciones, ''), ci.estado::text
                FROM citas ci
                LEFT JOIN citas_mascotas cm ON cm.cita_id = ci.id
                LEFT JOIN citas_servicios cs ON cs.cita_id = ci.id
                LEFT JOIN servicios s ON s.id = cs.servicio_id
                LEFT JOIN servicios servicio_principal ON servicio_principal.id = ci.servicio_id
                     WHERE ci.tenant_id = %s
                        AND (cm.mascota_id = %s OR
                              (cm.mascota_id IS NULL AND ci.mascota_nombre = %s
                                AND (ci.cliente_id IS NULL OR ci.cliente_id =
                                      (SELECT cliente_id FROM mascotas WHERE id = %s AND tenant_id = %s))))
                  AND (ci.fecha <= CURRENT_DATE OR ci.estado::text = 'completada')
                  AND ci.estado::text <> 'cancelada'
                GROUP BY ci.id, ci.fecha, ci.hora, ci.observaciones, ci.estado
                ORDER BY ci.fecha DESC, ci.hora DESC
            """, (tenant_id, mascota_id, mascota[1], mascota_id, tenant_id))
            for row in cursor.fetchall():
                visitas.append({
                    'fecha': row[0], 'servicio': row[2], 'diagnostico': row[3],
                    'tratamiento': '', 'indicaciones': '', 'proxima_cita': None,
                    'origen': f"Cita {row[4] or ''}".strip()
                })

            visitas.sort(key=lambda visita: (visita['fecha'] or '', visita['origen']), reverse=True)
            return mascota, visitas
    finally:
        conexion.close()


def registrar_visita(mascota_id, fecha_visita, servicio, diagnostico='', tratamiento='',
                     indicaciones='', proxima_cita=None, tenant_id=None):
    tenant_id = tenant_id if tenant_id is not None else obtener_tenant_id()
    if not servicio or not fecha_visita:
        return {'success': False, 'error': 'La fecha y el servicio son obligatorios.'}

    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM mascotas
                WHERE id = %s AND tenant_id = %s AND activo = TRUE
            """, (mascota_id, tenant_id))
            if not cursor.fetchone():
                return {'success': False, 'error': 'No se encontró la mascota en este local.'}
            cursor.execute("""
                INSERT INTO historial_clinico (
                    mascota_id, fecha_visita, servicio, diagnostico, tratamiento,
                    indicaciones, proxima_cita, tenant_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (mascota_id, fecha_visita, servicio.strip(), diagnostico or None,
                  tratamiento or None, indicaciones or None, proxima_cita or None, tenant_id))
            visita_id = cursor.fetchone()[0]
            conexion.commit()
            return {'success': True, 'visita_id': visita_id}
    except Exception as e:
        if conexion:
            conexion.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        if conexion:
            conexion.close()