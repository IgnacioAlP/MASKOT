-- Migration: crear tablas de fidelización
-- Tabla para llevar contador por cliente (por email)
CREATE TABLE IF NOT EXISTS fidelizacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_email VARCHAR(255) NOT NULL UNIQUE,
    cliente_nombre VARCHAR(255),
    contador INT DEFAULT 0,
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Historial de eventos para auditoría
CREATE TABLE IF NOT EXISTS fidelizacion_historial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_email VARCHAR(255) NOT NULL,
    evento VARCHAR(255) NOT NULL,
    descripcion TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_fidelizacion_email ON fidelizacion(cliente_email);
CREATE INDEX IF NOT EXISTS idx_fidelizacion_hist_email ON fidelizacion_historial(cliente_email);
