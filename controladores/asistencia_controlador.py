from flask import render_template, request, redirect, url_for, session, flash, jsonify
from bd import obtener_conexion, obtener_tenant_id
from datetime import datetime, date, time, timedelta

def asistencia():
    """Mostrar página de asistencia"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # admin_maskot tiene permisos completos
    usuario = session.get('usuario', '')
    if usuario == 'admin_maskot':
        session['rol'] = 'admin'
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener el registro de asistencia de hoy para el usuario actual
        hoy = date.today()
        cursor.execute("""
            SELECT id, fecha, hora_entrada, hora_salida
            FROM asistencia 
            WHERE personal_id = %s AND DATE(fecha) = %s
        """, (session['usuario_id'], hoy))
        
        asistencia_hoy = cursor.fetchone()
        
        tenant_id = obtener_tenant_id()
        # Si es admin o admin, mostrar asistencia de todos
        if session.get('rol') in ['admin']:
            cursor.execute("""
                SELECT a.id, a.personal_id, u.username,
                       a.fecha, a.hora_entrada, a.hora_salida
                FROM asistencia a
                LEFT JOIN personal p ON a.personal_id = p.id
                LEFT JOIN usuarios u ON p.usuario_id = u.id
                WHERE DATE(a.fecha) = %s AND a.tenant_id = %s
                ORDER BY a.fecha DESC, a.hora_entrada DESC
            """, (hoy, tenant_id))
            asistencias_del_dia = cursor.fetchall()
        else:
            asistencias_del_dia = []
        
        cursor.close()
        conexion.close()
        
        return render_template('asistencia.html', 
                             asistencia_hoy=asistencia_hoy,
                             asistencias_del_dia=asistencias_del_dia,
                             fecha_hoy=hoy)
    
    except Exception as e:
        flash(f'Error al cargar asistencia: {str(e)}', 'error')
        return render_template('asistencia.html', 
                             asistencia_hoy=None,
                             asistencias_del_dia=[],
                             fecha_hoy=date.today())

def marcar_entrada(personal_id=None, fecha=None, hora=None):
    """Marcar entrada del empleado.

    Firma: marcar_entrada(personal_id=None, fecha=None, hora=None)
    - Si se pasan parámetros, se usan para registrar la entrada (permitido desde llamadas internas).
    - Si no, se usa la sesión del usuario actual como antes.
    Devuelve JSON (tupla con status code cuando aplica) para uso en rutas AJAX o llamadas internas.
    """
    # Determinar personal_id desde argumentos o sesión
    if personal_id is None:
        if 'usuario_id' not in session:
            return jsonify({'error': 'No autorizado'}), 403
        personal_id = session['usuario_id']

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # Fecha a usar
        hoy = fecha if fecha is not None else date.today()

        tenant_id = obtener_tenant_id()
        # Verificar si ya marcó entrada hoy
        cursor.execute("""
            SELECT id FROM asistencia
            WHERE personal_id = %s AND DATE(fecha) = %s AND tenant_id = %s
        """, (personal_id, hoy, tenant_id))

        if cursor.fetchone():
            cursor.close()
            conexion.close()
            return jsonify({'error': 'Ya marcaste entrada hoy'}), 400

        # Registrar entrada
        ahora_dt = None
        if hora is not None:
            # hora puede venir como string 'HH:MM:SS' o como time
            try:
                if isinstance(hora, str):
                    hparts = hora.split(':')
                    ahora_dt = time(int(hparts[0]), int(hparts[1]), int(hparts[2]) if len(hparts) > 2 else 0)
                else:
                    ahora_dt = hora
            except Exception:
                ahora_dt = datetime.now().time()
        else:
            ahora_dt = datetime.now().time()

        cursor.execute("""
            INSERT INTO asistencia (personal_id, fecha, hora_entrada, tenant_id)
            VALUES (%s, %s, %s, %s)
        """, (personal_id, hoy, ahora_dt, tenant_id))

        conexion.commit()
        cursor.close()
        conexion.close()

        # Formatear mensaje con hora si tenemos datetime/time
        hora_str = ahora_dt.strftime('%H:%M') if hasattr(ahora_dt, 'strftime') else str(ahora_dt)

        return jsonify({
            'success': True,
            'message': f'Entrada marcada a las {hora_str}'
        })

    except Exception as e:
        return jsonify({'error': f'Error al marcar entrada: {str(e)}'}), 500

def marcar_salida(personal_id=None, fecha=None, hora=None):
    """Marcar salida del empleado.

    Firma: marcar_salida(personal_id=None, fecha=None, hora=None)
    - Si se pasan parámetros, se usan para buscar y registrar la salida.
    - Si no, se usa la sesión del usuario actual como antes.
    """
    if personal_id is None:
        if 'usuario_id' not in session:
            return jsonify({'error': 'No autorizado'}), 403
        personal_id = session['usuario_id']

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        tenant_id = obtener_tenant_id()
        hoy = fecha if fecha is not None else date.today()
        # Buscar registro de entrada de hoy sin salida
        cursor.execute("""
            SELECT id, hora_entrada FROM asistencia
            WHERE personal_id = %s AND DATE(fecha) = %s AND hora_salida IS NULL
            AND tenant_id = %s
        """, (personal_id, hoy, tenant_id))

        asistencia = cursor.fetchone()
        if not asistencia:
            cursor.close()
            conexion.close()
            return jsonify({'error': 'No hay registro de entrada para hoy o ya marcaste salida'}), 400

        # hora a usar
        ahora_time = None
        if hora is not None:
            try:
                if isinstance(hora, str):
                    parts = hora.split(':')
                    ahora_time = time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                else:
                    ahora_time = hora
            except Exception:
                ahora_time = datetime.now().time()
        else:
            ahora_time = datetime.now().time()

        cursor.execute("""
            UPDATE asistencia 
            SET hora_salida = %s
            WHERE id = %s
        """, (ahora_time, asistencia[0]))

        conexion.commit()
        cursor.close()
        conexion.close()

        hora_str = ahora_time.strftime('%H:%M') if hasattr(ahora_time, 'strftime') else str(ahora_time)

        return jsonify({
            'success': True,
            'message': f'Salida marcada a las {hora_str}'
        })

    except Exception as e:
        return jsonify({'error': f'Error al marcar salida: {str(e)}'}), 500

def obtener_asistencias():
    """Obtener historial de asistencias"""
    if 'usuario_id' not in session or session.get('rol') not in ['admin']:
        return jsonify({'error': 'No autorizado'}), 403
    
    try:
        fecha_desde = request.args.get('fecha_desde', date.today().strftime('%Y-%m-%d'))
        fecha_hasta = request.args.get('fecha_hasta', date.today().strftime('%Y-%m-%d'))
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        tenant_id = obtener_tenant_id()
        cursor.execute("""
            SELECT a.id, u.username, a.fecha, a.hora_entrada, a.hora_salida,
                   TIME_TO_SEC(TIMEDIFF(a.hora_salida, a.hora_entrada))/3600 as horas_trabajadas
            FROM asistencia a
            LEFT JOIN personal p ON a.personal_id = p.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            WHERE DATE(a.fecha) BETWEEN %s AND %s AND a.tenant_id = %s
            ORDER BY a.fecha DESC, a.hora_entrada DESC
        """, (fecha_desde, fecha_hasta, tenant_id))
        
        asistencias = cursor.fetchall()
        cursor.close()
        conexion.close()
        
        asistencias_list = []
        for asistencia in asistencias:
            asistencias_list.append({
                'id': asistencia[0],
                'usuario': asistencia[1],
                'fecha': asistencia[2].strftime('%Y-%m-%d'),
                'hora_entrada': str(asistencia[3]) if asistencia[3] else None,
                'hora_salida': str(asistencia[4]) if asistencia[4] else None,
                'horas_trabajadas': round(asistencia[5], 2) if asistencia[5] else 0
            })
        
        return jsonify({'asistencias': asistencias_list})
    
    except Exception as e:
        return jsonify({'error': f'Error al obtener asistencias: {str(e)}'}), 500

def obtener_resumen_asistencia():
    """Obtener resumen de asistencia por empleado"""
    if 'usuario_id' not in session or session.get('rol') not in ['admin']:
        return jsonify({'error': 'No autorizado'}), 403
    
    try:
        mes = request.args.get('mes', date.today().strftime('%Y-%m'))
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        tenant_id = obtener_tenant_id()
        cursor.execute("""
            SELECT u.username,
                   COUNT(a.id) as dias_trabajados,
                   SUM(TIME_TO_SEC(TIMEDIFF(a.hora_salida, a.hora_entrada))/3600) as total_horas,
                   AVG(TIME_TO_SEC(TIMEDIFF(a.hora_salida, a.hora_entrada))/3600) as promedio_horas_dia
            FROM usuarios u
            JOIN personal p ON u.id = p.usuario_id
            LEFT JOIN asistencia a ON p.id = a.personal_id AND DATE_FORMAT(a.fecha, '%Y-%m') = %s
            WHERE p.activo = TRUE AND p.tenant_id = %s
            GROUP BY u.id, u.username
        """, (mes, tenant_id))
        
        resumen = cursor.fetchall()
        cursor.close()
        conexion.close()
        
        resumen_list = []
        for emp in resumen:
            resumen_list.append({
                'usuario': emp[0],
                'dias_trabajados': emp[1] or 0,
                'total_horas': round(emp[2] or 0, 2),
                'promedio_horas_dia': round(emp[3] or 0, 2)
            })
        
        return jsonify({'resumen': resumen_list})
    
    except Exception as e:
        return jsonify({'error': f'Error al obtener resumen: {str(e)}'}), 500

def obtener_historial_completo():
    """Obtiene el historial completo de asistencias con información detallada"""
    conexion = obtener_conexion()
    historial = []
    try:
        cursor = conexion.cursor()
        tenant_id = obtener_tenant_id()
        cursor.execute("""
            SELECT 
                a.id,
                a.fecha,
                a.hora_entrada,
                a.hora_salida,
                u.username,
                COALESCE(p.cargo, 'Empleado') as cargo,
                CASE 
                    WHEN a.hora_entrada IS NOT NULL AND a.hora_salida IS NOT NULL THEN
                        CONCAT(
                            FLOOR(TIME_TO_SEC(TIMEDIFF(a.hora_salida, a.hora_entrada))/3600), 'h ',
                            FLOOR((TIME_TO_SEC(TIMEDIFF(a.hora_salida, a.hora_entrada))%3600)/60), 'm'
                        )
                    ELSE NULL
                END as horas_trabajadas
            FROM asistencia a
            LEFT JOIN personal p ON a.personal_id = p.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            WHERE u.username IS NOT NULL AND a.tenant_id = %s
            ORDER BY a.fecha DESC, a.hora_entrada DESC
        """, (tenant_id,))
        historial = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Error en obtener_historial_completo: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return historial

def obtener_asistencia_por_personal_y_fecha(personal_id, fecha):
    """Obtiene el registro de asistencia de un empleado en una fecha específica"""
    conexion = obtener_conexion()
    asistencia = None
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id, personal_id, fecha, hora_entrada, hora_salida
            FROM asistencia 
            WHERE personal_id = %s AND DATE(fecha) = %s
        """, (personal_id, fecha))
        asistencia = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(f"Error al obtener asistencia por personal y fecha: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return asistencia