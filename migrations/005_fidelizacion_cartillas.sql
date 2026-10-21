CREATE TABLE IF NOT EXISTS fidelizacion_programas (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    nombre VARCHAR(120) NOT NULL DEFAULT 'Cartilla de visitas',
    beneficio_nombre VARCHAR(150) NOT NULL,
    beneficio_descripcion TEXT NOT NULL,
    sellos_objetivo INTEGER NOT NULL DEFAULT 10 CHECK (sellos_objetivo > 0),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fidelizacion_programa_activo_tenant
    ON fidelizacion_programas (tenant_id) WHERE activo = TRUE;

CREATE TABLE IF NOT EXISTS fidelizacion_cartillas (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    sellos INTEGER NOT NULL DEFAULT 0 CHECK (sellos >= 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa', 'completada')),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fidelizacion_cartilla_activa_cliente
    ON fidelizacion_cartillas (tenant_id, cliente_id) WHERE estado = 'activa';

CREATE TABLE IF NOT EXISTS fidelizacion_visitas (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    cartilla_id INTEGER NOT NULL REFERENCES fidelizacion_cartillas(id),
    cita_id INTEGER NOT NULL UNIQUE REFERENCES citas(id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fidelizacion_recompensas (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    cartilla_id INTEGER NOT NULL UNIQUE REFERENCES fidelizacion_cartillas(id),
    beneficio_nombre VARCHAR(150) NOT NULL,
    beneficio_descripcion TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'disponible' CHECK (estado IN ('disponible', 'canjeada')),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    redeemed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_fidelizacion_cartillas_cliente
    ON fidelizacion_cartillas (tenant_id, cliente_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fidelizacion_recompensas_cliente
    ON fidelizacion_recompensas (tenant_id, cliente_id, estado);