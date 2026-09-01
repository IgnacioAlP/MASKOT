#!/usr/bin/env python3
"""
Script para ejecutar las actualizaciones de la base de datos y los datos de prueba
"""
import mysql.connector
from mysql.connector import Error
import os
import sys

def ejecutar_script_sql(cursor, archivo_sql):
    """Ejecuta un archivo SQL línea por línea"""
    try:
        with open(archivo_sql, 'r', encoding='utf-8') as file:
            sql_script = file.read()
            
        # Dividir en comandos individuales (por punto y coma)
        comandos = [cmd.strip() for cmd in sql_script.split(';') if cmd.strip()]
        
        ejecutados = 0
        for comando in comandos:
            if comando and not comando.startswith('--') and not comando.startswith('/*'):
                try:
                    cursor.execute(comando)
                    ejecutados += 1
                    print(f"✅ Comando ejecutado: {comando[:50]}...")
                except Error as e:
                    if "already exists" in str(e) or "Duplicate entry" in str(e):
                        print(f"⚠️  Ya existe: {comando[:50]}...")
                    else:
                        print(f"❌ Error en comando: {comando[:50]}...")
                        print(f"   Error: {e}")
        
        print(f"📊 Total comandos ejecutados: {ejecutados}")
        return True
        
    except FileNotFoundError:
        print(f"❌ Archivo no encontrado: {archivo_sql}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False

def main():
    try:
        # Configuración de conexión
        print("🔌 Conectando a MySQL...")
        connection = mysql.connector.connect(
            host='localhost',
            database='veterinaria',
            user='root',
            password=''  # Cambiar si tienes password
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            print("✅ Conexión exitosa a MySQL")
            
            # Ejecutar script de actualización de BD
            print("\n📋 Ejecutando actualizaciones de base de datos...")
            if ejecutar_script_sql(cursor, 'database_updates.sql'):
                connection.commit()
                print("✅ Actualizaciones de BD aplicadas")
            
            # Ejecutar datos de prueba
            print("\n📋 Insertando datos de prueba...")
            if ejecutar_script_sql(cursor, 'datos_prueba_citas.sql'):
                connection.commit()
                print("✅ Datos de prueba insertados")
            
            print("\n🎉 ¡Scripts ejecutados exitosamente!")
            
    except Error as e:
        print(f"❌ Error de MySQL: {e}")
        if "Access denied" in str(e):
            print("💡 Tip: Verifica el usuario y password de MySQL")
        elif "Unknown database" in str(e):
            print("💡 Tip: Asegúrate de que la base de datos 'veterinaria' exista")
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 Conexión cerrada")

if __name__ == "__main__":
    main()