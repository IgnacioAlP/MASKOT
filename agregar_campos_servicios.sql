-- Agregar campos faltantes a la tabla servicios
ALTER TABLE servicios 
ADD COLUMN precio DECIMAL(10,2) DEFAULT 0.00 AFTER descripcion,
ADD COLUMN duracion INT DEFAULT 30 AFTER precio;