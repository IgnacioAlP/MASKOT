"""
Configuración y utilidades para impresión de tickets en ticketeras
Optimizado para impresoras térmicas de 80mm
"""

def configuracion_ticketera():
    """
    Muestra la configuración recomendada para ticketeras
    """
    config = {
        "papel": {
            "tipo": "Térmico",
            "ancho": "80mm",
            "largo": "Continuo",
            "calidad": "Normal o Borrador"
        },
        "impresora": {
            "orientacion": "Vertical (Portrait)",
            "margenes": "Mínimos (1-3mm)",
            "tamaño_fuente": "Automático",
            "velocidad": "Alta",
            "densidad": "Media"
        },
        "software": {
            "navegador": "Chrome/Edge recomendado",
            "zoom": "100%",
            "modo_impresion": "Simplificado",
            "colores": "Solo negro"
        }
    }
    
    print("=" * 50)
    print("CONFIGURACIÓN RECOMENDADA PARA TICKETERA")
    print("=" * 50)
    
    for categoria, opciones in config.items():
        print(f"\n{categoria.upper()}:")
        for clave, valor in opciones.items():
            print(f"  • {clave.replace('_', ' ').title()}: {valor}")
    
    print("\n" + "=" * 50)
    print("PASOS PARA CONFIGURAR:")
    print("=" * 50)
    print("1. Instalar driver específico de tu ticketera")
    print("2. Configurar papel térmico 80mm en propiedades de impresora")
    print("3. Establecer márgenes mínimos (1-2mm)")
    print("4. Seleccionar calidad 'Borrador' para velocidad")
    print("5. Activar 'Ajustar al ancho de página'")
    print("6. Desactivar colores (solo negro)")
    print("7. Probar con ticket de prueba antes de imprimir facturas")
    
    return config

