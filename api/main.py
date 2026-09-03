from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import logging
import time
from datetime import datetime, date
import hashlib
import json
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

# Obtener la ruta de la carpeta raíz del proyecto (MASKOT)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # MASKOT/api
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

# Almacenamiento temporal en memoria para sincronización de escáner remoto en tiempo real
RECENT_SCANS = []


def _ensure_schema():
    """Migración ligera al arranque adaptada para PostgreSQL / Supabase."""
    column_migrations = [
        ("productos", "codigo_barra", "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo_barra VARCHAR(100) DEFAULT NULL"),
        ("citas",     "tenant_id",   "ALTER TABLE citas ADD COLUMN IF NOT EXISTS tenant_id INT DEFAULT 1"),
        ("ventas",    "tenant_id",   "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tenant_id INT DEFAULT 1"),
        ("ventas",    "vendedor_id", "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS vendedor_id INT DEFAULT NULL"),
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

            # Permitir NULL en vendedor_nombre y vendedor_id para evitar errores de constraing
            for col in ['vendedor_nombre', 'vendedor_id']:
                cursor.execute("""
                    SELECT is_nullable FROM information_schema.columns 
                    WHERE table_name = 'ventas' AND column_name = %s
                """, (col,))
                v_col = cursor.fetchone()
                if v_col and (v_col[0] or '').upper() == 'NO':
                    cursor.execute(f"ALTER TABLE ventas ALTER COLUMN {col} DROP NOT NULL")
                    conn.commit()
                    logger.info(f"Schema migration: ventas.{col} ahora acepta NULL.")

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


# ─── RUTAS PRINCIPALES DEL SISTEMA Y GESTIÓN ──────────────────────────────────

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


@app.route('/almacen', methods=['GET', 'POST'])
@app.route('/productos/agregar', methods=['POST'], endpoint='agregar_producto')
@app.route('/productos/editar', methods=['POST'], endpoint='editar_producto')
def almacen():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # Captura de ID
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

            # Captura dinámica del Stock Mínimo
            stk_min_raw = (request.form.get('stock_minimo') or 
                           request.form.get('cant_min') or 
                           request.form.get('stock_min') or '').strip()
            stock_minimo = int(stk_min_raw) if stk_min_raw and stk_min_raw.isdigit() else 5

            conexion = obtener_conexion()
            with conexion.cursor() as cursor:
                # Asegurar que la columna existe en la base de datos
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

    # Lectura de productos incluyendo la columna stock_minimo
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
                    # Mapeo posicional para la plantilla HTML
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

    # Lectura directa desde Supabase usando los campos reales
    productos_lista = []
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, nombre, tipo, NULL as img, cantidad, precio FROM productos ORDER BY id ASC")
            productos_lista = cursor.fetchall()
        conexion.close()
    except Exception as e:
        logger.error(f"Error consultando productos: {e}")

    return render_template('almacen.html', productos=productos_lista)
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    # Procesar registro de nuevo producto
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            codigo_barra = request.form.get('codigo_barra', '').strip()
            descripcion = request.form.get('descripcion', '').strip()

            # Conversión segura para evitar float('') o int('')
            precio_raw = request.form.get('precio', '').strip()
            precio = float(precio_raw) if precio_raw else 0.0

            stock_raw = request.form.get('stock', '').strip()
            stock = int(stock_raw) if stock_raw else 0

            if hasattr(productos_controlador, 'insertar_producto'):
                productos_controlador.insertar_producto(nombre, descripcion, stock, precio, codigo_barra)
            else:
                conexion = obtener_conexion()
                with conexion.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO productos (nombre, descripcion, stock, precio, codigo_barra, activo)
                        VALUES (%s, %s, %s, %s, %s, true)
                    """, (nombre, descripcion, stock, precio, codigo_barra))
                conexion.commit()
                conexion.close()

            flash('Producto registrado correctamente en el almacén.', 'success')
        except Exception as e:
            logger.error(f"Error al registrar producto: {e}")
            flash(f'Error al registrar producto: {e}', 'error')
        return redirect(url_for('almacen'))
        
    # Renderizar vista GET de Almacén
    raw_prods = productos_controlador.obtener_productos() if hasattr(productos_controlador, 'obtener_productos') else []
    productos_lista = []
    
    for p in raw_prods:
        if isinstance(p, (tuple, list)):
            p_list = list(p)
            while len(p_list) < 8:
                p_list.append(None)
            p_list[3] = p_list[3] if p_list[3] is not None else 0
            p_list[4] = float(p_list[4]) if p_list[4] is not None else 0.0
            p_list[5] = p_list[5] if p_list[5] is not None else 5
            productos_lista.append(p_list)
        else:
            productos_lista.append(p)

    return render_template('almacen.html', productos=productos_lista)


@app.route('/producto/<int:producto_id>')
def ver_producto(producto_id):
    producto = productos_controlador.obtener_producto_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('productos'))
    return render_template('ver_producto.html', producto=producto)


@app.route('/servicios', endpoint='servicios')
@app.route('/gestion_servicios', endpoint='gestion_servicios')
def servicios():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = servicios_controlador.obtener_servicios() if hasattr(servicios_controlador, 'obtener_servicios') else []
    return render_template('servicios.html', servicios=lista)


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
        servicio_id = data.get('id') or data.get('servicio_id')
        activo = data.get('activo', True)
        
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE servicios SET activo = %s WHERE id = %s", (activo, servicio_id))
        conexion.commit()
        conexion.close()
        return jsonify({'success': True, 'message': 'Estado del servicio actualizado'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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


# ─── MÓDULO DE GESTIÓN DE PERSONAL Y USUARIOS (COMPLETO Y SINCRONIZADO) ─────

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

    # ─── PROCESAMIENTO DE PETICIONES POST ─────────────────────────────────────
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

            # 1. Interceptar botón "Desactivar" desde el formulario HTML (<button name="eliminar">)
            if 'eliminar' in request.form or get_param('accion') in ['desactivar', 'eliminar']:
                if target_id:
                    conexion = obtener_conexion()
                    with conexion.cursor() as cursor:
                        cursor.execute("UPDATE personal SET activo = false WHERE id = %s OR usuario_id = %s RETURNING usuario_id", (target_id, target_id))
                        res = cursor.fetchone()
                        if res and res[0]:
                            cursor.execute("UPDATE usuarios SET activo = false WHERE id = %s", (res[0],))
                    conexion.commit()
                    conexion.close()
                    flash('Empleado desactivado correctamente.', 'success')
                    return redirect(url_for('personal'))

            # 2. Interceptar botón "Reactivar" desde el formulario HTML (<button name="reactivar">)
            if 'reactivar' in request.form or get_param('accion') in ['reactivar']:
                if target_id:
                    conexion = obtener_conexion()
                    with conexion.cursor() as cursor:
                        cursor.execute("UPDATE personal SET activo = true WHERE id = %s OR usuario_id = %s RETURNING usuario_id", (target_id, target_id))
                        res = cursor.fetchone()
                        if res and res[0]:
                            cursor.execute("UPDATE usuarios SET activo = true WHERE id = %s", (res[0],))
                    conexion.commit()
                    conexion.close()
                    flash('Empleado reactivado correctamente.', 'success')
                    return redirect(url_for('personal'))

            # 3. Procesar Edición o Registro de Nuevo Empleado
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
                    # CASO A: Modificación de un empleado existente
                    cursor.execute("SELECT id, usuario_id FROM personal WHERE id = %s OR usuario_id = %s", (target_id, target_id))
                    p_row = cursor.fetchone()
                    if p_row:
                        p_id, usuario_id = p_row[0], p_row[1]
                        cursor.execute("UPDATE personal SET cargo = %s, salario = %s WHERE id = %s", (cargo, salario, p_id))
                    else:
                        usuario_id = target_id
                        cursor.execute("INSERT INTO personal (usuario_id, cargo, salario, activo, tenant_id) VALUES (%s, %s, %s, true, %s)", (usuario_id, cargo, salario, tenant_id))

                    if usuario_id and username:
                        cursor.execute("UPDATE usuarios SET username = %s, rol = %s::rol_usuario_enum WHERE id = %s", (username, rol_final, usuario_id))
                    elif usuario_id and rol:
                        cursor.execute("UPDATE usuarios SET rol = %s::rol_usuario_enum WHERE id = %s", (rol_final, usuario_id))

                    mensaje = 'Datos del empleado actualizados correctamente.'
                else:
                    # CASO B: Creación de un nuevo empleado
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

    # ─── VISTA GET: CONSULTA CON MAPEO POSICIONAL EXACTO PARA PERSONAL.HTML ──
    empleados_lista = []
    usuarios_lista = []

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
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
                ORDER BY p.id ASC
            """)
            
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
                    # Mapeo de índices alineado a tu plantilla personal.html
                    0: p_id,         # empleado[0] -> ID
                    1: usuario_id,   # empleado[1] -> ID Usuario
                    2: username,     # empleado[2] -> Nombre de Usuario (Columna Usuario)
                    3: cargo,        # empleado[3] -> Cargo (Columna Cargo)
                    4: salario,      # empleado[4] -> Salario (Columna Salario)
                    5: activo_int,   # empleado[5] -> Activo (1 o 0) (Efectúa el check de badges)
                    6: rol,          # empleado[6] -> Rol (Columna Rol)
                    7: estado_str
                }
                empleados_lista.append(item)

            cursor.execute("SELECT id, username, rol, COALESCE(activo, true) FROM usuarios ORDER BY id ASC")
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

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                UPDATE personal
                SET activo = NOT COALESCE(activo, true)
                WHERE id = %s OR usuario_id = %s
                RETURNING usuario_id, activo
            """, (target_id, target_id))
            
            res = cursor.fetchone()
            
            if res:
                usuario_id, nuevo_estado = res[0], res[1]
                if usuario_id:
                    cursor.execute("UPDATE usuarios SET activo = %s WHERE id = %s", (nuevo_estado, usuario_id))
            else:
                cursor.execute("""
                    UPDATE usuarios
                    SET activo = NOT COALESCE(activo, true)
                    WHERE id = %s
                    RETURNING activo
                """, (target_id,))
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
    if session.get('rol') not in ['admin', 'dueño']:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Sin permisos'}), 403
        flash('Sin permisos para eliminar personal.', 'error')
        return redirect(url_for('personal'))

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, usuario_id FROM personal WHERE id = %s OR usuario_id = %s", (target_id, target_id))
            p_row = cursor.fetchone()
            
            if p_row:
                personal_id, usuario_id = p_row[0], p_row[1]
            else:
                personal_id, usuario_id = None, target_id

            if personal_id:
                cursor.execute("DELETE FROM asistencia WHERE personal_id = %s", (personal_id,))
                cursor.execute("DELETE FROM personal WHERE id = %s", (personal_id,))

            if usuario_id:
                cursor.execute("DELETE FROM asistencia WHERE personal_id IN (SELECT id FROM personal WHERE usuario_id = %s)", (usuario_id,))
                cursor.execute("DELETE FROM personal WHERE usuario_id = %s", (usuario_id,))
                cursor.execute("UPDATE ventas SET vendedor_id = NULL WHERE vendedor_id = %s", (usuario_id,))
                cursor.execute("UPDATE compras SET vendedor_id = NULL WHERE vendedor_id = %s", (usuario_id,))
                cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))

        conexion.commit()
        conexion.close()

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Usuario y ficha eliminados permanentemente.'})

        flash('Usuario eliminado permanentemente de la base de datos.', 'success')
    except Exception as e:
        logger.error(f"Error eliminando usuario/personal: {e}")
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error al eliminar permanentemente: {e}', 'error')

    return redirect(url_for('personal'))


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


@app.route('/ventas')
def ventas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    lista = ventas_controlador.obtener_ventas_por_fecha() if hasattr(ventas_controlador, 'obtener_ventas_por_fecha') else []
    return render_template('ventas.html', ventas=lista)


@app.route('/historial_ventas', endpoint='historial_ventas')
@app.route('/historial-ventas')
def historial_ventas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    filtros = {
        'fecha_inicio': request.args.get('fecha_inicio', ''),
        'fecha_fin': request.args.get('fecha_fin', ''),
        'busqueda': request.args.get('busqueda', '')
    }
    
    lista = ventas_controlador.obtener_ventas_por_fecha() if hasattr(ventas_controlador, 'obtener_ventas_por_fecha') else []
    return render_template('historial_ventas.html', ventas=lista, filtros=filtros)


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


# ─── MÓDULO DE GESTIÓN Y HISTORIAL DE ASISTENCIA ─────────────────────────────

@app.route('/asistencia', methods=['GET', 'POST'])
def asistencia():
    if 'rol' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'error': 'No autorizado'}), 401
        flash('Debes iniciar sesión para acceder a la asistencia.', 'error')
        return redirect(url_for('login'))
        
    tenant_id = session.get('tenant_id', 1)
    usuario_id = session.get('usuario_id') or session.get('user_id') or session.get('id')
    rol = session.get('rol', 'empleado')

    # Procesar registro cuando el formulario/AJAX envía POST a /asistencia
    if request.method == 'POST':
        return _procesar_marcar_asistencia(usuario_id, tenant_id)

    # Vista GET: Renderizado de plantilla con historial y estado actual
    registros = []
    asistencia_actual = None

    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # 1. Estado actual del usuario hoy (calculado según hora_salida)
            cursor.execute("""
                SELECT 
                    a.id, 
                    TO_CHAR(a.hora_entrada, 'HH12:MI AM'), 
                    TO_CHAR(a.hora_salida, 'HH12:MI AM'),
                    CASE WHEN a.hora_salida IS NOT NULL THEN 'completado' ELSE 'presente' END AS estado
                FROM asistencia a
                INNER JOIN personal p ON a.personal_id = p.id
                WHERE p.usuario_id = %s AND a.fecha = CURRENT_DATE AND a.tenant_id = %s
                ORDER BY a.id DESC LIMIT 1
            """, (usuario_id, tenant_id))
            a_row = cursor.fetchone()
            if a_row:
                asistencia_actual = {
                    'id': a_row[0],
                    'hora_entrada': a_row[1],
                    'hora_salida': a_row[2],
                    'estado': a_row[3],
                    0: a_row[0], 1: a_row[1], 2: a_row[2], 3: a_row[3]
                }

            # 2. Registros del día (Admin/Dueño ven todos, Empleado solo los suyos)
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
                    WHERE a.tenant_id = %s AND a.fecha = CURRENT_DATE
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
                    WHERE a.tenant_id = %s AND p.usuario_id = %s AND a.fecha = CURRENT_DATE
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
    usuario_id = session.get('usuario_id') or session.get('user_id') or session.get('id')
    return _procesar_marcar_asistencia(usuario_id, tenant_id)


def _procesar_marcar_asistencia(usuario_id, tenant_id):
    try:
        req_json = request.get_json(silent=True) or {}
        tipo = (req_json.get('tipo') or request.form.get('tipo') or '').strip().lower()
        
        if not tipo:
            if 'salida' in request.form or 'marcar_salida' in request.form:
                tipo = 'salida'
            elif 'entrada' in request.form or 'marcar_entrada' in request.form:
                tipo = 'entrada'

        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # 1. Obtener o enlazar personal_id
            cursor.execute("SELECT id FROM personal WHERE usuario_id = %s AND tenant_id = %s", (usuario_id, tenant_id))
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

            # 2. Consultar si existe un registro activo de hoy
            cursor.execute("""
                SELECT id, hora_salida 
                FROM asistencia 
                WHERE personal_id = %s AND fecha = CURRENT_DATE AND tenant_id = %s
                ORDER BY id DESC LIMIT 1
            """, (personal_id, tenant_id))
            reg_hoy = cursor.fetchone()

            # 3. Operaciones mapeadas únicamente a las 6 columnas del esquema: id, personal_id, fecha, hora_entrada, hora_salida, tenant_id
            if tipo == 'salida' or (not tipo and reg_hoy and reg_hoy[1] is None):
                if reg_hoy:
                    cursor.execute("""
                        UPDATE asistencia 
                        SET hora_salida = CURRENT_TIME 
                        WHERE id = %s AND tenant_id = %s
                    """, (reg_hoy[0], tenant_id))
                else:
                    cursor.execute("""
                        INSERT INTO asistencia (personal_id, fecha, hora_entrada, hora_salida, tenant_id)
                        VALUES (%s, CURRENT_DATE, CURRENT_TIME, CURRENT_TIME, %s)
                    """, (personal_id, tenant_id))
                mensaje = 'Hora de salida registrada correctamente.'
            else:
                cursor.execute("""
                    INSERT INTO asistencia (personal_id, fecha, hora_entrada, tenant_id)
                    VALUES (%s, CURRENT_DATE, CURRENT_TIME, %s)
                """, (personal_id, tenant_id))
                mensaje = 'Hora de entrada registrada correctamente.'

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
    usuario_id = session.get('usuario_id') or session.get('user_id') or session.get('id')
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
                    WHERE a.tenant_id = %s
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
                    WHERE a.tenant_id = %s AND p.usuario_id = %s
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


# ─── INYECTOR GLOBAL DE FECHA Y HORA EN PLANTILLAS (CONTEXT PROCESSOR) ───────

@app.context_processor
def inject_global_datetime():
    ahora = datetime.now()
    return {
        'momento_actual': ahora,
        'today': date.today,
        'now': ahora,
        'format_date': lambda d: d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') else str(d)
    }


# ─── MÓDULO DE GESTIÓN DE CITAS (COMPLETO) ───────────────────────────────────

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
            # 1. Obtener Citas con el ordenamiento exacto de posiciones que exige citas.html
            cursor.execute("""
                SELECT 
                    c.id,                                           -- 0
                    c.cliente_nombre,                               -- 1
                    COALESCE(c.cliente_email, c.cliente_telefono),  -- 2 (Email o Teléfono)
                    c.cliente_telefono,                             -- 3
                    TO_CHAR(c.hora, 'HH12:MI AM') AS hora_fmt,      -- 4 (Hora formateada)
                    c.estado,                                       -- 5 (Estado string)
                    COALESCE(s.nombre, 'Servicio General') AS s_nom, -- 6 (Nombre Servicio)
                    c.mascota_nombre,                               -- 7 (Nombre Mascota)
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
                    # Mapeo posicional exacto para citas.html
                    0: c_id,        # {{ cita[0] }} -> ID
                    1: c_nombre,    # {{ cita[1] }} -> Nombre del cliente
                    2: c_contacto,  # {{ cita[2] }} -> Email/Contacto
                    3: c_tel,       # {{ cita[3] }} -> Teléfono
                    4: c_hora,      # {{ cita[4] }} -> Hora
                    5: c_estado,    # {{ cita[5] }} -> Estado ('pendiente', 'confirmada', etc.)
                    6: s_nombre,    # {{ cita[6] }} -> Nombre Servicio
                    7: m_nombre,    # {{ cita[7] }} -> Nombre Mascota
                    8: m_especie,   # {{ cita[8] }} -> Especie
                    9: c_precio,    # {{ cita[9] }} -> Precio
                    10: c_fecha,    # {{ cita[10] }} -> Fecha
                    11: c_obs       # {{ cita[11] }} -> Observaciones
                }
                citas_list.append(item)

            # 2. Cargar lista de servicios (para el modal con condicional {% if s[5] %})
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


