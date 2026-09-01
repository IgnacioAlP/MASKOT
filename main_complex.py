from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import logging
from datetime import datetime, date
import hashlib
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from bd import obtener_conexion

# Importar controladores
from controladores import (
    usuarios_controlador,
    citas_controlador,
    servicios_controlador,
    personal_controlador,
    productos_controlador,
    asistencia_controlador,
    clientes_controlador,
    mascotas_controlador
)

app = Flask(__name__)
# Leer SECRET_KEY desde variable de entorno para seguridad
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_veterinaria')  # Cambia en prod y configura en el entorno

# Configuración de cookies de sesión seguras
# Session cookie security: enable secure cookies in production only (require HTTPS).
# For local development (HTTP) we must keep this False so the browser accepts the session cookie.
use_secure_cookies = os.environ.get('FLASK_ENV', '').lower() == 'production' or os.environ.get('USE_SECURE_COOKIES', '') == 'True'
app.config['SESSION_COOKIE_SECURE'] = bool(use_secure_cookies)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configurar logging básico para ver mensajes en la consola
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Configuración para uploads
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Manejador de errores global
@app.errorhandler(Exception)
def handle_exception(e):
    # En modo debug, Flask muestra el error interactivo.
    # En producción, podrías loggear el error y mostrar una página genérica.
    print(f"Error no controlado: {e}")
    return render_template('error.html'), 500


# Funciones helper para fechas (disponibles en todas las plantillas)
@app.template_filter('dateformat')
def dateformat(value, format='%d/%m/%Y'):
    if value is None:
        return ""
    if isinstance(value, str):
        # Convertir string de fecha a objeto datetime
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except:
            return value
    return value.strftime(format)

@app.template_filter('days_until')
def days_until(value):
    if value is None:
        return 999
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except:
            return 999
    today = date.today()
    delta = value - today
    return delta.days

# Funciones globales disponibles en templates
@app.context_processor
def utility_processor():
    def format_date(date_value, format='%d/%m/%Y'):
        if date_value is None:
            return ""
        if isinstance(date_value, str):
            try:
                date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
            except:
                return date_value
        return date_value.strftime(format)
    
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
            except:
                return 999
        return (date1 - date2).days
    
    def calculate_work_hours(entrada, salida):
        if not entrada or not salida:
            return 0
        try:
            # Convertir strings de tiempo a objetos datetime
            if isinstance(entrada, str):
                entrada = datetime.strptime(entrada, '%H:%M:%S').time()
            if isinstance(salida, str):
                salida = datetime.strptime(salida, '%H:%M:%S').time()
            
            # Crear datetime objects para el cálculo
            today_date = date.today()
            entrada_dt = datetime.combine(today_date, entrada)
            salida_dt = datetime.combine(today_date, salida)
            
            # Calcular diferencia en horas
            delta = salida_dt - entrada_dt
            return round(delta.total_seconds() / 3600, 1)
        except:
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
    """Expose cart count to all templates via `cart_count` variable."""
    cart = session.get('cart', {})
    total_qty = 0
    try:
        for v in cart.values():
            total_qty += int(v.get('qty', 0))
    except Exception:
        total_qty = 0
    return dict(cart_count=total_qty)

# Función helper para verificar extensiones
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Eliminar funciones helper que ahora están en los controladores
# def query_db(...): ...
# def hash_password(...): ...

@app.route('/')
def index():
    servicios = servicios_controlador.obtener_servicios_destacados(3)
    productos_mas_vendidos = productos_controlador.obtener_productos_mas_vendidos(4)
    return render_template('index.html', servicios=servicios, productos_venta=productos_mas_vendidos)

@app.route('/servicios-completos')
def servicios_completos():
    servicios = servicios_controlador.obtener_servicios_activos()
    return render_template('servicios_publicos.html', servicios=servicios)

@app.route('/productos')
def productos():
    productos_venta = productos_controlador.obtener_productos_por_tipo('venta')
    return render_template('productos.html', productos_venta=productos_venta)

@app.route('/producto/<int:id>')
def ver_producto(id):
    producto = productos_controlador.obtener_producto_por_id(id)
    if not producto:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('index'))
    # producto is a tuple: id, nombre, tipo, cantidad, stock_min, fecha_vencimiento, imagen, activo
    return render_template('producto_detalle.html', producto=producto)


def _get_cart():
    """Return cart dict from session. Keys are product ids (str) -> {'qty': int}."""
    return session.setdefault('cart', {})


def _save_cart(cart):
    session['cart'] = cart


