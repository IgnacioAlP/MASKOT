import sys
import os
from datetime import date, timedelta

# Asegurar import desde la raiz del proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from controladores import citas_controlador, servicios_controlador, fidelizacion_controlador
from bd import obtener_conexion

TEST_EMAIL = 'testcliente@example.com'
TEST_NAME = 'Cliente Test'

# Obtener o crear un servicio para usar en las citas
def get_or_create_service():
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM servicios WHERE activo = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row[0]
            # Insertar servicio mínimo
            cursor.execute("INSERT INTO servicios (nombre, descripcion, max_citas, activo) VALUES (%s, %s, %s, 1)",
                           ('Servicio de prueba', 'Servicio creado para pruebas automatizadas', 50))
            service_id = cursor.lastrowid
            conexion.commit()
            return service_id
    finally:
        conexion.close()


def simulate(n=10):
    service_id = get_or_create_service()
    print('Usando servicio id=', service_id)

    for i in range(n):
        fecha = (date.today() + timedelta(days=i)).strftime('%Y-%m-%d')
        hora = '10:00'
        mascotas = [{'nombre': f'MascotaTest{i+1}', 'especie': 'perro'}]
        try:
            cita_id = citas_controlador.insertar_cita_completa(TEST_NAME, TEST_EMAIL, mascotas, [service_id], fecha, hora)
            print(f'[{i+1}] Cita creada: id={cita_id} fecha={fecha}')
        except Exception as e:
            print(f'[{i+1}] Error creando cita: {e}')
            continue

        # Llamar al controlador de fidelización tal como lo hace la app
        try:
            res = fidelizacion_controlador.procesar_fidelizacion_para_cliente(TEST_NAME, TEST_EMAIL)
            print(f'    Fidelizacion result: {res}')
        except Exception as e:
            print(f'    Error en fidelizacion: {e}')

    # Mostrar estado final de tablas
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            print('\nEstado tabla fidelizacion:')
            cursor.execute('SELECT cliente_email, cliente_nombre, contador, fecha_inicio, updated_at FROM fidelizacion WHERE cliente_email = %s', (TEST_EMAIL,))
            print(cursor.fetchall())

            print('\nÚltimos eventos en fidelizacion_historial:')
            cursor.execute('SELECT created_at, evento, descripcion FROM fidelizacion_historial WHERE cliente_email = %s ORDER BY created_at DESC LIMIT 20', (TEST_EMAIL,))
            for r in cursor.fetchall():
                print(r)
    finally:
        conexion.close()


if __name__ == '__main__':
    simulate(10)
