import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from controladores import usuarios_controlador
from main import app
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('create_test_user')

TEST_USERNAME = 'temp_test_user'
TEST_PASSWORD = 'testpass123'

try:
    # Crear usuario
    user_id = usuarios_controlador.insertar_usuario(TEST_USERNAME, TEST_PASSWORD, 'empleado')
    logger.info('Usuario de prueba creado con id=%s', user_id)

    # Intentar login usando test_client
    app.config['TESTING'] = True
    with app.test_client() as client:
        resp = client.post('/login', data={'username': TEST_USERNAME, 'password': TEST_PASSWORD}, follow_redirects=False)
        logger.info('POST /login -> status=%s', resp.status_code)
        logger.info('Location: %s', resp.headers.get('Location'))
        if resp.status_code in (301,302) and resp.headers.get('Location'):
            logger.info('Redirigido a %s', resp.headers.get('Location'))
        else:
            body = resp.get_data(as_text=True)
            logger.info('Body snippet: %s', body[:500])

finally:
    # Eliminar usuario de prueba si existe
    try:
        usuarios_controlador.eliminar_usuario(user_id)
        logger.info('Usuario de prueba eliminado: id=%s', user_id)
    except Exception as e:
        logger.exception('Error al eliminar usuario de prueba: %s', e)

print('Script create_and_test_user finalizado')