@app.route('/carrito')
def ver_carrito():
    cart = _get_cart()
    items = []
    total_qty = 0
    for id_str, data in list(cart.items()):
        try:
            pid = int(id_str)
        except:
            continue
        producto = productos_controlador.obtener_producto_por_id(pid)
        if not producto:
            # Producto eliminado, quitar del carrito
            cart.pop(id_str, None)
            continue
        qty = int(data.get('qty', 0))
        # adjust qty if exceeds stock
        stock = producto[3] or 0
        if qty > stock:
            qty = stock
            cart[id_str]['qty'] = qty
        items.append({
            'id': pid,
            'nombre': producto[1],
            'imagen': producto[6],
            'qty': qty,
            'stock': stock
        })
        total_qty += qty
    # save any adjustments
    _save_cart(cart)
    return render_template('carrito.html', items=items, total_qty=total_qty)


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
    if cantidad <= 0:
        flash('Cantidad inválida.', 'warning')
        return redirect(url_for('ver_producto', id=producto_id))
    if stock < 1:
        flash('Producto agotado.', 'warning')
        return redirect(url_for('ver_producto', id=producto_id))

    cart = _get_cart()
    key = str(producto_id)
    existing = int(cart.get(key, {}).get('qty', 0))
    new_qty = existing + cantidad
    if new_qty > stock:
        new_qty = stock
        flash(f'Se ajustó la cantidad al stock disponible ({stock}).', 'info')

    cart[key] = {'qty': new_qty}
    _save_cart(cart)

    # Prepare response for AJAX (fetch) clients
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    total_qty = sum(int(v.get('qty', 0)) for v in session.get('cart', {}).values())
    message = f'Producto "{producto[1]}" agregado al carrito. Cantidad: {new_qty}'
    if is_ajax:
        return jsonify({'success': True, 'message': message, 'cart_count': total_qty})

    flash(message, 'success')
    return redirect(url_for('ver_carrito'))



@app.route('/carrito/eliminar', methods=['POST'])
def carrito_eliminar():
    """Elimina un producto específico del carrito via AJAX"""
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
    else:
        return 'Error: Producto no encontrado en carrito', 404


@app.route('/carrito/actualizar', methods=['POST'])
def carrito_actualizar():
    """Actualiza la cantidad de un producto en el carrito via AJAX"""
    try:
        producto_id = int(request.form.get('producto_id'))
        cantidad = int(request.form.get('cantidad', 1))
    except (ValueError, TypeError):
        return 'Error: Datos inválidos', 400

    # Verificar que el producto existe
    producto = productos_controlador.obtener_producto_por_id(producto_id)
    if not producto:
        return 'Error: Producto no encontrado', 404

    # Validar cantidad mínima
    if cantidad <= 0:
        return 'Error: La cantidad debe ser mayor a 0', 400

    cart = _get_cart()
    key = str(producto_id)
    
    # Verificar stock disponible
    stock = producto[3] or 0
    if cantidad > stock:
        cantidad = stock
    
    # Actualizar cantidad
    cart[key] = {'qty': cantidad}
    _save_cart(cart)
    
    return 'OK', 200

@app.route('/checkout')
def checkout():
    cart = _get_cart()
    if not cart:
        flash('Tu carrito está vacío', 'warning')
        return redirect(url_for('ver_carrito'))
    
    # Calcular items y totales
    items = []
    subtotal = 0
    for id_str, data in cart.items():
        try:
            pid = int(id_str)
        except:
            continue
        producto = productos_controlador.obtener_producto_por_id(pid)
        if not producto:
            continue
        qty = int(data.get('qty', 0))
        precio_unitario = 10000  # Precio base, puedes modificar según tu lógica
        subtotal_item = precio_unitario * qty
        items.append({
            'id': pid,
            'nombre': producto[1],
            'imagen': producto[6],
            'qty': qty,
            'precio_unitario': precio_unitario,
            'subtotal': subtotal_item
        })
        subtotal += subtotal_item
    
    # Calcular IGV (18%) y total final
    igv = round(subtotal * 0.18, 2)
    total_final = subtotal + igv
    
    return render_template('checkout.html', 
                         items=items, 
                         total=subtotal,
                         igv=igv,
                         total_final=total_final)

@app.route('/procesar-pago', methods=['POST'])
def procesar_pago():
    try:
        # Verificar que haya items en el carrito
        cart = _get_cart()
        if not cart:
            flash('Tu carrito está vacío', 'warning')
            return redirect(url_for('ver_carrito'))
        
        # Obtener datos del formulario
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        documento = request.form.get('documento')
        metodo_pago = request.form.get('metodo_pago')
        
        # Validar datos obligatorios
        if not all([nombre, email, telefono, direccion, metodo_pago]):
            flash('Por favor completa todos los campos obligatorios', 'error')
            return redirect(url_for('checkout'))
        
        # Calcular items, subtotal, IGV y total
        items = []
        subtotal = 0
        for id_str, data in cart.items():
            try:
                pid = int(id_str)
            except:
                continue
            producto = productos_controlador.obtener_producto_por_id(pid)
            if not producto:
                continue
            qty = int(data.get('qty', 0))
            precio_unitario = 10000  # Precio base
            subtotal_item = precio_unitario * qty
            items.append({
                'id': pid,
                'nombre': producto[1],
                'qty': qty,
                'precio_unitario': precio_unitario,
                'subtotal': subtotal_item
            })
            subtotal += subtotal_item
        
        # Calcular IGV (18%) y total final
        igv = round(subtotal * 0.18, 2)
        total_final = subtotal + igv
        
        # Buscar o crear cliente
        cliente = clientes_controlador.obtener_cliente_por_email(email)
        if cliente:
            cliente_id = cliente[0]
        else:
            cliente_id = clientes_controlador.insertar_cliente(nombre, email, telefono, direccion, documento)
        
        # Procesar datos de tarjeta si es necesario
        if metodo_pago in ['credito', 'debito']:
            numero_tarjeta = request.form.get('numero_tarjeta')
            nombre_titular = request.form.get('nombre_titular')
            expiracion = request.form.get('expiracion')
            guardar_tarjeta = request.form.get('guardar_tarjeta') == 'on'
            
            # Validar datos de tarjeta
            if not all([numero_tarjeta, nombre_titular, expiracion]):
                flash('Por favor completa todos los datos de la tarjeta', 'error')
                return redirect(url_for('checkout'))
            
            # Guardar tarjeta si el cliente lo solicitó
            if guardar_tarjeta:
                try:
                    clientes_controlador.guardar_tarjeta_cliente(
                        cliente_id, numero_tarjeta, nombre_titular, expiracion, metodo_pago
                    )
                except Exception as e:
                    logger.warning(f"No se pudo guardar la tarjeta: {e}")
                    # No fallar el pago por esto, solo advertir
        
        # Crear pedido con el total final (incluyendo IGV)
        pedido_id = clientes_controlador.insertar_pedido(cliente_id, items, total_final, metodo_pago, subtotal, igv)
        
        # Simular procesamiento de pago
        # En producción aquí se integraría con un procesador de pagos real
        
        # Actualizar stock de productos (opcional)
        for item in items:
            productos_controlador.actualizar_stock(item['id'], -item['qty'])
        
        # Limpiar carrito después del pago exitoso
        session.pop('cart', None)
        
        # Mensaje de éxito personalizado según método de pago
        if metodo_pago == 'transferencia':
            flash('¡Pedido confirmado! Revisa tu email para las instrucciones de transferencia.', 'success')
        else:
            flash('¡Pago procesado exitosamente! Recibirás un email de confirmación.', 'success')
        
        logger.info(f"Pedido {pedido_id} procesado exitosamente para cliente {cliente_id}")
        return redirect(url_for('index'))
        
    except Exception as e:
        logger.error(f"Error procesando pago: {e}")
        flash('Hubo un error procesando tu pago. Intenta nuevamente.', 'error')
        return redirect(url_for('checkout'))

