from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import logging
from datetime import datetime, date
import hashlib
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from functools import wraps
from bd import obtener_conexion
from functools import wraps

# Importar controladores
from controladores import (
    usuarios_controlador,
    citas_controlador,
    servicios_controlador,
    personal_controlador,
    productos_controlador,
    asistencia_controlador,
    clientes_controlador,
    compras_controlador,
    ventas_controlador
)
# Módulo de fidelización (moved into controladores)
from controladores import fidelizacion_controlador as fidelizacion

app = Flask(__name__)
# Leer SECRET_KEY desde variable de entorno para seguridad
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_veterinaria')  # Cambia en prod y configura en el entorno

# Configuración de cookies de sesión seguras

# Filtros personalizados para las plantillas
@app.template_filter('days_difference')
def days_difference(fecha):
    """Calcula la diferencia en días entre una fecha y hoy"""
    if not fecha:
        return 999
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    elif isinstance(fecha, datetime):
        fecha = fecha.date()
    
    today = date.today()
    difference = (fecha - today).days
    return difference

@app.template_filter('format_date')
def format_date(fecha):
    """Formatea una fecha para mostrar"""
    if not fecha:
        return 'Sin fecha'
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    elif isinstance(fecha, datetime):
        fecha = fecha.date()
    
    return fecha.strftime('%d/%m/%Y')
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

