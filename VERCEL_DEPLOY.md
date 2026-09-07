# Despliegue de MASKOT en Vercel

## 1. Variables de entorno

En el proyecto de Vercel, abre **Settings > Environment Variables** y agrega estas variables para `Production`, `Preview` y `Development`:

```text
DB_HOST=aws-0-sa-east-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.zpgwjgslescslwlwrwdw
DB_PASSWORD=tu_password_de_supabase
SECRET_KEY=una_clave_larga_y_aleatoria
USE_SECURE_COOKIES=True
```

Usa la contraseña real de Supabase. No la subas al repositorio ni la escribas en este archivo.

## 2. Publicar

1. Sube el repositorio a GitHub y crea un proyecto nuevo en Vercel desde ese repositorio.
2. Mantén el **Root Directory** en la raíz del proyecto, donde están `vercel.json` y `api/`.
3. Vercel detectará `api/main.py` mediante `vercel.json`; no necesitas configurar un build command.
4. Después del primer despliegue, abre `/health`. Debe responder un JSON con `"status": "ok"`.
5. Abre la URL principal y prueba `/login`, `/servicios` y el formulario de citas.

## 3. Base de datos

La aplicación ejecuta migraciones ligeras al arrancar para columnas faltantes. Para cambios estructurales grandes, ejecuta los SQL de `migrations/` directamente en Supabase antes de probar el flujo completo.

Los archivos escritos durante una función serverless son temporales. Los uploads usan `/tmp/uploads` en Vercel y no deben considerarse almacenamiento permanente.