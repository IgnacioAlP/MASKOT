import sys
import os
import logging

# Añadir carpeta raíz del proyecto al path para poder importar `main` desde este subdirectorio
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import app

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('test_login')

# Ajustar entorno de testing
app.config['TESTING'] = True

# Credenciales de prueba - uso un usuario que sabemos existe en la BD
# Según la inspección, existen usuarios como 'admin_maskot' con password 'admin' (texto plano)
TEST_USERNAME = 'admin_maskot'
TEST_PASSWORD = 'admin'

with app.test_client() as client:
    # GET para obtener la página de login
    resp_get = client.get('/login')
    logger.info('GET /login -> status=%s', resp_get.status_code)

    # Postear credenciales
    resp = client.post('/login', data={
        'username': TEST_USERNAME,
        'password': TEST_PASSWORD
    }, follow_redirects=False)

    logger.info('POST /login -> status=%s', resp.status_code)
    logger.info('Location header: %s', resp.headers.get('Location'))

    # Si hay redirección (302), seguirla con follow_redirects=True para ver el HTML
    if resp.status_code in (301, 302) and resp.headers.get('Location'):
        location = resp.headers.get('Location')
        logger.info('Redirigiendo a: %s', location)
        resp_follow = client.get(location)
        logger.info('GET %s -> status=%s', location, resp_follow.status_code)
        logger.info('Content snippet: %s', resp_follow.get_data(as_text=True)[:500])
    else:
        # Mostrar fragmento del HTML devuelto (por ejemplo, página de login con flash)
        body = resp.get_data(as_text=True)
        logger.info('Respuesta POST body snippet: %s', body[:800])

print('Prueba terminada.')