# Decorador para requerir autenticación
def requiere_autenticacion(roles_permitidos=None):
    """
    Decorador para verificar autenticación y roles
    roles_permitidos: lista de roles permitidos (ej: ['admin', 'dueño'])
    Si no se especifica, permite todos los roles autenticados
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Verificar si el usuario está logueado
            if 'usuario' not in session or 'rol' not in session:
                flash('Debes iniciar sesión para acceder a esta página.')
                return redirect(url_for('login'))
            
            # Verificar roles si se especificaron
            if roles_permitidos:
                if session['rol'] not in roles_permitidos:
                    flash('No tienes permisos para acceder a esta página.')
                    return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Eliminar funciones helper que ahora están en los controladores
# def query_db(...): ...
# def hash_password(...): ...

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'maskot-favicon.ico', mimetype='image/vnd.microsoft.icon')

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


def _add_service_to_cart(servicio_id, quantity=1):
    """Agregar un servicio al carrito"""
    cart = _get_cart()
    
    # Los servicios se identifican con un prefijo 'service_' para distinguirlos de productos
    key = f'service_{servicio_id}'
    
    # Los servicios no tienen límite de stock como los productos
    existing = int(cart.get(key, {}).get('qty', 0))
    new_qty = existing + quantity
    
    cart[key] = {'qty': new_qty, 'type': 'service'}
    _save_cart(cart)
    
    return True


@app.route('/carrito')
def ver_carrito():
    cart = _get_cart()
    items = []
    total_qty = 0
    total_price = 0.0
    
    for id_str, data in list(cart.items()):
        qty = int(data.get('qty', 0))
        
        # Verificar si es un servicio
        if id_str.startswith('service_'):
            try:
                servicio_id = int(id_str.replace('service_', ''))
                servicio = servicios_controlador.obtener_servicio_por_id(servicio_id)
                if not servicio:
                    # Servicio eliminado, quitar del carrito
                    cart.pop(id_str, None)
                    continue
                
                precio_unitario = float(servicio[3] or 0)  # precio está en posición 3
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
                print(f"Error procesando servicio {id_str}: {e}")
                continue
                
        # Manejar productos (lógica existente)
        else:
            try:
                pid = int(id_str)
                producto = productos_controlador.obtener_producto_por_id(pid)
                if not producto:
                    # Producto eliminado, quitar del carrito
                    cart.pop(id_str, None)
                    continue
                    
                # adjust qty if exceeds stock
                stock = producto[3] or 0  # cantidad está en posición 3
                if qty > stock:
                    qty = stock
                    cart[id_str]['qty'] = qty
                
                precio_unitario = float(producto[4] or 0)  # precio está en posición 4
                subtotal = precio_unitario * qty
                
                items.append({
                    'id': pid,
                    'nombre': producto[1],
                    'imagen': producto[7],  # imagen está en posición 7
                    'precio_unitario': precio_unitario,
                    'qty': qty,
                    'subtotal': subtotal,
                    'stock': stock,
                    'type': 'product'
                })
                total_qty += qty
                total_price += subtotal
            except Exception as e:
                print(f"Error procesando producto {id_str}: {e}")
                continue
    
    # save any adjustments
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
        
        # Registrar la compra en el historial
        try:
            # Preparar productos para el historial
            productos_compra = []
            for item in items:
                productos_compra.append({
                    'id': item['id'],
                    'nombre': item['nombre'],
                    'precio': item['precio_unitario'],
                    'cantidad': item['qty']
                })
            
            # Obtener vendedor_id desde la sesión (si está disponible)
            vendedor_id = session.get('user_id')
            
            # Registrar en el historial de compras
            compra_id = compras_controlador.registrar_compra(
                cliente_nombre=nombre,
                cliente_email=email,
                cliente_telefono=telefono,
                productos=productos_compra,
                metodo_pago=metodo_pago,
                observaciones=f"Pedido #{pedido_id} - Dirección: {direccion}",
                vendedor_id=vendedor_id
            )
            
            if compra_id:
                logger.info(f"Compra #{compra_id} registrada en historial para pedido #{pedido_id}")
            else:
                logger.warning(f"No se pudo registrar la compra en el historial para pedido #{pedido_id}")
                
        except Exception as e:
            # No fallar el pago si hay error en el historial, solo registrar
            logger.error(f"Error al registrar compra en historial: {e}")
        
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
        
        # Mensaje adicional sobre el historial
        if 'compra_id' in locals() and compra_id:
            flash(f'Tu compra #{compra_id} ha sido registrada. Puedes ver el historial en el área de gestión.', 'info')
        
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
        # New: capture telefono and direccion from the appointment form (if provided)
        telefono = request.form.get('cliente_telefono', '').strip()
        direccion = request.form.get('cliente_direccion', '').strip()
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

        # Require phone and address for appointment booking
        if not telefono or not direccion:
            flash('Por favor proporciona teléfono y dirección del cliente al agendar la cita.', 'error')
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
        
        # Ensure client exists or create/update with phone & address
        try:
            cliente = clientes_controlador.obtener_cliente_por_email(email)
            if cliente:
                # Update phone/direction if missing or changed
                clientes_controlador.actualizar_cliente(email, email, telefono, direccion)
            else:
                clientes_controlador.insertar_cliente(nombre, email, telefono, direccion)
        except Exception as e:
            # Log but continue to create the cita; clientes table should sync if DB allows
            logger.warning(f"No se pudo crear/actualizar cliente al agendar cita: {e}")

        # Insertar cita completa
        cita_id = citas_controlador.insertar_cita_completa(
            nombre, email, mascotas_data, servicios_ids, fecha, hora
        )

        # Procesar programa de fidelización: registrar y obtener URL de WA si corresponde
        try:
            fidel_res = fidelizacion.procesar_fidelizacion_para_cliente(nombre, email)
            if fidel_res and fidel_res.get('wa_url'):
                wa_link = fidel_res.get('wa_url')
                # Agregar info breve al mensaje de éxito para que el personal pueda abrir el enlace
                flash(f'Notificación de fidelización lista: {wa_link}', 'info')
        except Exception as e:
            logger.warning(f'No se pudo procesar fidelización para {email}: {e}')
        
        # Agregar servicios al carrito automáticamente
        servicios_agregados = []
        for servicio_id in servicios_ids:
            try:
                _add_service_to_cart(servicio_id, 1)
                servicio_info = servicios_controlador.obtener_servicio_por_id(servicio_id)
                if servicio_info:
                    servicios_agregados.append(servicio_info[1])  # nombre del servicio
            except Exception as e:
                print(f"Error agregando servicio {servicio_id} al carrito: {e}")
        
        # Mensaje de éxito
        mascotas_str = ', '.join([m['nombre'] for m in mascotas_data])
        success_msg = f'Cita agendada exitosamente para {mascotas_str} el {fecha} a las {hora}.'
        
        if servicios_agregados:
            servicios_str = ', '.join(servicios_agregados)
            success_msg += f' Los servicios ({servicios_str}) se agregaron al carrito para su pago.'
            
        flash(success_msg, 'success')
        
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
            auth = usuarios_controlador.verificar_credenciales(username, password)
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
        session['usuario'] = user[1]  # Cambiado de 'username' a 'usuario' para consistencia
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
    
    # Obtener/actualizar alertas de fidelización solo para roles de personal (empleado, admin, dueño)
    alertas_fidelizacion = []
    if rol in ['admin', 'empleado', 'dueño']:
        try:
            fidelizacion.sincronizar_fidelizacion_desde_citas()
        except Exception as e:
            logger.warning(f"Error sincronizando fidelizacion: {e}")

        try:
            alertas_fidelizacion = fidelizacion.obtener_alertas_recientes(limit=10)
        except Exception as e:
            logger.warning(f"Error obteniendo alertas de fidelizacion: {e}")
    
    if rol == 'dueño':
        total_empleados = len(personal_controlador.obtener_personal())
        servicios_activos = len(servicios_controlador.obtener_servicios_activos())
        productos_bajos = productos_controlador.obtener_productos_stock_bajo()
        
        return render_template('dashboard.html', 
                               citas_hoy=citas_hoy, 
                               total_empleados=total_empleados, 
                               servicios_activos=servicios_activos,
                               productos_bajos=productos_bajos,
                               alertas_fidelizacion=alertas_fidelizacion)
    
    return render_template('dashboard.html', citas_hoy=citas_hoy, alertas_fidelizacion=alertas_fidelizacion)

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
                servicios_controlador.desactivar_servicio(id_serv)
                flash('Servicio desactivado.', 'info')
            
            elif 'activar' in request.form:
                id_serv = int(request.form['id'])
                servicios_controlador.activar_servicio(id_serv)
                flash('Servicio activado.', 'success')

        except Exception as e:
            flash(f'Ocurrió un error: {e}', 'error')
        
        return redirect(url_for('servicios'))

    servicios = servicios_controlador.obtener_servicios()
    return render_template('servicios.html', servicios=servicios)

@app.route('/servicios/agregar', methods=['POST'])
def agregar_servicio():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        # Si es formulario normal, redirigir con error
        if request.form:
            flash('Acceso denegado', 'error')
            return redirect(url_for('servicios'))
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        # Manejar tanto JSON como form data
        if request.is_json:
            data = request.get_json()
            nombre = data.get('nombre')
            descripcion = data.get('descripcion', '')
            precio = float(data.get('precio', 0.00))
            duracion = int(data.get('duracion', 30))
        else:
            # Form data
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion', '')
            precio = float(request.form.get('precio', 0.00))
            duracion = int(request.form.get('duracion', 30))
        
        # Usar un valor por defecto para max_citas basado en duracion
        max_citas = max(1, 480 // duracion)  # 480 minutos = 8 horas laborales
        
        if servicios_controlador.insertar_servicio(nombre, descripcion, max_citas, precio, duracion):
            if request.is_json:
                return jsonify({'success': True, 'message': 'Servicio agregado exitosamente'})
            else:
                flash('Servicio agregado exitosamente', 'success')
                return redirect(url_for('servicios'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Error al agregar servicio'}), 500
            else:
                flash('Error al agregar servicio', 'error')
                return redirect(url_for('servicios'))
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('servicios'))

@app.route('/servicios/editar', methods=['POST'])
def editar_servicio():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        # Si es formulario normal, redirigir con error
        if request.form:
            flash('Acceso denegado', 'error')
            return redirect(url_for('servicios'))
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        # Manejar tanto JSON como form data
        if request.is_json:
            data = request.get_json()
            servicio_id = int(data.get('servicio_id'))
            nombre = data.get('nombre')
            descripcion = data.get('descripcion', '')
            precio = float(data.get('precio', 0.00))
            duracion = int(data.get('duracion', 30))
        else:
            # Form data
            servicio_id = int(request.form.get('servicio_id'))
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion', '')
            precio = float(request.form.get('precio', 0.00))
            duracion = int(request.form.get('duracion', 30))
        
        # Usar un valor por defecto para max_citas basado en duracion
        max_citas = max(1, 480 // duracion)  # 480 minutos = 8 horas laborales
        
        if servicios_controlador.actualizar_servicio(servicio_id, nombre, descripcion, max_citas, precio, duracion):
            if request.is_json:
                return jsonify({'success': True, 'message': 'Servicio actualizado exitosamente'})
            else:
                flash('Servicio actualizado exitosamente', 'success')
                return redirect(url_for('servicios'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Error al actualizar servicio'}), 500
            else:
                flash('Error al actualizar servicio', 'error')
                return redirect(url_for('servicios'))
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        else:
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('servicios'))

@app.route('/servicios/cambiar-estado', methods=['POST'])
def cambiar_estado_servicio():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        data = request.get_json()
        servicio_id = int(data.get('servicio_id'))
        activo = data.get('activo')
        
        if activo:
            success = servicios_controlador.activar_servicio(servicio_id)
            message = 'Servicio activado exitosamente'
        else:
            success = servicios_controlador.desactivar_servicio(servicio_id)
            message = 'Servicio desactivado exitosamente'
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': 'Error al cambiar estado del servicio'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/almacen', methods=['GET', 'POST'])
def almacen():
    """Gestión completa del inventario de productos"""
    # Allow empleados to view the almacen page (GET) but restrict POST actions
    if 'rol' not in session:
        flash('Acceso denegado. Debes iniciar sesión.', 'error')
        return redirect(url_for('login'))

    # If POST request (mutating actions), allow dueño, admin and empleado
    if request.method == 'POST' and session.get('rol') not in ['dueño', 'admin', 'empleado']:
        flash('Acceso denegado. No tienes permisos para modificar el almacén.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            if 'agregar' in request.form:
                nombre = request.form['nombre']
                tipo = request.form['tipo']
                cantidad = int(request.form.get('cantidad', 0))
                stock_min = int(request.form.get('stock_min', 0))
                fecha_vencimiento = request.form.get('fecha_vencimiento')
                if fecha_vencimiento == '':
                    fecha_vencimiento = None
                
                resultado = productos_controlador.insertar_producto(nombre, tipo, cantidad, stock_min, fecha_vencimiento)
                
                if resultado:
                    flash('Producto agregado exitosamente.', 'success')
                else:
                    flash('Error al agregar producto.', 'error')

            elif 'eliminar' in request.form:
                producto_id = int(request.form['id'])
                if productos_controlador.eliminar_producto(producto_id):
                    flash('Producto eliminado exitosamente.', 'success')
                else:
                    flash('Error al eliminar producto.', 'error')
            
            elif 'actualizar_stock' in request.form:
                producto_id = int(request.form['id'])
                nueva_cantidad = int(request.form['nueva_cantidad'])
                if productos_controlador.actualizar_stock_producto(producto_id, nueva_cantidad):
                    flash('Stock actualizado exitosamente.', 'success')
                else:
                    flash('Error al actualizar stock.', 'error')
                    
            elif 'modificar' in request.form:
                producto_id = int(request.form['id'])
                nombre = request.form['nombre']
                cantidad = int(request.form.get('cantidad', 0))
                stock_min = int(request.form.get('stock_min', 0))
                fecha_vencimiento = request.form.get('fecha_vencimiento')
                if fecha_vencimiento == '':
                    fecha_vencimiento = None
                
                # Obtener tipo actual del producto para no cambiarlo
                producto_actual = productos_controlador.obtener_producto_por_id(producto_id)
                if producto_actual:
                    tipo_actual = producto_actual[2]  # índice 2 es el tipo
                    
                    resultado = productos_controlador.actualizar_producto(producto_id, nombre, tipo_actual, cantidad, stock_min, fecha_vencimiento)
                    
                    if resultado:
                        flash('Producto actualizado exitosamente.', 'success')
                    else:
                        flash('Error al actualizar producto.', 'error')
                else:
                    flash('Producto no encontrado.', 'error')

        except Exception as e:
            flash(f'Ocurrió un error: {e}', 'error')
        
        # Siempre redirigir después del POST para evitar reenvíos
        return redirect(url_for('almacen'))

    # GET: show products depending on role
    if session.get('rol') == 'empleado':
        # Employees should only see internal stock items
        productos = productos_controlador.obtener_productos_por_tipo('stock')
        # For employees we still may want to show alerts; compute filtered lists
        productos_bajo_stock = [p for p in productos if p[3] <= p[5]]
        productos_por_vencer = [p for p in productos if p[6] and days_difference(p[6]) <= 30]
    else:
        # Admins and dueños see everything
        productos = productos_controlador.obtener_productos()
        productos_bajo_stock = productos_controlador.obtener_productos_bajo_stock()
        productos_por_vencer = productos_controlador.obtener_productos_por_vencer()

    return render_template('almacen.html', 
                         productos=productos,
                         productos_bajo_stock=productos_bajo_stock,
                         productos_por_vencer=productos_por_vencer)

@app.route('/almacen/agregar', methods=['POST'])
def agregar_producto_api():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        tipo = data.get('tipo', 'stock')
        cantidad = int(data.get('cantidad', 0))
        stock_min = int(data.get('stock_min', 0))
        fecha_vencimiento = data.get('fecha_vencimiento')
        if fecha_vencimiento == '':
            fecha_vencimiento = None
        
        producto_id = productos_controlador.insertar_producto(nombre, tipo, cantidad, stock_min, fecha_vencimiento)
        if producto_id:
            return jsonify({'success': True, 'message': 'Producto agregado exitosamente', 'producto_id': producto_id})
        else:
            return jsonify({'success': False, 'error': 'Error al agregar producto'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/almacen/editar', methods=['POST'])
def editar_producto_api():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        data = request.get_json()
        producto_id = int(data.get('producto_id'))
        nombre = data.get('nombre')
        tipo = data.get('tipo', 'stock')
        cantidad = int(data.get('cantidad', 0))
        stock_min = int(data.get('stock_min', 0))
        fecha_vencimiento = data.get('fecha_vencimiento')
        if fecha_vencimiento == '':
            fecha_vencimiento = None
        
        if productos_controlador.actualizar_producto(producto_id, nombre, tipo, cantidad, stock_min, fecha_vencimiento):
            return jsonify({'success': True, 'message': 'Producto actualizado exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al actualizar producto'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/almacen/eliminar', methods=['POST'])
def eliminar_producto_api():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        data = request.get_json()
        producto_id = int(data.get('producto_id'))
        
        if productos_controlador.eliminar_producto(producto_id):
            return jsonify({'success': True, 'message': 'Producto eliminado exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al eliminar producto'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/almacen/actualizar-stock', methods=['POST'])
def actualizar_stock_api():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin']:
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    
    try:
        data = request.get_json()
        producto_id = int(data.get('producto_id'))
        nueva_cantidad = int(data.get('nueva_cantidad'))
        
        if productos_controlador.actualizar_stock_producto(producto_id, nueva_cantidad):
            return jsonify({'success': True, 'message': 'Stock actualizado exitosamente'})
        else:
            return jsonify({'success': False, 'error': 'Error al actualizar stock'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/almacen/usar_producto', methods=['POST'])
def usar_producto():
    if 'rol' not in session or session['rol'] not in ['dueño', 'admin', 'empleado']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('almacen'))
    
    try:
        producto_id = int(request.form.get('producto_id'))
        cantidad_a_usar = int(request.form.get('cantidad'))
        motivo = request.form.get('motivo', 'Uso interno').strip()
        
        if cantidad_a_usar <= 0:
            flash('La cantidad debe ser mayor a cero.', 'error')
            return redirect(url_for('almacen'))
        
        # Obtener el producto actual
        producto = productos_controlador.obtener_producto_por_id(producto_id)
        if not producto:
            flash('Producto no encontrado.', 'error')
            return redirect(url_for('almacen'))
        
        stock_actual = producto[3]  # cantidad actual
        
        if stock_actual < cantidad_a_usar:
            flash(f'Stock insuficiente. Solo hay {stock_actual} unidades disponibles.', 'error')
            return redirect(url_for('almacen'))
        
        # Reducir el stock
        nuevo_stock = stock_actual - cantidad_a_usar
        if productos_controlador.actualizar_stock_producto(producto_id, nuevo_stock):
            flash(f'Se usaron {cantidad_a_usar} unidades de "{producto[1]}". Motivo: {motivo}', 'success')
        else:
            flash('Error al actualizar el stock.', 'error')
            
    except ValueError:
        flash('Datos inválidos proporcionados.', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('almacen'))

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
                personal_controlador.actualizar_empleado(id_p, cargo, salario)
                flash('Empleado modificado exitosamente.', 'success')

            elif 'eliminar' in request.form:
                id_p = int(request.form['id'])
                print(f'DEBUG: Intentando eliminar personal con ID: {id_p}')
                
                personal_info = personal_controlador.obtener_empleado_por_id(id_p)
                print(f'DEBUG: Personal encontrado: {personal_info}')
                
                if personal_info:
                    try:
                        # Desactivar tanto en personal como en usuarios
                        personal_controlador.desactivar_empleado(id_p)
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
                
                personal_info = personal_controlador.obtener_empleado_por_id(id_p)
                print(f'DEBUG: Personal encontrado: {personal_info}')
                
                if personal_info:
                    try:
                        # Reactivar tanto en personal como en usuarios
                        personal_controlador.activar_empleado(id_p)
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
    personal_list = personal_controlador.obtener_empleados()  # Mostrar todo el personal
    usuarios_list = usuarios_controlador.obtener_todos_usuarios()  # Obtener todos los usuarios
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
                asistencia_controlador.marcar_entrada(personal_id=personal_id, fecha=hoy, hora=datetime.now().strftime('%H:%M:%S'))
                flash('Entrada marcada exitosamente.', 'success')
            elif 'salida' in request.form and asistencia_hoy and not asistencia_hoy[4]:  # Si no hay hora_salida
                asistencia_controlador.marcar_salida(personal_id=personal_id, fecha=hoy, hora=datetime.now().strftime('%H:%M:%S'))
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
    """Página para que admins/dueños y empleados vean el historial completo de clientes"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        flash('Acceso denegado. No tienes permisos para ver el historial de clientes.', 'error')
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
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        flash('Acceso denegado. No tienes permisos para ver detalles de clientes.', 'error')
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



