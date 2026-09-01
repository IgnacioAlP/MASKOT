from controladores.fidelizacion_controlador import sincronizar_fidelizacion_desde_citas, obtener_alertas_recientes

if __name__ == '__main__':
    print('Ejecutando sincronización...')
    sincronizar_fidelizacion_desde_citas()
    print('Sincronización completada. Mostrando alertas recientes:')
    alerts = obtener_alertas_recientes(limit=10)
    for a in alerts:
        print(a)