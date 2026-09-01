-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Sep 29, 2025 at 05:22 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `veterinaria`
--

-- --------------------------------------------------------

--
-- Table structure for table `asistencia`
--

CREATE TABLE `asistencia` (
  `id` int(11) NOT NULL,
  `personal_id` int(11) DEFAULT NULL,
  `fecha` date NOT NULL,
  `hora_entrada` time DEFAULT NULL,
  `hora_salida` time DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `citas`
--

CREATE TABLE `citas` (
  `id` int(11) NOT NULL,
  `cliente_id` int(11) DEFAULT NULL,
  `cliente_nombre` varchar(100) NOT NULL,
  `cliente_email` varchar(100) DEFAULT NULL,
  `cliente_telefono` varchar(20) DEFAULT NULL,
  `servicio_id` int(11) DEFAULT NULL,
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  `mascota_nombre` varchar(100) DEFAULT NULL,
  `mascota_especie` varchar(50) DEFAULT NULL,
  `mascota_raza` varchar(100) DEFAULT NULL,
  `mascota_edad` int(3) DEFAULT NULL,
  `mascota_peso` decimal(5,2) DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  `precio_total` decimal(8,2) DEFAULT NULL,
  `estado` enum('pendiente','completada','cancelada') DEFAULT 'pendiente',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `citas`
--

INSERT INTO `citas` (`id`, `cliente_id`, `cliente_nombre`, `cliente_email`, `cliente_telefono`, `servicio_id`, `fecha`, `hora`, `mascota_nombre`, `mascota_especie`, `mascota_raza`, `mascota_edad`, `mascota_peso`, `observaciones`, `precio_total`, `estado`, `created_at`) VALUES
(1, 1, 'María González', 'maria.gonzalez@email.com', NULL, NULL, '2024-10-01', '09:00:00', NULL, NULL, NULL, NULL, NULL, 'Cita de rutina para ambas mascotas', 180.00, 'pendiente', '2025-09-28 23:41:45'),
(2, 2, 'Carlos Rodríguez', 'carlos.rodriguez@email.com', NULL, NULL, '2024-10-01', '10:30:00', NULL, NULL, NULL, NULL, NULL, 'Revisión general y vacunación', 120.00, 'pendiente', '2025-09-28 23:41:45'),
(3, 3, 'Ana Torres', 'ana.torres@email.com', NULL, NULL, '2024-10-02', '14:00:00', NULL, NULL, NULL, NULL, NULL, 'Grooming completo para ambos perros', 160.00, 'completada', '2025-09-28 23:41:45'),
(4, 4, 'Luis Mendoza', 'luis.mendoza@email.com', NULL, NULL, '2024-10-02', '11:15:00', NULL, NULL, NULL, NULL, NULL, 'Solo limpieza dental', 80.00, 'pendiente', '2025-09-28 23:41:45'),
(5, 5, 'Patricia Silva', 'patricia.silva@email.com', NULL, NULL, '2024-10-03', '16:30:00', NULL, NULL, NULL, NULL, NULL, 'Consulta para perro pequeño', 60.00, 'pendiente', '2025-09-28 23:41:45'),
(6, 1, 'María González', 'maria.gonzalez@email.com', NULL, NULL, '2024-10-04', '08:30:00', NULL, NULL, NULL, NULL, NULL, 'Vacunación de refuerzo', 70.00, 'pendiente', '2025-09-28 23:41:45'),
(7, 3, 'Ana Torres', 'ana.torres@email.com', NULL, NULL, '2024-10-05', '15:45:00', NULL, NULL, NULL, NULL, NULL, 'Cita cancelada por cliente', 0.00, 'cancelada', '2025-09-28 23:41:45'),
(8, 2, 'Carlos Rodríguez', 'carlos.rodriguez@email.com', NULL, NULL, '2024-10-07', '09:30:00', NULL, NULL, NULL, NULL, NULL, 'Esterilización + microchip para Rocky', 250.00, 'pendiente', '2025-09-28 23:41:46'),
(9, 5, 'Patricia Silva', 'patricia.silva@email.com', NULL, NULL, '2024-10-08', '14:15:00', NULL, NULL, NULL, NULL, NULL, 'Consulta para ambas mascotas exóticas', 120.00, 'pendiente', '2025-09-28 23:41:46'),
(10, 1, 'María González', 'maria.gonzalez@email.com', NULL, NULL, '2024-10-10', '10:00:00', NULL, NULL, NULL, NULL, NULL, 'Desparasitación completa', 140.00, 'pendiente', '2025-09-28 23:41:46'),
(11, 4, 'Luis Mendoza', 'luis.mendoza@email.com', NULL, NULL, '2024-10-15', '11:00:00', NULL, NULL, NULL, NULL, NULL, 'Cirugía menor programada', 300.00, 'pendiente', '2025-09-28 23:41:46'),
(12, 3, 'Ana Torres', 'ana.torres@email.com', NULL, NULL, '2024-10-16', '13:30:00', NULL, NULL, NULL, NULL, NULL, 'Revisión post-grooming', 60.00, 'pendiente', '2025-09-28 23:41:46'),
(13, NULL, 'María González', 'maria.gonzalez@email.com', NULL, 1, '2025-09-28', '10:30:00', 'Max', 'perro', 'Labrador', 5, 28.50, '', 0.00, 'pendiente', '2025-09-29 01:17:54'),
(14, NULL, 'Carlos Ruiz', 'carlos.ruiz@email.com', NULL, 2, '2025-09-28', '14:15:00', 'Luna', 'gato', 'Siamés', 3, 4.20, NULL, NULL, 'pendiente', '2025-09-29 01:17:54'),
(15, 6, 'Ignacio Alonzo', 'alonzopezoi@gmail.com', NULL, NULL, '2025-09-30', '20:40:00', NULL, NULL, NULL, NULL, NULL, '', NULL, 'pendiente', '2025-09-29 01:38:47');

-- --------------------------------------------------------

--
-- Table structure for table `citas_mascotas`
--

CREATE TABLE `citas_mascotas` (
  `id` int(11) NOT NULL,
  `cita_id` int(11) NOT NULL,
  `mascota_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `citas_mascotas`
--

INSERT INTO `citas_mascotas` (`id`, `cita_id`, `mascota_id`) VALUES
(1, 1, 1),
(2, 1, 2),
(3, 2, 3),
(4, 2, 4),
(5, 3, 5),
(6, 3, 6),
(7, 4, 7),
(8, 5, 8),
(9, 6, 1),
(10, 7, 5),
(11, 8, 3),
(12, 9, 8),
(13, 9, 9),
(14, 10, 1),
(15, 10, 2),
(16, 15, 10),
(17, 15, 11);

-- --------------------------------------------------------

--
-- Table structure for table `citas_servicios`
--

CREATE TABLE `citas_servicios` (
  `id` int(11) NOT NULL,
  `cita_id` int(11) NOT NULL,
  `servicio_id` int(11) NOT NULL,
  `precio` decimal(8,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `citas_servicios`
--

INSERT INTO `citas_servicios` (`id`, `cita_id`, `servicio_id`, `precio`) VALUES
(1, 1, 1, 90.00),
(2, 1, 2, 90.00),
(3, 2, 1, 60.00),
(4, 2, 3, 60.00),
(5, 3, 3, 80.00),
(6, 3, 4, 80.00),
(7, 4, 6, 80.00),
(8, 5, 1, 60.00),
(9, 6, 2, 70.00),
(10, 7, 1, 60.00),
(11, 8, 9, 200.00),
(12, 8, 10, 50.00),
(13, 9, 1, 120.00),
(14, 10, 7, 140.00),
(15, 15, 4, NULL),
(16, 15, 5, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `clientes`
--

CREATE TABLE `clientes` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `direccion` text DEFAULT NULL,
  `documento` varchar(20) DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `clientes`
--

INSERT INTO `clientes` (`id`, `nombre`, `email`, `telefono`, `direccion`, `documento`, `fecha_registro`, `activo`) VALUES
(1, 'María González', 'maria.gonzalez@email.com', '+51 987 654 321', 'Av. Los Rosales 123, San Isidro', NULL, '2024-01-15 05:00:00', 1),
(2, 'Carlos Rodríguez', 'carlos.rodriguez@email.com', '+51 965 432 109', 'Jr. Las Flores 456, Miraflores', NULL, '2024-02-20 05:00:00', 1),
(3, 'Ana Torres', 'ana.torres@email.com', '+51 923 456 789', 'La coruña 377, La Molina', NULL, '2024-03-10 05:00:00', 1),
(4, 'Luis Mendoza', 'luis.mendoza@email.com', '+51 912 345 678', 'Av. Universitaria 321, Los Olivos', NULL, '2024-01-25 05:00:00', 1),
(5, 'Patricia Silva', 'patricia.silva@email.com', '+51 998 765 432', 'Jr. Libertad 654, Pueblo Libre', NULL, '2024-02-14 05:00:00', 1),
(6, 'Ignacio Alonzo', 'alonzopezoi@gmail.com', NULL, NULL, NULL, '2025-09-29 01:38:47', 1);

-- --------------------------------------------------------

--
-- Table structure for table `detalle_pedidos`
--

CREATE TABLE `detalle_pedidos` (
  `id` int(11) NOT NULL,
  `pedido_id` int(11) NOT NULL,
  `producto_id` int(11) NOT NULL,
  `cantidad` int(11) NOT NULL,
  `precio_unitario` decimal(8,2) NOT NULL,
  `subtotal` decimal(8,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `mascotas`
--

CREATE TABLE `mascotas` (
  `id` int(11) NOT NULL,
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
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `mascotas`
--

INSERT INTO `mascotas` (`id`, `cliente_id`, `nombre`, `especie`, `raza`, `edad`, `peso`, `color`, `genero`, `esterilizado`, `observaciones`, `fecha_registro`, `activo`) VALUES
(1, 1, 'Max', 'perro', 'Golden Retriever', 3, 28.50, NULL, 'macho', 0, NULL, '2024-01-15 05:00:00', 1),
(2, 1, 'Luna', 'gato', 'Persa', 2, 4.20, NULL, 'hembra', 0, NULL, '2024-01-15 05:00:00', 1),
(3, 2, 'Rocky', 'perro', 'Bulldog Francés', 4, 12.80, NULL, 'macho', 0, NULL, '2024-02-20 05:00:00', 1),
(4, 2, 'Mimi', 'gato', 'Siamés', 1, 3.50, NULL, 'hembra', 0, NULL, '2024-02-20 05:00:00', 1),
(5, 3, 'Buddy', 'perro', 'Labrador', 5, 32.00, NULL, 'macho', 0, NULL, '2024-03-10 05:00:00', 1),
(6, 3, 'Bella', 'perro', 'Cocker Spaniel', 3, 15.20, NULL, 'hembra', 0, NULL, '2024-03-10 05:00:00', 1),
(7, 4, 'Simba', 'gato', 'Maine Coon', 6, 7.80, NULL, 'macho', 0, NULL, '2024-01-25 05:00:00', 1),
(8, 5, 'Lola', 'perro', 'Chihuahua', 2, 2.80, NULL, 'hembra', 0, NULL, '2024-02-14 05:00:00', 1),
(9, 5, 'Coco', 'conejo', 'Holandés Enano', 1, 1.20, NULL, 'hembra', 0, NULL, '2024-02-14 05:00:00', 1),
(10, 6, 'Bongo', 'perro', NULL, 11, NULL, NULL, NULL, 0, NULL, '2025-09-29 01:38:47', 1),
(11, 6, 'pinky', 'perro', NULL, 2, NULL, NULL, NULL, 0, NULL, '2025-09-29 01:38:47', 1);

-- --------------------------------------------------------

--
-- Table structure for table `pedidos`
--

CREATE TABLE `pedidos` (
  `id` int(11) NOT NULL,
  `cliente_id` int(11) NOT NULL,
  `subtotal` decimal(8,2) NOT NULL,
  `igv` decimal(8,2) NOT NULL,
  `total` decimal(8,2) NOT NULL,
  `metodo_pago` enum('efectivo','tarjeta','transferencia') NOT NULL,
  `estado` enum('pendiente','pagado','enviado','entregado','cancelado') DEFAULT 'pendiente',
  `fecha_pedido` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_pago` timestamp NULL DEFAULT NULL,
  `fecha_entrega` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `personal`
--

CREATE TABLE `personal` (
  `id` int(11) NOT NULL,
  `usuario_id` int(11) DEFAULT NULL,
  `cargo` varchar(50) DEFAULT NULL,
  `salario` decimal(10,2) DEFAULT NULL,
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `personal`
--

INSERT INTO `personal` (`id`, `usuario_id`, `cargo`, `salario`, `activo`) VALUES
(1, 7, 'Administrador', 0.00, 1);

-- --------------------------------------------------------

--
-- Table structure for table `productos`
--

CREATE TABLE `productos` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `tipo` enum('stock','venta') DEFAULT 'stock',
  `cantidad` int(11) DEFAULT 0,
  `stock_min` int(11) DEFAULT 0,
  `fecha_vencimiento` date DEFAULT NULL,
  `imagen` varchar(255) DEFAULT NULL,
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `productos`
--

INSERT INTO `productos` (`id`, `nombre`, `tipo`, `cantidad`, `stock_min`, `fecha_vencimiento`, `imagen`, `activo`) VALUES
(1, 'Alimento Premium Perro Adulto 15kg', 'venta', 25, 5, '2026-08-15', NULL, 1),
(2, 'Alimento Premium Gato Adulto 7.5kg', 'venta', 18, 4, '2026-07-22', NULL, 1),
(3, 'Collar Antipulgas y Garrapatas', 'venta', 30, 8, '2027-01-10', NULL, 1),
(4, 'Juguete Kong Clásico', 'venta', 15, 3, NULL, NULL, 1),
(5, 'Correa Retráctil 5m', 'venta', 12, 2, NULL, NULL, 1),
(6, 'Cama Ortopédica para Perros', 'venta', 8, 2, NULL, NULL, 1),
(7, 'Arena para Gatos Aglomerante 10kg', 'venta', 22, 5, NULL, NULL, 1),
(8, 'Shampoo Medicado Antipulgas', 'venta', 20, 4, '2026-12-30', NULL, 1),
(9, 'Vitaminas para Mascotas', 'venta', 35, 8, '2026-11-15', NULL, 1),
(10, 'Transportadora Mediana', 'venta', 6, 1, NULL, NULL, 1),
(11, 'Vacuna Triple Canina', 'stock', 50, 10, '2025-12-31', NULL, 1),
(12, 'Vacuna Triple Felina', 'stock', 35, 8, '2025-11-28', NULL, 1),
(13, 'Antibiótico Amoxicilina 500mg', 'stock', 100, 20, '2026-06-15', NULL, 1),
(14, 'Desparasitante Interno Perros', 'stock', 80, 15, '2026-09-30', NULL, 1),
(15, 'Anestesia Local Lidocaína', 'stock', 25, 5, '2025-10-22', NULL, 1),
(16, 'Suero Fisiológico 500ml', 'stock', 60, 12, '2026-03-18', NULL, 1),
(17, 'Gasas Estériles', 'stock', 200, 40, NULL, NULL, 1),
(18, 'Jeringas Desechables 5ml', 'stock', 500, 100, NULL, NULL, 1),
(19, 'Guantes Látex (Caja 100)', 'stock', 15, 3, NULL, NULL, 1),
(20, 'Vendas Elásticas', 'stock', 50, 10, NULL, NULL, 1);

-- --------------------------------------------------------

--
-- Table structure for table `servicios`
--

CREATE TABLE `servicios` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `max_citas_dia` int(11) DEFAULT 10,
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `servicios`
--

INSERT INTO `servicios` (`id`, `nombre`, `descripcion`, `max_citas_dia`, `activo`) VALUES
(1, 'Consulta Veterinaria', 'Revisión general del estado de salud de tu mascota', 8, 1),
(2, 'Vacunación', 'Aplicación de vacunas preventivas según calendario', 12, 1),
(3, 'Grooming Completo', 'Baño, corte, limpieza de oídos y corte de uñas', 6, 1),
(4, 'Baño y Secado', 'Baño con productos especializados y secado profesional', 10, 1),
(5, 'Corte de Uñas', 'Corte profesional de uñas para perros y gatos', 15, 1),
(6, 'Limpieza Dental', 'Limpieza profesional de dientes y encías', 4, 1),
(7, 'Desparasitación', 'Tratamiento antiparasitario interno y externo', 8, 1),
(8, 'Cirugía Menor', 'Procedimientos quirúrgicos ambulatorios', 2, 1),
(9, 'Esterilización', 'Cirugía de esterilización para machos y hembras', 3, 1),
(10, 'Microchip', 'Implantación de microchip de identificación', 6, 1);

-- --------------------------------------------------------

--
-- Table structure for table `tarjetas_cliente`
--

CREATE TABLE `tarjetas_cliente` (
  `id` int(11) NOT NULL,
  `cliente_id` int(11) NOT NULL,
  `numero_enmascarado` varchar(20) NOT NULL,
  `numero_hash` varchar(64) NOT NULL,
  `nombre_titular` varchar(100) NOT NULL,
  `expiracion` varchar(7) NOT NULL,
  `tipo_tarjeta` enum('credito','debito') NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `rol` enum('cliente','dueño','admin','empleado') NOT NULL,
  `activo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `usuarios`
--

INSERT INTO `usuarios` (`id`, `username`, `password`, `rol`, `activo`, `created_at`) VALUES
(2, 'admin_sistema', '$2b$12$8vJ2K1qR3nZ7wX5fL8tY9OeUvWzP4mH6jN8cQ2aB1rS5dT9gF3kL7', 'admin', 1, '2025-09-24 11:54:36'),
(3, 'carlos_vet', '$2b$12$9kM3L2pS4nA8xV6gM9uZ0PfVwXzQ5mI7kO9dR3bC2tU6eY8hG4mN8', 'empleado', 1, '2025-09-24 11:54:36'),
(4, 'maria_grooming', '$2b$12$7hN4M3qT5oB9yW7hN0vA1QgVxYzR6nJ8lP0eS4cD3uV7fZ9iH5oO9', 'empleado', 1, '2025-09-24 11:54:36'),
(5, 'sofia_recepcion', '$2b$12$6jO5N4rU6pC0zX8jO1wB2RhWyZzS7oK9mQ1fT5dE4vW8gA0jI6pP0', 'empleado', 1, '2025-09-24 11:54:36'),
(6, 'luis_asistente', '$2b$12$5iP6O5sV7qD1aY9kP2xC3SiXzAzT8pL0nR2gU6eF5wX9hB1kJ7qQ1', 'empleado', 1, '2025-09-24 11:54:36'),
(7, 'admin_maskot', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin', 1, '2025-09-24 13:05:39');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `asistencia`
--
ALTER TABLE `asistencia`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_asistencia` (`personal_id`,`fecha`);

--
-- Indexes for table `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `servicio_id` (`servicio_id`),
  ADD KEY `idx_cliente_id` (`cliente_id`),
  ADD KEY `idx_cliente_email` (`cliente_email`),
  ADD KEY `idx_fecha_hora` (`fecha`,`hora`);

--
-- Indexes for table `citas_mascotas`
--
ALTER TABLE `citas_mascotas`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `cita_mascota_unique` (`cita_id`,`mascota_id`),
  ADD KEY `idx_cita_id` (`cita_id`),
  ADD KEY `idx_mascota_id` (`mascota_id`);

--
-- Indexes for table `citas_servicios`
--
ALTER TABLE `citas_servicios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `cita_servicio_unique` (`cita_id`,`servicio_id`),
  ADD KEY `idx_cita_id` (`cita_id`),
  ADD KEY `idx_servicio_id` (`servicio_id`);

--
-- Indexes for table `clientes`
--
ALTER TABLE `clientes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `email_unique` (`email`);

--
-- Indexes for table `detalle_pedidos`
--
ALTER TABLE `detalle_pedidos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_pedido_id` (`pedido_id`),
  ADD KEY `idx_producto_id` (`producto_id`);

--
-- Indexes for table `mascotas`
--
ALTER TABLE `mascotas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_cliente_id` (`cliente_id`);

--
-- Indexes for table `pedidos`
--
ALTER TABLE `pedidos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_cliente_id` (`cliente_id`),
  ADD KEY `idx_estado` (`estado`);

--
-- Indexes for table `personal`
--
ALTER TABLE `personal`
  ADD PRIMARY KEY (`id`),
  ADD KEY `usuario_id` (`usuario_id`);

--
-- Indexes for table `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `servicios`
--
ALTER TABLE `servicios`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `tarjetas_cliente`
--
ALTER TABLE `tarjetas_cliente`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_cliente_id` (`cliente_id`);

--
-- Indexes for table `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `asistencia`
--
ALTER TABLE `asistencia`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `citas`
--
ALTER TABLE `citas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT for table `citas_mascotas`
--
ALTER TABLE `citas_mascotas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT for table `citas_servicios`
--
ALTER TABLE `citas_servicios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT for table `clientes`
--
ALTER TABLE `clientes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `detalle_pedidos`
--
ALTER TABLE `detalle_pedidos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `mascotas`
--
ALTER TABLE `mascotas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `pedidos`
--
ALTER TABLE `pedidos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `personal`
--
ALTER TABLE `personal`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `productos`
--
ALTER TABLE `productos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT for table `servicios`
--
ALTER TABLE `servicios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT for table `tarjetas_cliente`
--
ALTER TABLE `tarjetas_cliente`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `asistencia`
--
ALTER TABLE `asistencia`
  ADD CONSTRAINT `asistencia_ibfk_1` FOREIGN KEY (`personal_id`) REFERENCES `personal` (`id`);

--
-- Constraints for table `citas`
--
ALTER TABLE `citas`
  ADD CONSTRAINT `citas_ibfk_1` FOREIGN KEY (`servicio_id`) REFERENCES `servicios` (`id`);

--
-- Constraints for table `citas_mascotas`
--
ALTER TABLE `citas_mascotas`
  ADD CONSTRAINT `citas_mascotas_ibfk_1` FOREIGN KEY (`cita_id`) REFERENCES `citas` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `citas_mascotas_ibfk_2` FOREIGN KEY (`mascota_id`) REFERENCES `mascotas` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `citas_servicios`
--
ALTER TABLE `citas_servicios`
  ADD CONSTRAINT `citas_servicios_ibfk_1` FOREIGN KEY (`cita_id`) REFERENCES `citas` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `citas_servicios_ibfk_2` FOREIGN KEY (`servicio_id`) REFERENCES `servicios` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `detalle_pedidos`
--
ALTER TABLE `detalle_pedidos`
  ADD CONSTRAINT `detalle_pedidos_ibfk_1` FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `detalle_pedidos_ibfk_2` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `mascotas`
--
ALTER TABLE `mascotas`
  ADD CONSTRAINT `mascotas_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `pedidos`
--
ALTER TABLE `pedidos`
  ADD CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `personal`
--
ALTER TABLE `personal`
  ADD CONSTRAINT `personal_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`);

--
-- Constraints for table `tarjetas_cliente`
--
ALTER TABLE `tarjetas_cliente`
  ADD CONSTRAINT `tarjetas_cliente_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