@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/clientes')
def listar_clientes():
    """Lista todos los clientes para administradores y dueños"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        flash('Acceso denegado. No tienes permisos para ver la lista de clientes.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Obtener todos los clientes únicos de las citas
        clientes = clientes_controlador.obtener_todos_clientes()
        return render_template('clientes.html', clientes=clientes)
    
    except Exception as e:
        flash(f'Error al cargar la lista de clientes: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/crear-cliente', methods=['GET', 'POST'])
def crear_cliente():
    """Crear un nuevo cliente"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        flash('Acceso denegado. No tienes permisos para crear clientes.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        documento = request.form.get('documento')
        
        if not nombre or not email:
            flash('El nombre y email son requeridos', 'error')
            return redirect(url_for('listar_clientes'))
        
        try:
            clientes_controlador.insertar_cliente(nombre, email, telefono, direccion, documento)
            flash(f'Cliente {nombre} creado exitosamente', 'success')
        except Exception as e:
            flash(f'Error al crear cliente: {str(e)}', 'error')
        
        return redirect(url_for('listar_clientes'))
    
    return render_template('crear-cliente.html')

@app.route('/editar-cliente/<cliente_email>', methods=['GET', 'POST'])
def editar_cliente(cliente_email):
    """Edita la información de un cliente (excepto el nombre)"""
    if 'rol' not in session or session['rol'] not in ['admin', 'dueño', 'empleado']:
        flash('Acceso denegado. No tienes permisos para editar clientes.', 'error')
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