@app.route('/agendar_cita', methods=['POST'])
def agendar_cita():
    try:
        nombre = request.form['cliente_nombre']
        email = request.form['cliente_email']
        fecha = request.form['fecha']
        hora = request.form['hora']
        
        # Obtener múltiples servicios
        servicios_ids = request.form.getlist('servicio_id[]')
        servicios_ids = [int(sid) for sid in servicios_ids if sid]
        
        if not servicios_ids:
            flash('Debe seleccionar al menos un servicio.', 'error')
            return redirect(url_for('index'))
        
        # Obtener múltiples mascotas
        mascota_nombres = request.form.getlist('mascota_nombre[]')
        mascota_especies = request.form.getlist('mascota_especie[]')
        mascota_razas = request.form.getlist('mascota_raza[]')
        mascota_edades = request.form.getlist('mascota_edad[]')
        mascota_pesos = request.form.getlist('mascota_peso[]')
        
        # Validar que hay al menos una mascota
        if not mascota_nombres or not any(nombre.strip() for nombre in mascota_nombres):
            flash('Debe registrar al menos una mascota.', 'error')
            return redirect(url_for('index'))
        
        # Procesar datos de mascotas
        mascotas_data = []
        for i, nombre_mascota in enumerate(mascota_nombres):
            if nombre_mascota.strip():  # Solo procesar mascotas con nombre
                mascota_data = {
                    'nombre': nombre_mascota.strip(),
                    'especie': mascota_especies[i] if i < len(mascota_especies) else '',
                    'raza': mascota_razas[i] if i < len(mascota_razas) and mascota_razas[i] else None,
                    'edad': int(mascota_edades[i]) if i < len(mascota_edades) and mascota_edades[i] else None,
                    'peso': float(mascota_pesos[i]) if i < len(mascota_pesos) and mascota_pesos[i] else None
                }
                mascotas_data.append(mascota_data)
        
        # Validar límites de citas para cada servicio
        for servicio_id in servicios_ids:
            servicio = servicios_controlador.obtener_max_citas_dia(servicio_id)
            if not servicio:
                flash(f'Servicio con ID {servicio_id} no válido.', 'error')
                return redirect(url_for('index'))
            
            max_citas = servicio
            citas_hoy = citas_controlador.contar_citas_pendientes(servicio_id, fecha)
            
            if citas_hoy >= max_citas:
                servicio_info = servicios_controlador.obtener_servicio_por_id(servicio_id)
                servicio_nombre = servicio_info[1] if servicio_info else f'Servicio {servicio_id}'
                flash(f'Límite de {max_citas} citas alcanzado para "{servicio_nombre}" en la fecha seleccionada.', 'warning')
                return redirect(url_for('index'))
        
        # Insertar cita completa
        cita_id = citas_controlador.insertar_cita_completa(
            nombre, email, mascotas_data, servicios_ids, fecha, hora
        )
        
        # Mensaje de éxito
        mascotas_str = ', '.join([m['nombre'] for m in mascotas_data])
        flash(f'Cita agendada exitosamente para {mascotas_str} el {fecha} a las {hora}.', 'success')
        
    except Exception as e:
        flash(f'Error al agendar la cita: {str(e)}', 'error')
        logger.error(f"Error en agendar_cita: {e}")
    
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("=== LOGIN ROUTE ACCESSED ===")
    print(f"Method: {request.method}")
    print(f"Session before: {dict(session)}")
    
    # Si ya está autenticado, ir directo al dashboard
    if 'rol' in session and session.get('rol') in ['dueño', 'admin', 'empleado']:
        print("Usuario ya autenticado, redirigiendo al dashboard")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        print("--- Intento de login (POST) ---")
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        next_url = request.args.get('next') or request.form.get('next')
        print(f"Usuario recibido: '{username}', Password length: {len(password) if password else 0}")
        print(f"Next URL: {next_url}")

        if not username or not password:
            print("Campos vacíos detectados")
            flash('Por favor complete todos los campos.', 'warning')
            return render_template('login.html')
        
        # Usar el controlador para verificar credenciales
        print('Verificando credenciales con el controlador...')
        try:
            auth = usuarios_controlador.autenticar_usuario(username, password)
            print(f'Resultado de la autenticación: {auth}')
        except Exception as e:
            print(f"Error en autenticación: {e}")
            flash('Error interno del sistema', 'error')
            return render_template('login.html')
            
        if not auth.get('success'):
            print("Autenticación fallida")
            flash(auth.get('message', 'Credenciales inválidas'), 'error')
            return render_template('login.html')
            
        user = auth.get('user')
        print(f"Usuario autenticado exitosamente: {user}")
        
        # user es una tupla: (id, username, password, rol, activo)
        print(f"Estableciendo sesión para usuario id={user[0]}, username={user[1]}, rol={user[3]}")
        session.permanent = True
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['rol'] = user[3]
        
        print(f"Session después: {dict(session)}")
        
        flash(f"¡Bienvenido de nuevo, {user[1]}!", 'success')
        
        # Validar next_url seguro: solo rutas internas
        if next_url and next_url.startswith('/'):
            print(f'Redirigiendo al siguiente URL: {next_url}')
            return redirect(next_url)
            
        print('Redirigiendo al dashboard...')
        return redirect(url_for('dashboard'))
            
    print("Mostrando formulario de login (GET)")
    return render_template('login.html')

