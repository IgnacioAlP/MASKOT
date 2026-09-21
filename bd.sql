-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.
CREATE TABLE public.tenants (
  id integer NOT NULL DEFAULT nextval('tenants_id_seq'::regclass),
  nombre character varying NOT NULL,
  slug character varying NOT NULL UNIQUE,
  activo boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT tenants_pkey PRIMARY KEY (id)
);
CREATE TABLE public.usuarios (
  id integer NOT NULL DEFAULT nextval('usuarios_id_seq'::regclass),
  username character varying NOT NULL UNIQUE,
  password character varying NOT NULL,
  rol USER - DEFINED NOT NULL,
  activo boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  tenant_id integer DEFAULT 1,
  CONSTRAINT usuarios_pkey PRIMARY KEY (id),
  CONSTRAINT usuarios_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.personal (
  id integer NOT NULL DEFAULT nextval('personal_id_seq'::regclass),
  usuario_id integer,
  cargo character varying,
  salario numeric,
  activo boolean DEFAULT true,
  tenant_id integer DEFAULT 1,
  CONSTRAINT personal_pkey PRIMARY KEY (id),
  CONSTRAINT personal_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id),
  CONSTRAINT personal_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.asistencia (
  id integer NOT NULL DEFAULT nextval('asistencia_id_seq'::regclass),
  personal_id integer,
  fecha date NOT NULL,
  hora_entrada time without time zone,
  hora_salida time without time zone,
  tenant_id integer DEFAULT 1,
  CONSTRAINT asistencia_pkey PRIMARY KEY (id),
  CONSTRAINT asistencia_personal_id_fkey FOREIGN KEY (personal_id) REFERENCES public.personal(id),
  CONSTRAINT asistencia_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.clientes (
  id integer NOT NULL DEFAULT nextval('clientes_id_seq'::regclass),
  nombre character varying NOT NULL,
  email character varying UNIQUE,
  telefono character varying,
  direccion text,
  documento character varying,
  fecha_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  activo boolean DEFAULT true,
  tenant_id integer DEFAULT 1,
  CONSTRAINT clientes_pkey PRIMARY KEY (id),
  CONSTRAINT clientes_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.servicios (
  id integer NOT NULL DEFAULT nextval('servicios_id_seq'::regclass),
  nombre character varying NOT NULL,
  descripcion text,
  precio numeric DEFAULT 0.00,
  duracion integer DEFAULT 30,
  max_citas_dia integer DEFAULT 10,
  activo boolean DEFAULT true,
  tenant_id integer DEFAULT 1,
  CONSTRAINT servicios_pkey PRIMARY KEY (id),
  CONSTRAINT servicios_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.mascotas (
  id integer NOT NULL DEFAULT nextval('mascotas_id_seq'::regclass),
  cliente_id integer,
  nombre character varying NOT NULL,
  especie character varying NOT NULL,
  raza character varying,
  edad integer,
  peso numeric,
  color character varying,
  genero USER - DEFINED,
  esterilizado boolean DEFAULT false,
  observaciones text,
  fecha_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  activo boolean DEFAULT true,
  tenant_id integer DEFAULT 1,
  CONSTRAINT mascotas_pkey PRIMARY KEY (id),
  CONSTRAINT mascotas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id),
  CONSTRAINT mascotas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.productos (
  id integer NOT NULL DEFAULT nextval('productos_id_seq'::regclass),
  nombre character varying NOT NULL,
  codigo_barra character varying,
  tipo USER - DEFINED DEFAULT 'stock'::tipo_producto_enum,
  cantidad integer DEFAULT 0,
  precio numeric DEFAULT 0.00,
  stock_min integer DEFAULT 0,
  fecha_vencimiento date,
  imagen character varying,
  activo boolean DEFAULT true,
  tenant_id integer DEFAULT 1,
  stock_minimo integer DEFAULT 5,
  CONSTRAINT productos_pkey PRIMARY KEY (id),
  CONSTRAINT productos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.citas (
  id integer NOT NULL DEFAULT nextval('citas_id_seq'::regclass),
  cliente_id integer,
  cliente_nombre character varying NOT NULL,
  cliente_email character varying,
  cliente_telefono character varying,
  servicio_id integer,
  fecha date NOT NULL,
  hora time without time zone NOT NULL,
  mascota_nombre character varying,
  mascota_especie character varying,
  mascota_raza character varying,
  mascota_edad integer,
  mascota_peso numeric,
  observaciones text,
  precio_total numeric,
  estado USER - DEFINED DEFAULT 'pendiente'::estado_cita_enum,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  tenant_id integer DEFAULT 1,
  CONSTRAINT citas_pkey PRIMARY KEY (id),
  CONSTRAINT citas_servicio_id_fkey FOREIGN KEY (servicio_id) REFERENCES public.servicios(id),
  CONSTRAINT citas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.citas_mascotas (
  id integer NOT NULL DEFAULT nextval('citas_mascotas_id_seq'::regclass),
  cita_id integer NOT NULL,
  mascota_id integer NOT NULL,
  tenant_id integer DEFAULT 1,
  CONSTRAINT citas_mascotas_pkey PRIMARY KEY (id),
  CONSTRAINT citas_mascotas_cita_id_fkey FOREIGN KEY (cita_id) REFERENCES public.citas(id),
  CONSTRAINT citas_mascotas_mascota_id_fkey FOREIGN KEY (mascota_id) REFERENCES public.mascotas(id),
  CONSTRAINT citas_mascotas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.citas_servicios (
  id integer NOT NULL DEFAULT nextval('citas_servicios_id_seq'::regclass),
  cita_id integer NOT NULL,
  servicio_id integer NOT NULL,
  precio numeric,
  tenant_id integer DEFAULT 1,
  CONSTRAINT citas_servicios_pkey PRIMARY KEY (id),
  CONSTRAINT citas_servicios_cita_id_fkey FOREIGN KEY (cita_id) REFERENCES public.citas(id),
  CONSTRAINT citas_servicios_servicio_id_fkey FOREIGN KEY (servicio_id) REFERENCES public.servicios(id),
  CONSTRAINT citas_servicios_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.compras (
  id integer NOT NULL DEFAULT nextval('compras_id_seq'::regclass),
  cliente_nombre character varying NOT NULL,
  cliente_email character varying,
  cliente_telefono character varying,
  productos text NOT NULL,
  subtotal numeric NOT NULL DEFAULT 0.00,
  igv numeric NOT NULL DEFAULT 0.00,
  total numeric NOT NULL,
  metodo_pago USER - DEFINED DEFAULT 'efectivo'::metodo_pago_enum,
  estado USER - DEFINED DEFAULT 'pagado'::estado_compra_enum,
  fecha_compra timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  observaciones text,
  vendedor_id integer,
  tenant_id integer DEFAULT 1,
  CONSTRAINT compras_pkey PRIMARY KEY (id),
  CONSTRAINT compras_vendedor_id_fkey FOREIGN KEY (vendedor_id) REFERENCES public.usuarios(id),
  CONSTRAINT compras_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.pedidos (
  id integer NOT NULL DEFAULT nextval('pedidos_id_seq'::regclass),
  cliente_id integer NOT NULL,
  subtotal numeric NOT NULL,
  igv numeric NOT NULL,
  total numeric NOT NULL,
  metodo_pago USER - DEFINED NOT NULL,
  estado USER - DEFINED DEFAULT 'pendiente'::estado_pedido_enum,
  fecha_pedido timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  fecha_pago timestamp without time zone,
  fecha_entrega timestamp without time zone,
  tenant_id integer DEFAULT 1,
  CONSTRAINT pedidos_pkey PRIMARY KEY (id),
  CONSTRAINT pedidos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id),
  CONSTRAINT pedidos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.detalle_pedidos (
  id integer NOT NULL DEFAULT nextval('detalle_pedidos_id_seq'::regclass),
  pedido_id integer NOT NULL,
  producto_id integer NOT NULL,
  cantidad integer NOT NULL,
  precio_unitario numeric NOT NULL,
  subtotal numeric NOT NULL,
  tenant_id integer DEFAULT 1,
  CONSTRAINT detalle_pedidos_pkey PRIMARY KEY (id),
  CONSTRAINT detalle_pedidos_pedido_id_fkey FOREIGN KEY (pedido_id) REFERENCES public.pedidos(id),
  CONSTRAINT detalle_pedidos_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id),
  CONSTRAINT detalle_pedidos_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.fidelizacion (
  id integer NOT NULL DEFAULT nextval('fidelizacion_id_seq'::regclass),
  cliente_email character varying NOT NULL UNIQUE,
  cliente_nombre character varying,
  contador integer DEFAULT 0,
  fecha_inicio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  tenant_id integer DEFAULT 1,
  CONSTRAINT fidelizacion_pkey PRIMARY KEY (id),
  CONSTRAINT fidelizacion_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.fidelizacion_historial (
  id integer NOT NULL DEFAULT nextval('fidelizacion_historial_id_seq'::regclass),
  cliente_email character varying NOT NULL,
  evento character varying NOT NULL,
  descripcion text,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  tenant_id integer DEFAULT 1,
  CONSTRAINT fidelizacion_historial_pkey PRIMARY KEY (id),
  CONSTRAINT fidelizacion_historial_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.tarjetas_cliente (
  id integer NOT NULL DEFAULT nextval('tarjetas_cliente_id_seq'::regclass),
  cliente_id integer NOT NULL,
  numero_enmascarado character varying NOT NULL,
  numero_hash character varying NOT NULL,
  nombre_titular character varying NOT NULL,
  expiracion character varying NOT NULL,
  tipo_tarjeta USER - DEFINED NOT NULL,
  fecha_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  activo boolean DEFAULT true,
  tenant_id integer DEFAULT 1,
  CONSTRAINT tarjetas_cliente_pkey PRIMARY KEY (id),
  CONSTRAINT tarjetas_cliente_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id),
  CONSTRAINT tarjetas_cliente_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);
CREATE TABLE public.ventas (
  id integer NOT NULL DEFAULT nextval('ventas_id_seq'::regclass),
  numero_venta character varying NOT NULL UNIQUE,
  vendedor_id integer,
  vendedor_nombre character varying,
  cliente_nombre character varying DEFAULT 'Cliente General'::character varying,
  cliente_documento character varying,
  productos text NOT NULL,
  subtotal numeric NOT NULL,
  igv numeric NOT NULL,
  total numeric NOT NULL,
  metodo_pago character varying NOT NULL DEFAULT 'efectivo'::character varying,
  monto_recibido numeric,
  cambio_entregado numeric DEFAULT 0.00,
  referencia_pago character varying,
  estado USER - DEFINED DEFAULT 'completada'::estado_venta_enum,
  notas text,
  fecha_venta timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  tenant_id integer DEFAULT 1,
  cliente_id integer,
  CONSTRAINT ventas_pkey PRIMARY KEY (id),
  CONSTRAINT ventas_vendedor_id_fkey FOREIGN KEY (vendedor_id) REFERENCES public.usuarios(id),
  CONSTRAINT ventas_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id)
);