-- Datos de prueba para citas con múltiples mascotas y servicios
-- Ejecutar después de haber corrido database_updates.sql

-- Insertar clientes de prueba
INSERT INTO `clientes` (`id`, `nombre`, `email`, `telefono`, `direccion`, `fecha_registro`) VALUES
(1, 'María González', 'maria.gonzalez@email.com', '+51 987 654 321', 'Av. Los Rosales 123, San Isidro', '2024-01-15'),
(2, 'Carlos Rodríguez', 'carlos.rodriguez@email.com', '+51 965 432 109', 'Jr. Las Flores 456, Miraflores', '2024-02-20'),
(3, 'Ana Torres', 'ana.torres@email.com', '+51 923 456 789', 'Calle Los Pinos 789, San Borja', '2024-03-10'),
(4, 'Luis Mendoza', 'luis.mendoza@email.com', '+51 912 345 678', 'Av. Universitaria 321, Los Olivos', '2024-01-25'),
(5, 'Patricia Silva', 'patricia.silva@email.com', '+51 998 765 432', 'Jr. Libertad 654, Pueblo Libre', '2024-02-14');

-- Insertar mascotas de prueba
INSERT INTO `mascotas` (`id`, `cliente_id`, `nombre`, `especie`, `raza`, `edad`, `peso`, `genero`, `fecha_registro`) VALUES
(1, 1, 'Max', 'perro', 'Golden Retriever', 3, 28.5, 'macho', '2024-01-15'),
(2, 1, 'Luna', 'gato', 'Persa', 2, 4.2, 'hembra', '2024-01-15'),
(3, 2, 'Rocky', 'perro', 'Bulldog Francés', 4, 12.8, 'macho', '2024-02-20'),
(4, 2, 'Mimi', 'gato', 'Siamés', 1, 3.5, 'hembra', '2024-02-20'),
(5, 3, 'Buddy', 'perro', 'Labrador', 5, 32.0, 'macho', '2024-03-10'),
(6, 3, 'Bella', 'perro', 'Cocker Spaniel', 3, 15.2, 'hembra', '2024-03-10'),
(7, 4, 'Simba', 'gato', 'Maine Coon', 6, 7.8, 'macho', '2024-01-25'),
(8, 5, 'Lola', 'perro', 'Chihuahua', 2, 2.8, 'hembra', '2024-02-14'),
(9, 5, 'Coco', 'conejo', 'Holandés Enano', 1, 1.2, 'hembra', '2024-02-14');

-- Insertar citas de prueba
INSERT INTO `citas` (`id`, `cliente_id`, `cliente_nombre`, `cliente_email`, `fecha`, `hora`, `estado`, `observaciones`, `precio_total`) VALUES
(1, 1, 'María González', 'maria.gonzalez@email.com', '2024-10-01', '09:00:00', 'pendiente', 'Cita de rutina para ambas mascotas', 180.00),
(2, 2, 'Carlos Rodríguez', 'carlos.rodriguez@email.com', '2024-10-01', '10:30:00', 'pendiente', 'Revisión general y vacunación', 120.00),
(3, 3, 'Ana Torres', 'ana.torres@email.com', '2024-10-02', '14:00:00', 'completada', 'Grooming completo para ambos perros', 160.00),
(4, 4, 'Luis Mendoza', 'luis.mendoza@email.com', '2024-10-02', '11:15:00', 'pendiente', 'Solo limpieza dental', 80.00),
(5, 5, 'Patricia Silva', 'patricia.silva@email.com', '2024-10-03', '16:30:00', 'pendiente', 'Consulta para perro pequeño', 60.00),
(6, 1, 'María González', 'maria.gonzalez@email.com', '2024-10-04', '08:30:00', 'pendiente', 'Vacunación de refuerzo', 70.00),
(7, 3, 'Ana Torres', 'ana.torres@email.com', '2024-10-05', '15:45:00', 'cancelada', 'Cita cancelada por cliente', 0.00);

-- Relación citas con mascotas
INSERT INTO `citas_mascotas` (`cita_id`, `mascota_id`) VALUES
-- Cita 1: María con Max y Luna (2 mascotas)
(1, 1), (1, 2),
-- Cita 2: Carlos con Rocky y Mimi (2 mascotas)
(2, 3), (2, 4),
-- Cita 3: Ana con Buddy y Bella (2 mascotas)
(3, 5), (3, 6),
-- Cita 4: Luis con Simba (1 mascota)
(4, 7),
-- Cita 5: Patricia con Lola (1 mascota)
(5, 8),
-- Cita 6: María con Max (1 mascota)
(6, 1),
-- Cita 7: Ana con Buddy (1 mascota)
(7, 5);

