#!/usr/bin/env python3
"""
Script para verificar y crear las tablas relacionales necesarias
"""

from bd import obtener_conexion

def verificar_y_crear_tablas():
    """Verifica si existen las tablas relacionales y las crea si es necesario"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        print("🔍 Verificando estructura de la base de datos...")
        
        # Verificar qué tablas existen
        cursor.execute("SHOW TABLES")
        tablas_existentes = [tabla[0] for tabla in cursor.fetchall()]
        
        print(f"📋 Tablas existentes: {', '.join(tablas_existentes)}")
        
        tablas_necesarias = ['cita_mascotas', 'cita_servicios', 'mascotas', 'servicios']
        tablas_faltantes = [tabla for tabla in tablas_necesarias if tabla not in tablas_existentes]
        
        if tablas_faltantes:
            print(f"⚠️ Tablas faltantes: {', '.join(tablas_faltantes)}")
            
            # Crear tabla mascotas si no existe
            if 'mascotas' in tablas_faltantes:
                print("🔧 Creando tabla mascotas...")
                cursor.execute("""
                    CREATE TABLE `mascotas` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `cliente_id` int(11) DEFAULT NULL,
                        `nombre` varchar(100) NOT NULL,
                        `especie` varchar(50) NOT NULL,
                        `raza` varchar(100) DEFAULT NULL,
                        `edad` int(3) DEFAULT NULL,
                        `peso` decimal(5,2) DEFAULT NULL,
                        `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
                        `activo` tinyint(1) DEFAULT 1,
                        PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """)
                print("✅ Tabla mascotas creada")
            
            # Crear tabla cita_mascotas si no existe
            if 'cita_mascotas' in tablas_faltantes:
                print("🔧 Creando tabla cita_mascotas...")
                cursor.execute("""
                    CREATE TABLE `cita_mascotas` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `cita_id` int(11) NOT NULL,
                        `mascota_id` int(11) DEFAULT NULL,
                        `nombre` varchar(100) NOT NULL,
                        `especie` varchar(50) NOT NULL,
                        `raza` varchar(100) DEFAULT NULL,
                        `edad` int(3) DEFAULT NULL,
                        `peso` decimal(5,2) DEFAULT NULL,
                        PRIMARY KEY (`id`),
                        KEY `cita_id` (`cita_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """)
                print("✅ Tabla cita_mascotas creada")
            
            # Crear tabla cita_servicios si no existe
            if 'cita_servicios' in tablas_faltantes:
                print("🔧 Creando tabla cita_servicios...")
                cursor.execute("""
                    CREATE TABLE `cita_servicios` (
                        `id` int(11) NOT NULL AUTO_INCREMENT,
                        `cita_id` int(11) NOT NULL,
                        `servicio_id` int(11) NOT NULL,
                        PRIMARY KEY (`id`),
                        KEY `cita_id` (`cita_id`),
                        KEY `servicio_id` (`servicio_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
                """)
                print("✅ Tabla cita_servicios creada")
            
            conexion.commit()
            
        else:
            print("✅ Todas las tablas necesarias existen")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conexion' in locals():
            conexion.close()

def crear_datos_dummy_para_recibo():
    """Crea algunos datos de ejemplo para poder generar recibos"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        print("🔧 Creando datos de ejemplo para recibos...")
        
        # Obtener una cita de prueba
        cursor.execute("SELECT id FROM citas LIMIT 1")
        cita_result = cursor.fetchone()
        
        if not cita_result:
            print("⚠️ No hay citas disponibles")
            return False
            
        cita_id = cita_result[0]
        print(f"📋 Usando cita ID: {cita_id}")
        
        # Verificar si ya hay datos de mascotas para esta cita
        cursor.execute("SELECT COUNT(*) FROM cita_mascotas WHERE cita_id = %s", (cita_id,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Agregar una mascota de ejemplo
            cursor.execute("""
                INSERT INTO cita_mascotas (cita_id, nombre, especie, raza, edad, peso)
                VALUES (%s, 'Firulais', 'perro', 'Labrador', 3, 25.5)
            """, (cita_id,))
            print("🐕 Mascota de ejemplo agregada")
        
        # Verificar si hay servicios
        cursor.execute("SELECT COUNT(*) FROM servicios")
        servicios_count = cursor.fetchone()[0]
        
        if servicios_count == 0:
            # Crear algunos servicios de ejemplo
            cursor.execute("""
                INSERT INTO servicios (nombre, descripcion, precio) VALUES
                ('Consulta General', 'Consulta veterinaria básica', 50.00),
                ('Vacunación', 'Aplicación de vacunas', 30.00),
                ('Baño y Corte', 'Servicio de grooming completo', 40.00)
            """)
            print("💉 Servicios de ejemplo creados")
        
        # Agregar servicio a la cita
        cursor.execute("SELECT COUNT(*) FROM cita_servicios WHERE cita_id = %s", (cita_id,))
        servicios_cita_count = cursor.fetchone()[0]
        
        if servicios_cita_count == 0:
            cursor.execute("SELECT id FROM servicios LIMIT 1")
            servicio_result = cursor.fetchone()
            if servicio_result:
                cursor.execute("""
                    INSERT INTO cita_servicios (cita_id, servicio_id)
                    VALUES (%s, %s)
                """, (cita_id, servicio_result[0]))
                print("🛠️ Servicio vinculado a la cita")
        
        conexion.commit()
        print("✅ Datos de ejemplo creados exitosamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando datos: {e}")
        return False
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("🚀 Verificando y configurando base de datos...")
    if verificar_y_crear_tablas():
        crear_datos_dummy_para_recibo()
    print("🎉 Configuración completada")