def generar_ticket_prueba():
    """
    Genera contenido HTML para ticket de prueba
    """
    html_prueba = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Ticket de Prueba - MASKOT</title>
        <style>
            @page {
                size: 80mm auto;
                margin: 2mm;
            }
            
            body {
                font-family: 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.2;
                margin: 0;
                padding: 2mm;
                width: 76mm;
            }
            
            .center { text-align: center; }
            .bold { font-weight: bold; }
            .separator { 
                border-top: 1px dashed #000;
                margin: 4mm 0;
            }
        </style>
    </head>
    <body>
        <div class="center bold">
            MASKOT VETERINARIA
        </div>
        <div class="center">
            Ticket de Prueba
        </div>
        
        <div class="separator"></div>
        
        <div>
            <strong>Fecha:</strong> $(fecha_actual)
            <br>
            <strong>Hora:</strong> $(hora_actual)
        </div>
        
        <div class="separator"></div>
        
        <div class="center">
            CONFIGURACIÓN DE IMPRESORA
        </div>
        
        <div>
            • Papel: 80mm térmico<br>
            • Orientación: Vertical<br>
            • Márgenes: 2mm<br>
            • Calidad: Normal<br>
        </div>
        
        <div class="separator"></div>
        
        <div class="center">
            Si este ticket se imprime correctamente,
            tu impresora está configurada.
        </div>
        
        <div class="separator"></div>
        
        <div class="center bold">
            ¡Configuración exitosa!
        </div>
        
        <div class="center">
            maskot@veterinaria.com
        </div>
    </body>
    </html>
    """
    
    # Reemplazar placeholders con datos actuales
    from datetime import datetime
    now = datetime.now()
    html_prueba = html_prueba.replace("$(fecha_actual)", now.strftime("%d/%m/%Y"))
    html_prueba = html_prueba.replace("$(hora_actual)", now.strftime("%H:%M:%S"))
    
    return html_prueba

def verificar_soporte_impresion():
    """
    Verifica si el entorno soporta impresión
    """
    print("\n" + "=" * 40)
    print("VERIFICACIÓN DE SOPORTE DE IMPRESIÓN")
    print("=" * 40)
    
    # Verificar sistema operativo
    import platform
    sistema = platform.system()
    print(f"Sistema operativo: {sistema}")
    
    if sistema == "Windows":
        print("✅ Windows detectado - Soporte completo para ticketeras")
        print("  Recomendación: Usar driver oficial del fabricante")
    elif sistema == "Darwin":  # macOS
        print("✅ macOS detectado - Soporte disponible")
        print("  Recomendación: Configurar como impresora genérica")
    elif sistema == "Linux":
        print("✅ Linux detectado - Soporte vía CUPS")
        print("  Recomendación: Instalar cups-pdf para pruebas")
    else:
        print("⚠️  Sistema no reconocido - Verificar soporte manual")
    
    # Verificar navegadores comunes
    print(f"\nNavegadores recomendados para impresión:")
    print("  • Google Chrome (mejor soporte)")
    print("  • Microsoft Edge")
    print("  • Mozilla Firefox (limitaciones en @page)")
    
    return True

def instrucciones_ticketera():
    """
    Muestra instrucciones específicas para diferentes marcas
    """
    marcas = {
        "EPSON": {
            "modelos": ["TM-T20", "TM-T82", "TM-T88"],
            "driver": "Epson Advanced Printer Driver",
            "configuracion": "Papel personalizado 80x297mm",
            "especial": "Activar 'Recibo' en tipo de documento"
        },
        "STAR": {
            "modelos": ["TSP100", "TSP650", "TSP700"],
            "driver": "Star CloudPRNT",
            "configuracion": "80mm Roll Paper",
            "especial": "Usar StarPRNT SDK para mejor compatibilidad"
        },
        "BIXOLON": {
            "modelos": ["SRP-330", "SRP-350", "SRP-275"],
            "driver": "Bixolon Unified POS Driver",
            "configuracion": "Receipt 80mm",
            "especial": "Configurar velocidad de impresión a 200mm/s"
        },
        "CITIZEN": {
            "modelos": ["CT-S310", "CT-S4000", "CT-E651"],
            "driver": "Citizen POS Driver",
            "configuracion": "80mm Paper Roll",
            "especial": "Habilitar corte automático si está disponible"
        }
    }
    
    print("\n" + "=" * 50)
    print("CONFIGURACIÓN POR MARCA DE TICKETERA")
    print("=" * 50)
    
    for marca, info in marcas.items():
        print(f"\n{marca}:")
        print(f"  Modelos comunes: {', '.join(info['modelos'])}")
        print(f"  Driver: {info['driver']}")
        print(f"  Configuración: {info['configuracion']}")
        print(f"  Nota especial: {info['especial']}")
    
    print(f"\n{'='*50}")
    print("CONFIGURACIÓN UNIVERSAL:")
    print("="*50)
    print("1. Agregar impresora como 'Impresora genérica/Texto'")
    print("2. Configurar papel personalizado: 80mm x 200mm")
    print("3. Márgenes: Superior 2mm, Inferior 5mm, Izq/Der 1mm")
    print("4. Fuente: Courier New, tamaño 10-12px")
    print("5. Probar con página de prueba antes de usar")

if __name__ == "__main__":
    print("UTILIDAD DE CONFIGURACIÓN PARA TICKETERAS")
    print("="*50)
    
    # Mostrar configuración
    configuracion_ticketera()
    
    # Verificar soporte
    verificar_soporte_impresion()
    
    # Mostrar instrucciones por marca
    instrucciones_ticketera()
    
    # Generar ticket de prueba
    print(f"\n{'='*50}")
    print("GENERANDO TICKET DE PRUEBA...")
    print("="*50)
    
    html_prueba = generar_ticket_prueba()
    
    # Guardar ticket de prueba
    with open("ticket_prueba.html", "w", encoding="utf-8") as f:
        f.write(html_prueba)
    
    print("✅ Ticket de prueba generado: ticket_prueba.html")
    print("📝 Abre este archivo en tu navegador e imprímelo para probar la configuración")
    
    print(f"\n{'='*50}")
    print("PRÓXIMOS PASOS:")
    print("="*50)
    print("1. Configurar tu ticketera según las instrucciones arriba")
    print("2. Imprimir ticket_prueba.html para verificar")
    print("3. Ajustar configuración si es necesario")
    print("4. Usar la aplicación para generar tickets reales")
    print("5. ¡Listo para usar!")