-- Relación citas con servicios
INSERT INTO `citas_servicios` (`cita_id`, `servicio_id`, `precio`) VALUES
-- Cita 1: Consulta + Vacunación (2 servicios)
(1, 1, 90.00), (1, 2, 90.00),
-- Cita 2: Consulta + Grooming (2 servicios)  
(2, 1, 60.00), (2, 3, 60.00),
-- Cita 3: Grooming + Baño (2 servicios)
(3, 3, 80.00), (3, 4, 80.00),
-- Cita 4: Solo Limpieza Dental (1 servicio)
(4, 6, 80.00),
-- Cita 5: Solo Consulta (1 servicio)
(5, 1, 60.00),
-- Cita 6: Solo Vacunación (1 servicio)
(6, 2, 70.00),
-- Cita 7: Solo Consulta (1 servicio)
(7, 1, 60.00);

-- Insertar algunas citas adicionales con diferentes combinaciones
INSERT INTO `citas` (`id`, `cliente_id`, `cliente_nombre`, `cliente_email`, `fecha`, `hora`, `estado`, `observaciones`, `precio_total`) VALUES
(8, 2, 'Carlos Rodríguez', 'carlos.rodriguez@email.com', '2024-10-07', '09:30:00', 'pendiente', 'Esterilización + microchip para Rocky', 250.00),
(9, 5, 'Patricia Silva', 'patricia.silva@email.com', '2024-10-08', '14:15:00', 'pendiente', 'Consulta para ambas mascotas exóticas', 120.00),
(10, 1, 'María González', 'maria.gonzalez@email.com', '2024-10-10', '10:00:00', 'pendiente', 'Desparasitación completa', 140.00);

-- Más relaciones mascotas-citas
INSERT INTO `citas_mascotas` (`cita_id`, `mascota_id`) VALUES
-- Cita 8: Carlos con Rocky (1 mascota, 2 servicios)
(8, 3),
-- Cita 9: Patricia con Lola y Coco (2 mascotas, 1 servicio)
(9, 8), (9, 9),
-- Cita 10: María con Max y Luna (2 mascotas, 1 servicio)
(10, 1), (10, 2);

-- Más relaciones servicios-citas
INSERT INTO `citas_servicios` (`cita_id`, `servicio_id`, `precio`) VALUES
-- Cita 8: Esterilización + Microchip (2 servicios)
(8, 9, 200.00), (8, 10, 50.00),
-- Cita 9: Solo Consulta (1 servicio)
(9, 1, 120.00),
-- Cita 10: Solo Desparasitación (1 servicio)
(10, 7, 140.00);

-- Citas para fechas futuras (próximos días)
INSERT INTO `citas` (`id`, `cliente_id`, `cliente_nombre`, `cliente_email`, `fecha`, `hora`, `estado`, `observaciones`, `precio_total`) VALUES
(11, 4, 'Luis Mendoza', 'luis.mendoza@email.com', '2024-10-15', '11:00:00', 'pendiente', 'Cirugía menor programada', 300.00),
(12, 3, 'Ana Torres', 'ana.torres@email.com', '2024-10-16', '13:30:00', 'pendiente', 'Revisión post-grooming', 60.00);

-- Relaciones finales
INSERT INTO `citas_mascotas` (`cita_id`, `mascota_id`) VALUES
(11, 7), -- Luis con Simba
(12, 5); -- Ana con Buddy

INSERT INTO `citas_servicios` (`cita_id`, `servicio_id`, `precio`) VALUES
(11, 8, 300.00), -- Cirugía menor
(12, 1, 60.00);  -- Consulta

-- Comentarios explicativos de las combinaciones creadas:
/*
RESUMEN DE CITAS CREADAS:

1. 2 MASCOTAS + 2 SERVICIOS:
   - Cita 1: María (Max + Luna) → Consulta + Vacunación
   - Cita 2: Carlos (Rocky + Mimi) → Consulta + Grooming
   - Cita 3: Ana (Buddy + Bella) → Grooming + Baño

2. 1 MASCOTA + 2 SERVICIOS:
   - Cita 8: Carlos (Rocky) → Esterilización + Microchip

3. 2 MASCOTAS + 1 SERVICIO:
   - Cita 9: Patricia (Lola + Coco) → Consulta
   - Cita 10: María (Max + Luna) → Desparasitación

4. 1 MASCOTA + 1 SERVICIO:
   - Cita 4: Luis (Simba) → Limpieza Dental
   - Cita 5: Patricia (Lola) → Consulta
   - Cita 6: María (Max) → Vacunación
   - Cita 11: Luis (Simba) → Cirugía menor
   - Cita 12: Ana (Buddy) → Consulta

ESTADOS VARIADOS:
- Pendientes: La mayoría
- Completada: Cita 3
- Cancelada: Cita 7

FECHAS DISTRIBUIDAS:
- Octubre 2024 con diferentes fechas y horarios
- Incluye citas pasadas, actuales y futuras
*/