@app.route('/test-db')
def test_db():
    """Ruta de prueba para verificar la conexión a la base de datos"""
    try:
        import bd
        conexion = bd.obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            count = cursor.fetchone()[0]
            
            cursor.execute("SELECT username, rol, activo FROM usuarios LIMIT 5")
            usuarios = cursor.fetchall()
            
        conexion.close()
        
        response = f"""
        <h2>Test de Base de Datos</h2>
        <p><strong>Usuarios en total:</strong> {count}</p>
        <h3>Primeros 5 usuarios:</h3>
        <ul>
        """
        for usuario in usuarios:
            response += f"<li>{usuario[0]} - {usuario[1]} - {'Activo' if usuario[2] else 'Inactivo'}</li>"
        response += "</ul>"
        
        return response
        
    except Exception as e:
        return f"<h2>Error de Base de Datos</h2><p>{str(e)}</p>"


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'rol' not in session:
        return redirect(url_for('login'))
    
    rol = session['rol']
    hoy = date.today().strftime('%Y-%m-%d')
    
    # Usar controladores para obtener datos
    citas_hoy = citas_controlador.obtener_citas_por_fecha(hoy) if rol in ['admin', 'empleado', 'dueño'] else []
    
    if rol == 'dueño':
        total_empleados = len(personal_controlador.obtener_personal())
        servicios_activos = len(servicios_controlador.obtener_servicios_activos())
        productos_bajos = productos_controlador.obtener_productos_stock_bajo()
        
        return render_template('dashboard.html', 
                               citas_hoy=citas_hoy, 
                               total_empleados=total_empleados, 
                               servicios_activos=servicios_activos,
                               productos_bajos=productos_bajos)
    
    return render_template('dashboard.html', citas_hoy=citas_hoy)

@app.route('/citas')
def citas():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    fecha_filtro = request.args.get('fecha', default=date.today().strftime('%Y-%m-%d'))
    
    citas = citas_controlador.obtener_citas_por_fecha(fecha_filtro)
    
    return render_template('citas.html', citas=citas, fecha_filtro=fecha_filtro)

@app.route('/servicios', methods=['GET', 'POST'])
def servicios():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            if 'agregar' in request.form:
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                max_citas = int(request.form.get('max_citas', 10))
                servicios_controlador.insertar_servicio(nombre, descripcion, max_citas)
                flash('Servicio agregado exitosamente.', 'success')

            elif 'desactivar' in request.form:
                id_serv = int(request.form['id'])
                servicios_controlador.cambiar_estado_servicio(id_serv, 0)
                flash('Servicio desactivado.', 'info')
            
            elif 'activar' in request.form:
                id_serv = int(request.form['id'])
                servicios_controlador.cambiar_estado_servicio(id_serv, 1)
                flash('Servicio activado.', 'success')

        except Exception as e:
            flash(f'Ocurrió un error: {e}', 'error')
        
        return redirect(url_for('servicios'))

    servicios = servicios_controlador.obtener_servicios()
    return render_template('servicios.html', servicios=servicios)

