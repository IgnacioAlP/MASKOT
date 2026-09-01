-- ============================================================
-- SCRIPT DE CREACIÓN DE BASE DE DATOS PARA SUPABASE (POSTGRESQL)
-- Proyecto: MASKOT Veterinaria
-- Ejecutar este script en el SQL Editor de tu proyecto en Supabase
-- ============================================================

-- 1. Tabla de Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  rol VARCHAR(20) NOT NULL DEFAULT 'empleado',
  activo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Clientes
CREATE TABLE IF NOT EXISTS clientes (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  telefono VARCHAR(20),
  direccion TEXT,
  documento VARCHAR(20),
  fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  activo BOOLEAN DEFAULT TRUE
);

-- 3. Tabla de Mascotas
CREATE TABLE IF NOT EXISTS mascotas (
  id SERIAL PRIMARY KEY,
  cliente_id INT REFERENCES clientes(id) ON DELETE CASCADE,
  nombre VARCHAR(100) NOT NULL,
  especie VARCHAR(50) NOT NULL,
  raza VARCHAR(100),
  edad INT,
  peso DECIMAL(5,2),
  color VARCHAR(50),
  genero VARCHAR(20),
  esterilizado BOOLEAN DEFAULT FALSE,
  observaciones TEXT,
  fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  activo BOOLEAN DEFAULT TRUE
);

