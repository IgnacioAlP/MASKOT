import os
import sys
import json
import time
import logging
import hashlib
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, 
    session, flash, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename

# Conexión a Base de Datos
from bd import obtener_conexion, obtener_tenant_id

# Importar todos los controladores
from controladores import (
    usuarios_controlador,
    citas_controlador,
    servicios_controlador,
    personal_controlador,
    productos_controlador,
    asistencia_controlador,
    clientes_controlador,
    compras_controlador,
    ventas_controlador,
    mascotas_controlador
)
from controladores import fidelizacion_controlador as fidelizacion_ctrl

# ─── CONFIGURACIÓN DE LA APLICACIÓN ──────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # MASKOT/api
ROOT_DIR = os.path.dirname(BASE_DIR)                   # MASKOT

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, 'templates'),
    static_folder=os.path.join(ROOT_DIR, 'static'),
    static_url_path='/static'
)

# Configuración de cookies de sesión seguras
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_veterinaria')
use_secure_cookies = os.environ.get('FLASK_ENV', '').lower() == 'production' or os.environ.get('USE_SECURE_COOKIES', '') == 'True'
app.config['SESSION_COOKIE_SECURE'] = bool(use_secure_cookies)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    pass

# Almacenamiento temporal en memoria para escáner en tiempo real
RECENT_SCANS = []


def _ensure_schema():
    """Migración ligera al arranque adaptada para PostgreSQL / Supabase."""
    column_migrations = [
        ("productos", "codigo_barra", "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo_barra VARCHAR(100) DEFAULT NULL"),
        ("productos", "stock_minimo", "ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INT DEFAULT 5"),
        ("citas",     "tenant_id",   "ALTER TABLE citas ADD COLUMN IF NOT EXISTS tenant_id INT DEFAULT 1"),
        ("ventas",    "tenant_id",   "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tenant_id INT DEFAULT 1"),
        ("ventas",    "vendedor_id", "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS vendedor_id INT DEFAULT NULL"),
        ("ventas",    "productos",   "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS productos TEXT DEFAULT '[]'"),
    ]
    try:
        conn = obtener_conexion()
        with conn.cursor() as cursor:
            for table, column, sql in column_migrations:
                cursor.execute("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                """, (table, column))
                if not cursor.fetchone():
                    cursor.execute(sql)
                    conn.commit()
                    logger.info(f"Schema migration: columna '{column}' añadida a {table}.")

            # Permitir NULL en vendedor_nombre y vendedor_id
            for col in ['vendedor_nombre', 'vendedor_id']:
                cursor.execute("""
                    SELECT is_nullable FROM information_schema.columns 
                    WHERE table_name = 'ventas' AND column_name = %s
                """, (col,))
                v_col = cursor.fetchone()
                if v_col and (v_col[0] or '').upper() == 'NO':
                    cursor.execute(f"ALTER TABLE ventas ALTER COLUMN {col} DROP NOT NULL")
                    conn.commit()

        conn.close()
    except Exception as e:
        logger.warning(f"Schema migration check failed: {e}")


try:
    _ensure_schema()
except Exception:
    pass


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Error no controlado: {e}")
    return render_template('error.html'), 500


# ─── FILTROS Y CONTEXT PROCESSORS DE TEMPLATES ──────────────────────────────

@app.template_filter('dateformat')
def dateformat(value, format='%d/%m/%Y'):
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return value
    elif isinstance(value, datetime):
        value = value.date()
    
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    return str(value)


@app.template_filter('days_until')
def days_until(value):
    if value is None:
        return 999
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return 999
    elif isinstance(value, datetime):
        value = value.date()
    
    if hasattr(value, '__sub__'):
        today_d = date.today()
        delta = value - today_d
        return delta.days
    return 999


@app.context_processor
def utility_processor():
    def format_date(date_value, format='%d/%m/%Y'):
        if date_value is None:
            return ""
        if isinstance(date_value, str):
            try:
                date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
            except Exception:
                return date_value
        elif isinstance(date_value, datetime):
            date_value = date_value.date()
        
        if hasattr(date_value, 'strftime'):
            return date_value.strftime(format)
        return str(date_value)
    
    def today():
        return date.today()
    
    def today_string():
        return date.today().strftime('%Y-%m-%d')
    
    def days_difference(date1, date2=None):
        if date2 is None:
            date2 = date.today()
        if isinstance(date1, str):
            try:
                date1 = datetime.strptime(date1, '%Y-%m-%d').date()
            except Exception:
                return 999
        elif isinstance(date1, datetime):
            date1 = date1.date()
        return (date1 - date2).days
    
    def calculate_work_hours(entrada, salida):
        if not entrada or not salida:
            return 0
        try:
            if isinstance(entrada, str):
                entrada = datetime.strptime(entrada, '%H:%M:%S').time()
            if isinstance(salida, str):
                salida = datetime.strptime(salida, '%H:%M:%S').time()
            
            today_date = date.today()
            entrada_dt = datetime.combine(today_date, entrada)
            salida_dt = datetime.combine(today_date, salida)
            
            delta = salida_dt - entrada_dt
            return round(delta.total_seconds() / 3600, 1)
        except Exception:
            return 0
    
    return dict(
        format_date=format_date, 
        today=today, 
        today_string=today_string, 
        days_difference=days_difference,
        calculate_work_hours=calculate_work_hours
    )


@app.context_processor
def cart_context():
    cart = session.get('cart', {})
    total_qty = 0
    try:
        for v in cart.values():
            total_qty += int(v.get('qty', 0))
    except Exception:
        total_qty = 0
    return dict(cart_count=total_qty)