# ─── AGENDAR NUEVA CITA ──────────────────────────────────────────────────────

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


# ─── ACCIONES DE CAMBIO DE ESTADO ────────────────────────────────────────────

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


# ─── REPROGRAMAR CITA ────────────────────────────────────────────────────────

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


# ─── VISTAS DE DETALLES, RECIBOS Y TICKETS DE CITAS ──────────────────────────

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
                    c.id,                                           -- 0
                    c.cliente_nombre,                               -- 1
                    COALESCE(c.cliente_email, '') AS email,         -- 2
                    COALESCE(c.cliente_telefono, '') AS telefono,   -- 3
                    TO_CHAR(c.fecha, 'YYYY-MM-DD') AS fecha_str,    -- 4
                    TO_CHAR(c.hora, 'HH12:MI AM') AS hora_str,      -- 5
                    COALESCE(c.mascota_nombre, '') AS mascota,      -- 6
                    COALESCE(c.mascota_especie, 'perro') AS especie,-- 7
                    COALESCE(c.observaciones, '') AS obs,           -- 8
                    COALESCE(c.precio_total, 0.00) AS precio,       -- 9
                    COALESCE(c.estado, 'pendiente') AS estado,      -- 10
                    COALESCE(s.nombre, 'Servicio General') AS servicio_nombre, -- 11
                    COALESCE(s.precio, 0.00) AS servicio_precio     -- 12
                FROM citas c
                LEFT JOIN servicios s ON c.servicio_id = s.id
                WHERE c.id = %s AND c.tenant_id = %s
            """, (cita_id, tenant_id))
            
            r = cursor.fetchone()
            if r:
                c_id = r[0]
                c_nombre = r[1] or 'Cliente General'
                c_email = r[2]
                c_tel = r[3]
                c_fecha = r[4] or ''
                c_hora = r[5] or ''
                m_nombre = r[6]
                m_especie = r[7]
                c_obs = r[8]
                c_precio = float(r[9]) if r[9] is not None else 0.0
                c_estado = str(r[10]).lower()
                s_nombre = r[11]
                s_precio = float(r[12]) if r[12] is not None else 0.0

                cita = {
                    'id': c_id,
                    'cliente_nombre': c_nombre,
                    'cliente_email': c_email,
                    'cliente_telefono': c_tel,
                    'fecha': c_fecha,
                    'hora': c_hora,
                    'mascota_nombre': m_nombre,
                    'mascota_especie': m_especie,
                    'observaciones': c_obs,
                    'precio_total': c_precio,
                    'estado': c_estado,
                    'servicio_nombre': s_nombre,
                    'servicio_precio': s_precio,
                    # Mapeo posicional
                    0: c_id, 1: c_nombre, 2: c_email, 3: c_tel, 4: c_fecha, 5: c_hora,
                    6: m_nombre, 7: m_especie, 8: c_obs, 9: c_precio, 10: c_estado,
                    11: s_nombre, 12: s_precio
                }
        conexion.close()
    except Exception as e:
        logger.error(f"Error generando recibo de cita ID={cita_id}: {e}")

    if not cita:
        flash('La cita solicitada no existe o no se encontró en el sistema.', 'error')
        return redirect(url_for('citas'))

    return render_template(
        'recibo_cita.html', 
        cita=cita, 
        momento_actual=datetime.now()
    )


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

    return render_template(
        'ticket_cita.html', 
        cita=cita, 
        momento_actual=datetime.now()
    )


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


# ─── ELIMINAR CITA ───────────────────────────────────────────────────────────

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
        data = request.get_json(silent=True) or {}
        
        # Obtener items de JSON, Form Data o Sesión
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
            items = [{'id': k, 'cantidad': v.get('qty', 1), 'precio': 0} for k, v in cart.items()]
        
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

        vendedor_id = session.get('user_id')
        vendedor_nombre = session.get('usuario', 'Cajero')
        tenant_id = session.get('tenant_id', 1)
        num_venta = f"VNT-{int(time.time())}"
        
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ventas (numero_venta, fecha_venta, cliente_nombre, cliente_documento, 
                                    vendedor_id, vendedor_nombre, metodo_pago, subtotal, igv, total, 
                                    monto_recibido, cambio_entregado, estado, tenant_id)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completada', %s)
                RETURNING id
            """, (num_venta, cliente_nombre, cliente_doc, vendedor_id, vendedor_nombre, metodo_pago,
                  subtotal, igv, total, monto_recibido, cambio, tenant_id))
            
            venta_id = cursor.fetchone()[0]
            
            for item in items:
                pid = item.get('id')
                cant = int(item.get('cantidad', item.get('qty', 1)))
                precio = float(item.get('precio', item.get('precio_unitario', 0.0)))
                cursor.execute("""
                    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (venta_id, pid, cant, precio, cant * precio))
                
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cant, pid))
                
        conexion.commit()
        conexion.close()
        
        session.pop('cart', None)
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