-- 4. Tabla de Servicios
CREATE TABLE IF NOT EXISTS servicios (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  descripcion TEXT,
  precio DECIMAL(10,2) NOT NULL,
  duracion INT DEFAULT 30,
  categoria VARCHAR(50),
  activo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tabla de Citas
CREATE TABLE IF NOT EXISTS citas (
  id SERIAL PRIMARY KEY,
  cliente_id INT REFERENCES clientes(id) ON DELETE SET NULL,
  cliente_nombre VARCHAR(100) NOT NULL,
  cliente_email VARCHAR(100),
  cliente_telefono VARCHAR(20),
  servicio_id INT REFERENCES servicios(id) ON DELETE SET NULL,
  fecha DATE NOT NULL,
  hora TIME NOT NULL,
  mascota_nombre VARCHAR(100),
  mascota_especie VARCHAR(50),
  mascota_raza VARCHAR(100),
  mascota_edad INT,
  mascota_peso DECIMAL(5,2),
  observaciones TEXT,
  precio_total DECIMAL(10,2) DEFAULT 0.00,
  estado VARCHAR(20) DEFAULT 'pendiente',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Relación Citas - Mascotas
CREATE TABLE IF NOT EXISTS citas_mascotas (
  id SERIAL PRIMARY KEY,
  cita_id INT NOT NULL REFERENCES citas(id) ON DELETE CASCADE,
  mascota_id INT NOT NULL REFERENCES mascotas(id) ON DELETE CASCADE,
  UNIQUE (cita_id, mascota_id)
);

-- 7. Relación Citas - Servicios
CREATE TABLE IF NOT EXISTS citas_servicios (
  id SERIAL PRIMARY KEY,
  cita_id INT NOT NULL REFERENCES citas(id) ON DELETE CASCADE,
  servicio_id INT NOT NULL REFERENCES servicios(id) ON DELETE CASCADE,
  precio DECIMAL(10,2),
  UNIQUE (cita_id, servicio_id)
);

-- 8. Tabla de Personal
CREATE TABLE IF NOT EXISTS personal (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  cargo VARCHAR(50),
  email VARCHAR(100),
  telefono VARCHAR(20),
  activo BOOLEAN DEFAULT TRUE
);

-- 9. Tabla de Asistencia
CREATE TABLE IF NOT EXISTS asistencia (
  id SERIAL PRIMARY KEY,
  personal_id INT REFERENCES personal(id) ON DELETE CASCADE,
  fecha DATE NOT NULL,
  hora_entrada TIME,
  hora_salida TIME
);

-- 10. Tabla de Productos
CREATE TABLE IF NOT EXISTS productos (
  id SERIAL PRIMARY KEY,
  codigo VARCHAR(50) UNIQUE,
  nombre VARCHAR(100) NOT NULL,
  categoria VARCHAR(50),
  precio DECIMAL(10,2) NOT NULL,
  stock INT DEFAULT 0,
  activo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Tabla de Tarjetas de Cliente
CREATE TABLE IF NOT EXISTS tarjetas_cliente (
  id SERIAL PRIMARY KEY,
  cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  numero_enmascarado VARCHAR(20) NOT NULL,
  numero_hash VARCHAR(64) NOT NULL,
  nombre_titular VARCHAR(100) NOT NULL,
  expiracion VARCHAR(7) NOT NULL,
  tipo_tarjeta VARCHAR(20) NOT NULL,
  fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  activo BOOLEAN DEFAULT TRUE
);

-- 12. Tabla de Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
  id SERIAL PRIMARY KEY,
  cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  subtotal DECIMAL(10,2) NOT NULL,
  igv DECIMAL(10,2) NOT NULL,
  total DECIMAL(10,2) NOT NULL,
  metodo_pago VARCHAR(50) NOT NULL,
  estado VARCHAR(20) DEFAULT 'pendiente',
  fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  fecha_pago TIMESTAMP,
  fecha_entrega TIMESTAMP
);

-- 13. Detalle de Pedidos
CREATE TABLE IF NOT EXISTS detalle_pedidos (
  id SERIAL PRIMARY KEY,
  pedido_id INT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
  producto_id INT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
  cantidad INT NOT NULL,
  precio_unitario DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL
);

-- 14. Tabla de Proveedores
CREATE TABLE IF NOT EXISTS proveedores (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  ruc VARCHAR(20),
  telefono VARCHAR(20),
  email VARCHAR(100),
  direccion TEXT,
  activo BOOLEAN DEFAULT TRUE
);

-- 15. Tabla de Compras
CREATE TABLE IF NOT EXISTS compras (
  id SERIAL PRIMARY KEY,
  proveedor_id INT REFERENCES proveedores(id) ON DELETE SET NULL,
  numero_factura VARCHAR(50),
  total DECIMAL(10,2) NOT NULL,
  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Detalle de Compras
CREATE TABLE IF NOT EXISTS detalle_compras (
  id SERIAL PRIMARY KEY,
  compra_id INT NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
  producto_id INT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
  cantidad INT NOT NULL,
  precio_unitario DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL
);

-- 17. Tabla de Ventas (POS)
CREATE TABLE IF NOT EXISTS ventas (
  id SERIAL PRIMARY KEY,
  cliente_id INT REFERENCES clientes(id) ON DELETE SET NULL,
  cliente_nombre VARCHAR(100),
  subtotal DECIMAL(10,2) NOT NULL,
  igv DECIMAL(10,2) NOT NULL,
  total DECIMAL(10,2) NOT NULL,
  metodo_pago VARCHAR(50) NOT NULL,
  vendedor VARCHAR(100),
  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. Detalle de Ventas (POS)
CREATE TABLE IF NOT EXISTS detalle_ventas (
  id SERIAL PRIMARY KEY,
  venta_id INT NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
  producto_id INT REFERENCES productos(id) ON DELETE SET NULL,
  producto_nombre VARCHAR(100) NOT NULL,
  cantidad INT NOT NULL,
  precio_unitario DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL
);

-- 19. Fidelización de Clientes
CREATE TABLE IF NOT EXISTS fidelizacion (
  id SERIAL PRIMARY KEY,
  cliente_id INT UNIQUE NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  puntos INT DEFAULT 0,
  nivel VARCHAR(20) DEFAULT 'Bronce',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 20. Configuración de Ventas / Boletas / Tickets
CREATE TABLE IF NOT EXISTS ventas_config (
  id SERIAL PRIMARY KEY,
  empresa_nombre VARCHAR(100) DEFAULT 'MASKOT VETERINARIA',
  empresa_ruc VARCHAR(20) DEFAULT '20123456789',
  empresa_direccion TEXT,
  empresa_telefono VARCHAR(20),
  impresion_automatica BOOLEAN DEFAULT TRUE,
  metodos_pago_permitidos TEXT DEFAULT 'efectivo,tarjeta,transferencia,yape,plin'
);

CREATE TABLE IF NOT EXISTS recibos_config (
  id SERIAL PRIMARY KEY,
  formato VARCHAR(20) DEFAULT 'ticket',
  encabezado TEXT,
  pie_pagina TEXT
);

CREATE TABLE IF NOT EXISTS ticketera_config (
  id SERIAL PRIMARY KEY,
  nombre_impresora VARCHAR(100),
  ancho_papel INT DEFAULT 80,
  activa BOOLEAN DEFAULT TRUE
);

-- Insertar usuario por defecto (admin / admin123 hash sha256) si no existe
INSERT INTO usuarios (username, password, rol) 
VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin')
ON CONFLICT (username) DO NOTHING;