@app.context_processor
def inject_global_datetime():
    ahora = datetime.now()
    return {
        'momento_actual': ahora,
        'today': date.today,
        'now': ahora,
        'format_date': lambda d: d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') else str(d)
    }


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def requiere_autenticacion(roles_permitidos=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'usuario' not in session or 'rol' not in session:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('login'))
            
            if session['rol'] == 'superadmin':
                return f(*args, **kwargs)
            
            if roles_permitidos and session['rol'] not in roles_permitidos:
                flash('No tienes permisos para acceder a esta página.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'maskot-favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# ─── AUTENTICACIÓN Y SESIÓN ──────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'rol' in session and session.get('rol') in ['dueño', 'admin', 'empleado', 'superadmin']:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        next_url = request.args.get('next') or request.form.get('next')

        if not username or not password:
            flash('Por favor complete todos los campos.', 'warning')
            return render_template('login.html')
        
        try:
            auth = usuarios_controlador.verificar_credenciales(username, password)
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            flash('Error interno del sistema', 'error')
            return render_template('login.html')
            
        if not auth.get('success'):
            flash(auth.get('message', 'Credenciales inválidas'), 'error')
            return render_template('login.html')
            
        user = auth.get('user')
        session.permanent = True
        session['user_id'] = user[0]
        session['usuario_id'] = user[0]
        session['usuario'] = user[1]
        session['rol'] = user[3]
        session['tenant_id'] = user[5] if len(user) > 5 and user[5] else 1
        
        flash(f"¡Bienvenido de nuevo, {user[1]}!", 'success')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        
        if user[3] == 'superadmin':
            return redirect(url_for('gestionar_tenants'))
            
        return redirect(url_for('dashboard'))
            
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    rol = session['rol']
    hoy = date.today().strftime('%Y-%m-%d')
    
    citas_hoy = []
    alertas_fidelizacion = []
    
    if rol in ['admin', 'empleado', 'dueño']:
        try:
            citas_hoy = citas_controlador.obtener_citas_por_fecha(hoy)
        except Exception as e:
            logger.warning(f"Error obteniendo citas de hoy: {e}")
            
        try:
            if hasattr(fidelizacion_ctrl, 'sincronizar_fidelizacion_desde_citas'):
                fidelizacion_ctrl.sincronizar_fidelizacion_desde_citas()
            if hasattr(fidelizacion_ctrl, 'obtener_alertas_recientes'):
                alertas_fidelizacion = fidelizacion_ctrl.obtener_alertas_recientes(limit=10)
        except Exception as e:
            logger.warning(f"Error fidelización: {e}")
    
    if rol == 'dueño':
        total_empleados = 0
        servicios_activos = 0
        productos_bajos = []
        
        try:
            if hasattr(personal_controlador, 'obtener_personal'):
                total_empleados = len(personal_controlador.obtener_personal())
            elif hasattr(personal_controlador, 'obtener_empleados'):
                total_empleados = len(personal_controlador.obtener_empleados())
        except Exception as e:
            logger.warning(f"Error personal dashboard: {e}")

        try:
            if hasattr(servicios_controlador, 'obtener_servicios_activos'):
                servicios_activos = len(servicios_controlador.obtener_servicios_activos())
            elif hasattr(servicios_controlador, 'obtener_servicios'):
                servicios_activos = len(servicios_controlador.obtener_servicios())
        except Exception as e:
            logger.warning(f"Error servicios dashboard: {e}")

        try:
            if hasattr(productos_controlador, 'obtener_productos_bajo_stock'):
                productos_bajos = productos_controlador.obtener_productos_bajo_stock()
        except Exception as e:
            logger.warning(f"Error productos stock bajo dashboard: {e}")
        
        return render_template('dashboard.html', citas_hoy=citas_hoy, total_empleados=total_empleados,
                               servicios_activos=servicios_activos, productos_bajos=productos_bajos,
                               alertas_fidelizacion=alertas_fidelizacion)
    
    return render_template('dashboard.html', citas_hoy=citas_hoy, alertas_fidelizacion=alertas_fidelizacion)


# ─── VISTA PRINCIPAL DEL PUNTO DE VENTA (POS) ─────────────────────────────────

# ─── VISTA PRINCIPAL DEL PUNTO DE VENTA (POS) ─────────────────────────────────

@app.route('/punto_de_venta', methods=['GET', 'POST'])
@app.route('/pos', methods=['GET', 'POST'])
def punto_de_venta():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado al punto de venta.', 'error')
        return redirect(url_for('dashboard'))
    
    tenant_id = session.get('tenant_id', 1)
    productos_lista = []
    servicios_lista = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # 1. Obtener SOLO productos de tipo 'venta' y activos
            cursor.execute("""
                SELECT 
                    id,                                           -- 0
                    nombre,                                       -- 1
                    COALESCE(precio, 0.00) AS precio,             -- 2
                    COALESCE(cantidad, 0) AS cantidad,            -- 3
                    COALESCE(codigo_barra, '') AS codigo_barra,   -- 4
                    'General' AS categoria,                       -- 5
                    COALESCE(imagen, '') AS imagen                -- 6
                FROM productos
                WHERE (tenant_id = %s OR tenant_id IS NULL) 
                  AND COALESCE(activo, true) = true
                  AND LOWER(tipo::text) = 'venta'
                ORDER BY nombre ASC
            """, (tenant_id,))
            
            for r in cursor.fetchall():
                p_id = r[0]
                p_nom = r[1] or ''
                
                try:
                    p_prec = float(r[2])
                except (ValueError, TypeError):
                    p_prec = 0.0
                
                try:
                    p_stk = int(r[3])
                except (ValueError, TypeError):
                    p_stk = 0
                
                p_code = str(r[4]) if r[4] else ''
                p_cat = str(r[5])
                p_img = str(r[6]) if r[6] else ''

                productos_lista.append({
                    'id': p_id,
                    'nombre': p_nom,
                    'precio': p_prec,
                    'stock': p_stk,
                    'cantidad': p_stk,
                    'codigo_barra': p_code,
                    'categoria': p_cat,
                    'imagen': p_img,
                    0: p_id,
                    1: p_nom,
                    2: p_prec,
                    3: p_stk,
                    4: p_code,
                    5: p_cat,
                    6: p_img
                })

            # 2. Obtener servicios según la estructura de Supabase
            cursor.execute("""
                SELECT 
                    id, 
                    nombre, 
                    COALESCE(precio, 0.00) AS precio, 
                    COALESCE(duracion, 0) AS duracion
                FROM servicios
                WHERE (tenant_id = %s OR tenant_id IS NULL) 
                  AND COALESCE(activo, true) = true
                ORDER BY nombre ASC
            """, (tenant_id,))
            
            for s in cursor.fetchall():
                s_id = s[0]
                s_nom = s[1] or ''
                try:
                    s_prec = float(s[2])
                except (ValueError, TypeError):
                    s_prec = 0.0
                s_dur = f"{s[3]} min" if s[3] else ''

                servicios_lista.append({
                    'id': s_id,
                    'nombre': s_nom,
                    'precio': s_prec,
                    'duracion': s_dur,
                    0: s_id,
                    1: s_nom,
                    2: s_prec,
                    3: s_dur,
                    5: True
                })

        conexion.close()
    except Exception as e:
        logger.error(f"Error consultando productos/servicios para el POS: {e}")

    return render_template('pos.html', productos=productos_lista, servicios=servicios_lista)


# ─── API POS & BÚSQUEDA POR CÓDIGO DE BARRAS / NOMBRE ───────────────────────
@app.route('/api/ventas/buscar-productos')
def api_buscar_productos():
    q = request.args.get('q', '').strip()
    tenant_id = session.get('tenant_id', 1)
    
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            if q:
                query_like = f"%{q}%"
                cursor.execute("""
                    SELECT id, nombre, precio, cantidad, COALESCE(codigo_barra, ''), 'General' AS categoria
                    FROM productos 
                    WHERE (tenant_id = %s OR tenant_id IS NULL)
                      AND COALESCE(activo, true) = true
                      AND LOWER(tipo::text) = 'venta'
                      AND (nombre ILIKE %s OR codigo_barra ILIKE %s OR codigo_barra = %s)
                    ORDER BY nombre ASC
                    LIMIT 30
                """, (tenant_id, query_like, query_like, q))
            else:
                cursor.execute("""
                    SELECT id, nombre, precio, cantidad, COALESCE(codigo_barra, ''), 'General' AS categoria
                    FROM productos 
                    WHERE (tenant_id = %s OR tenant_id IS NULL)
                      AND COALESCE(activo, true) = true
                      AND LOWER(tipo::text) = 'venta'
                    ORDER BY nombre ASC
                    LIMIT 50
                """, (tenant_id,))
            
            rows = cursor.fetchall()
            productos = [{
                'id': r[0],
                'nombre': r[1],
                'precio': float(r[2]) if r[2] is not None else 0.0,
                'stock': int(r[3]) if r[3] is not None else 0,
                'codigo_barra': r[4] or '',
                'categoria': r[5]
            } for r in rows]

        conexion.close()
        return jsonify({'success': True, 'productos': productos})
    except Exception as e:
        logger.error(f"Error buscando productos POS: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ventas/validar-stock', methods=['POST'])
def api_validar_stock():
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    errores = []
    
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            for item in items:
                pid = item.get('id')
                cant = int(item.get('cantidad', 1))
                if pid and str(pid).isdigit():
                    cursor.execute("SELECT nombre, cantidad FROM productos WHERE id = %s", (int(pid),))
                    row = cursor.fetchone()
                    if not row:
                        errores.append(f"Producto ID {pid} no encontrado.")
                    elif (row[1] or 0) < cant:
                        errores.append(f"Stock insuficiente para '{row[0]}'. Disponible: {row[1]}, Solicitado: {cant}")
        conexion.close()
        
        if errores:
            return jsonify({'success': False, 'message': 'Validación fallida', 'errors': errores}), 400
        return jsonify({'success': True, 'message': 'Stock verificado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── PROCESAMIENTO DE VENTAS POS ─────────────────────────────────────────────

@app.route('/ventas/procesar', methods=['POST'])
def procesar_venta_pos():
    if 'rol' not in session:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        
        items = data.get('items') or data.get('productos') or data.get('cart')
        if not items and request.form.get('items'):
            try:
                items = json.loads(request.form.get('items'))
            except Exception:
                items = []
                
        if not items and request.form.get('cart'):
            try:
                items = json.loads(request.form.get('cart'))
            except Exception:
                items = []

        if not items:
            cart = session.get('cart', {})
            items = [{'id': k, 'cantidad': v.get('qty', 1), 'precio': 0.0} for k, v in cart.items()]
        
        if not items:
            return jsonify({'success': False, 'error': 'El carrito está vacío'}), 400

        cliente_nombre = data.get('cliente_nombre') or request.form.get('cliente_nombre', 'Cliente General')
        cliente_doc = data.get('cliente_documento') or request.form.get('cliente_documento', '')
        metodo_pago = data.get('metodo_pago') or request.form.get('metodo_pago', 'efectivo')
        
        monto_recibido = float(data.get('monto_recibido') or request.form.get('monto_recibido', 0.0))
        subtotal = float(data.get('subtotal') or request.form.get('subtotal', 0.0))
        igv = float(data.get('igv') or request.form.get('igv', 0.0))
        total = float(data.get('total') or request.form.get('total', 0.0))
        cambio = float(data.get('cambio') or request.form.get('cambio', 0.0))

        vendedor_id = session.get('usuario_id') or session.get('user_id')
        vendedor_nombre = session.get('usuario') or session.get('username') or 'Cajero'
        tenant_id = session.get('tenant_id', 1)
        num_venta = f"VNT-{int(time.time())}"
        
        productos_json = json.dumps(items, ensure_ascii=False)
        
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ventas (
                    numero_venta, fecha_venta, cliente_nombre, cliente_documento, 
                    vendedor_id, vendedor_nombre, metodo_pago, subtotal, igv, total, 
                    monto_recibido, cambio_entregado, productos, estado, tenant_id
                ) VALUES (
                    %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completada'::estado_venta_enum, %s
                ) RETURNING id
            """, (
                num_venta, cliente_nombre, cliente_doc, vendedor_id, vendedor_nombre, metodo_pago,
                subtotal, igv, total, monto_recibido, cambio, productos_json, tenant_id
            ))
            
            venta_id = cursor.fetchone()[0]
            
            # Actualización de existencias en la columna 'cantidad' de la tabla productos
            for item in items:
                pid = item.get('id')
                cant = int(item.get('cantidad', item.get('qty', 1)))
                if pid and str(pid).isdigit():
                    cursor.execute("""
                        UPDATE productos 
                        SET cantidad = GREATEST(COALESCE(cantidad, 0) - %s, 0) 
                        WHERE id = %s
                    """, (cant, int(pid)))
                
        conexion.commit()
        conexion.close()
        
        session.pop('cart', None)
        ticket_url = url_for('ticket_venta', venta_id=venta_id) if 'ticket_venta' in app.view_functions else f"/venta/ticket/{venta_id}"
        return jsonify({'success': True, 'venta_id': venta_id, 'ticket_url': ticket_url})
    except Exception as e:
        logger.error(f"Error procesando venta POS: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/ventas/scan-push', methods=['POST'])
def scan_push():
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    if code:
        RECENT_SCANS.append({'code': code, 'timestamp': time.time()})
        if len(RECENT_SCANS) > 20:
            RECENT_SCANS.pop(0)
        return jsonify({'success': True, 'code': code})
    return jsonify({'success': False, 'error': 'Código no enviado'}), 400


@app.route('/ventas/scan-poll')
def scan_poll():
    last_time = float(request.args.get('since', 0))
    scans = [s for s in RECENT_SCANS if s['timestamp'] > last_time]
    return jsonify({'success': True, 'scans': scans, 'timestamp': time.time()})


# ─── HISTORIAL DE VENTAS ──────────────────────────────────────────────────────

@app.route('/historial_ventas', endpoint='historial_ventas')
@app.route('/historial-ventas')
@app.route('/ventas/historial')
def historial_ventas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    tenant_id = session.get('tenant_id', 1)
    
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    busqueda = request.args.get('busqueda', '').strip()
    
    filtros = {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'busqueda': busqueda
    }
    
    ventas_lista = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            condiciones = ["(v.tenant_id = %s OR v.tenant_id IS NULL)"]
            params = [tenant_id]

            if fecha_inicio:
                condiciones.append("v.fecha_venta >= %s")
                params.append(f"{fecha_inicio} 00:00:00")

            if fecha_fin:
                condiciones.append("v.fecha_venta <= %s")
                params.append(f"{fecha_fin} 23:59:59")

            if busqueda:
                condiciones.append("(v.numero_venta ILIKE %s OR v.cliente_nombre ILIKE %s OR v.cliente_documento ILIKE %s)")
                param_like = f"%{busqueda}%"
                params.extend([param_like, param_like, param_like])

            where_clause = " AND ".join(condiciones)

            query = f"""
                SELECT 
                    v.id,                                                 -- 0
                    v.numero_venta,                                       -- 1
                    TO_CHAR(v.fecha_venta, 'DD/MM/YYYY HH12:MI AM') AS fecha,-- 2
                    COALESCE(v.cliente_nombre, 'Cliente General') AS cliente, -- 3
                    COALESCE(v.cliente_documento, '') AS doc,             -- 4
                    COALESCE(v.vendedor_nombre, 'Cajero') AS vendedor,    -- 5
                    COALESCE(v.metodo_pago, 'efectivo') AS pago,          -- 6
                    COALESCE(v.subtotal, 0.00) AS subtotal,               -- 7
                    COALESCE(v.igv, 0.00) AS igv,                         -- 8
                    COALESCE(v.total, 0.00) AS total,                     -- 9
                    COALESCE(v.estado::text, 'completada') AS estado      -- 10
                FROM ventas v
                WHERE {where_clause}
                ORDER BY v.fecha_venta DESC
                LIMIT 200
            """
            
            cursor.execute(query, tuple(params))
            
            for r in cursor.fetchall():
                v_id = r[0]
                v_num = r[1] or ''
                v_fecha = r[2] or ''
                v_cliente = r[3]
                v_doc = r[4]
                v_vendedor = r[5]
                v_pago = r[6]
                v_subtotal = float(r[7]) if r[7] is not None else 0.0
                v_igv = float(r[8]) if r[8] is not None else 0.0
                v_total = float(r[9]) if r[9] is not None else 0.0
                v_estado = str(r[10]).lower()

                ventas_lista.append({
                    'id': v_id,
                    'numero_venta': v_num,
                    'fecha_venta': v_fecha,
                    'cliente_nombre': v_cliente,
                    'cliente_documento': v_doc,
                    'vendedor_nombre': v_vendedor,
                    'metodo_pago': v_pago,
                    'subtotal': v_subtotal,
                    'igv': v_igv,
                    'total': v_total,
                    'estado': v_estado,
                    0: v_id,
                    1: v_num,
                    2: v_fecha,
                    3: v_cliente,
                    4: v_doc,
                    5: v_vendedor,
                    6: v_pago,
                    7: v_subtotal,
                    8: v_igv,
                    9: v_total,
                    10: v_estado
                })

        conexion.close()
    except Exception as e:
        logger.error(f"Error consultando historial de ventas: {e}")

    return render_template('historial_ventas.html', ventas=ventas_lista, filtros=filtros)


# ─── VISTA Y GENERACIÓN DE TICKET DE VENTA ───────────────────────────────────

@app.route('/venta/ticket/<int:venta_id>', endpoint='ticket_venta')
@app.route('/ventas/ticket/<int:venta_id>')
def ticket_venta(venta_id):
    if 'rol' not in session:
        return redirect(url_for('login'))

    tenant_id = session.get('tenant_id', 1)
    venta = None
    items = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    v.id,                                                 -- 0
                    v.numero_venta,                                       -- 1
                    TO_CHAR(v.fecha_venta, 'DD/MM/YYYY HH12:MI AM') AS fecha,-- 2
                    COALESCE(v.cliente_nombre, 'Cliente General') AS cliente, -- 3
                    COALESCE(v.cliente_documento, '-') AS doc,            -- 4
                    COALESCE(v.vendedor_nombre, 'Cajero') AS vendedor,    -- 5
                    COALESCE(v.metodo_pago, 'Efectivo') AS pago,          -- 6
                    COALESCE(v.subtotal, 0.00) AS subtotal,               -- 7
                    COALESCE(v.igv, 0.00) AS igv,                         -- 8
                    COALESCE(v.total, 0.00) AS total,                     -- 9
                    COALESCE(v.monto_recibido, 0.00) AS recibido,         -- 10
                    COALESCE(v.cambio_entregado, 0.00) AS cambio,         -- 11
                    COALESCE(v.estado::text, 'completada') AS estado,     -- 12
                    v.productos                                           -- 13 (JSON/Text)
                FROM ventas v
                WHERE v.id = %s AND (v.tenant_id = %s OR v.tenant_id IS NULL)
            """, (venta_id, tenant_id))
            
            r = cursor.fetchone()
            if r:
                subtotal_f = float(r[7]) if r[7] is not None else 0.0
                igv_f = float(r[8]) if r[8] is not None else 0.0
                total_f = float(r[9]) if r[9] is not None else 0.0
                recibido_f = float(r[10]) if r[10] is not None else 0.0
                cambio_f = float(r[11]) if r[11] is not None else 0.0

                venta = {
                    'id': r[0],
                    'numero_venta': r[1],
                    'fecha_venta': r[2],
                    'cliente_nombre': r[3],
                    'cliente_documento': r[4],
                    'vendedor_nombre': r[5],
                    'metodo_pago': r[6],
                    'subtotal': subtotal_f,
                    'igv': igv_f,
                    'total': total_f,
                    'monto_recibido': recibido_f,
                    'cambio_entregado': cambio_f,
                    'estado': str(r[12]).lower(),
                    0: r[0], 1: r[1], 2: r[2], 3: r[3], 4: r[4], 5: r[5],
                    6: r[6], 7: subtotal_f, 8: igv_f, 9: total_f, 10: recibido_f, 11: cambio_f, 12: str(r[12]).lower()
                }

                raw_productos = r[13]

                # Decodificación directa del campo JSON 'productos' guardado en la venta
                if raw_productos:
                    try:
                        p_list = json.loads(raw_productos) if isinstance(raw_productos, str) else raw_productos
                        for p in p_list:
                            cant = int(p.get('cantidad', p.get('qty', 1)))
                            pu = float(p.get('precio', p.get('precio_unitario', 0.0)))
                            items.append({
                                'nombre': p.get('nombre', p.get('title', 'Producto / Servicio')),
                                'cantidad': cant,
                                'precio_unitario': pu,
                                'subtotal': cant * pu
                            })
                    except Exception as ex_json:
                        logger.warning(f"No se pudo decodificar JSON de productos para venta {venta_id}: {ex_json}")

        conexion.close()
    except Exception as e:
        logger.error(f"Error generando ticket para venta ID={venta_id}: {e}")

    if not venta:
        flash('La venta solicitada no existe o fue eliminada.', 'error')
        return redirect(url_for('historial_ventas'))

    return render_template('ticket_venta.html', venta=venta, items=items, momento_actual=datetime.now())


# ─── INVENTARIO & ALMACÉN ───────────────────────────────────────────────────

@app.route('/productos')
def productos():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = productos_controlador.obtener_productos() if hasattr(productos_controlador, 'obtener_productos') else []
    return render_template('productos.html', productos=lista)


@app.route('/almacen', methods=['GET', 'POST'])
@app.route('/productos/agregar', methods=['POST'], endpoint='agregar_producto')
@app.route('/productos/editar', methods=['POST'], endpoint='editar_producto')
def almacen():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            raw_id = (request.form.get('id') or 
                      request.form.get('producto_id') or 
                      request.form.get('edit_id') or 
                      request.form.get('id_producto') or '').strip()
            
            producto_id = int(raw_id) if raw_id and raw_id.isdigit() else None

            nombre = request.form.get('nombre', '').strip()
            codigo_barra = request.form.get('codigo_barra', '').strip() or None
            tipo = request.form.get('tipo', 'stock').strip().lower()

            precio_raw = request.form.get('precio', '').strip()
            precio = float(precio_raw) if precio_raw else 0.0

            cantidad_raw = request.form.get('stock', request.form.get('cantidad', '')).strip()
            cantidad = int(cantidad_raw) if cantidad_raw else 0

            stk_min_raw = (request.form.get('stock_minimo') or 
                           request.form.get('cant_min') or 
                           request.form.get('stock_min') or '').strip()
            stock_minimo = int(stk_min_raw) if stk_min_raw and stk_min_raw.isdigit() else 5

            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INT DEFAULT 5")
                
                if producto_id:
                    cursor.execute("""
                        UPDATE productos 
                        SET nombre = %s, codigo_barra = %s, tipo = %s, cantidad = %s, precio = %s, stock_minimo = %s
                        WHERE id = %s
                    """, (nombre, codigo_barra, tipo, cantidad, precio, stock_minimo, producto_id))
                    
                    if cursor.rowcount > 0:
                        mensaje = f'Producto "{nombre}" actualizado correctamente.'
                        categoria = 'success'
                    else:
                        mensaje = f'No se encontró el producto con ID {producto_id}.'
                        categoria = 'warning'
                else:
                    cursor.execute("""
                        INSERT INTO productos (nombre, codigo_barra, tipo, cantidad, precio, stock_minimo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (nombre, codigo_barra, tipo, cantidad, precio, stock_minimo))
                    mensaje = f'Producto "{nombre}" registrado correctamente.'
                    categoria = 'success'

            conexion.commit()
            conexion.close()

            flash(mensaje, categoria)
        except Exception as e:
            logger.error(f"Error procesando producto en almacén: {e}")
            flash(f'Error al procesar el producto: {e}', 'error')
        return redirect(url_for('almacen'))

    productos_lista = []
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INT DEFAULT 5")
            cursor.execute("""
                SELECT id, nombre, tipo, cantidad, precio, COALESCE(stock_minimo, 5), codigo_barra 
                FROM productos 
                ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            for r in rows:
                p_id = r[0]
                nombre = r[1] or ''
                tipo = str(r[2]) if r[2] is not None else 'stock'
                cantidad = int(r[3]) if r[3] is not None else 0
                precio = float(r[4]) if r[4] is not None else 0.0
                stock_minimo = int(r[5]) if r[5] is not None else 5
                codigo_barra = r[6] or ''

                item = {
                    'id': p_id,
                    'nombre': nombre,
                    'tipo': tipo,
                    'cantidad': cantidad,
                    'stock': cantidad,
                    'precio': precio,
                    'stock_minimo': stock_minimo,
                    'codigo_barra': codigo_barra,
                    0: p_id,
                    1: nombre,
                    2: tipo,
                    3: cantidad,
                    4: precio,
                    5: stock_minimo,
                    6: codigo_barra
                }
                productos_lista.append(item)
        conexion.close()
    except Exception as e:
        logger.error(f"Error consultando productos en almacén: {e}")

    return render_template('almacen.html', productos=productos_lista)


@app.route('/producto/<int:producto_id>')
def ver_producto(producto_id):
    producto = productos_controlador.obtener_producto_por_id(producto_id) if hasattr(productos_controlador, 'obtener_producto_por_id') else None
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('productos'))
    return render_template('ver_producto.html', producto=producto)


# ─── SERVICIOS ───────────────────────────────────────────────────────────────

@app.template_filter('moneda')
def formato_moneda_filter(val):
    """Formatea precios a moneda (S/ 0.00) de forma ultra segura."""
    try:
        return f"S/ {float(val):.2f}"
    except (ValueError, TypeError):
        return "S/ 0.00"

@app.template_filter('decimales')
def formato_decimales_filter(val):
    """Formatea números a 2 decimales (0.00) de forma ultra segura."""
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return "0.00"

@app.route('/servicios', endpoint='servicios')
@app.route('/gestion_servicios', endpoint='gestion_servicios')
def servicios():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    tenant_id = session.get('tenant_id', 1)
    servicios_lista = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, 
                    nombre, 
                    COALESCE(descripcion, '') AS descripcion, 
                    COALESCE(precio, 0.00) AS precio, 
                    COALESCE(duracion, 30) AS duracion, 
                    COALESCE(activo, true) AS activo
                FROM servicios
                WHERE (tenant_id = %s OR tenant_id IS NULL)
                ORDER BY nombre ASC
            """, (tenant_id,))
            
            rows = cursor.fetchall()
            for s in rows:
                # Compatibilidad unificada para DictCursor y Tuplas
                if isinstance(s, dict):
                    s_id = s.get('id')
                    s_nom = s.get('nombre')
                    s_desc = s.get('descripcion')
                    raw_prec = s.get('precio')
                    raw_dur = s.get('duracion')
                    s_act = s.get('activo')
                else:
                    s_id, s_nom, s_desc = s[0], s[1], s[2]
                    raw_prec, raw_dur, s_act = s[3], s[4], s[5]

                try:
                    s_prec = float(raw_prec) if raw_prec is not None else 0.0
                except (ValueError, TypeError):
                    s_prec = 0.0

                try:
                    s_dur = int(raw_dur) if raw_dur is not None else 30
                except (ValueError, TypeError):
                    s_dur = 30

                servicios_lista.append({
                    'id': s_id,
                    'nombre': str(s_nom or ''),
                    'descripcion': str(s_desc or ''),
                    'precio': s_prec,
                    'duracion': s_dur,
                    'duracion_minutos': s_dur,
                    'activo': bool(s_act),
                    0: s_id, 1: str(s_nom or ''), 2: str(s_desc or ''), 3: s_prec, 4: s_dur, 5: bool(s_act)
                })
        conexion.close()
    except Exception as e:
        logger.error(f"Error consultando servicios desde DB: {e}")
        if hasattr(servicios_controlador, 'obtener_servicios'):
            raw_lista = servicios_controlador.obtener_servicios() or []
            for item in raw_lista:
                if isinstance(item, dict):
                    try:
                        item['precio'] = float(item.get('precio', 0.0))
                    except (ValueError, TypeError):
                        item['precio'] = 0.0
                    try:
                        item['duracion'] = int(item.get('duracion', 30))
                    except (ValueError, TypeError):
                        item['duracion'] = 30
                    servicios_lista.append(item)

    return render_template('servicios.html', servicios=servicios_lista)

# ─── CLIENTES & MASCOTAS ─────────────────────────────────────────────────────

@app.route('/clientes', endpoint='clientes')
@app.route('/clientes/lista', endpoint='listar_clientes')
def clientes():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = []
    try:
        if hasattr(clientes_controlador, 'obtener_clientes'):
            lista = clientes_controlador.obtener_clientes() or []
    except Exception as e:
        logger.error(f"Error cargando clientes: {e}")
        
    return render_template('clientes.html', clientes=lista)


@app.route('/clientes/crear', methods=['POST'], endpoint='crear_cliente')
@app.route('/clientes/agregar', methods=['POST'], endpoint='agregar_cliente')
def crear_cliente():
    if session.get('rol') not in ['admin', 'empleado', 'dueño']:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    try:
        nombre = request.form.get('nombre')
        email = request.form.get('email', '')
        telefono = request.form.get('telefono', '')
        direccion = request.form.get('direccion', '')
        documento = request.form.get('documento', '')
        
        if hasattr(clientes_controlador, 'insertar_cliente'):
            clientes_controlador.insertar_cliente(nombre, email, telefono, direccion, documento)
        else:
            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO clientes (nombre, email, telefono, direccion, documento)
                    VALUES (%s, %s, %s, %s, %s)
                """, (nombre, email, telefono, direccion, documento))
            conexion.commit()
            conexion.close()
            
        flash('Cliente registrado exitosamente.', 'success')
    except Exception as e:
        logger.error(f"Error al registrar cliente: {e}")
        flash(f'Error al registrar cliente: {e}', 'error')
    return redirect(url_for('clientes'))


@app.route('/historial_clientes', endpoint='historial_clientes')
@app.route('/historial-clientes')
def historial_clientes():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = clientes_controlador.obtener_clientes() if hasattr(clientes_controlador, 'obtener_clientes') else []
    return render_template('historial_clientes.html', clientes=lista, historial=lista)


@app.route('/mascotas')
def mascotas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = mascotas_controlador.obtener_mascotas() if hasattr(mascotas_controlador, 'obtener_mascotas') else []
    return render_template('mascotas.html', mascotas=lista)


# ─── GESTIÓN DE PERSONAL Y USUARIOS ──────────────────────────────────────────

@app.route('/personal', methods=['GET', 'POST'])
@app.route('/personal/agregar', methods=['POST'], endpoint='agregar_personal')
@app.route('/personal/editar', methods=['POST'], endpoint='editar_personal')
def personal():
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'error': 'Acceso denegado.'}), 403
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    tenant_id = session.get('tenant_id', 1)

    if request.method == 'POST':
        try:
            req_json = request.get_json(silent=True) or {}
            
            def get_param(*keys, default=''):
                for k in keys:
                    v = req_json.get(k)
                    if v is not None and str(v).strip() != '':
                        return str(v).strip()
                    v = request.form.get(k)
                    if v is not None and str(v).strip() != '':
                        return str(v).strip()
                return default

            raw_id = get_param('id', 'personal_id', 'usuario_id', 'edit_id')
            target_id = int(raw_id) if raw_id and raw_id.isdigit() else None

            # Desactivar empleado respetando el tenant
            if 'eliminar' in request.form or get_param('accion') in ['desactivar', 'eliminar']:
                if target_id:
                    conexion = obtener_conexion()
                    with conexion.cursor() as cursor:
                        cursor.execute("""
                            UPDATE personal 
                            SET activo = false 
                            WHERE (id = %s OR usuario_id = %s) AND (tenant_id = %s OR tenant_id IS NULL)
                            RETURNING usuario_id
                        """, (target_id, target_id, tenant_id))
                        res = cursor.fetchone()
                        if res and res[0]:
                            cursor.execute("""
                                UPDATE usuarios 
                                SET activo = false 
                                WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                            """, (res[0], tenant_id))
                    conexion.commit()
                    conexion.close()
                    flash('Empleado desactivado correctamente.', 'success')
                    return redirect(url_for('personal'))

            # Reactivar empleado respetando el tenant
            if 'reactivar' in request.form or get_param('accion') in ['reactivar']:
                if target_id:
                    conexion = obtener_conexion()
                    with conexion.cursor() as cursor:
                        cursor.execute("""
                            UPDATE personal 
                            SET activo = true 
                            WHERE (id = %s OR usuario_id = %s) AND (tenant_id = %s OR tenant_id IS NULL)
                            RETURNING usuario_id
                        """, (target_id, target_id, tenant_id))
                        res = cursor.fetchone()
                        if res and res[0]:
                            cursor.execute("""
                                UPDATE usuarios 
                                SET activo = true 
                                WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                            """, (res[0], tenant_id))
                    conexion.commit()
                    conexion.close()
                    flash('Empleado reactivado correctamente.', 'success')
                    return redirect(url_for('personal'))

            username = get_param('username', 'nombre', 'usuario')
            cargo = get_param('cargo', default='Empleado')
            rol = get_param('rol', default='empleado').lower()
            
            roles_validos = ['cliente', 'dueño', 'admin', 'empleado', 'superadmin']
            rol_final = rol if rol in roles_validos else 'empleado'

            salario_raw = get_param('salario', 'sueldo')
            salario = float(salario_raw) if salario_raw else 0.0

            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                if target_id:
                    cursor.execute("""
                        SELECT id, usuario_id 
                        FROM personal 
                        WHERE (id = %s OR usuario_id = %s) AND (tenant_id = %s OR tenant_id IS NULL)
                    """, (target_id, target_id, tenant_id))
                    p_row = cursor.fetchone()
                    
                    if p_row:
                        p_id, usuario_id = p_row[0], p_row[1]
                        cursor.execute("""
                            UPDATE personal 
                            SET cargo = %s, salario = %s 
                            WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                        """, (cargo, salario, p_id, tenant_id))
                    else:
                        usuario_id = target_id
                        cursor.execute("""
                            INSERT INTO personal (usuario_id, cargo, salario, activo, tenant_id) 
                            VALUES (%s, %s, %s, true, %s)
                        """, (usuario_id, cargo, salario, tenant_id))

                    if usuario_id and username:
                        cursor.execute("""
                            UPDATE usuarios 
                            SET username = %s, rol = %s::rol_usuario_enum 
                            WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                        """, (username, rol_final, usuario_id, tenant_id))
                    elif usuario_id and rol:
                        cursor.execute("""
                            UPDATE usuarios 
                            SET rol = %s::rol_usuario_enum 
                            WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                        """, (rol_final, usuario_id, tenant_id))

                    mensaje = 'Datos del empleado actualizados correctamente.'
                else:
                    if not username:
                        conexion.close()
                        msg = 'El nombre de usuario es obligatorio para registrar un nuevo empleado.'
                        if request.is_json:
                            return jsonify({'success': False, 'error': msg}), 400
                        flash(msg, 'warning')
                        return redirect(url_for('personal'))

                    from controladores.usuarios_controlador import hash_password
                    password_default = hash_password('123456')

                    cursor.execute("""
                        INSERT INTO usuarios (username, password, rol, activo, tenant_id)
                        VALUES (%s, %s, %s::rol_usuario_enum, true, %s)
                        RETURNING id
                    """, (username, password_default, rol_final, tenant_id))
                    nuevo_usuario_id = cursor.fetchone()[0]

                    cursor.execute("""
                        INSERT INTO personal (usuario_id, cargo, salario, activo, tenant_id)
                        VALUES (%s, %s, %s, true, %s)
                    """, (nuevo_usuario_id, cargo, salario, tenant_id))

                    mensaje = f'Empleado "{username}" registrado correctamente.'

            conexion.commit()
            conexion.close()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': True, 'message': mensaje})

            flash(mensaje, 'success')
        except Exception as e:
            logger.error(f"Error procesando personal (POST): {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            flash(f'Error al procesar personal: {e}', 'error')

        return redirect(url_for('personal'))

    empleados_lista = []
    usuarios_lista = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # Filtrado estricto de personal por tenant_id
            cursor.execute("""
                SELECT 
                    p.id AS personal_id,
                    u.username,
                    COALESCE(p.cargo, 'Empleado') AS cargo,
                    u.rol,
                    COALESCE(p.salario, 0.00) AS salario,
                    COALESCE(p.activo, true) AS activo,
                    u.id AS usuario_id
                FROM personal p
                INNER JOIN usuarios u ON p.usuario_id = u.id
                WHERE (p.tenant_id = %s OR p.tenant_id IS NULL)
                  AND (u.tenant_id = %s OR u.tenant_id IS NULL)
                ORDER BY p.id ASC
            """, (tenant_id, tenant_id))
            
            rows = cursor.fetchall()
            for r in rows:
                p_id = r[0]
                username = r[1] or 'Sin Usuario'
                cargo = r[2] or 'Empleado'
                rol = str(r[3]) if r[3] else 'empleado'
                salario = float(r[4]) if r[4] is not None else 0.0
                activo_bool = bool(r[5])
                activo_int = 1 if activo_bool else 0
                usuario_id = r[6]
                estado_str = 'Activo' if activo_bool else 'Inactivo'

                item = {
                    'id': p_id,
                    'personal_id': p_id,
                    'usuario': username,
                    'nombre': username,
                    'username': username,
                    'cargo': cargo,
                    'rol': rol,
                    'salario': salario,
                    'sueldo': salario,
                    'activo': activo_int,
                    'estado': estado_str,
                    'usuario_id': usuario_id,
                    0: p_id,
                    1: usuario_id,
                    2: username,
                    3: cargo,
                    4: salario,
                    5: activo_int,
                    6: rol,
                    7: estado_str
                }
                empleados_lista.append(item)

            # Filtrado estricto de usuarios por tenant_id
            cursor.execute("""
                SELECT id, username, rol, COALESCE(activo, true) 
                FROM usuarios 
                WHERE (tenant_id = %s OR tenant_id IS NULL)
                ORDER BY id ASC
            """, (tenant_id,))
            
            for u in cursor.fetchall():
                usuarios_lista.append({
                    'id': u[0],
                    'username': u[1],
                    'rol': str(u[2]),
                    'activo': u[3],
                    0: u[0], 1: u[1], 2: str(u[2]), 3: u[3]
                })

        conexion.close()
    except Exception as e:
        logger.error(f"Error cargando módulo personal: {e}")

    puede_modificar = session.get('rol') in ['admin', 'dueño']

    return render_template(
        'personal.html', 
        empleados=empleados_lista, 
        personal=empleados_lista, 
        usuarios=usuarios_lista, 
        puede_modificar=puede_modificar
    )


@app.route('/personal/toggle-estado/<int:target_id>', methods=['POST'])
@app.route('/usuario/toggle-estado/<int:target_id>', methods=['POST'])
def toggle_estado_personal(target_id):
    if session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403

    tenant_id = session.get('tenant_id', 1)

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE personal
                SET activo = NOT COALESCE(activo, true)
                WHERE (id = %s OR usuario_id = %s) AND (tenant_id = %s OR tenant_id IS NULL)
                RETURNING usuario_id, activo
            """, (target_id, target_id, tenant_id))
            
            res = cursor.fetchone()
            
            if res:
                usuario_id, nuevo_estado = res[0], res[1]
                if usuario_id:
                    cursor.execute("""
                        UPDATE usuarios 
                        SET activo = %s 
                        WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                    """, (nuevo_estado, usuario_id, tenant_id))
            else:
                cursor.execute("""
                    UPDATE usuarios
                    SET activo = NOT COALESCE(activo, true)
                    WHERE id = %s AND (tenant_id = %s OR tenant_id IS NULL)
                    RETURNING activo
                """, (target_id, tenant_id))
                res_u = cursor.fetchone()
                if not res_u:
                    conexion.close()
                    return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
                nuevo_estado = res_u[0]

        conexion.commit()
        conexion.close()

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'nuevo_estado': nuevo_estado, 'message': 'Estado de acceso actualizado.'})

        flash('Estado de acceso actualizado correctamente.', 'success')
        return redirect(url_for('personal'))
    except Exception as e:
        logger.error(f"Error al cambiar estado de acceso: {e}")
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error al cambiar estado: {e}', 'error')
        return redirect(url_for('personal'))


@app.route('/personal/eliminar/<int:target_id>', methods=['POST', 'DELETE'])
@app.route('/usuario/eliminar/<int:target_id>', methods=['POST', 'DELETE'])
def eliminar_personal_permanente(target_id):
    if session.get('rol') not in ['admin', 'dueño', 'superadmin']:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Sin permisos'}), 403
        flash('Sin permisos para eliminar personal.', 'error')
        return redirect(url_for('personal'))

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # 1. Obtener IDs asociados
            cursor.execute("""
                SELECT p.id AS personal_id, u.id AS usuario_id 
                FROM usuarios u
                LEFT JOIN personal p ON p.usuario_id = u.id
                WHERE u.id = %s OR p.id = %s
            """, (target_id, target_id))
            
            row = cursor.fetchone()
            personal_id = row[0] if row else None
            usuario_id = row[1] if row else target_id

            # 2. Borrar asistencias
            if personal_id:
                cursor.execute("DELETE FROM asistencia WHERE personal_id = %s", (personal_id,))

            if usuario_id:
                cursor.execute("""
                    DELETE FROM asistencia 
                    WHERE personal_id IN (SELECT id FROM personal WHERE usuario_id = %s)
                """, (usuario_id,))

                # 3. Borrar ventas y compras asociadas al vendedor
                cursor.execute("DELETE FROM ventas WHERE vendedor_id = %s", (usuario_id,))
                
                try:
                    cursor.execute("DELETE FROM compras WHERE vendedor_id = %s", (usuario_id,))
                except Exception:
                    pass

                # 4. Borrar personal y usuario
                cursor.execute("DELETE FROM personal WHERE usuario_id = %s", (usuario_id,))
                cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))

        conexion.commit()
        conexion.close()

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Usuario y todo su historial eliminados permanentemente.'})

        flash('Usuario y todos sus registros asociados fueron eliminados permanentemente.', 'success')
    except Exception as e:
        logger.error(f"Error eliminando usuario/personal: {e}")
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error al eliminar permanentemente: {e}', 'error')

    return redirect(url_for('personal'))

# ─── ASISTENCIA DEL PERSONAL ──────────────────────────────────────────────────

def obtener_usuario_id_sesion():
    uid = session.get('usuario_id') or session.get('user_id') or session.get('id')
    if uid and str(uid).isdigit():
        return int(uid)
    
    username = session.get('usuario') or session.get('username')
    if username:
        try:
            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                cursor.execute("SELECT id FROM usuarios WHERE username = %s OR id::text = %s LIMIT 1", (str(username), str(username)))
                row = cursor.fetchone()
                if row:
                    conexion.close()
                    return row[0]
            conexion.close()
        except Exception as e:
            logger.error(f"Error resolviendo ID de usuario: {e}")
            
    return None


@app.route('/asistencia', methods=['GET', 'POST'])
def asistencia():
    if 'rol' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
        flash('Debes iniciar sesión para acceder a la asistencia.', 'error')
        return redirect(url_for('login'))
        
    tenant_id = session.get('tenant_id', 1)
    usuario_id = obtener_usuario_id_sesion()
    rol = session.get('rol', 'empleado')

    if not usuario_id:
        flash('Sesión de usuario no válida.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        return _procesar_marcar_asistencia(usuario_id, tenant_id)

    registros = []
    asistencia_actual = None

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.id, 
                    TO_CHAR(a.hora_entrada, 'HH12:MI AM') AS entrada_fmt, 
                    TO_CHAR(a.hora_salida, 'HH12:MI AM') AS salida_fmt
                FROM asistencia a
                INNER JOIN personal p ON a.personal_id = p.id
                WHERE p.usuario_id = %s AND a.fecha = CURRENT_DATE AND a.hora_salida IS NULL
                ORDER BY a.id DESC LIMIT 1
            """, (usuario_id,))
            a_row = cursor.fetchone()
            
            if a_row:
                asistencia_actual = {
                    'id': a_row[0],
                    'hora_entrada': a_row[1],
                    'hora_salida': a_row[2],
                    'estado': 'presente',
                    0: a_row[0], 1: a_row[1], 2: a_row[2], 3: 'presente'
                }

            if rol in ['admin', 'dueño']:
                cursor.execute("""
                    SELECT 
                        a.id,
                        u.username,
                        COALESCE(p.cargo, 'Empleado') AS cargo,
                        a.fecha,
                        TO_CHAR(a.hora_entrada, 'HH12:MI AM') AS entrada,
                        TO_CHAR(a.hora_salida, 'HH12:MI AM') AS salida,
                        CASE WHEN a.hora_salida IS NOT NULL THEN 'completado' ELSE 'presente' END AS estado
                    FROM asistencia a
                    INNER JOIN personal p ON a.personal_id = p.id
                    INNER JOIN usuarios u ON p.usuario_id = u.id
                    WHERE (a.tenant_id = %s OR a.tenant_id IS NULL) AND a.fecha = CURRENT_DATE
                    ORDER BY a.hora_entrada DESC
                """, (tenant_id,))
            else:
                cursor.execute("""
                    SELECT 
                        a.id,
                        u.username,
                        COALESCE(p.cargo, 'Empleado') AS cargo,
                        a.fecha,
                        TO_CHAR(a.hora_entrada, 'HH12:MI AM') AS entrada,
                        TO_CHAR(a.hora_salida, 'HH12:MI AM') AS salida,
                        CASE WHEN a.hora_salida IS NOT NULL THEN 'completado' ELSE 'presente' END AS estado
                    FROM asistencia a
                    INNER JOIN personal p ON a.personal_id = p.id
                    INNER JOIN usuarios u ON p.usuario_id = u.id
                    WHERE (a.tenant_id = %s OR a.tenant_id IS NULL) AND p.usuario_id = %s AND a.fecha = CURRENT_DATE
                    ORDER BY a.hora_entrada DESC
                """, (tenant_id, usuario_id))

            for r in cursor.fetchall():
                item = {
                    'id': r[0],
                    'usuario': r[1] or 'Empleado',
                    'nombre': r[1] or 'Empleado',
                    'username': r[1] or 'Empleado',
                    'cargo': r[2] or 'Empleado',
                    'fecha': str(r[3]),
                    'hora_entrada': r[4] or '--:--',
                    'entrada': r[4] or '--:--',
                    'hora_salida': r[5] or 'En turno',
                    'salida': r[5] or 'En turno',
                    'estado': r[6],
                    0: r[0], 1: r[1], 2: r[2], 3: str(r[3]), 4: r[4] or '--:--', 5: r[5] or 'En turno', 6: r[6]
                }
                registros.append(item)

        conexion.close()
    except Exception as e:
        logger.error(f"Error cargando registros de asistencia: {e}")

    return render_template(
        'asistencia.html', 
        registros=registros, 
        historial=registros,
        asistencia=asistencia_actual, 
        asistencia_actual=asistencia_actual
    )