# ======================= RUTAS DE GESTIÓN DE CITAS =======================

@app.route('/cita/<int:cita_id>/status', methods=['POST'])
def cambiar_estado_cita(cita_id):
    """Cambia el estado de una cita"""
    print(f"=== CAMBIAR ESTADO CITA {cita_id} ===")
    print(f"Session actual: {dict(session)}")
    print(f"Usuario en sesión: {session.get('usuario', 'No encontrado')}")
    print(f"Rol en sesión: {session.get('rol', 'No encontrado')}")
    
    if 'usuario' not in session:
        print("ERROR: No hay 'usuario' en sesión")
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    # Verificar permisos de rol
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        print(f"ERROR: Rol '{session.get('rol')}' no tiene permisos")
        return jsonify({'success': False, 'error': 'Sin permisos para modificar citas'}), 403
    
    try:
        data = request.get_json()
        print(f"Datos recibidos: {data}")
        nuevo_estado = data.get('status')
        motivo = data.get('motivo', '')
        print(f"Nuevo estado: {nuevo_estado}, Motivo: {motivo}")
        
        if not nuevo_estado:
            print("ERROR: Estado requerido")
            return jsonify({'success': False, 'error': 'Estado requerido'}), 400
        
        # Validar estados válidos
        estados_validos = ['pendiente', 'confirmada', 'en_progreso', 'completada', 'cancelada']
        if nuevo_estado not in estados_validos:
            print(f"ERROR: Estado '{nuevo_estado}' no válido")
            return jsonify({'success': False, 'error': 'Estado no válido'}), 400
        
        # Actualizar estado en la base de datos
        print("Conectando a la base de datos...")
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Actualizar la cita
        print(f"Actualizando cita {cita_id} a estado '{nuevo_estado}'")
        cursor.execute("""
            UPDATE citas 
            SET estado = %s 
            WHERE id = %s
        """, (nuevo_estado, cita_id))
        
        # Si hay motivo (para cancelaciones), guardarlo en observaciones
        if motivo:
            cursor.execute("""
                UPDATE citas 
                SET observaciones = CONCAT(IFNULL(observaciones, ''), 
                                         IF(observaciones IS NULL OR observaciones = '', '', ' | '), 
                                         %s)
                WHERE id = %s
            """, (f"Motivo: {motivo}", cita_id))
        
        conexion.commit()
        
        # Mensaje según el estado
        mensajes = {
            'pendiente': 'Cita marcada como pendiente',
            'confirmada': 'Cita confirmada exitosamente',
            'en_progreso': 'Cita marcada como en progreso',
            'completada': 'Cita completada exitosamente',
            'cancelada': 'Cita cancelada'
        }
        
        return jsonify({
            'success': True, 
            'message': mensajes.get(nuevo_estado, 'Estado actualizado')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conexion' in locals():
            conexion.close()

@app.route('/cita/<int:cita_id>/reprogramar', methods=['POST'])
def reprogramar_cita(cita_id):
    """Reprograma una cita cambiando fecha y hora"""
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    # Verificar permisos de rol
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos para reprogramar citas'}), 403
    
    try:
        data = request.get_json()
        nueva_fecha = data.get('fecha')
        nueva_hora = data.get('hora')
        
        if not nueva_fecha or not nueva_hora:
            return jsonify({'success': False, 'error': 'Fecha y hora requeridas'}), 400
        
        # Validar formato de fecha
        from datetime import datetime
        try:
            datetime.strptime(nueva_fecha, '%Y-%m-%d')
            datetime.strptime(nueva_hora, '%H:%M')
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato de fecha/hora inválido'}), 400
        
        # Actualizar en la base de datos
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            UPDATE citas 
            SET fecha = %s, hora = %s, estado = 'pendiente'
            WHERE id = %s
        """, (nueva_fecha, nueva_hora, cita_id))
        
        conexion.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Cita reprogramada para {nueva_fecha} a las {nueva_hora}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conexion' in locals():
            conexion.close()

@app.route('/cita/<int:cita_id>/detalles')
def ver_detalles_cita(cita_id):
    """Muestra los detalles completos de una cita"""
    if 'usuario' not in session:
        flash('Debe iniciar sesión para acceder a esta página.', 'error')
        return redirect(url_for('login'))
    
    # Verificar permisos de rol
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Sin permisos para ver detalles de citas.', 'error')
        return redirect(url_for('index'))
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener detalles completos de la cita
        cursor.execute("""
            SELECT 
                c.id,
                c.cliente_nombre,
                c.cliente_email,
                s.nombre as servicio_nombre,
                c.fecha,
                c.hora,
                c.estado,
                c.created_at,
                c.observaciones,
                c.mascota_nombre,
                c.mascota_especie,
                c.mascota_raza,
                c.mascota_edad,
                c.mascota_peso,
                c.cliente_telefono,
                c.precio_total
            FROM citas c
            LEFT JOIN servicios s ON c.servicio_id = s.id
            WHERE c.id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        
        if not cita:
            flash('Cita no encontrada.', 'error')
            return redirect(url_for('citas'))
        
        # Procesar información de mascotas desde los campos directos de la tabla citas
        mascotas = []
        if cita[9]:  # mascota_nombre
            mascotas.append({
                'nombre': cita[9] or 'No especificado',
                'especie': cita[10] or 'No especificado',
                'raza': cita[11] or 'No especificado',
                'edad': cita[12] or 'No especificado',
                'peso': cita[13] or 'No especificado'
            })
        
        # Obtener servicios adicionales si los hay
        cursor.execute("""
            SELECT cs.servicio_id, s.nombre 
            FROM citas_servicios cs
            JOIN servicios s ON cs.servicio_id = s.id
            WHERE cs.cita_id = %s
        """, (cita_id,))
        
        servicios_adicionales = cursor.fetchall()
        
        return render_template('detalle_cita.html', 
                             cita=cita, 
                             mascotas=mascotas,
                             servicios_adicionales=servicios_adicionales)
        
    except Exception as e:
        flash(f'Error al cargar detalles de la cita: {e}', 'error')
        return redirect(url_for('citas'))
    finally:
        if 'conexion' in locals():
            conexion.close()

@app.route('/cita/<int:cita_id>/editar', methods=['GET', 'POST'])
def editar_cita(cita_id):
    """Edita una cita existente"""
    if 'usuario' not in session:
        flash('Debe iniciar sesión para acceder a esta página.', 'error')
        return redirect(url_for('login'))
    
    # Verificar permisos de rol
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Sin permisos para editar citas.', 'error')
        return redirect(url_for('citas'))
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            cliente_nombre = request.form['cliente_nombre']
            cliente_email = request.form['cliente_email']
            fecha = request.form['fecha']
            hora = request.form['hora']
            servicio_id = request.form['servicio_id']
            observaciones = request.form.get('observaciones', '')
            
            # Validar datos básicos
            if not all([cliente_nombre, cliente_email, fecha, hora, servicio_id]):
                flash('Todos los campos básicos son obligatorios.', 'error')
                return redirect(request.url)
            
            # Actualizar en la base de datos
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            
            cursor.execute("""
                UPDATE citas 
                SET cliente_nombre = %s, cliente_email = %s, fecha = %s, 
                    hora = %s, servicio_id = %s, observaciones = %s
                WHERE id = %s
            """, (cliente_nombre, cliente_email, fecha, hora, servicio_id, observaciones, cita_id))
            
            conexion.commit()
            
            flash('Cita actualizada exitosamente.', 'success')
            return redirect(url_for('citas'))
            
        except Exception as e:
            flash(f'Error al actualizar la cita: {e}', 'error')
            return redirect(request.url)
        finally:
            if 'conexion' in locals():
                conexion.close()
    
    # GET: Mostrar formulario de edición
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener datos de la cita
        cursor.execute("""
            SELECT id, cliente_nombre, cliente_email, servicio_id, fecha, hora, observaciones, estado
            FROM citas 
            WHERE id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        
        if not cita:
            flash('Cita no encontrada.', 'error')
            return redirect(url_for('citas'))
        
        # Obtener servicios disponibles
        cursor.execute("SELECT id, nombre FROM servicios WHERE activo = 1")
        servicios = cursor.fetchall()
        
        return render_template('editar_cita.html', cita=cita, servicios=servicios)
        
    except Exception as e:
        flash(f'Error al cargar datos de la cita: {e}', 'error')
        return redirect(url_for('citas'))
    finally:
        if 'conexion' in locals():
            conexion.close()

@app.route('/cita/<int:cita_id>/recibo')
def generar_recibo(cita_id):
    """Genera un recibo para una cita"""
    if 'usuario' not in session:
        flash('Debe iniciar sesión para acceder a esta página.', 'error')
        return redirect(url_for('login'))
    
    # Verificar permisos de rol
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Sin permisos para generar recibos.', 'error')
        return redirect(url_for('citas'))
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener detalles básicos de la cita
        cursor.execute("""
            SELECT 
                c.id,
                c.cliente_nombre,
                c.cliente_email,
                c.servicio_id,
                c.fecha,
                c.hora,
                c.observaciones,
                c.estado
            FROM citas c
            WHERE c.id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        
        if not cita:
            flash('Cita no encontrada.', 'error')
            return redirect(url_for('citas'))
        
        # Obtener nombre del servicio principal si existe
        servicio_nombre = "Servicio no especificado"
        if cita[3]:  # servicio_id
            cursor.execute("SELECT nombre FROM servicios WHERE id = %s", (cita[3],))
            servicio_result = cursor.fetchone()
            if servicio_result:
                servicio_nombre = servicio_result[0]
        
        # Intentar obtener mascotas de la cita (opcional)
        mascotas = []
        try:
            cursor.execute("""
                SELECT nombre, especie, raza, edad 
                FROM citas_mascotas 
                WHERE cita_id = %s
            """, (cita_id,))
            mascotas = cursor.fetchall()
        except:
            # Si la tabla no existe o hay error, usar datos básicos de la cita
            if hasattr(cita, '__getitem__') and len(cita) > 8:
                # Usar datos de mascota de la tabla principal si existen
                pass
        
        # Intentar obtener servicios adicionales (opcional)
        servicios_adicionales = []
        try:
            cursor.execute("""
                SELECT s.nombre, s.precio 
                FROM citas_servicios cs
                JOIN servicios s ON cs.servicio_id = s.id
                WHERE cs.cita_id = %s
            """, (cita_id,))
            servicios_adicionales = cursor.fetchall()
        except:
            # Si no hay servicios adicionales, usar el servicio principal
            if servicio_nombre != "Servicio no especificado":
                cursor.execute("SELECT precio FROM servicios WHERE id = %s", (cita[3],))
                precio_result = cursor.fetchone()
                if precio_result:
                    servicios_adicionales = [(servicio_nombre, precio_result[0])]
        
        # Momento actual para el recibo
        from datetime import datetime
        momento_actual = datetime.now()
        
        return render_template('ticket_cita.html', 
                             cita=cita, 
                             servicio_nombre=servicio_nombre,
                             mascotas=mascotas,
                             servicios_adicionales=servicios_adicionales,
                             momento_actual=momento_actual)
        
    except Exception as e:
        flash(f'Error al generar recibo: {e}', 'error')
        return redirect(url_for('citas'))
    finally:
        if 'conexion' in locals():
            conexion.close()

@app.route('/cita/<int:cita_id>/eliminar', methods=['DELETE'])
def eliminar_cita(cita_id):
    """Elimina permanentemente una cita"""
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'No autorizado'}), 401
    
    # Solo admin y dueño pueden eliminar permanentemente
    if 'rol' not in session or session.get('rol') not in ['admin', 'dueño']:
        return jsonify({'success': False, 'error': 'Sin permisos para eliminar citas'}), 403
    
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Verificar que la cita existe
        cursor.execute("SELECT id FROM citas WHERE id = %s", (cita_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'Cita no encontrada'}), 404
        
        # Eliminar registros relacionados primero
        cursor.execute("DELETE FROM cita_mascotas WHERE cita_id = %s", (cita_id,))
        cursor.execute("DELETE FROM cita_servicios WHERE cita_id = %s", (cita_id,))
        
        # Eliminar la cita
        cursor.execute("DELETE FROM citas WHERE id = %s", (cita_id,))
        
        conexion.commit()
        
        return jsonify({'success': True, 'message': 'Cita eliminada permanentemente'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if 'conexion' in locals():
            conexion.close()

# Ruta de debug para verificar sesión
@app.route('/debug/session')
def debug_session():
    """Ruta de debug para verificar el estado de la sesión"""
    if 'usuario' not in session:
        return jsonify({
            'authenticated': False,
            'message': 'No hay sesión activa'
        })
    
    return jsonify({
        'authenticated': True,
        'usuario': session.get('usuario'),
        'rol': session.get('rol'),
        'session_keys': list(session.keys()),
        'can_access_citas': 'rol' in session and session['rol'] in ['admin', 'empleado', 'dueño'],
        'can_modify': 'rol' in session and session['rol'] in ['admin', 'dueño']
    })

@app.route('/debug/session-page')
def debug_session_page():
    """Página de debug para verificar el estado de la sesión en el navegador"""
    from datetime import datetime
    import json
    
    # Preparar datos de sesión para mostrar
    session_dict = {}
    for key in session.keys():
        session_dict[key] = session[key]
    
    session_data = json.dumps(session_dict, indent=2, ensure_ascii=False)
    
    return render_template('debug_session.html', 
                         session_data=session_data,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/test/estado')
def test_estado():
    """Página de test para cambiar estado de citas"""
    return render_template('test_estado.html')

# ==========================================
# RUTAS DE COMPRAS Y HISTORIAL
# ==========================================

@app.route('/compras')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def historial_compras():
    """Muestra el historial de compras con filtros"""
    # Verificar permisos de rol
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Sin permisos para ver el historial de compras.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        cliente_email = request.args.get('cliente_email')
        estado = request.args.get('estado')
        pagina = int(request.args.get('pagina', 1))
        por_pagina = 20
        offset = (pagina - 1) * por_pagina
        
        # Obtener compras filtradas
        compras = compras_controlador.obtener_compras_por_fecha(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            cliente_email=cliente_email,
            estado=estado,
            limit=por_pagina,
            offset=offset
        )
        
        # Obtener estadísticas
        estadisticas = compras_controlador.obtener_estadisticas_compras(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return render_template('historial_compras.html', 
                             compras=compras,
                             estadisticas=estadisticas,
                             filtros={
                                 'fecha_inicio': fecha_inicio,
                                 'fecha_fin': fecha_fin,
                                 'cliente_email': cliente_email,
                                 'estado': estado
                             },
                             pagina=pagina)
        
    except Exception as e:
        flash(f'Error al cargar historial de compras: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/compra/<int:compra_id>/detalle')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def detalle_compra(compra_id):
    """Muestra los detalles completos de una compra"""
    
    try:
        compra = compras_controlador.obtener_detalle_compra(compra_id)
        
        if not compra:
            flash('Compra no encontrada.', 'error')
            return redirect(url_for('historial_compras'))
        
        return render_template('detalle_compra.html', compra=compra)
        
    except Exception as e:
        flash(f'Error al cargar detalle de compra: {e}', 'error')
        return redirect(url_for('historial_compras'))

@app.route('/compra/<int:compra_id>/ticket')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def generar_ticket_compra(compra_id):
    """Genera un ticket para una compra"""
    if 'rol' not in session or session['rol'] not in ['admin', 'empleado', 'dueño']:
        flash('Sin permisos para generar tickets.', 'error')
        return redirect(url_for('historial_compras'))
    
    try:
        compra = compras_controlador.obtener_detalle_compra(compra_id)
        
        if not compra:
            flash('Compra no encontrada.', 'error')
            return redirect(url_for('historial_compras'))
        
        # Momento actual para el ticket
        momento_actual = datetime.now()
        
        return render_template('ticket_compra.html', 
                             compra=compra,
                             momento_actual=momento_actual)
        
    except Exception as e:
        flash(f'Error al generar ticket: {e}', 'error')
        return redirect(url_for('historial_compras'))

@app.route('/compra/registrar', methods=['POST'])
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def registrar_compra():
    """Registra una nueva compra en el historial"""
    
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        if not all(k in data for k in ['cliente_nombre', 'cliente_email', 'productos']):
            return jsonify({'success': False, 'message': 'Datos incompletos'})
        
        # Obtener vendedor_id desde la sesión
        vendedor_id = session.get('user_id')
        
        # Registrar la compra
        compra_id = compras_controlador.registrar_compra(
            cliente_nombre=data['cliente_nombre'],
            cliente_email=data['cliente_email'],
            cliente_telefono=data.get('cliente_telefono'),
            productos=data['productos'],
            metodo_pago=data.get('metodo_pago', 'efectivo'),
            observaciones=data.get('observaciones'),
            vendedor_id=vendedor_id
        )
        
        if compra_id:
            return jsonify({
                'success': True, 
                'message': 'Compra registrada exitosamente',
                'compra_id': compra_id
            })
        else:
            return jsonify({'success': False, 'message': 'Error al registrar la compra'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/compra/<int:compra_id>/estado', methods=['PUT'])
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def cambiar_estado_compra(compra_id):
    """Cambia el estado de una compra"""
    
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['pendiente', 'pagado', 'cancelado', 'reembolsado']:
            return jsonify({'success': False, 'message': 'Estado no válido'})
        
        success = compras_controlador.actualizar_estado_compra(compra_id, nuevo_estado)
        
        if success:
            return jsonify({'success': True, 'message': f'Estado cambiado a {nuevo_estado}'})
        else:
            return jsonify({'success': False, 'message': 'No se pudo cambiar el estado'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/compras/buscar')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def buscar_compras():
    """API para buscar compras por cliente"""
    
    try:
        termino = request.args.get('q', '')
        
        if len(termino) < 2:
            return jsonify({'compras': []})
        
        compras = compras_controlador.buscar_compras_por_cliente(termino)
        
        # Formatear resultados
        resultados = []
        for compra in compras:
            resultados.append({
                'id': compra[0],
                'cliente_nombre': compra[1],
                'cliente_email': compra[2],
                'total': float(compra[3]),
                'fecha_compra': compra[4].strftime('%d/%m/%Y'),
                'estado': compra[5]
            })
        
        return jsonify({'compras': resultados})
        
    except Exception as e:
        return jsonify({'error': str(e)})

# ==========================================
# RUTAS DE VENTAS EN TIENDA
# ==========================================

@app.route('/ventas')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def punto_de_venta():
    """Interfaz principal de ventas en tienda (POS)"""
    try:
        # Obtener productos disponibles para venta
        productos = ventas_controlador.obtener_productos_venta()
        
        return render_template('pos.html', productos=productos)
        
    except Exception as e:
        flash(f'Error cargando punto de venta: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/productos-venta')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def api_productos_venta():
    """API para obtener productos disponibles para venta"""
    try:
        productos = ventas_controlador.obtener_productos_venta()
        productos_json = []
        
        for producto in productos:
            productos_json.append({
                'id': producto[0],
                'nombre': producto[1],
                'precio': float(producto[2]),
                'cantidad': producto[3],
                'imagen': producto[4] or ''
            })
        
        return jsonify({'productos': productos_json})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/procesar-venta', methods=['POST'])
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def procesar_venta_tienda():
    """Procesa una venta en tienda"""
    try:
        data = request.get_json()
        
        # Agregar ID del vendedor desde la sesión
        data['vendedor_id'] = session.get('user_id', 1)  # Usar 1 como fallback
        
        resultado = ventas_controlador.procesar_venta(data)
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/venta/<int:venta_id>/ticket')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def generar_ticket_venta(venta_id):
    """Genera un ticket para una venta"""
    try:
        venta = ventas_controlador.obtener_detalle_venta(venta_id)
        
        if not venta:
            flash('Venta no encontrada.', 'error')
            return redirect(url_for('punto_de_venta'))
        
        return render_template('ticket_venta.html', venta=venta)
        
    except Exception as e:
        flash(f'Error al generar ticket: {e}', 'error')
        return redirect(url_for('punto_de_venta'))
    """API para buscar productos disponibles para venta"""
    try:
        termino = request.args.get('q', '')
        categoria_id = request.args.get('categoria_id', type=int)
        
        productos = ventas_controlador.buscar_productos_para_venta(
            termino_busqueda=termino,
            categoria_id=categoria_id,
            limit=50
        )
        
        return jsonify({'productos': productos})
        
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/ventas/validar-stock', methods=['POST'])
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def validar_stock_venta():
    """API para validar stock antes de procesar venta"""
    try:
        data = request.get_json()
        productos = data.get('productos', [])
        
        if not productos:
            return jsonify({'valido': False, 'errores': ['No se proporcionaron productos']})
        
        validacion = ventas_controlador.validar_stock_productos(productos)
        return jsonify(validacion)
        
    except Exception as e:
        return jsonify({'valido': False, 'errores': [f'Error: {str(e)}']})

@app.route('/ventas/procesar', methods=['POST'])
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def procesar_venta():
    """Procesa una venta nueva"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        campos_requeridos = ['productos', 'metodo_pago']
        for campo in campos_requeridos:
            if campo not in data:
                return jsonify({'success': False, 'error': f'Campo {campo} es requerido'})
        
        # Agregar datos del vendedor desde la sesión
        data['vendedor_id'] = session.get('user_id', 1)  # Fallback a ID 1
        data['vendedor_nombre'] = session.get('usuario', 'Usuario')
        
        # Validar método de pago
        metodos_validos = ['efectivo', 'tarjeta', 'yape', 'multipago']
        if data['metodo_pago'] not in metodos_validos:
            return jsonify({'success': False, 'error': 'Método de pago no válido'})

        # Validaciones específicas por método de pago
        if data['metodo_pago'] == 'efectivo':
            if 'monto_recibido' not in data:
                return jsonify({'success': False, 'error': 'Monto recibido es requerido para efectivo'})

            # Preferir el total enviado por el cliente si existe; si no, calcularlo
            if 'total' in data and data['total'] is not None:
                try:
                    total_venta = float(data['total'])
                except Exception:
                    total_venta = ventas_controlador.calcular_totales_venta(data.get('productos', []))['total']
            else:
                total_venta = ventas_controlador.calcular_totales_venta(data.get('productos', []))['total']

            monto_recibido = float(data['monto_recibido'])
            # Añadir pequeña tolerancia por redondeos
            if monto_recibido + 0.0001 < total_venta:
                return jsonify({'success': False, 'error': 'Monto recibido insuficiente'})

            data['cambio_entregado'] = round(monto_recibido - total_venta, 2)
        
        elif data['metodo_pago'] in ['tarjeta', 'yape']:
            # For in-person (presencial) sales we allow tarjeta/yape without a stored reference.
            # If a referencia_pago is provided, keep it; otherwise normalize to empty string so
            # downstream code (registrar_venta) can always expect the key to exist.
            referencia = data.get('referencia_pago')
            if referencia is None:
                data['referencia_pago'] = ''
            else:
                # Trim any provided value
                try:
                    data['referencia_pago'] = str(referencia).strip()
                except Exception:
                    data['referencia_pago'] = ''

        elif data['metodo_pago'] == 'multipago':
            # Esperamos detalle_multipago con metodo1,monto1,metodo2,monto2
            detalle = data.get('detalle_multipago')
            if not detalle:
                return jsonify({'success': False, 'error': 'Detalle de multipago es requerido'})
            monto1 = float(detalle.get('monto1', 0))
            monto2 = float(detalle.get('monto2', 0))
            # Preferir total enviado por cliente si existe
            if 'total' in data and data['total'] is not None:
                try:
                    total_venta = float(data['total'])
                except Exception:
                    total_venta = ventas_controlador.calcular_totales_venta(data.get('productos', []))['total']
            else:
                total_venta = ventas_controlador.calcular_totales_venta(data.get('productos', []))['total']

            if (monto1 + monto2) + 0.0001 < total_venta:
                return jsonify({'success': False, 'error': 'Montos de multipago insuficientes'})
            data['cambio_entregado'] = round((monto1 + monto2) - total_venta, 2)
        
        # Registrar la venta
        resultado = ventas_controlador.registrar_venta(data)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'venta_id': resultado['venta_id'],
                'numero_venta': resultado['numero_venta'],
                'total': resultado['total'],
                'message': 'Venta registrada exitosamente'
            })
        else:
            return jsonify({'success': False, 'error': resultado['error']})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error procesando venta: {str(e)}'})

@app.route('/venta/<int:venta_id>/ticket')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def ticket_venta(venta_id):
    """Genera ticket de venta para impresión"""
    try:
        venta = ventas_controlador.obtener_venta_por_id(venta_id)
        
        if not venta:
            flash('Venta no encontrada.', 'error')
            return redirect(url_for('historial_ventas'))
        
        return render_template('ticket_venta.html', venta=venta)
        
    except Exception as e:
        flash(f'Error generando ticket: {e}', 'error')
        return redirect(url_for('historial_ventas'))

@app.route('/ventas/historial')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def historial_ventas():
    """Muestra el historial de ventas con filtros"""
    try:
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        vendedor_id = request.args.get('vendedor_id', type=int)
        metodo_pago = request.args.get('metodo_pago')
        estado = request.args.get('estado')
        pagina = request.args.get('pagina', 1, type=int)
        
        # Configurar paginación
        por_pagina = 20
        offset = (pagina - 1) * por_pagina
        
        # Obtener ventas filtradas
        ventas = ventas_controlador.obtener_ventas_por_fecha(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            vendedor_id=vendedor_id,
            metodo_pago=metodo_pago,
            estado=estado,
            limit=por_pagina,
            offset=offset
        )
        
        # Obtener estadísticas
        estadisticas = ventas_controlador.obtener_estadisticas_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return render_template('historial_ventas.html',
                             ventas=ventas,
                             estadisticas=estadisticas,
                             filtros={
                                 'fecha_inicio': fecha_inicio,
                                 'fecha_fin': fecha_fin,
                                 'vendedor_id': vendedor_id,
                                 'metodo_pago': metodo_pago,
                                 'estado': estado
                             },
                             pagina=pagina)
        
    except Exception as e:
        flash(f'Error cargando historial de ventas: {e}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/venta/<int:venta_id>/detalle')
@requiere_autenticacion(['admin', 'empleado', 'dueño'])
def detalle_venta(venta_id):
    """Muestra el detalle completo de una venta"""
    try:
        venta = ventas_controlador.obtener_venta_por_id(venta_id)
        
        if not venta:
            flash('Venta no encontrada.', 'error')
            return redirect(url_for('historial_ventas'))
        
        return render_template('detalle_venta.html', venta=venta)
        
    except Exception as e:
        flash(f'Error cargando detalle de venta: {e}', 'error')
        return redirect(url_for('historial_ventas'))


@app.route('/api/ventas/<int:venta_id>/cancelar', methods=['POST'])
@requiere_autenticacion(['admin', 'dueño'])
def api_cancelar_venta(venta_id):
    """API para anular una venta y reponer stock"""
    try:
        data = request.get_json(silent=True) or {}
        motivo = data.get('motivo') if isinstance(data, dict) else None
        usuario_id = session.get('user_id')
        resultado = ventas_controlador.cancelar_venta(venta_id, motivo=motivo, usuario_id=usuario_id)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ventas/estadisticas')
@requiere_autenticacion(['admin', 'dueño'])
def api_estadisticas_ventas():
    """API para obtener estadísticas de ventas"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        estadisticas = ventas_controlador.obtener_estadisticas_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        # Obtener productos más vendidos
        productos_mas_vendidos = ventas_controlador.obtener_productos_mas_vendidos(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=5
        )
        
        estadisticas['productos_mas_vendidos'] = productos_mas_vendidos
        
        return jsonify(estadisticas)
        
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
