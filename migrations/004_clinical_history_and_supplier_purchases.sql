ALTER TYPE public.metodo_pago_enum ADD VALUE IF NOT EXISTS 'multipago';
ALTER TYPE public.metodo_pago_enum ADD VALUE IF NOT EXISTS 'credito';

CREATE TABLE IF NOT EXISTS public.historial_clinico (
    id SERIAL PRIMARY KEY,
    mascota_id INTEGER NOT NULL REFERENCES public.mascotas(id) ON DELETE CASCADE,
    fecha_visita DATE NOT NULL DEFAULT CURRENT_DATE,
    servicio VARCHAR(255) NOT NULL,
    diagnostico TEXT,
    tratamiento TEXT,
    indicaciones TEXT,
    proxima_cita DATE,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_historial_clinico_mascota_fecha
    ON public.historial_clinico(mascota_id, fecha_visita DESC);
CREATE INDEX IF NOT EXISTS idx_historial_clinico_tenant
    ON public.historial_clinico(tenant_id);

CREATE TABLE IF NOT EXISTS public.compras_inventario (
    id SERIAL PRIMARY KEY,
    proveedor VARCHAR(255) NOT NULL,
    tipo_comprobante VARCHAR(20) NOT NULL DEFAULT 'FC',
    serie VARCHAR(30),
    numero_comprobante VARCHAR(50),
    fecha_emision DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_entrega DATE,
    dias_plazo INTEGER NOT NULL DEFAULT 0,
    moneda VARCHAR(5) NOT NULL DEFAULT 'PEN',
    tipo_cambio NUMERIC(12,4) NOT NULL DEFAULT 1,
    local_actual VARCHAR(50),
    almacen_actual VARCHAR(50),
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0,
    descuento NUMERIC(12,2) NOT NULL DEFAULT 0,
    flete NUMERIC(12,2) NOT NULL DEFAULT 0,
    igv NUMERIC(12,2) NOT NULL DEFAULT 0,
    percepcion NUMERIC(12,2) NOT NULL DEFAULT 0,
    total NUMERIC(12,2) NOT NULL DEFAULT 0,
    observaciones TEXT,
    tenant_id INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_compras_inventario_tenant_fecha
    ON public.compras_inventario(tenant_id, fecha_emision DESC);

CREATE TABLE IF NOT EXISTS public.compras_inventario_detalle (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES public.compras_inventario(id) ON DELETE CASCADE,
    producto_id INTEGER REFERENCES public.productos(id) ON DELETE SET NULL,
    producto_nombre VARCHAR(255) NOT NULL,
    unidad VARCHAR(30) NOT NULL DEFAULT 'UND',
    factor NUMERIC(12,3) NOT NULL DEFAULT 1,
    cantidad INTEGER NOT NULL,
    precio_unitario NUMERIC(12,2) NOT NULL,
    descuento_pct NUMERIC(6,2) NOT NULL DEFAULT 0,
    igv_pct NUMERIC(6,2) NOT NULL DEFAULT 18,
    total NUMERIC(12,2) NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_compras_inventario_detalle_compra
    ON public.compras_inventario_detalle(compra_id);