@app.route('/asistencia/marcar', methods=['GET', 'POST'])
@app.route('/marcar_asistencia', methods=['GET', 'POST'])
def marcar_asistencia():
    if 'rol' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
        flash('Debes iniciar sesión para registrar asistencia.', 'error')
        return redirect(url_for('login'))

    if request.method == 'GET':
        return redirect(url_for('asistencia'))

    tenant_id = session.get('tenant_id', 1)
    usuario_id = obtener_usuario_id_sesion()
    
    if not usuario_id:
        msg = 'Sesión no válida. Por favor inicia sesión nuevamente.'
        return jsonify({'success': False, 'error': msg}) if request.is_json else (flash(msg, 'error') or redirect(url_for('login')))

    return _procesar_marcar_asistencia(usuario_id, tenant_id)


def _procesar_marcar_asistencia(usuario_id, tenant_id):
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM personal WHERE usuario_id = %s ORDER BY id DESC LIMIT 1", (usuario_id,))
            p_row = cursor.fetchone()

            if p_row:
                personal_id = p_row[0]
            else:
                cursor.execute("""
                    INSERT INTO personal (usuario_id, cargo, salario, activo, tenant_id)
                    VALUES (%s, 'Empleado', 0.00, true, %s)
                    RETURNING id
                """, (usuario_id, tenant_id))
                personal_id = cursor.fetchone()[0]

            cursor.execute("""
                SELECT id, hora_salida 
                FROM asistencia 
                WHERE personal_id = %s AND fecha = CURRENT_DATE 
                LIMIT 1
            """, (personal_id,))
            reg_hoy = cursor.fetchone()

            if not reg_hoy:
                cursor.execute("""
                    INSERT INTO asistencia (personal_id, fecha, hora_entrada, tenant_id)
                    VALUES (%s, CURRENT_DATE, CURRENT_TIME, %s)
                """, (personal_id, tenant_id))
                mensaje = 'Hora de entrada registrada correctamente.'
            else:
                asistencia_id = reg_hoy[0]
                hora_salida_existente = reg_hoy[1]

                if hora_salida_existente is None:
                    cursor.execute("""
                        UPDATE asistencia 
                        SET hora_salida = CURRENT_TIME 
                        WHERE id = %s
                    """, (asistencia_id,))
                    mensaje = 'Hora de salida registrada correctamente.'
                else:
                    cursor.execute("""
                        UPDATE asistencia 
                        SET hora_entrada = CURRENT_TIME, hora_salida = NULL 
                        WHERE id = %s
                    """, (asistencia_id,))
                    mensaje = 'Nueva hora de entrada registrada correctamente.'

        conexion.commit()
        conexion.close()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'message': mensaje})
            
        flash(mensaje, 'success')
    except Exception as e:
        logger.error(f"Error registrando asistencia: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash('Error al registrar la asistencia.', 'error')

    return redirect(url_for('asistencia'))


@app.route('/historial_asistencia', endpoint='historial_asistencia')
@app.route('/historial-asistencia')
def historial_asistencia():
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    tenant_id = session.get('tenant_id', 1)
    usuario_id = obtener_usuario_id_sesion()
    rol = session.get('rol', 'empleado')
    registros = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            if rol in ['admin', 'dueño']:
                cursor.execute("""
                    SELECT 
                        a.id,
                        u.username,
                        COALESCE(p.cargo, 'Empleado') AS cargo,
                        a.fecha,
                        TO_CHAR(a.hora_entrada, 'HH12:MI AM') AS entrada,
                        TO_CHAR(a.hora_salida, 'HH12:MI AM') AS salida,
                        CASE WHEN a.hora_salida IS NOT NULL THEN 'completado' ELSE 'presente' END AS estado
                    FROM asistencia a
                    INNER JOIN personal p ON a.personal_id = p.id
                    INNER JOIN usuarios u ON p.usuario_id = u.id
                    WHERE (a.tenant_id = %s OR a.tenant_id IS NULL)
                    ORDER BY a.fecha DESC, a.hora_entrada DESC
                    LIMIT 200
                """, (tenant_id,))
            else:
                cursor.execute("""
                    SELECT 
                        a.id,
                        u.username,
                        COALESCE(p.cargo, 'Empleado') AS cargo,
                        a.fecha,
                        TO_CHAR(a.hora_entrada, 'HH12:MI AM') AS entrada,
                        TO_CHAR(a.hora_salida, 'HH12:MI AM') AS salida,
                        CASE WHEN a.hora_salida IS NOT NULL THEN 'completado' ELSE 'presente' END AS estado
                    FROM asistencia a
                    INNER JOIN personal p ON a.personal_id = p.id
                    INNER JOIN usuarios u ON p.usuario_id = u.id
                    WHERE (a.tenant_id = %s OR a.tenant_id IS NULL) AND p.usuario_id = %s
                    ORDER BY a.fecha DESC, a.hora_entrada DESC
                    LIMIT 100
                """, (tenant_id, usuario_id))

            for r in cursor.fetchall():
                item = {
                    'id': r[0],
                    'usuario': r[1] or 'Empleado',
                    'nombre': r[1] or 'Empleado',
                    'username': r[1] or 'Empleado',
                    'cargo': r[2] or 'Empleado',
                    'fecha': str(r[3]),
                    'hora_entrada': r[4] or '--:--',
                    'entrada': r[4] or '--:--',
                    'hora_salida': r[5] or 'En turno',
                    'salida': r[5] or 'En turno',
                    'estado': r[6],
                    0: r[0], 1: r[1], 2: r[2], 3: str(r[3]), 4: r[4] or '--:--', 5: r[5] or 'En turno', 6: r[6]
                }
                registros.append(item)

        conexion.close()
    except Exception as e:
        logger.error(f"Error cargando historial de asistencia: {e}")

    return render_template('historial_asistencia.html', historial=registros, registros=registros)


# ─── MÓDULO DE GESTIÓN DE CITAS ───────────────────────────────────────────────

@app.route('/citas')
def citas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    tenant_id = session.get('tenant_id', 1)
    fecha_filtro = request.args.get('fecha', default=date.today().strftime('%Y-%m-%d'))
    citas_list = []
    servicios_lista = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.id,                                           -- 0
                    c.cliente_nombre,                               -- 1
                    COALESCE(c.cliente_email, c.cliente_telefono),  -- 2
                    c.cliente_telefono,                             -- 3
                    TO_CHAR(c.hora, 'HH12:MI AM') AS hora_fmt,      -- 4
                    c.estado,                                       -- 5
                    COALESCE(s.nombre, 'Servicio General') AS s_nom, -- 6
                    c.mascota_nombre,                               -- 7
                    c.mascota_especie,                              -- 8
                    COALESCE(c.precio_total, 0.00) AS precio,       -- 9
                    c.fecha,                                        -- 10
                    c.observaciones                                 -- 11
                FROM citas c
                LEFT JOIN servicios s ON c.servicio_id = s.id
                WHERE c.tenant_id = %s AND c.fecha = %s
                ORDER BY c.hora ASC
            """, (tenant_id, fecha_filtro))
            
            for r in cursor.fetchall():
                c_id = r[0]
                c_nombre = r[1] or ''
                c_contacto = r[2] or ''
                c_tel = r[3] or ''
                c_hora = r[4] or ''
                c_estado = str(r[5]).lower() if r[5] else 'pendiente'
                s_nombre = r[6]
                m_nombre = r[7] or ''
                m_especie = r[8] or ''
                c_precio = float(r[9]) if r[9] is not None else 0.0
                c_fecha = str(r[10]) if r[10] else ''
                c_obs = r[11] or ''

                item = {
                    'id': c_id,
                    'cliente_nombre': c_nombre,
                    'cliente_email': c_contacto,
                    'cliente_telefono': c_tel,
                    'hora': c_hora,
                    'estado': c_estado,
                    'servicio_nombre': s_nombre,
                    'mascota_nombre': m_nombre,
                    'mascota_especie': m_especie,
                    'precio_total': c_precio,
                    'fecha': c_fecha,
                    'observaciones': c_obs,
                    0: c_id, 1: c_nombre, 2: c_contacto, 3: c_tel, 4: c_hora, 5: c_estado,
                    6: s_nombre, 7: m_nombre, 8: m_especie, 9: c_precio, 10: c_fecha, 11: c_obs
                }
                citas_list.append(item)

            cursor.execute("""
                SELECT id, nombre, precio, duracion, max_citas_dia, COALESCE(activo, true)
                FROM servicios
                WHERE tenant_id = %s
                ORDER BY nombre ASC
            """, (tenant_id,))
            
            for s in cursor.fetchall():
                servicios_lista.append({
                    'id': s[0], 'nombre': s[1], 'precio': float(s[2]) if s[2] else 0.0,
                    0: s[0], 1: s[1], 2: float(s[2]) if s[2] else 0.0, 5: bool(s[5])
                })

        conexion.close()
    except Exception as e:
        logger.error(f"Error consultando citas: {e}")

    return render_template('citas.html', citas=citas_list, fecha_filtro=fecha_filtro, servicios=servicios_lista)


@app.route('/agendar_cita', methods=['POST'])
def agendar_cita():
    try:
        tenant_id = session.get('tenant_id', 1)

        nombre = request.form.get('cliente_nombre', '').strip()
        email = request.form.get('cliente_email', '').strip() or None
        telefono = request.form.get('cliente_telefono', '').strip() or None
        direccion = request.form.get('cliente_direccion', '').strip() or None
        
        fecha = request.form.get('fecha', '').strip()
        hora = request.form.get('hora', '').strip()
        
        servicio_id_raw = request.form.get('servicio_id') or request.form.get('servicio')
        if not servicio_id_raw and request.form.getlist('servicio_id[]'):
            servicio_id_raw = request.form.getlist('servicio_id[]')[0]
            
        servicio_id = int(servicio_id_raw) if servicio_id_raw and str(servicio_id_raw).isdigit() else None

        mascota_nombre = request.form.get('mascota_nombre', '').strip() or None
        mascota_especie = request.form.get('mascota_especie', 'perro').strip() or 'perro'
        
        obs_input = request.form.get('observaciones', '').strip()
        obs_partes = []
        if direccion:
            obs_partes.append(f"Dirección: {direccion}")
        if obs_input:
            obs_partes.append(obs_input)
        observaciones = " | ".join(obs_partes) if obs_partes else None

        if not nombre or not fecha or not hora or not servicio_id or not mascota_nombre:
            flash('Por favor completa todos los campos obligatorios (*).', 'error')
            return redirect(request.referrer or url_for('citas'))

        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            precio_total = 0.0
            cursor.execute("SELECT precio FROM servicios WHERE id = %s", (servicio_id,))
            s_row = cursor.fetchone()
            if s_row and s_row[0] is not None:
                precio_total = float(s_row[0])

            cursor.execute("""
                INSERT INTO citas (
                    cliente_nombre, cliente_email, cliente_telefono,
                    servicio_id, fecha, hora, mascota_nombre, mascota_especie,
                    observaciones, precio_total, estado, tenant_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendiente'::estado_cita_enum, %s)
            """, (nombre, email, telefono, servicio_id, fecha, hora, mascota_nombre, mascota_especie, observaciones, precio_total, tenant_id))

        conexion.commit()
        conexion.close()

        flash('Cita agendada exitosamente.', 'success')
    except Exception as e:
        logger.error(f"Error al agendar cita: {e}")
        flash(f'Error al agendar la cita: {str(e)}', 'error')

    return redirect(request.referrer or url_for('citas'))


@app.route('/cita/<int:cita_id>/status', methods=['POST'])
@app.route('/citas/estado/<int:cita_id>', methods=['POST'])
def cambiar_estado_cita(cita_id):
    if session.get('rol') not in ['admin', 'empleado', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403

    try:
        tenant_id = session.get('tenant_id', 1)
        data = request.get_json(silent=True) or {}
        
        nuevo_estado = (data.get('status') or data.get('estado') or request.form.get('estado') or '').strip().lower()
        motivo = (data.get('motivo') or request.form.get('motivo') or '').strip()

        estados_validos = ['pendiente', 'confirmada', 'en_progreso', 'completada', 'cancelada']
        if not nuevo_estado or nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'error': 'Estado no válido'}), 400

        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE citas SET estado = %s::estado_cita_enum WHERE id = %s AND tenant_id = %s", (nuevo_estado, cita_id, tenant_id))

            if motivo:
                cursor.execute("""
                    UPDATE citas 
                    SET observaciones = CASE 
                        WHEN observaciones IS NULL OR observaciones = '' THEN %s
                        ELSE observaciones || ' | ' || %s
                    END
                    WHERE id = %s AND tenant_id = %s
                """, (f"Motivo: {motivo}", f"Motivo: {motivo}", cita_id, tenant_id))

        conexion.commit()
        conexion.close()

        return jsonify({'success': True, 'message': f'Estado de cita actualizado a {nuevo_estado}.'})
    except Exception as e:
        logger.error(f"Error cambiando estado de cita: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/cita/<int:cita_id>/reprogramar', methods=['POST'])
def reprogramar_cita(cita_id):
    if session.get('rol') not in ['admin', 'empleado', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403

    try:
        tenant_id = session.get('tenant_id', 1)
        data = request.get_json(silent=True) or {}
        nueva_fecha = (data.get('fecha') or request.form.get('fecha') or '').strip()
        nueva_hora = (data.get('hora') or request.form.get('hora') or '').strip()

        if not nueva_fecha or not nueva_hora:
            return jsonify({'success': False, 'error': 'Fecha y hora requeridas.'}), 400

        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE citas 
                SET fecha = %s, hora = %s
                WHERE id = %s AND tenant_id = %s
            """, (nueva_fecha, nueva_hora, cita_id, tenant_id))

        conexion.commit()
        conexion.close()

        return jsonify({'success': True, 'message': 'Cita reprogramada correctamente.'})
    except Exception as e:
        logger.error(f"Error reprogramando cita: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/cita/<int:cita_id>', endpoint='ver_detalles_cita')
@app.route('/cita/<int:cita_id>/recibo', endpoint='ver_recibo_cita')
@app.route('/cita/recibo/<int:cita_id>')
@app.route('/cita/<int:cita_id>/detalles')
def ver_recibo_cita(cita_id):
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    tenant_id = session.get('tenant_id', 1)
    cita = None

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.id, c.cliente_nombre, COALESCE(c.cliente_email, ''), COALESCE(c.cliente_telefono, ''),
                    TO_CHAR(c.fecha, 'YYYY-MM-DD'), TO_CHAR(c.hora, 'HH12:MI AM'), COALESCE(c.mascota_nombre, ''),
                    COALESCE(c.mascota_especie, 'perro'), COALESCE(c.observaciones, ''), COALESCE(c.precio_total, 0.00),
                    COALESCE(c.estado, 'pendiente'), COALESCE(s.nombre, 'Servicio General'), COALESCE(s.precio, 0.00)
                FROM citas c
                LEFT JOIN servicios s ON c.servicio_id = s.id
                WHERE c.id = %s AND c.tenant_id = %s
            """, (cita_id, tenant_id))
            
            r = cursor.fetchone()
            if r:
                cita = {
                    'id': r[0], 'cliente_nombre': r[1] or 'Cliente General', 'cliente_email': r[2], 'cliente_telefono': r[3],
                    'fecha': r[4] or '', 'hora': r[5] or '', 'mascota_nombre': r[6], 'mascota_especie': r[7],
                    'observaciones': r[8], 'precio_total': float(r[9]) if r[9] is not None else 0.0, 'estado': str(r[10]).lower(),
                    'servicio_nombre': r[11], 'servicio_precio': float(r[12]) if r[12] is not None else 0.0,
                    0: r[0], 1: r[1], 2: r[2], 3: r[3], 4: r[4], 5: r[5],
                    6: r[6], 7: r[7], 8: r[8], 9: float(r[9]) if r[9] else 0.0, 10: str(r[10]).lower(),
                    11: r[11], 12: float(r[12]) if r[12] else 0.0
                }
        conexion.close()
    except Exception as e:
        logger.error(f"Error generando recibo de cita ID={cita_id}: {e}")

    if not cita:
        flash('La cita solicitada no existe o no se encontró en el sistema.', 'error')
        return redirect(url_for('citas'))

    return render_template('recibo_cita.html', cita=cita, momento_actual=datetime.now())


@app.route('/cita/ticket/<int:cita_id>', endpoint='ticket_cita')
@app.route('/cita/<int:cita_id>/ticket')
def ver_ticket_cita(cita_id):
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    tenant_id = session.get('tenant_id', 1)
    cita = None

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.id, c.cliente_nombre, COALESCE(c.cliente_email, ''), COALESCE(c.cliente_telefono, ''),
                    TO_CHAR(c.fecha, 'YYYY-MM-DD'), TO_CHAR(c.hora, 'HH12:MI AM'), COALESCE(c.mascota_nombre, ''),
                    COALESCE(c.mascota_especie, 'perro'), COALESCE(c.observaciones, ''), COALESCE(c.precio_total, 0.00),
                    COALESCE(c.estado, 'pendiente'), COALESCE(s.nombre, 'Servicio General')
                FROM citas c
                LEFT JOIN servicios s ON c.servicio_id = s.id
                WHERE c.id = %s AND c.tenant_id = %s
            """, (cita_id, tenant_id))
            
            r = cursor.fetchone()
            if r:
                cita = {
                    'id': r[0], 'cliente_nombre': r[1] or 'Cliente General', 'cliente_email': r[2], 'cliente_telefono': r[3],
                    'fecha': r[4] or '', 'hora': r[5] or '', 'mascota_nombre': r[6], 'mascota_especie': r[7],
                    'observaciones': r[8], 'precio_total': float(r[9]) if r[9] else 0.0, 'estado': str(r[10]).lower(),
                    'servicio_nombre': r[11],
                    0: r[0], 1: r[1], 2: r[2], 3: r[3], 4: r[4], 5: r[5],
                    6: r[6], 7: r[7], 8: r[8], 9: float(r[9]) if r[9] else 0.0,
                    10: str(r[10]).lower(), 11: r[11]
                }
        conexion.close()
    except Exception as e:
        logger.error(f"Error generando ticket de cita ID={cita_id}: {e}")

    if not cita:
        flash('La cita solicitada no existe.', 'error')
        return redirect(url_for('citas'))

    return render_template('ticket_cita.html', cita=cita, momento_actual=datetime.now())


@app.route('/cita/<int:cita_id>/editar', methods=['GET', 'POST'])
def editar_cita(cita_id):
    if session.get('rol') not in ['admin', 'empleado', 'dueño']:
        flash('Sin permisos.', 'error')
        return redirect(url_for('citas'))

    tenant_id = session.get('tenant_id', 1)

    if request.method == 'POST':
        try:
            nombre = request.form.get('cliente_nombre', '').strip()
            fecha = request.form.get('fecha', '').strip()
            hora = request.form.get('hora', '').strip()
            servicio_id = request.form.get('servicio_id')
            mascota_nombre = request.form.get('mascota_nombre', '').strip()
            observaciones = request.form.get('observaciones', '').strip()

            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                cursor.execute("""
                    UPDATE citas 
                    SET cliente_nombre = %s, fecha = %s, hora = %s, servicio_id = %s,
                        mascota_nombre = %s, observaciones = %s
                    WHERE id = %s AND tenant_id = %s
                """, (nombre, fecha, hora, servicio_id, mascota_nombre, observaciones, cita_id, tenant_id))
            conexion.commit()
            conexion.close()

            flash('Cita actualizada correctamente.', 'success')
            return redirect(url_for('citas'))
        except Exception as e:
            logger.error(f"Error editando cita: {e}")
            flash(f'Error al editar cita: {e}', 'error')
            return redirect(url_for('citas'))

    return redirect(url_for('citas'))


@app.route('/cita/<int:cita_id>/eliminar', methods=['POST', 'DELETE'])
@app.route('/citas/eliminar/<int:cita_id>', methods=['POST', 'DELETE'])
def eliminar_cita(cita_id):
    if session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403

    try:
        tenant_id = session.get('tenant_id', 1)
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM citas_mascotas WHERE cita_id = %s AND tenant_id = %s", (cita_id, tenant_id))
            cursor.execute("DELETE FROM citas_servicios WHERE cita_id = %s AND tenant_id = %s", (cita_id, tenant_id))
            cursor.execute("DELETE FROM citas WHERE id = %s AND tenant_id = %s", (cita_id, tenant_id))
        conexion.commit()
        conexion.close()

        return jsonify({'success': True, 'message': 'Cita eliminada permanentemente.'})
    except Exception as e:
        logger.error(f"Error eliminando cita: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ─── COMPRAS Y PROVEEDORES ───────────────────────────────────────────────────

@app.route('/compras')
def compras():
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = compras_controlador.obtener_compras() if hasattr(compras_controlador, 'obtener_compras') else []
    return render_template('compras.html', compras=lista)


@app.route('/historial_compras', endpoint='historial_compras')
@app.route('/historial-compras')
def historial_compras():
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = compras_controlador.obtener_compras() if hasattr(compras_controlador, 'obtener_compras') else []
    monto_total = 0.0
    for c in lista:
        try:
            monto_total += float(c[3] if isinstance(c, (list, tuple)) and len(c) > 3 else getattr(c, 'total', 0))
        except Exception:
            pass
            
    estadisticas = {
        'total_compras': len(lista),
        'monto_total': monto_total
    }
    return render_template('historial_compras.html', compras=lista, estadisticas=estadisticas)


# ─── CARRITO Y PAGO E-COMMERCE ───────────────────────────────────────────────

def _get_cart():
    return session.get('cart', {})

def _save_cart(cart):
    session['cart'] = cart
    session.modified = True

@app.route('/carrito')
def ver_carrito():
    cart = _get_cart()
    items = []
    total_qty = 0
    total_price = 0.0
    
    for id_str, data in list(cart.items()):
        qty = int(data.get('qty', 0))
        if id_str.startswith('service_'):
            try:
                servicio_id = int(id_str.replace('service_', ''))
                servicio = servicios_controlador.obtener_servicio_por_id(servicio_id) if hasattr(servicios_controlador, 'obtener_servicio_por_id') else None
                if not servicio:
                    cart.pop(id_str, None)
                    continue
                
                precio_unitario = float(servicio[3] if len(servicio) > 3 and servicio[3] else 0.0)
                subtotal = precio_unitario * qty
                
                items.append({
                    'id': f'service_{servicio_id}',
                    'nombre': f"🏥 {servicio[1]} (Servicio)",
                    'descripcion': servicio[2] if len(servicio) > 2 else 'Servicio veterinario',
                    'precio_unitario': precio_unitario,
                    'qty': qty,
                    'subtotal': subtotal,
                    'type': 'service',
                    'imagen': None
                })
                total_qty += qty
                total_price += subtotal
            except Exception as e:
                logger.warning(f"Error procesando servicio {id_str}: {e}")
                continue
        else:
            try:
                pid = int(id_str)
                producto = productos_controlador.obtener_producto_por_id(pid) if hasattr(productos_controlador, 'obtener_producto_por_id') else None
                if not producto:
                    cart.pop(id_str, None)
                    continue
                
                stock = int(producto[3] or 0)
                if qty > stock:
                    qty = stock
                    cart[id_str]['qty'] = qty
                
                precio_unitario = float(producto[4] if len(producto) > 4 and producto[4] else 0.0)
                subtotal = precio_unitario * qty
                
                items.append({
                    'id': pid,
                    'nombre': producto[1],
                    'imagen': producto[7] if len(producto) > 7 else None,
                    'precio_unitario': precio_unitario,
                    'qty': qty,
                    'subtotal': subtotal,
                    'stock': stock,
                    'type': 'product'
                })
                total_qty += qty
                total_price += subtotal
            except Exception as e:
                logger.warning(f"Error procesando producto {id_str}: {e}")
                continue
    
    _save_cart(cart)
    return render_template('carrito.html', items=items, total_qty=total_qty, total_price=total_price)


@app.route('/carrito/agregar', methods=['POST'])
def agregar_al_carrito():
    try:
        producto_id = int(request.form.get('producto_id'))
        cantidad = int(request.form.get('cantidad', 1))
    except Exception:
        flash('Datos inválidos para agregar al carrito.', 'error')
        return redirect(request.referrer or url_for('index'))

    producto = productos_controlador.obtener_producto_por_id(producto_id) if hasattr(productos_controlador, 'obtener_producto_por_id') else None
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('index'))

    stock = int(producto[3] or 0)
    if cantidad <= 0 or stock < 1:
        flash('Cantidad inválida o producto agotado.', 'warning')
        return redirect(url_for('index'))

    cart = _get_cart()
    key = str(producto_id)
    existing = int(cart.get(key, {}).get('qty', 0))
    new_qty = existing + cantidad
    if new_qty > stock:
        new_qty = stock
        flash(f'Se ajustó la cantidad al stock disponible ({stock}).', 'info')

    cart[key] = {'qty': new_qty}
    _save_cart(cart)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    total_qty = sum(int(v.get('qty', 0)) for v in session.get('cart', {}).values())
    message = f'Producto "{producto[1]}" agregado al carrito. Cantidad: {new_qty}'
    if is_ajax:
        return jsonify({'success': True, 'message': message, 'cart_count': total_qty})

    flash(message, 'success')
    return redirect(url_for('ver_carrito'))


@app.route('/carrito/eliminar', methods=['POST'])
def carrito_eliminar():
    try:
        producto_id = int(request.form.get('producto_id'))
    except (ValueError, TypeError):
        return 'Error: ID de producto inválido', 400

    cart = _get_cart()
    key = str(producto_id)
    
    if key in cart:
        del cart[key]
        _save_cart(cart)
        return 'OK', 200
    return 'Error: Producto no encontrado en carrito', 404


@app.route('/carrito/actualizar', methods=['POST'])
def carrito_actualizar():
    try:
        producto_id = int(request.form.get('producto_id'))
        cantidad = int(request.form.get('cantidad', 1))
    except (ValueError, TypeError):
        return 'Error: Datos inválidos', 400

    producto = productos_controlador.obtener_producto_por_id(producto_id) if hasattr(productos_controlador, 'obtener_producto_por_id') else None
    if not producto or cantidad <= 0:
        return 'Error al actualizar', 400

    cart = _get_cart()
    key = str(producto_id)
    stock = int(producto[3] or 0)
    if cantidad > stock:
        cantidad = stock
    
    cart[key] = {'qty': cantidad}
    _save_cart(cart)
    return 'OK', 200


@app.route('/checkout')
def checkout():
    cart = _get_cart()
    if not cart:
        flash('Tu carrito está vacío', 'warning')
        return redirect(url_for('ver_carrito'))
    
    items = []
    subtotal = 0.0
    for id_str, data in cart.items():
        try:
            pid = int(id_str)
        except Exception:
            continue
        producto = productos_controlador.obtener_producto_por_id(pid) if hasattr(productos_controlador, 'obtener_producto_por_id') else None
        if not producto:
            continue
        qty = int(data.get('qty', 0))
        precio_unitario = float(producto[4] if len(producto) > 4 and producto[4] else 0.0)
        subtotal_item = precio_unitario * qty
        items.append({
            'id': pid,
            'nombre': producto[1],
            'imagen': producto[7] if len(producto) > 7 else None,
            'qty': qty,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal_item
        })
        subtotal += subtotal_item
    
    igv = round(subtotal * 0.18, 2)
    total_final = subtotal + igv
    
    return render_template('checkout.html', items=items, total=subtotal, igv=igv, total_final=total_final)


@app.route('/procesar-pago', methods=['POST'])
def procesar_pago():
    try:
        cart = _get_cart()
        if not cart:
            flash('Tu carrito está vacío', 'warning')
            return redirect(url_for('ver_carrito'))
        
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        documento = request.form.get('documento', '').strip()
        metodo_pago = request.form.get('metodo_pago', 'efectivo').strip()
        
        if not all([nombre, email, telefono, direccion, metodo_pago]):
            flash('Por favor completa todos los campos obligatorios.', 'error')
            return redirect(url_for('checkout'))
        
        items = []
        subtotal = 0.0
        for id_str, data in cart.items():
            try:
                pid = int(id_str)
            except Exception:
                continue
            
            producto = productos_controlador.obtener_producto_por_id(pid) if hasattr(productos_controlador, 'obtener_producto_por_id') else None
            if not producto:
                continue
            qty = int(data.get('qty', 0))
            precio_unitario = float(producto[4] if len(producto) > 4 and producto[4] else 0.0)
            subtotal_item = precio_unitario * qty
            items.append({
                'id': pid,
                'nombre': producto[1],
                'cantidad': qty,
                'precio': precio_unitario,
                'subtotal': subtotal_item
            })
            subtotal += subtotal_item
        
        igv = round(subtotal * 0.18, 2)
        total_final = subtotal + igv
        tenant_id = session.get('tenant_id', 1)
        num_venta = f"VNT-{int(time.time())}"
        productos_json = json.dumps(items, ensure_ascii=False)

        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ventas (
                    numero_venta, fecha_venta, cliente_nombre, cliente_documento,
                    vendedor_nombre, metodo_pago, subtotal, igv, total,
                    monto_recibido, cambio_entregado, productos, estado, tenant_id
                ) VALUES (
                    %s, NOW(), %s, %s, 'Web Store', %s, %s, %s, %s, %s, 0.00, %s, 'completada'::estado_venta_enum, %s
                ) RETURNING id
            """, (num_venta, nombre, documento, metodo_pago, subtotal, igv, total_final, total_final, productos_json, tenant_id))
            
            venta_id = cursor.fetchone()[0]

            for item in items:
                cursor.execute("UPDATE productos SET stock = GREATEST(stock - %s, 0) WHERE id = %s", (item['cantidad'], item['id']))

        conexion.commit()
        conexion.close()

        session.pop('cart', None)
        flash('¡Pago y pedido procesados exitosamente!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error procesando pago e-commerce: {e}")
        flash(f'Hubo un error procesando tu pago: {str(e)}', 'error')
        return redirect(url_for('checkout'))


# ─── FIDELIZACIÓN Y TENANTS ──────────────────────────────────────────────────

@app.route('/fidelizacion')
def fidelizacion():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    alertas = fidelizacion_ctrl.obtener_alertas_recientes() if hasattr(fidelizacion_ctrl, 'obtener_alertas_recientes') else []
    return render_template('fidelizacion.html', alertas=alertas)


@app.route('/gestionar_tenants')
def gestionar_tenants():
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, nombre, slug, activo, created_at FROM tenants ORDER BY id")
            tenants = cursor.fetchall()
    finally:
        conexion.close()
    return render_template('gestionar_tenants.html', tenants=tenants)


@app.route('/gestionar_tenants/crear', methods=['POST'])
def crear_tenant():
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    
    nombre = request.form.get('nombre', '').strip()
    slug = request.form.get('slug', '').strip().lower().replace(' ', '_')
    admin_username = request.form.get('admin_username', '').strip()
    admin_password = request.form.get('admin_password', '').strip()
    
    if not all([nombre, slug, admin_username, admin_password]):
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('gestionar_tenants'))
        
    from controladores.usuarios_controlador import hash_password
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tenants (nombre, slug) VALUES (%s, %s) RETURNING id", 
                (nombre, slug)
            )
            res = cursor.fetchone()
            tenant_id = res[0] if res else None
            
            hashed = hash_password(admin_password)
            cursor.execute(
                "INSERT INTO usuarios (username, password, rol, activo, tenant_id) VALUES (%s, %s, 'admin', true, %s)",
                (admin_username, hashed, tenant_id)
            )
        conexion.commit()
        flash(f'Tenant "{nombre}" creado con éxito.', 'success')
    except Exception as e:
        conexion.rollback()
        flash(f'Error al crear tenant: {str(e)}', 'error')
    finally:
        conexion.close()
    return redirect(url_for('gestionar_tenants'))


@app.route('/gestionar_tenants/toggle/<int:tenant_id>', methods=['POST'])
def toggle_tenant(tenant_id):
    if session.get('rol') != 'superadmin':
        return redirect(url_for('login'))
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE tenants SET activo = NOT activo WHERE id = %s", (tenant_id,))
        conexion.commit()
        flash('Estado del tenant actualizado.', 'success')
    except Exception as e:
        conexion.rollback()
        flash(f'Error: {str(e)}', 'error')
    finally:
        conexion.close()
    return redirect(url_for('gestionar_tenants'))


if __name__ == '__main__':
    app.run(debug=True)