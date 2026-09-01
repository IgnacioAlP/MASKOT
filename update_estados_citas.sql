-- Actualizar los estados de la tabla citas para incluir todos los estados necesarios
ALTER TABLE `citas` 
MODIFY `estado` enum('pendiente','confirmada','en_progreso','completada','cancelada') DEFAULT 'pendiente';

-- Verificar la estructura actualizada
DESCRIBE citas;