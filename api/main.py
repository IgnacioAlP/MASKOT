from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import logging
import time
from datetime import datetime, date
import hashlib
import os
from werkzeug.utils import secure_filename
from functools import wraps
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

app = Flask(
    __name__, 
    template_folder=os.path.join(os.path.dirname(__file__), '../templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '../static')
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

# Almacenamiento temporal en memoria para sincronización de escáner remoto en tiempo real
RECENT_SCANS = []


def _ensure_schema():
    """Migración ligera al arranque adaptada para PostgreSQL / Supabase."""
    column_migrations = [
        ("productos", "codigo_barra", "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo_barra VARCHAR(100) DEFAULT NULL"),
        ("citas",     "tenant_id",   "ALTER TABLE citas ADD COLUMN IF NOT EXISTS tenant_id INT DEFAULT 1"),
        ("ventas",    "tenant_id",   "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tenant_id INT DEFAULT 1"),
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

            cursor.execute("""
                SELECT is_nullable FROM information_schema.columns 
                WHERE table_name = 'ventas' AND column_name = 'vendedor_nombre'
            """)
            vn_col = cursor.fetchone()
            if vn_col and (vn_col[0] or '').upper() == 'NO':
                cursor.execute("ALTER TABLE ventas ALTER COLUMN vendedor_nombre DROP NOT NULL")
                conn.commit()
                logger.info("Schema migration: ventas.vendedor_nombre ahora acepta NULL.")

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
        today = date.today()
        delta = value - today
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


def _get_cart():
    return session.setdefault('cart', {})


def _save_cart(cart):
    session['cart'] = cart


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


# ─── RUTAS PRINCIPALES DEL SISTEMA (ENDPOINTS DEL MENÚ) ──────────────────────

@app.route('/punto_de_venta', methods=['GET', 'POST'])
@app.route('/pos', methods=['GET', 'POST'])
def punto_de_venta():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    productos_lista = productos_controlador.obtener_productos_tienda() if hasattr(productos_controlador, 'obtener_productos_tienda') else productos_controlador.obtener_productos()
    servicios_lista = servicios_controlador.obtener_servicios() if hasattr(servicios_controlador, 'obtener_servicios') else []
    return render_template('pos.html', productos=productos_lista, servicios=servicios_lista)


@app.route('/productos')
def productos():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = productos_controlador.obtener_productos()
    return render_template('productos.html', productos=lista)


@app.route('/producto/<int:producto_id>')
def ver_producto(producto_id):
    producto = productos_controlador.obtener_producto_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('productos'))
    return render_template('ver_producto.html', producto=producto)


@app.route('/servicios')
def servicios():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = servicios_controlador.obtener_servicios()
    return render_template('gestion_servicios.html', servicios=lista)


@app.route('/servicios/agregar', methods=['POST'])
def agregar_servicio():
    if session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    try:
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion', '')
        precio = float(request.form.get('precio', 0.0))
        duracion = int(request.form.get('duracion_minutos', 30))
        
        if hasattr(servicios_controlador, 'insertar_servicio'):
            servicios_controlador.insertar_servicio(nombre, descripcion, precio, duracion)
        flash('Servicio registrado exitosamente.', 'success')
        return redirect(url_for('servicios'))
    except Exception as e:
        flash(f'Error al registrar servicio: {e}', 'error')
        return redirect(url_for('servicios'))


@app.route('/servicios/editar', methods=['POST'])
def editar_servicio():
    if session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    try:
        servicio_id = int(request.form.get('id'))
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion', '')
        precio = float(request.form.get('precio', 0.0))
        duracion = int(request.form.get('duracion_minutos', 30))
        
        if hasattr(servicios_controlador, 'actualizar_servicio'):
            servicios_controlador.actualizar_servicio(servicio_id, nombre, descripcion, precio, duracion)
        flash('Servicio actualizado exitosamente.', 'success')
        return redirect(url_for('servicios'))
    except Exception as e:
        flash(f'Error al actualizar servicio: {e}', 'error')
        return redirect(url_for('servicios'))


@app.route('/servicios/cambiar-estado', methods=['POST'])
def cambiar_estado_servicio():
    if session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    try:
        data = request.get_json() or {}
        servicio_id = data.get('id')
        activo = data.get('activo', True)
        
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE servicios SET activo = %s WHERE id = %s", (activo, servicio_id))
        conexion.commit()
        conexion.close()
        return jsonify({'success': True, 'message': 'Estado del servicio actualizado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/clientes')
def clientes():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = clientes_controlador.obtener_clientes() if hasattr(clientes_controlador, 'obtener_clientes') else []
    return render_template('clientes.html', clientes=lista)


@app.route('/mascotas')
def mascotas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = mascotas_controlador.obtener_mascotas() if hasattr(mascotas_controlador, 'obtener_mascotas') else []
    return render_template('mascotas.html', mascotas=lista)


@app.route('/personal')
def personal():
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    empleados = personal_controlador.obtener_empleados() if hasattr(personal_controlador, 'obtener_empleados') else []
    usuarios = usuarios_controlador.obtener_usuarios() if hasattr(usuarios_controlador, 'obtener_usuarios') else []
    return render_template('personal.html', empleados=empleados, usuarios=usuarios)


@app.route('/personal/agregar', methods=['POST'])
def agregar_personal():
    if session.get('rol') not in ['admin', 'dueño']:
        flash('Sin permisos.', 'error')
        return redirect(url_for('personal'))
    try:
        nombre = request.form.get('nombre')
        cargo = request.form.get('cargo')
        salario = float(request.form.get('salario', 0.0))
        if hasattr(personal_controlador, 'insertar_empleado'):
            personal_controlador.insertar_empleado(nombre, cargo, salario)
        flash('Personal agregado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al agregar personal: {e}', 'error')
    return redirect(url_for('personal'))


@app.route('/compras')
def compras():
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = compras_controlador.obtener_compras() if hasattr(compras_controlador, 'obtener_compras') else []
    return render_template('compras.html', compras=lista)


@app.route('/ventas', endpoint='historial_ventas')
@app.route('/historial_ventas')
def ventas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = ventas_controlador.obtener_ventas_por_fecha() if hasattr(ventas_controlador, 'obtener_ventas_por_fecha') else []
    return render_template('ventas.html', ventas=lista)


@app.route('/venta/ticket/<int:venta_id>', endpoint='ticket_venta')
def ver_ticket_venta(venta_id):
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    venta = None
    if hasattr(ventas_controlador, 'obtener_venta_por_id'):
        venta = ventas_controlador.obtener_venta_por_id(venta_id)
    
    if not venta:
        flash('Venta no encontrada.', 'error')
        return redirect(url_for('historial_ventas'))
        
    return render_template('ticket_venta.html', venta=venta)


@app.route('/fidelizacion')
def fidelizacion():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    alertas = fidelizacion_ctrl.obtener_alertas_recientes() if hasattr(fidelizacion_ctrl, 'obtener_alertas_recientes') else []
    return render_template('fidelizacion.html', alertas=alertas)


@app.route('/asistencia', methods=['GET', 'POST'])
def asistencia():
    if 'rol' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        try:
            usuario_id = session.get('user_id')
            tipo = request.form.get('tipo', 'entrada')
            if hasattr(asistencia_controlador, 'registrar_asistencia'):
                asistencia_controlador.registrar_asistencia(usuario_id, tipo)
            flash('Asistencia registrada correctamente.', 'success')
        except Exception as e:
            logger.error(f"Error registrando asistencia: {e}")
            flash('Error al registrar la asistencia.', 'error')
        return redirect(url_for('asistencia'))

    registros = []
    try:
        if hasattr(asistencia_controlador, 'obtener_asistencia_hoy'):
            registros = asistencia_controlador.obtener_asistencia_hoy()
        elif hasattr(asistencia_controlador, 'obtener_registros'):
            registros = asistencia_controlador.obtener_registros()
    except Exception as e:
        logger.warning(f"Error cargando registros de asistencia: {e}")

    return render_template('asistencia.html', registros=registros)


@app.route('/citas')
def citas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    fecha_filtro = request.args.get('fecha', default=date.today().strftime('%Y-%m-%d'))
    citas_list = citas_controlador.obtener_citas_por_fecha(fecha_filtro)
    servicios_lista = servicios_controlador.obtener_servicios()
    
    return render_template('citas.html', citas=citas_list, fecha_filtro=fecha_filtro, servicios=servicios_lista)


@app.route('/cita/<int:cita_id>', endpoint='ver_detalles_cita')
@app.route('/cita/recibo/<int:cita_id>')
def ver_recibo_cita(cita_id):
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    cita = citas_controlador.obtener_cita_por_id(cita_id) if hasattr(citas_controlador, 'obtener_cita_por_id') else None
    if not cita:
        flash('Cita no encontrada.', 'error')
        return redirect(url_for('citas'))
    return render_template('recibo_cita.html', cita=cita)


@app.route('/cita/ticket/<int:cita_id>', endpoint='ticket_cita')
def ver_ticket_cita(cita_id):
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    cita = citas_controlador.obtener_cita_por_id(cita_id) if hasattr(citas_controlador, 'obtener_cita_por_id') else None
    if not cita:
        flash('Cita no encontrada.', 'error')
        return redirect(url_for('citas'))
    return render_template('ticket_cita.html', cita=cita)


# ─── ACCIONES CITAS ──────────────────────────────────────────────────────────

@app.route('/cita/<int:cita_id>/status', methods=['POST'])
def cambiar_estado_cita(cita_id):
    if 'usuario' not in session or session.get('rol') not in ['admin', 'empleado', 'dueño']:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    conexion = None
    try:
        data = request.get_json() or {}
        nuevo_estado = data.get('status')
        motivo = data.get('motivo', '')
        
        if not nuevo_estado or nuevo_estado not in ['pendiente', 'confirmada', 'en_progreso', 'completada', 'cancelada']:
            return jsonify({'success': False, 'error': 'Estado no válido'}), 400
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("UPDATE citas SET estado = %s WHERE id = %s", (nuevo_estado, cita_id))
        
        if motivo:
            cursor.execute("""
                UPDATE citas 
                SET observaciones = CASE 
                    WHEN observaciones IS NULL OR observaciones = '' THEN %s
                    ELSE observaciones || ' | ' || %s
                END
                WHERE id = %s
            """, (f"Motivo: {motivo}", f"Motivo: {motivo}", cita_id))
        
        conexion.commit()
        return jsonify({'success': True, 'message': 'Estado actualizado'})
    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conexion:
            conexion.close()


@app.route('/cita/<int:cita_id>/eliminar', methods=['DELETE'])
def eliminar_cita(cita_id):
    if session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403
    
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("DELETE FROM cita_mascotas WHERE cita_id = %s", (cita_id,))
        cursor.execute("DELETE FROM cita_servicios WHERE cita_id = %s", (cita_id,))
        cursor.execute("DELETE FROM citas WHERE id = %s", (cita_id,))
        
        conexion.commit()
        return jsonify({'success': True, 'message': 'Cita eliminada permanentemente'})
    except Exception as e:
        if conexion:
            conexion.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conexion:
            conexion.close()


@app.route('/agendar_cita', methods=['POST'])
def agendar_cita():
    try:
        nombre = request.form['cliente_nombre']
        email = request.form['cliente_email']
        telefono = request.form.get('cliente_telefono', '').strip()
        direccion = request.form.get('cliente_direccion', '').strip()
        fecha = request.form['fecha']
        hora = request.form['hora']
        
        servicios_ids = [int(sid) for sid in request.form.getlist('servicio_id[]') if sid]
        if not servicios_ids or not telefono or not direccion:
            flash('Por favor proporciona los campos requeridos.', 'error')
            return redirect(url_for('index'))

        mascota_nombres = request.form.getlist('mascota_nombre[]')
        mascotas_data = [{'nombre': m.strip()} for m in mascota_nombres if m.strip()]
        
        cita_id = citas_controlador.insertar_cita_completa(nombre, email, mascotas_data, servicios_ids, fecha, hora)
        flash('Cita agendada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al agendar la cita: {str(e)}', 'error')
    
    return redirect(url_for('index'))


# ─── API POS & TRANSACCIONES EN TIEMPO REAL ─────────────────────────────────

@app.route('/api/ventas/buscar-productos')
def api_buscar_productos():
    q = request.args.get('q', '').strip()
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            if q:
                cursor.execute("""
                    SELECT id, nombre, precio, stock, codigo_barra 
                    FROM productos 
                    WHERE (nombre ILIKE %s OR codigo_barra = %s) AND activo = true
                    LIMIT 20
                """, (f"%{q}%", q))
            else:
                cursor.execute("SELECT id, nombre, precio, stock, codigo_barra FROM productos WHERE activo = true LIMIT 30")
            
            rows = cursor.fetchall()
            productos = [{
                'id': r[0],
                'nombre': r[1],
                'precio': float(r[2] or 0),
                'stock': r[3] or 0,
                'codigo_barra': r[4] or ''
            } for r in rows]
        conexion.close()
        return jsonify({'success': True, 'productos': productos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ventas/validar-stock', methods=['POST'])
def api_validar_stock():
    data = request.get_json() or {}
    items = data.get('items', [])
    errores = []
    
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            for item in items:
                pid = item.get('id')
                cant = int(item.get('cantidad', 1))
                cursor.execute("SELECT nombre, stock FROM productos WHERE id = %s", (pid,))
                row = cursor.fetchone()
                if not row:
                    errores.append(f"Producto ID {pid} no encontrado.")
                elif row[1] < cant:
                    errores.append(f"Stock insuficiente para {row[0]}. Disponible: {row[1]}, Solicitado: {cant}")
        conexion.close()
        
        if errores:
            return jsonify({'success': False, 'message': 'Validation failed', 'errors': errores}), 400
        return jsonify({'success': True, 'message': 'Stock verificado correctamente'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/ventas/procesar', methods=['POST'])
def procesar_venta_pos():
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    try:
        data = request.get_json() or {}
        items = data.get('items', [])
        cliente_nombre = data.get('cliente_nombre', 'Cliente General')
        cliente_doc = data.get('cliente_documento', '')
        metodo_pago = data.get('metodo_pago', 'efectivo')
        monto_recibido = float(data.get('monto_recibido', 0.0))
        subtotal = float(data.get('subtotal', 0.0))
        igv = float(data.get('igv', 0.0))
        total = float(data.get('total', 0.0))
        cambio = float(data.get('cambio', 0.0))
        
        if not items:
            return jsonify({'success': False, 'error': 'El carrito está vacío'}), 400

        vendedor_nombre = session.get('usuario', 'Cajero')
        tenant_id = session.get('tenant_id', 1)
        num_venta = f"VNT-{int(time.time())}"
        
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ventas (numero_venta, fecha_venta, cliente_nombre, cliente_documento, 
                                    vendedor_nombre, metodo_pago, subtotal, igv, total, 
                                    monto_recibido, cambio_entregado, estado, tenant_id)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completada', %s)
                RETURNING id
            """, (num_venta, cliente_nombre, cliente_doc, vendedor_nombre, metodo_pago,
                  subtotal, igv, total, monto_recibido, cambio, tenant_id))
            
            venta_id = cursor.fetchone()[0]
            
            for item in items:
                pid = item.get('id')
                cant = int(item.get('cantidad', 1))
                precio = float(item.get('precio', 0.0))
                cursor.execute("""
                    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (venta_id, pid, cant, precio, cant * precio))
                
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cant, pid))
                
        conexion.commit()
        conexion.close()
        
        ticket_url = url_for('ticket_venta', venta_id=venta_id)
        return jsonify({'success': True, 'venta_id': venta_id, 'ticket_url': ticket_url})
    except Exception as e:
        logger.error(f"Error procesando venta POS: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/ventas/scan-push', methods=['POST'])
def scan_push():
    data = request.get_json() or {}
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


# ─── CARRITO Y CHECKOUT TIENDA ───────────────────────────────────────────────

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
                servicio = servicios_controlador.obtener_servicio_por_id(servicio_id)
                if not servicio:
                    cart.pop(id_str, None)
                    continue
                
                precio_unitario = float(servicio[3] or 0)
                subtotal = precio_unitario * qty
                
                items.append({
                    'id': f'service_{servicio_id}',
                    'nombre': f"🏥 {servicio[1]} (Servicio)",
                    'descripcion': servicio[2] or 'Servicio veterinario',
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
                producto = productos_controlador.obtener_producto_por_id(pid)
                if not producto:
                    cart.pop(id_str, None)
                    continue
                
                stock = producto[3] or 0
                if qty > stock:
                    qty = stock
                    cart[id_str]['qty'] = qty
                
                precio_unitario = float(producto[4] or 0)
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

    producto = productos_controlador.obtener_producto_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('index'))

    stock = producto[3] or 0
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

    producto = productos_controlador.obtener_producto_por_id(producto_id)
    if not producto or cantidad <= 0:
        return 'Error al actualizar', 400

    cart = _get_cart()
    key = str(producto_id)
    stock = producto[3] or 0
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
        producto = productos_controlador.obtener_producto_por_id(pid)
        if not producto:
            continue
        qty = int(data.get('qty', 0))
        precio_unitario = float(producto[4] or 0)
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
        
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        documento = request.form.get('documento')
        metodo_pago = request.form.get('metodo_pago')
        
        if not all([nombre, email, telefono, direccion, metodo_pago]):
            flash('Por favor completa todos los campos obligatorios', 'error')
            return redirect(url_for('checkout'))
        
        items = []
        subtotal = 0.0
        for id_str, data in cart.items():
            try:
                pid = int(id_str)
            except Exception:
                continue
            producto = productos_controlador.obtener_producto_por_id(pid)
            if not producto:
                continue
            qty = int(data.get('qty', 0))
            precio_unitario = float(producto[4] or 0)
            subtotal_item = precio_unitario * qty
            items.append({
                'id': pid,
                'nombre': producto[1],
                'qty': qty,
                'precio_unitario': precio_unitario,
                'subtotal': subtotal_item
            })
            subtotal += subtotal_item
        
        igv = round(subtotal * 0.18, 2)
        total_final = subtotal + igv
        
        cliente_id = None
        if hasattr(clientes_controlador, 'obtener_cliente_por_email'):
            cliente = clientes_controlador.obtener_cliente_por_email(email)
            if cliente:
                cliente_id = cliente[0]
        
        if not cliente_id and hasattr(clientes_controlador, 'insertar_cliente'):
            cliente_id = clientes_controlador.insertar_cliente(nombre, email, telefono, direccion, documento)
        
        if hasattr(clientes_controlador, 'insertar_pedido'):
            clientes_controlador.insertar_pedido(cliente_id, items, total_final, metodo_pago, subtotal, igv)
        
        session.pop('cart', None)
        flash('¡Pago procesado exitosamente!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error procesando pago: {e}")
        flash('Hubo un error procesando tu pago.', 'error')
        return redirect(url_for('checkout'))


# ─── GESTIÓN DE TENANTS ──────────────────────────────────────────────────────

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