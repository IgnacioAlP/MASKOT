#!/usr/bin/env python3
"""
Script de debug para verificar el estado de la sesión del usuario
"""

from bd import obtener_conexion

def verificar_usuario(username):
    """Verifica los datos de un usuario en la base de datos"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("SELECT id, username, rol, activo FROM usuarios WHERE username = %s", (username,))
        usuario = cursor.fetchone()
        
        if usuario:
            print(f"✅ Usuario encontrado:")
            print(f"   ID: {usuario[0]}")
            print(f"   Username: {usuario[1]}")
            print(f"   Rol: {usuario[2]}")
            print(f"   Activo: {'Sí' if usuario[3] else 'No'}")
            
            # Verificar permisos específicos
            permisos_citas = usuario[2] in ['admin', 'empleado', 'dueño']
            permisos_edicion = usuario[2] in ['admin', 'dueño']
            
            print(f"\n🔐 Permisos:")
            print(f"   Acceso a citas: {'✅ Sí' if permisos_citas else '❌ No'}")
            print(f"   Editar citas: {'✅ Sí' if permisos_edicion else '❌ No'}")
            
        else:
            print(f"❌ Usuario '{username}' no encontrado en la base de datos")
            
    except Exception as e:
        print(f"❌ Error al verificar usuario: {e}")
    finally:
        if 'conexion' in locals():
            conexion.close()

def listar_todos_usuarios():
    """Lista todos los usuarios en la base de datos"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("SELECT id, username, rol, activo FROM usuarios ORDER BY id")
        usuarios = cursor.fetchall()
        
        print("📋 Todos los usuarios en la base de datos:")
        print("-" * 50)
        for usuario in usuarios:
            estado = "Activo" if usuario[3] else "Inactivo"
            print(f"ID: {usuario[0]:2d} | {usuario[1]:15s} | {usuario[2]:10s} | {estado}")
            
    except Exception as e:
        print(f"❌ Error al listar usuarios: {e}")
    finally:
        if 'conexion' in locals():
            conexion.close()

if __name__ == "__main__":
    print("🔍 VERIFICACIÓN DE USUARIOS - SISTEMA MASKOT")
    print("=" * 50)
    
    # Listar todos los usuarios
    listar_todos_usuarios()
    
    print("\n" + "=" * 50)
    
    # Verificar usuario específico
    username = input("Ingresa el username que quieres verificar (o presiona Enter para 'admin_maskot'): ").strip()
    if not username:
        username = "admin_maskot"
    
    print(f"\n🔍 Verificando usuario: {username}")
    print("-" * 30)
    verificar_usuario(username)
    
    print("\n✅ Verificación completada")