@app.route('/personal', methods=['GET', 'POST'])
def personal():
    print(f'DEBUG: === ACCESO A RUTA /personal ===')
    print(f'DEBUG: Método: {request.method}')
    print(f'DEBUG: Session: {session}')
    
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    rol = session['rol']
    puede_modificar = rol in ['dueño', 'admin']  # Tanto dueño como admin pueden modificar
    
    print(f'DEBUG: Usuario actual - Rol: {rol}, Puede modificar: {puede_modificar}')
    
    if request.method == 'POST':
        print(f'DEBUG: POST request recibido con form data: {request.form}')
        print(f'DEBUG: Método de request: {request.method}')
        print(f'DEBUG: Puede modificar: {puede_modificar}')
        print(f'DEBUG: Claves en request.form: {list(request.form.keys())}')
        
        # Procesar POST sin restricción de puede_modificar para debug
        try:
            if 'agregar' in request.form:
                username = request.form['username']
                password = request.form['password']
                cargo = request.form['cargo']
                rol = request.form['rol']
                
                print(f'DEBUG: === AGREGANDO NUEVO USUARIO ===')  
                print(f'DEBUG: Username: {username}, Cargo: {cargo}, Rol: {rol}')
                
                # Verificar que el usuario no exista ya
                existing_user = None
                try:
                    conexion = obtener_conexion()
                    with conexion.cursor() as cursor:
                        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
                        existing_user = cursor.fetchone()
                    conexion.close()
                except Exception as e:
                    print(f'DEBUG: Error verificando usuario existente: {e}')
                
                if existing_user:
                    print(f'DEBUG: Usuario ya existe: {username}')
                    flash(f'El usuario "{username}" ya existe.', 'error')
                else:
                    try:
                        # Insertar usuario con el rol seleccionado
                        user_id = usuarios_controlador.insertar_usuario(username, password, rol)
                        print(f'DEBUG: Usuario creado con ID: {user_id} y rol: {rol}')
                        
                        # Solo insertar en personal si es empleado
                        if rol == 'empleado':
                            cargo_final = cargo if cargo else 'Empleado General'
                            personal_controlador.insertar_personal(user_id, cargo_final, 1200.00)  # Salario base por defecto
                            print(f'DEBUG: Personal agregado con cargo: {cargo_final}')
                            flash('Empleado agregado exitosamente.', 'success')
                        else:
                            flash(f'{rol.title()} agregado exitosamente.', 'success')
                            
                    except Exception as e:
                        print(f'DEBUG: Error al agregar usuario: {e}')
                        flash(f'Error al agregar usuario: {e}', 'error')

            elif 'modificar' in request.form:
                id_p = int(request.form['id'])
                cargo = request.form['cargo']
                salario = float(request.form['salario'])
                personal_controlador.actualizar_personal(id_p, cargo, salario)
                flash('Empleado modificado exitosamente.', 'success')

            elif 'eliminar' in request.form:
                id_p = int(request.form['id'])
                print(f'DEBUG: Intentando eliminar personal con ID: {id_p}')
                
                personal_info = personal_controlador.obtener_personal_por_id(id_p)
                print(f'DEBUG: Personal encontrado: {personal_info}')
                
                if personal_info:
                    try:
                        # Desactivar tanto en personal como en usuarios
                        personal_controlador.cambiar_estado_personal(id_p, 0)
                        print(f'DEBUG: Personal desactivado en tabla personal')
                        
                        usuarios_controlador.cambiar_estado_usuario(personal_info[1], 0) # personal_info[1] es usuario_id
                        print(f'DEBUG: Usuario {personal_info[1]} desactivado en tabla usuarios')
                        
                        flash('Empleado desactivado exitosamente.', 'success')
                    except Exception as e:
                        print(f'DEBUG: Error al desactivar: {e}')
                        flash(f'Error al desactivar empleado: {e}', 'error')
                else:
                    print(f'DEBUG: Personal no encontrado con ID: {id_p}')
                    flash('Empleado no encontrado.', 'error')
                    
            elif 'reactivar' in request.form:
                id_p = int(request.form['id'])
                print(f'DEBUG: Intentando reactivar personal con ID: {id_p}')
                
                personal_info = personal_controlador.obtener_personal_por_id(id_p)
                print(f'DEBUG: Personal encontrado: {personal_info}')
                
                if personal_info:
                    try:
                        # Reactivar tanto en personal como en usuarios
                        personal_controlador.cambiar_estado_personal(id_p, 1)
                        print(f'DEBUG: Personal reactivado en tabla personal')
                        
                        usuarios_controlador.cambiar_estado_usuario(personal_info[1], 1) # personal_info[1] es usuario_id
                        print(f'DEBUG: Usuario {personal_info[1]} reactivado en tabla usuarios')
                        
                        flash('Empleado reactivado exitosamente.', 'success')
                    except Exception as e:
                        print(f'DEBUG: Error al reactivar: {e}')
                        flash(f'Error al reactivar empleado: {e}', 'error')
                else:
                    print(f'DEBUG: Personal no encontrado con ID: {id_p}')
                    flash('Empleado no encontrado.', 'error')
                    
            elif 'activar_usuario' in request.form:
                user_id = int(request.form['user_id'])
                usuarios_controlador.cambiar_estado_usuario(user_id, 1)
                flash('Usuario activado exitosamente.', 'success')
                
            elif 'desactivar_usuario' in request.form:
                user_id = int(request.form['user_id'])
                usuarios_controlador.cambiar_estado_usuario(user_id, 0)
                flash('Usuario desactivado exitosamente.', 'info')
                
            elif 'eliminar_usuario' in request.form:
                user_id = int(request.form['user_id'])
                print(f'DEBUG: === ELIMINAR USUARIO ===')
                print(f'DEBUG: User ID a eliminar: {user_id}')
                print(f'DEBUG: Usuario actual en sesión: {session.get("user_id")}')
                
                # Verificar que no sea el usuario actual
                if user_id == session.get('user_id'):
                    print(f'DEBUG: Intento de auto-eliminación bloqueado')
                    flash('No puedes eliminar tu propio usuario.', 'error')
                else:
                    try:
                        # Obtener información del usuario antes de eliminar
                        usuario_info = usuarios_controlador.obtener_usuario_por_id(user_id)
                        print(f'DEBUG: Info del usuario obtenida: {usuario_info}')
                        
                        if usuario_info:
                            username = usuario_info[1]
                            rol = usuario_info[2]
                            print(f'DEBUG: Username: {username}, Rol: {rol}')
                            
                            # Proteger usuarios críticos del sistema
                            usuarios_protegidos = ['admin_sistema', 'admin_maskot']
                            if username in usuarios_protegidos:
                                print(f'DEBUG: Usuario protegido, eliminación bloqueada')
                                flash(f'No se puede eliminar el usuario "{username}" porque es un usuario del sistema.', 'error')
                            else:
                                print(f'DEBUG: Usuario no protegido, procediendo con eliminación')
                                
                                # Eliminar usuario directamente (simplificado para debug)
                                print(f'DEBUG: Llamando a usuarios_controlador.eliminar_usuario({user_id})')
                                usuarios_controlador.eliminar_usuario(user_id)
                                print(f'DEBUG: Usuario {username} eliminado exitosamente')
                                flash(f'Usuario "{username}" eliminado permanentemente.', 'success')
                        else:
                            print(f'DEBUG: Usuario no encontrado en la base de datos')
                            flash('Usuario no encontrado.', 'error')
                            
                    except Exception as e:
                        print(f'DEBUG: ERROR CRÍTICO en eliminación: {e}')
                        print(f'DEBUG: Tipo de error: {type(e).__name__}')
                        import traceback
                        print(f'DEBUG: Traceback completo: {traceback.format_exc()}')
                        flash(f'Error al eliminar usuario: {e}', 'error')

        except Exception as e:
            print(f'DEBUG: === EXCEPCIÓN CAPTURADA EN PERSONAL ===')
            print(f'DEBUG: Tipo de error: {type(e).__name__}')
            print(f'DEBUG: Mensaje de error: {e}')
            import traceback
            print(f'DEBUG: Traceback completo: {traceback.format_exc()}')
            flash(f'Ocurrió un error: {e}', 'error')
        
        return redirect(url_for('personal'))
    
    # Si no es POST o si hay algún error, mostrar la página
    personal_list = personal_controlador.obtener_todo_personal_con_usuario()  # Mostrar todo el personal
    usuarios_list = usuarios_controlador.obtener_usuarios()  # Obtener todos los usuarios
    return render_template('personal.html', personal=personal_list, usuarios=usuarios_list, puede_modificar=puede_modificar)

