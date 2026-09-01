-- MySQL dump 10.13  Distrib 8.0.40, for Linux (x86_64)
--
-- Host: MASKOT.mysql.pythonanywhere-services.com    Database: MASKOT$Veterinaria
-- ------------------------------------------------------
-- Server version	8.0.40

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `asistencia`
--

DROP TABLE IF EXISTS `asistencia`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `asistencia` (
  `id` int NOT NULL AUTO_INCREMENT,
  `personal_id` int DEFAULT NULL,
  `fecha` date NOT NULL,
  `hora_entrada` time DEFAULT NULL,
  `hora_salida` time DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_asistencia` (`personal_id`,`fecha`),
  CONSTRAINT `asistencia_ibfk_1` FOREIGN KEY (`personal_id`) REFERENCES `personal` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `asistencia`
--

LOCK TABLES `asistencia` WRITE;
/*!40000 ALTER TABLE `asistencia` DISABLE KEYS */;
/*!40000 ALTER TABLE `asistencia` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cita_mascotas`
--

DROP TABLE IF EXISTS `cita_mascotas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cita_mascotas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cita_id` int NOT NULL,
  `mascota_id` int DEFAULT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `especie` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `raza` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `edad` int DEFAULT NULL,
  `peso` decimal(5,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cita_id` (`cita_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cita_mascotas`
--

LOCK TABLES `cita_mascotas` WRITE;
/*!40000 ALTER TABLE `cita_mascotas` DISABLE KEYS */;
/*!40000 ALTER TABLE `cita_mascotas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cita_servicios`
--

DROP TABLE IF EXISTS `cita_servicios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cita_servicios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cita_id` int NOT NULL,
  `servicio_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `cita_id` (`cita_id`),
  KEY `servicio_id` (`servicio_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cita_servicios`
--

LOCK TABLES `cita_servicios` WRITE;
/*!40000 ALTER TABLE `cita_servicios` DISABLE KEYS */;
/*!40000 ALTER TABLE `cita_servicios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `citas`
--

DROP TABLE IF EXISTS `citas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `citas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_id` int DEFAULT NULL,
  `cliente_nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `cliente_email` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `cliente_telefono` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `servicio_id` int DEFAULT NULL,
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  `mascota_nombre` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mascota_especie` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mascota_raza` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `mascota_edad` int DEFAULT NULL,
  `mascota_peso` decimal(5,2) DEFAULT NULL,
  `observaciones` text COLLATE utf8mb4_general_ci,
  `precio_total` decimal(8,2) DEFAULT NULL,
  `estado` enum('pendiente','confirmada','en_progreso','completada','cancelada') COLLATE utf8mb4_general_ci DEFAULT 'pendiente',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `servicio_id` (`servicio_id`),
  KEY `idx_cliente_id` (`cliente_id`),
  KEY `idx_cliente_email` (`cliente_email`),
  KEY `idx_fecha_hora` (`fecha`,`hora`),
  CONSTRAINT `citas_ibfk_1` FOREIGN KEY (`servicio_id`) REFERENCES `servicios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `citas`
--

LOCK TABLES `citas` WRITE;
/*!40000 ALTER TABLE `citas` DISABLE KEYS */;
/*!40000 ALTER TABLE `citas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `citas_mascotas`
--

DROP TABLE IF EXISTS `citas_mascotas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `citas_mascotas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cita_id` int NOT NULL,
  `mascota_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cita_mascota_unique` (`cita_id`,`mascota_id`),
  KEY `idx_cita_id` (`cita_id`),
  KEY `idx_mascota_id` (`mascota_id`),
  CONSTRAINT `citas_mascotas_ibfk_1` FOREIGN KEY (`cita_id`) REFERENCES `citas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `citas_mascotas_ibfk_2` FOREIGN KEY (`mascota_id`) REFERENCES `mascotas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `citas_mascotas`
--

LOCK TABLES `citas_mascotas` WRITE;
/*!40000 ALTER TABLE `citas_mascotas` DISABLE KEYS */;
/*!40000 ALTER TABLE `citas_mascotas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `citas_servicios`
--

DROP TABLE IF EXISTS `citas_servicios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `citas_servicios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cita_id` int NOT NULL,
  `servicio_id` int NOT NULL,
  `precio` decimal(8,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cita_servicio_unique` (`cita_id`,`servicio_id`),
  KEY `idx_cita_id` (`cita_id`),
  KEY `idx_servicio_id` (`servicio_id`),
  CONSTRAINT `citas_servicios_ibfk_1` FOREIGN KEY (`cita_id`) REFERENCES `citas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `citas_servicios_ibfk_2` FOREIGN KEY (`servicio_id`) REFERENCES `servicios` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `citas_servicios`
--

LOCK TABLES `citas_servicios` WRITE;
/*!40000 ALTER TABLE `citas_servicios` DISABLE KEYS */;
/*!40000 ALTER TABLE `citas_servicios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `clientes`
--

DROP TABLE IF EXISTS `clientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `clientes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `direccion` text COLLATE utf8mb4_general_ci,
  `documento` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `email_unique` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clientes`
--

LOCK TABLES `clientes` WRITE;
/*!40000 ALTER TABLE `clientes` DISABLE KEYS */;
INSERT INTO `clientes` VALUES (1,'Lucas Pezo','lucaspezov@gmail.com','969347478','Av. Abelardo Quiñones- San Juan ','70669478','2025-10-05 02:38:22',1);
/*!40000 ALTER TABLE `clientes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `compras`
--

DROP TABLE IF EXISTS `compras`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `compras` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cliente_email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cliente_telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `productos` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `subtotal` decimal(10,2) NOT NULL DEFAULT '0.00',
  `igv` decimal(10,2) NOT NULL DEFAULT '0.00',
  `total` decimal(10,2) NOT NULL,
  `metodo_pago` enum('efectivo','tarjeta','transferencia','credito') COLLATE utf8mb4_unicode_ci DEFAULT 'efectivo',
  `estado` enum('pendiente','pagado','cancelado','reembolsado') COLLATE utf8mb4_unicode_ci DEFAULT 'pagado',
  `fecha_compra` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `observaciones` text COLLATE utf8mb4_unicode_ci,
  `vendedor_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cliente_email` (`cliente_email`),
  KEY `idx_fecha_compra` (`fecha_compra`),
  KEY `idx_estado` (`estado`),
  KEY `vendedor_id` (`vendedor_id`),
  CONSTRAINT `compras_ibfk_1` FOREIGN KEY (`vendedor_id`) REFERENCES `usuarios` (`id`) ON DELETE SET NULL,
  CONSTRAINT `compras_chk_1` CHECK (json_valid(`productos`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `compras`
--

LOCK TABLES `compras` WRITE;
/*!40000 ALTER TABLE `compras` DISABLE KEYS */;
/*!40000 ALTER TABLE `compras` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `detalle_pedidos`
--

DROP TABLE IF EXISTS `detalle_pedidos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `detalle_pedidos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `pedido_id` int NOT NULL,
  `producto_id` int NOT NULL,
  `cantidad` int NOT NULL,
  `precio_unitario` decimal(8,2) NOT NULL,
  `subtotal` decimal(8,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_pedido_id` (`pedido_id`),
  KEY `idx_producto_id` (`producto_id`),
  CONSTRAINT `detalle_pedidos_ibfk_1` FOREIGN KEY (`pedido_id`) REFERENCES `pedidos` (`id`) ON DELETE CASCADE,
  CONSTRAINT `detalle_pedidos_ibfk_2` FOREIGN KEY (`producto_id`) REFERENCES `productos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `detalle_pedidos`
--

LOCK TABLES `detalle_pedidos` WRITE;
/*!40000 ALTER TABLE `detalle_pedidos` DISABLE KEYS */;
/*!40000 ALTER TABLE `detalle_pedidos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fidelizacion`
--

DROP TABLE IF EXISTS `fidelizacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fidelizacion` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `cliente_nombre` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `contador` int DEFAULT '0',
  `fecha_inicio` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cliente_email` (`cliente_email`),
  KEY `idx_fidelizacion_email` (`cliente_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fidelizacion`
--

LOCK TABLES `fidelizacion` WRITE;
/*!40000 ALTER TABLE `fidelizacion` DISABLE KEYS */;
/*!40000 ALTER TABLE `fidelizacion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fidelizacion_historial`
--

DROP TABLE IF EXISTS `fidelizacion_historial`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fidelizacion_historial` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `evento` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_general_ci,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_fidelizacion_hist_email` (`cliente_email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fidelizacion_historial`
--

LOCK TABLES `fidelizacion_historial` WRITE;
/*!40000 ALTER TABLE `fidelizacion_historial` DISABLE KEYS */;
/*!40000 ALTER TABLE `fidelizacion_historial` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `mascotas`
--

DROP TABLE IF EXISTS `mascotas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mascotas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_id` int DEFAULT NULL,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `especie` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `raza` varchar(100) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `edad` int DEFAULT NULL,
  `peso` decimal(5,2) DEFAULT NULL,
  `color` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `genero` enum('macho','hembra') COLLATE utf8mb4_general_ci DEFAULT NULL,
  `esterilizado` tinyint(1) DEFAULT '0',
  `observaciones` text COLLATE utf8mb4_general_ci,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_cliente_id` (`cliente_id`),
  CONSTRAINT `mascotas_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `mascotas`
--

LOCK TABLES `mascotas` WRITE;
/*!40000 ALTER TABLE `mascotas` DISABLE KEYS */;
/*!40000 ALTER TABLE `mascotas` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pedidos`
--

DROP TABLE IF EXISTS `pedidos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pedidos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_id` int NOT NULL,
  `subtotal` decimal(8,2) NOT NULL,
  `igv` decimal(8,2) NOT NULL,
  `total` decimal(8,2) NOT NULL,
  `metodo_pago` enum('efectivo','tarjeta','transferencia') COLLATE utf8mb4_general_ci NOT NULL,
  `estado` enum('pendiente','pagado','enviado','entregado','cancelado') COLLATE utf8mb4_general_ci DEFAULT 'pendiente',
  `fecha_pedido` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `fecha_pago` timestamp NULL DEFAULT NULL,
  `fecha_entrega` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cliente_id` (`cliente_id`),
  KEY `idx_estado` (`estado`),
  CONSTRAINT `pedidos_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pedidos`
--

LOCK TABLES `pedidos` WRITE;
/*!40000 ALTER TABLE `pedidos` DISABLE KEYS */;
/*!40000 ALTER TABLE `pedidos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `personal`
--

DROP TABLE IF EXISTS `personal`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `personal` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int DEFAULT NULL,
  `cargo` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `salario` decimal(10,2) DEFAULT NULL,
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`),
  CONSTRAINT `personal_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `personal`
--

LOCK TABLES `personal` WRITE;
/*!40000 ALTER TABLE `personal` DISABLE KEYS */;
INSERT INTO `personal` VALUES (1,2,'Administrador',0.00,1),(2,1,'Administrador',0.00,1);
/*!40000 ALTER TABLE `personal` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `productos`
--

DROP TABLE IF EXISTS `productos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `productos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `tipo` enum('stock','venta') COLLATE utf8mb4_general_ci DEFAULT 'stock',
  `cantidad` int DEFAULT '0',
  `precio` decimal(10,2) DEFAULT '0.00',
  `stock_min` int DEFAULT '0',
  `fecha_vencimiento` date DEFAULT NULL,
  `imagen` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `productos`
--

LOCK TABLES `productos` WRITE;
/*!40000 ALTER TABLE `productos` DISABLE KEYS */;
/*!40000 ALTER TABLE `productos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `servicios`
--

DROP TABLE IF EXISTS `servicios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servicios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_general_ci,
  `precio` decimal(10,2) DEFAULT '0.00',
  `duracion` int DEFAULT '30',
  `max_citas_dia` int DEFAULT '10',
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `servicios`
--

LOCK TABLES `servicios` WRITE;
/*!40000 ALTER TABLE `servicios` DISABLE KEYS */;
INSERT INTO `servicios` VALUES (1,'Baño Medicado Razas Pequeñas','Un baño pensado con cariño para los peluditos con problemas de piel. \r\nIncluye shampoo medicado según necesidad, cepillado de pelito, limpieza de oídos, corte de uñas, limpieza de plantares, limpieza higiénica, secado y perfumado. ',35.00,50,9,1),(2,'Baño Medicado Raza Mediana ','Un baño pensado con cariño para los peluditos con problemas de piel. \r\nIncluye shampoo medicado según necesidad, cepillado de pelito, limpieza de oídos, corte de uñas, limpieza de plantares, limpieza higiénica, secado y perfumado.',45.00,60,8,1);
/*!40000 ALTER TABLE `servicios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tarjetas_cliente`
--

DROP TABLE IF EXISTS `tarjetas_cliente`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tarjetas_cliente` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cliente_id` int NOT NULL,
  `numero_enmascarado` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `numero_hash` varchar(64) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre_titular` varchar(100) COLLATE utf8mb4_general_ci NOT NULL,
  `expiracion` varchar(7) COLLATE utf8mb4_general_ci NOT NULL,
  `tipo_tarjeta` enum('credito','debito') COLLATE utf8mb4_general_ci NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `activo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `idx_cliente_id` (`cliente_id`),
  CONSTRAINT `tarjetas_cliente_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tarjetas_cliente`
--

LOCK TABLES `tarjetas_cliente` WRITE;
/*!40000 ALTER TABLE `tarjetas_cliente` DISABLE KEYS */;
/*!40000 ALTER TABLE `tarjetas_cliente` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `password` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `rol` enum('cliente','dueño','admin','empleado') COLLATE utf8mb4_general_ci NOT NULL,
  `activo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
INSERT INTO `usuarios` VALUES (1,'admin_maskot','690446643041c337b1c054106428b41c660c1586b40178e24c3d3408119d75cc','admin',1,'2025-09-24 13:05:39'),(2,'LUCAS','77f26144fb2f1a74ba475662b57fa9b4e01f556e81ee30e7c48f46f0f342fc2c','admin',1,'2025-10-04 14:21:57');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ventas`
--

DROP TABLE IF EXISTS `ventas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ventas` (
  `id` int NOT NULL,
  `numero_venta` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vendedor_id` int NOT NULL,
  `vendedor_nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cliente_nombre` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT 'Cliente General',
  `cliente_documento` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `productos` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  `subtotal` decimal(10,2) NOT NULL,
  `igv` decimal(10,2) NOT NULL,
  `total` decimal(10,2) NOT NULL,
  `metodo_pago` enum('efectivo','tarjeta','yape') COLLATE utf8mb4_unicode_ci NOT NULL,
  `monto_recibido` decimal(10,2) DEFAULT NULL,
  `cambio_entregado` decimal(10,2) DEFAULT '0.00',
  `referencia_pago` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` enum('completada','cancelada','pendiente') COLLATE utf8mb4_unicode_ci DEFAULT 'completada',
  `notas` text COLLATE utf8mb4_unicode_ci,
  `fecha_venta` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero_venta` (`numero_venta`),
  KEY `idx_fecha_venta` (`fecha_venta`),
  KEY `idx_vendedor` (`vendedor_id`),
  KEY `idx_metodo_pago` (`metodo_pago`),
  KEY `idx_estado` (`estado`),
  KEY `idx_numero_venta` (`numero_venta`),
  CONSTRAINT `ventas_ibfk_1` FOREIGN KEY (`vendedor_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `ventas_chk_1` CHECK (json_valid(`productos`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ventas`
--

LOCK TABLES `ventas` WRITE;
/*!40000 ALTER TABLE `ventas` DISABLE KEYS */;
/*!40000 ALTER TABLE `ventas` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-22  5:05:20
