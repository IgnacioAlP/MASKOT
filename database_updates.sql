-- Script para actualizar la base de datos con nuevas funcionalidades
-- Ejecutar en orden para agregar soporte a múltiples mascotas y servicios por cita

-- 1. Crear tabla clientes si no existe
CREATE TABLE IF NOT EXISTS `clientes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `direccion` text DEFAULT NULL,
  `documento` varchar(20) DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email_unique` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 2. Crear tabla mascotas
CREATE TABLE IF NOT EXISTS `mascotas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cliente_id` int(11) DEFAULT NULL,
  `nombre` varchar(100) NOT NULL,
  `especie` varchar(50) NOT NULL,
  `raza` varchar(100) DEFAULT NULL,
  `edad` int(3) DEFAULT NULL,
  `peso` decimal(5,2) DEFAULT NULL,
  `color` varchar(50) DEFAULT NULL,
  `genero` enum('macho','hembra') DEFAULT NULL,
  `esterilizado` tinyint(1) DEFAULT 0,
  `observaciones` text DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_cliente_id` (`cliente_id`),
  FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 3. Crear tabla intermedia para citas con múltiples mascotas
CREATE TABLE IF NOT EXISTS `citas_mascotas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cita_id` int(11) NOT NULL,
  `mascota_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cita_id` (`cita_id`),
  KEY `idx_mascota_id` (`mascota_id`),
  FOREIGN KEY (`cita_id`) REFERENCES `citas` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`mascota_id`) REFERENCES `mascotas` (`id`) ON DELETE CASCADE,
  UNIQUE KEY `cita_mascota_unique` (`cita_id`, `mascota_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 4. Crear tabla intermedia para citas con múltiples servicios
CREATE TABLE IF NOT EXISTS `citas_servicios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cita_id` int(11) NOT NULL,
  `servicio_id` int(11) NOT NULL,
  `precio` decimal(8,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cita_id` (`cita_id`),
  KEY `idx_servicio_id` (`servicio_id`),
  FOREIGN KEY (`cita_id`) REFERENCES `citas` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`servicio_id`) REFERENCES `servicios` (`id`) ON DELETE CASCADE,
  UNIQUE KEY `cita_servicio_unique` (`cita_id`, `servicio_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 5. Agregar nuevas columnas a la tabla citas si no existen
ALTER TABLE `citas` 
ADD COLUMN IF NOT EXISTS `cliente_id` int(11) DEFAULT NULL AFTER `id`,
ADD COLUMN IF NOT EXISTS `mascota_nombre` varchar(100) DEFAULT NULL AFTER `hora`,
ADD COLUMN IF NOT EXISTS `mascota_especie` varchar(50) DEFAULT NULL AFTER `mascota_nombre`,
ADD COLUMN IF NOT EXISTS `mascota_raza` varchar(100) DEFAULT NULL AFTER `mascota_especie`,
ADD COLUMN IF NOT EXISTS `mascota_edad` int(3) DEFAULT NULL AFTER `mascota_raza`,
ADD COLUMN IF NOT EXISTS `mascota_peso` decimal(5,2) DEFAULT NULL AFTER `mascota_edad`,
ADD COLUMN IF NOT EXISTS `observaciones` text DEFAULT NULL AFTER `mascota_peso`,
ADD COLUMN IF NOT EXISTS `precio_total` decimal(8,2) DEFAULT NULL AFTER `observaciones`;

-- 6. Crear índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS `idx_cliente_id` ON `citas` (`cliente_id`);
CREATE INDEX IF NOT EXISTS `idx_cliente_email` ON `citas` (`cliente_email`);
CREATE INDEX IF NOT EXISTS `idx_fecha_hora` ON `citas` (`fecha`, `hora`);

-- 7. Crear tabla para tarjetas de clientes (para el checkout)
CREATE TABLE IF NOT EXISTS `tarjetas_cliente` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cliente_id` int(11) NOT NULL,
  `numero_enmascarado` varchar(20) NOT NULL,
  `numero_hash` varchar(64) NOT NULL,
  `nombre_titular` varchar(100) NOT NULL,
  `expiracion` varchar(7) NOT NULL,
  `tipo_tarjeta` enum('credito','debito') NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_cliente_id` (`cliente_id`),
  FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 8. Crear tabla para pedidos (si no existe)
CREATE TABLE IF NOT EXISTS `pedidos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cliente_id` int(11) NOT NULL,
  `subtotal` decimal(8,2) NOT NULL,
  `igv` decimal(8,2) NOT NULL,
  `total` decimal(8,2) NOT NULL,
  `metodo_pago` enum('efectivo','tarjeta','transferencia') NOT NULL,
  `estado` enum('pendiente','pagado','enviado','entregado','cancelado') DEFAULT 'pendiente',
  `fecha_pedido` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_pago` timestamp NULL DEFAULT NULL,
  `fecha_entrega` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cliente_id` (`cliente_id`),
  KEY `idx_estado` (`estado`),
  FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 9. Crear tabla para detalle de pedidos
CREATE TABLE IF NOT EXISTS `detalle_pedidos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pedido_id` int(11) NOT NULL,
  `producto_id` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precio_unitario` decimal(8,2) NOT NULL,
  `subtotal` decimal(8,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_pedido_id` (`pedido_id`),
  KEY `idx_producto_id` (`producto_id`),
  FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Comando para ejecutar: mysql -u root -p veterinaria < database_updates.sql