@app.route('/asistencia', methods=['GET', 'POST'])
def asistencia():
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    hoy = date.today().strftime('%Y-%m-%d')
    
    # Para empleados, buscar en la tabla personal
    # Para admins y dueños, usar directamente su user_id
    personal_info = None
    personal_id = None
    
    if session['rol'] == 'empleado':
        personal_info = personal_controlador.obtener_personal_por_usuario_id(user_id)
        if not personal_info:
            flash('No eres personal registrado para marcar asistencia.', 'error')
            return redirect(url_for('dashboard'))
        personal_id = personal_info[0]
    else:
        # Para admin y dueño, crear entrada temporal en personal si no existe
        personal_info = personal_controlador.obtener_personal_por_usuario_id(user_id)
        if not personal_info:
            # Crear entrada en personal para admin/dueño
            cargo = 'Administrador' if session['rol'] == 'admin' else 'Dueño'
            personal_controlador.insertar_personal(user_id, cargo, 0.00)
            personal_info = personal_controlador.obtener_personal_por_usuario_id(user_id)
        personal_id = personal_info[0]

    asistencia_hoy = asistencia_controlador.obtener_asistencia_por_personal_y_fecha(personal_id, hoy)
    
    if request.method == 'POST':
        try:
            if 'entrada' in request.form and not asistencia_hoy:
                asistencia_controlador.marcar_entrada(personal_id, hoy, datetime.now().strftime('%H:%M:%S'))
                flash('Entrada marcada exitosamente.', 'success')
            elif 'salida' in request.form and asistencia_hoy and not asistencia_hoy[4]:  # Si no hay hora_salida
                asistencia_controlador.marcar_salida(personal_id, hoy, datetime.now().strftime('%H:%M:%S'))
                flash('Salida marcada exitosamente.', 'success')
            else:
                flash('Acción no válida o ya realizada.', 'warning')
        
        except Exception as e:
            flash(f'Ocurrió un error: {e}', 'error')

        return redirect(url_for('asistencia'))
    
    # Volver a cargar la asistencia por si se actualizó
    asistencia_hoy = asistencia_controlador.obtener_asistencia_por_personal_y_fecha(personal_id, hoy)
    return render_template('asistencia.html', asistencia=asistencia_hoy)

@app.route('/historial-asistencias')
def historial_asistencias():
    """Página para que admins/dueños vean el historial completo de asistencias"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado. Solo admins y dueños pueden ver el historial de asistencias.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Obtener todas las asistencias con información detallada
        historial = asistencia_controlador.obtener_historial_completo()
        return render_template('historial-asistencias.html', historial=historial)
    
    except Exception as e:
        flash(f'Error al cargar el historial de asistencias: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/historial-clientes')
def historial_clientes():
    """Página para que admins/dueños vean el historial completo de clientes"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado. Solo admins y dueños pueden ver el historial de clientes.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Obtener historial completo de clientes
        historial = clientes_controlador.obtener_historial_completo()
        return render_template('historial-clientes.html', historial=historial)
    
    except Exception as e:
        flash(f'Error al cargar el historial de clientes: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/detalle-cliente')
