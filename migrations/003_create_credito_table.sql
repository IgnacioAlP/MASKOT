-- ==============================================================================
-- Migración 003: Crear tablas de credito y credito_abonos
-- MASKOT - Petshop y Veterinaria
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.credito (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER NULL REFERENCES public.ventas(id) ON DELETE SET NULL,
    cliente_id INTEGER NOT NULL REFERENCES public.clientes(id) ON DELETE CASCADE,
    cliente_nombre CHARACTER VARYING(255) NOT NULL,
    cliente_documento CHARACTER VARYING(50),
    monto_total NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    monto_pagado NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    saldo_pendiente NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    fecha_credito TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_vencimiento DATE,
    estado CHARACTER VARYING(20) NOT NULL DEFAULT 'pendiente',
    notas TEXT,
    tenant_id INTEGER DEFAULT 1 REFERENCES public.tenants(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credito_tenant_estado ON public.credito(tenant_id, estado);
CREATE INDEX IF NOT EXISTS idx_credito_cliente_id ON public.credito(cliente_id);
CREATE INDEX IF NOT EXISTS idx_credito_venta_id ON public.credito(venta_id);

CREATE TABLE IF NOT EXISTS public.credito_abonos (
    id SERIAL PRIMARY KEY,
    credito_id INTEGER NOT NULL REFERENCES public.credito(id) ON DELETE CASCADE,
    monto NUMERIC(12,2) NOT NULL,
    metodo_pago CHARACTER VARYING(50) DEFAULT 'efectivo',
    notas TEXT,
    usuario_nombre CHARACTER VARYING(100),
    fecha_abono TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tenant_id INTEGER DEFAULT 1 REFERENCES public.tenants(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_credito_abonos_credito_id ON public.credito_abonos(credito_id);
