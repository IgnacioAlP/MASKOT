from bd import obtener_conexion, obtener_tenant_id
from datetime import datetime

def obtener_personal_por_usuario_id(usuario_id):
    """Obtiene información del personal por usuario_id"""
    conexion = obtener_conexion()
    personal = None
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id, usuario_id, cargo, salario, activo
            FROM personal 
            WHERE usuario_id = %s
        """, (usuario_id,))
        personal = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(f"Error al obtener personal por usuario_id: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return personal

def insertar_personal(usuario_id, cargo, salario):
    """Inserta nuevo registro en personal"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO personal (usuario_id, cargo, salario, activo, tenant_id)
            VALUES (%s, %s, %s, TRUE, %s)
        """, (usuario_id, cargo, salario, tenant_id))
        conexion.commit()
        personal_id = cursor.lastrowid
        cursor.close()
        return personal_id
    except Exception as e:
        conexion.rollback()
        print(f"Error al insertar personal: {e}")
        if 'cursor' in locals():
            cursor.close()
        return None
    finally:
        conexion.close()

def obtener_empleados():
    """Obtiene todos los empleados registrados"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    empleados = []
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT p.id, p.usuario_id, u.username, p.cargo, p.salario, p.activo, u.rol
            FROM personal p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.tenant_id = %s
            ORDER BY u.username
        """, (tenant_id,))
        empleados = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Error al obtener empleados: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return empleados

def obtener_empleado_por_id(personal_id):
    """Obtiene un empleado específico por su ID de personal"""
    conexion = obtener_conexion()
    empleado = None
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT p.id, p.usuario_id, u.username, p.cargo, p.salario, p.activo, u.rol
            FROM personal p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.id = %s
        """, (personal_id,))
        empleado = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(f"Error al obtener empleado por ID: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return empleado

def actualizar_empleado(personal_id, cargo, salario):
    """Actualiza la información de un empleado"""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE personal 
            SET cargo = %s, salario = %s
            WHERE id = %s
        """, (cargo, salario, personal_id))
        conexion.commit()
        cursor.close()
        return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al actualizar empleado: {e}")
        if 'cursor' in locals():
            cursor.close()
        return False
    finally:
        conexion.close()

def desactivar_empleado(personal_id):
    """Desactiva un empleado (baja lógica)"""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE personal 
            SET activo = FALSE 
            WHERE id = %s
        """, (personal_id,))
        conexion.commit()
        cursor.close()
        return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al desactivar empleado: {e}")
        if 'cursor' in locals():
            cursor.close()
        return False
    finally:
        conexion.close()

def activar_empleado(personal_id):
    """Reactiva un empleado"""
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE personal 
            SET activo = TRUE 
            WHERE id = %s
        """, (personal_id,))
        conexion.commit()
        cursor.close()
        return True
    except Exception as e:
        conexion.rollback()
        print(f"Error al activar empleado: {e}")
        if 'cursor' in locals():
            cursor.close()
        return False
    finally:
        conexion.close()

def obtener_empleados_activos():
    """Obtiene solo los empleados activos"""
    conexion = obtener_conexion()
    tenant_id = obtener_tenant_id()
    empleados = []
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT p.id, u.username, p.cargo, p.salario
            FROM personal p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.activo = TRUE AND p.tenant_id = %s
            ORDER BY u.username
        """, (tenant_id,))
        empleados = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Error al obtener empleados activos: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return empleados

def buscar_empleados_por_cargo(cargo):
    """Busca empleados por cargo específico"""
    conexion = obtener_conexion()
    empleados = []
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT p.id, u.username, p.cargo, p.salario, p.activo
            FROM personal p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.cargo LIKE %s AND p.activo = TRUE
            ORDER BY u.username
        """, (f'%{cargo}%',))
        empleados = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Error al buscar empleados por cargo: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return empleados

def obtener_estadisticas_personal():
    """Obtiene estadísticas generales del personal"""
    conexion = obtener_conexion()
    estadisticas = {}
    try:
        cursor = conexion.cursor()
        # Total empleados activos
        cursor.execute("SELECT COUNT(*) FROM personal WHERE activo = TRUE")
        estadisticas['total_activos'] = cursor.fetchone()[0]
        
        # Total empleados inactivos
        cursor.execute("SELECT COUNT(*) FROM personal WHERE activo = FALSE")
        estadisticas['total_inactivos'] = cursor.fetchone()[0]
        
        # Empleados por cargo
        cursor.execute("""
            SELECT cargo, COUNT(*) as cantidad
            FROM personal 
            WHERE activo = TRUE
            GROUP BY cargo
            ORDER BY cantidad DESC
        """)
        estadisticas['por_cargo'] = cursor.fetchall()
        
        # Salario promedio
        cursor.execute("""
            SELECT AVG(salario) as salario_promedio
            FROM personal 
            WHERE activo = TRUE
        """)
        resultado = cursor.fetchone()
        estadisticas['salario_promedio'] = float(resultado[0]) if resultado[0] else 0
        
        cursor.close()
    except Exception as e:
        print(f"Error al obtener estadísticas: {e}")
        if 'cursor' in locals():
            cursor.close()
    finally:
        conexion.close()
    return estadisticas