def detalle_cliente():
    """Página para ver detalles completos de un cliente específico"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado. Solo admins y dueños pueden ver detalles de clientes.', 'error')
        return redirect(url_for('dashboard'))
    
    cliente_id = request.args.get('id')
    email = request.args.get('email')
    
    if not cliente_id and not email:
        flash('Se requiere ID o email del cliente.', 'error')
        return redirect(url_for('historial_clientes'))
    
    try:
        # Obtener detalles completos del cliente
        detalles = clientes_controlador.obtener_detalles_cliente(cliente_id, email)
        if not detalles:
            flash('Cliente no encontrado.', 'error')
            return redirect(url_for('historial_clientes'))
        
        return render_template('detalle-cliente.html', detalles=detalles)
    
    except Exception as e:
        flash(f'Error al cargar los detalles del cliente: {e}', 'error')
        return redirect(url_for('historial_clientes'))

@app.route('/almacen', methods=['GET', 'POST'])
def almacen():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            if 'agregar' in request.form:
                nombre = request.form['nombre']
                cantidad = int(request.form['cantidad'])
                stock_min = int(request.form['stock_min'])
                tipo = request.form.get('tipo', 'stock')
                fecha_venc = request.form.get('fecha_vencimiento') or None
                imagen_filename = None
                
                if tipo == 'venta' and 'imagen' in request.files:
                    file = request.files['imagen']
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        if filename:
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            file.save(filepath)
                            imagen_filename = filename
                    else:
                        flash('Archivo no permitido. Solo PNG/JPG.', 'warning')
                        return redirect(url_for('almacen'))
                
                productos_controlador.insertar_producto(nombre, tipo, cantidad, stock_min, fecha_venc, imagen_filename)
                flash('Producto agregado exitosamente.', 'success')

            elif 'modificar' in request.form:
                id_prod = int(request.form['id'])
                # Lógica de modificación con controlador...
                flash('Producto modificado exitosamente.', 'success')

        except Exception as e:
            flash(f'Ocurrió un error: {e}', 'error')
            return redirect(url_for('almacen'))

        return redirect(url_for('almacen'))

    productos = productos_controlador.obtener_productos()
    return render_template('almacen.html', productos=productos)

@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/clientes')
def listar_clientes():
    """Lista todos los clientes para administradores y dueños"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado. Solo administradores y dueños pueden ver la lista de clientes.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Obtener todos los clientes únicos de las citas
        clientes = clientes_controlador.obtener_todos_clientes()
        return render_template('clientes.html', clientes=clientes)
    
    except Exception as e:
        flash(f'Error al cargar la lista de clientes: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/editar-cliente/<cliente_email>', methods=['GET', 'POST'])
def editar_cliente(cliente_email):
    """Edita la información de un cliente (excepto el nombre)"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('listar_clientes'))
    
    if request.method == 'POST':
        try:
            nuevo_email = request.form['email']
            telefono = request.form.get('telefono', '')
            direccion = request.form.get('direccion', '')
            
            # Actualizar información del cliente
            clientes_controlador.actualizar_cliente(cliente_email, nuevo_email, telefono, direccion)
            flash('Cliente actualizado exitosamente.', 'success')
            return redirect(url_for('listar_clientes'))
        
        except Exception as e:
            flash(f'Error al actualizar cliente: {e}', 'error')
    
    try:
        # Obtener datos actuales del cliente
        cliente = clientes_controlador.obtener_cliente_por_email(cliente_email)
        return render_template('editar-cliente.html', cliente=cliente)
    
    except Exception as e:
        flash(f'Error al cargar datos del cliente: {e}', 'error')
        return redirect(url_for('listar_clientes'))

# ===== RUTAS DE MASCOTAS =====
@app.route('/mascotas')
def listar_mascotas():
    """Página para listar todas las mascotas"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'veterinario']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        mascotas = mascotas_controlador.obtener_todas_mascotas()
        estadisticas = mascotas_controlador.obtener_estadisticas_mascotas()
        return render_template('mascotas.html', mascotas=mascotas, estadisticas=estadisticas)
    
    except Exception as e:
        flash(f'Error al cargar las mascotas: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/mascota/<int:mascota_id>')
