-- =============================================
-- Migración 002: Multi-Tenant
-- Ejecutar en PythonAnywhere MySQL console
-- =============================================

-- 1. Tabla de tenants
CREATE TABLE IF NOT EXISTS tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE,
    activo TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 2. Insertar tenant por defecto
INSERT INTO tenants (id, nombre, slug) VALUES (1, 'MASKOT', 'maskot');

-- 3. Agregar rol superadmin a usuarios
ALTER TABLE usuarios
  MODIFY COLUMN rol ENUM('cliente','dueño','admin','empleado','superadmin') NOT NULL;

-- 4. Agregar tenant_id a TODAS las tablas
ALTER TABLE usuarios ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE clientes ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE mascotas ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE citas ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE servicios ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE productos ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE personal ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE asistencia ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE pedidos ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE detalle_pedidos ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE tarjetas_cliente ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE citas_mascotas ADD COLUMN tenant_id INT DEFAULT 1;
ALTER TABLE citas_servicios ADD COLUMN tenant_id INT DEFAULT 1;

-- 5. Indices para performance
ALTER TABLE usuarios ADD INDEX idx_tenant (tenant_id);
ALTER TABLE clientes ADD INDEX idx_tenant (tenant_id);
ALTER TABLE mascotas ADD INDEX idx_tenant (tenant_id);
ALTER TABLE citas ADD INDEX idx_tenant (tenant_id);
ALTER TABLE servicios ADD INDEX idx_tenant (tenant_id);
ALTER TABLE productos ADD INDEX idx_tenant (tenant_id);
ALTER TABLE personal ADD INDEX idx_tenant (tenant_id);
ALTER TABLE asistencia ADD INDEX idx_tenant (tenant_id);
ALTER TABLE pedidos ADD INDEX idx_tenant (tenant_id);
ALTER TABLE detalle_pedidos ADD INDEX idx_tenant (tenant_id);
ALTER TABLE tarjetas_cliente ADD INDEX idx_tenant (tenant_id);
ALTER TABLE citas_mascotas ADD INDEX idx_tenant (tenant_id);
ALTER TABLE citas_servicios ADD INDEX idx_tenant (tenant_id);

-- 6. Foreign keys a tenants
ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE clientes ADD CONSTRAINT fk_clientes_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE mascotas ADD CONSTRAINT fk_mascotas_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE citas ADD CONSTRAINT fk_citas_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE servicios ADD CONSTRAINT fk_servicios_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE productos ADD CONSTRAINT fk_productos_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE personal ADD CONSTRAINT fk_personal_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE asistencia ADD CONSTRAINT fk_asistencia_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE pedidos ADD CONSTRAINT fk_pedidos_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE detalle_pedidos ADD CONSTRAINT fk_detalle_pedidos_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE tarjetas_cliente ADD CONSTRAINT fk_tarjetas_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE citas_mascotas ADD CONSTRAINT fk_citas_mascotas_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);
ALTER TABLE citas_servicios ADD CONSTRAINT fk_citas_servicios_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);

-- 7. Crear usuario superadmin (password: 'superadmin123' con SHA-256)
-- Hash SHA-256 de 'superadmin123' = 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8... 
-- Usa el hash correcto para tu password deseado
-- INSERT INTO usuarios (username, password, rol, activo, tenant_id) 
--   VALUES ('superadmin', '<SHA256_HASH>', 'superadmin', 1, 1);
