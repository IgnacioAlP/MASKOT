#!/usr/bin/env python3
"""
Script para crear la base de datos y ejecutar todos los scripts necesarios
"""
import mysql.connector
from mysql.connector import Error
import os

def crear_base_datos():
    """Crear la base de datos veterinaria si no existe"""
    try:
        print("🔌 Conectando a MySQL (sin base de datos específica)...")
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=''  # Cambiar si tienes password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Crear base de datos si no existe
            cursor.execute("CREATE DATABASE IF NOT EXISTS veterinaria")
            cursor.execute("USE veterinaria")
            print("✅ Base de datos 'veterinaria' creada/seleccionada")
            
            return connection, cursor
            
    except Error as e:
        print(f"❌ Error creando base de datos: {e}")
        return None, None

def ejecutar_script_sql(cursor, archivo_sql, descripcion=""):
    """Ejecuta un archivo SQL línea por línea"""
    try:
        print(f"\n📋 {descripcion}...")
        with open(archivo_sql, 'r', encoding='utf-8') as file:
            sql_script = file.read()
            
        # Dividir en comandos individuales
        comandos = []
        comando_actual = ""
        
        for linea in sql_script.split('\n'):
            linea = linea.strip()
            if not linea or linea.startswith('--'):
                continue
            
            comando_actual += linea + "\n"
            
            if linea.endswith(';'):
                comandos.append(comando_actual.strip())
                comando_actual = ""
        
        ejecutados = 0
        errores = 0
        
        for comando in comandos:
            if comando and not comando.startswith('/*'):
                try:
                    cursor.execute(comando)
                    ejecutados += 1
                    # Mostrar solo comandos importantes
                    if any(word in comando.upper() for word in ['CREATE TABLE', 'INSERT INTO', 'ALTER TABLE']):
                        cmd_preview = comando.split('\n')[0][:60]
                        print(f"✅ {cmd_preview}...")
                        
                except Error as e:
                    if any(phrase in str(e) for phrase in ["already exists", "Duplicate entry", "Unknown column"]):
                        # Errores esperados/no críticos
                        pass
                    else:
                        print(f"❌ Error: {str(e)[:100]}")
                        errores += 1
        
        print(f"📊 Ejecutados: {ejecutados}, Errores: {errores}")
        return errores == 0
        
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {archivo_sql}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def main():
    try:
        # Crear base de datos
        connection, cursor = crear_base_datos()
        if not connection:
            return
        
        # Lista de scripts a ejecutar en orden
        scripts = [
            ('bd.sql', 'Creando estructura básica de la BD'),
            ('database_updates.sql', 'Aplicando actualizaciones de BD'),
            ('datos_prueba_citas.sql', 'Insertando datos de prueba')
        ]
        
        for archivo, descripcion in scripts:
            if os.path.exists(archivo):
                if ejecutar_script_sql(cursor, archivo, descripcion):
                    connection.commit()
                    print(f"✅ {descripcion} - COMPLETADO")
                else:
                    print(f"⚠️  {descripcion} - CON ADVERTENCIAS")
                    connection.commit()  # Commit de cualquier manera
            else:
                print(f"⚠️  Archivo no encontrado: {archivo}")
        
        print("\n🎉 ¡Proceso completado!")
        print("\n📋 Verificando datos creados...")
        
        # Verificar algunos datos
        cursor.execute("SELECT COUNT(*) FROM clientes")
        clientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mascotas")
        mascotas = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM citas")
        citas = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM servicios")
        servicios = cursor.fetchone()[0]
        
        print(f"📊 Resumen:")
        print(f"   👥 Clientes: {clientes}")
        print(f"   🐕 Mascotas: {mascotas}")
        print(f"   📅 Citas: {citas}")
        print(f"   🔧 Servicios: {servicios}")
        
    except Error as e:
        print(f"❌ Error de MySQL: {e}")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 Conexión cerrada")

if __name__ == "__main__":
    main()