def ver_mascota(mascota_id):
    """Página para ver detalles de una mascota"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'veterinario']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        mascota = mascotas_controlador.obtener_mascota_por_id(mascota_id)
        if not mascota:
            flash('Mascota no encontrada.', 'error')
            return redirect(url_for('listar_mascotas'))
        
        return render_template('detalle-mascota.html', mascota=mascota)
    
    except Exception as e:
        flash(f'Error al cargar la mascota: {e}', 'error')
        return redirect(url_for('listar_mascotas'))

@app.route('/agregar-mascota', methods=['GET', 'POST'])
def agregar_mascota():
    """Página para agregar una nueva mascota"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'veterinario']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            cliente_id = request.form.get('cliente_id')
            nombre = request.form.get('nombre', '').strip()
            especie = request.form.get('especie', '').strip()
            raza = request.form.get('raza', '').strip() or None
            edad = request.form.get('edad', '').strip()
            peso = request.form.get('peso', '').strip()
            observaciones = request.form.get('observaciones', '').strip() or None
            
            # Validaciones
            if not all([cliente_id, nombre, especie]):
                flash('Cliente, nombre y especie son obligatorios.', 'error')
                return render_template('agregar-mascota.html', 
                                     clientes=clientes_controlador.obtener_todos_clientes())
            
            # Convertir edad y peso a números si están presentes
            edad_num = int(edad) if edad and edad.isdigit() else None
            peso_num = float(peso) if peso else None
            
            # Insertar mascota
            mascota_id = mascotas_controlador.insertar_mascota(
                cliente_id, nombre, especie, raza, edad_num, peso_num, observaciones
            )
            
            if mascota_id:
                flash(f'Mascota {nombre} agregada exitosamente.', 'success')
                return redirect(url_for('listar_mascotas'))
            else:
                flash('Error al agregar la mascota.', 'error')
        
        except Exception as e:
            flash(f'Error al agregar mascota: {e}', 'error')
    
    try:
        clientes = clientes_controlador.obtener_todos_clientes()
        return render_template('agregar-mascota.html', clientes=clientes)
    
    except Exception as e:
        flash(f'Error al cargar la página: {e}', 'error')
        return redirect(url_for('listar_mascotas'))

@app.route('/editar-mascota/<int:mascota_id>', methods=['GET', 'POST'])
def editar_mascota(mascota_id):
    """Página para editar una mascota"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'veterinario']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            especie = request.form.get('especie', '').strip()
            raza = request.form.get('raza', '').strip() or None
            edad = request.form.get('edad', '').strip()
            peso = request.form.get('peso', '').strip()
            observaciones = request.form.get('observaciones', '').strip() or None
            
            # Validaciones
            if not all([nombre, especie]):
                flash('Nombre y especie son obligatorios.', 'error')
                return redirect(request.url)
            
            # Convertir edad y peso a números si están presentes
            edad_num = int(edad) if edad and edad.isdigit() else None
            peso_num = float(peso) if peso else None
            
            # Actualizar mascota
            success = mascotas_controlador.actualizar_mascota(
                mascota_id, nombre, especie, raza, edad_num, peso_num, observaciones
            )
            
            if success:
                flash(f'Mascota {nombre} actualizada exitosamente.', 'success')
                return redirect(url_for('listar_mascotas'))
            else:
                flash('Error al actualizar la mascota.', 'error')
        
        except Exception as e:
            flash(f'Error al actualizar mascota: {e}', 'error')
    
    try:
        mascota = mascotas_controlador.obtener_mascota_por_id(mascota_id)
        if not mascota:
            flash('Mascota no encontrada.', 'error')
            return redirect(url_for('listar_mascotas'))
        
        return render_template('editar-mascota.html', mascota=mascota)
    
    except Exception as e:
        flash(f'Error al cargar la mascota: {e}', 'error')
        return redirect(url_for('listar_mascotas'))

@app.route('/eliminar-mascota/<int:mascota_id>', methods=['POST'])
def eliminar_mascota(mascota_id):
    """API para eliminar una mascota"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    try:
        success = mascotas_controlador.eliminar_mascota(mascota_id)
        if success:
            return jsonify({'success': True, 'message': 'Mascota eliminada exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'No se pudo eliminar la mascota'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {e}'})

@app.route('/cambiar-estado-cita/<int:cita_id>', methods=['POST'])
def cambiar_estado_cita(cita_id):
    """API para cambiar el estado de una cita"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    try:
        data = request.get_json()
        if not data or 'estado' not in data:
            return jsonify({'success': False, 'message': 'Estado no especificado'})
        
        nuevo_estado = data['estado']
        estados_validos = ['pendiente', 'en_proceso', 'completada', 'cancelada']
        
        if nuevo_estado not in estados_validos:
            return jsonify({'success': False, 'message': 'Estado no válido'})
        
        # Importar el controlador de citas si no está importado
        success = citas_controlador.actualizar_estado_cita(cita_id, nuevo_estado)
        
        if success:
            return jsonify({'success': True, 'message': f'Estado cambiado a {nuevo_estado} exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'No se pudo actualizar el estado de la cita'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/eliminar-cita/<int:cita_id>', methods=['DELETE'])
def eliminar_cita(cita_id):
    """API para eliminar una cita - Solo administradores"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño']:
        return jsonify({'success': False, 'message': 'Solo los administradores pueden eliminar citas'})
    
    try:
        success = citas_controlador.eliminar_cita(cita_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Cita eliminada exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'No se pudo eliminar la cita'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/obtener-cita/<int:cita_id>')
def obtener_cita(cita_id):
    """API para obtener los datos de una cita específica"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    try:
        cita_data = citas_controlador.obtener_cita_completa_por_id(cita_id)
        
        if cita_data:
            return jsonify({'success': True, 'cita': cita_data})
        else:
            return jsonify({'success': False, 'message': 'Cita no encontrada'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/editar-cita/<int:cita_id>', methods=['POST'])
def editar_cita(cita_id):
    """API para actualizar los datos de una cita"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        return jsonify({'success': False, 'message': 'Acceso denegado'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No se recibieron datos'})
        
        success = citas_controlador.actualizar_cita_completa(
            cita_id,
            data.get('cliente_nombre'),
            data.get('cliente_email'),
            data.get('fecha'),
            data.get('hora'),
            data.get('estado'),
            data.get('precio_total'),
            data.get('observaciones')
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Cita actualizada exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'No se pudo actualizar la cita'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
