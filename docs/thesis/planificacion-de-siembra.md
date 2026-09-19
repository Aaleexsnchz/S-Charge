---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Planificación de la siembra — cron y el contrato por tick

El ETL del catálogo REVE se ejecuta con cron en el host: una sola línea invoca el orquestador `seed_reve` dentro del contenedor del backend, que gasta hasta cinco llamadas a REVE por hora y termina. A lo largo de ~12 días de ticks desatendidos, el catálogo español completo aterriza en Postgres. Cuando las tres filas de `reve_etl_cursor` tienen `completed_at`, el cron pasa a invocar el refresco incremental descrito en [precios-y-actualizacion.md](precios-y-actualizacion.md). Véase [plan/phases/phase-2.md](../plan/phases/phase-2.md) para los criterios de la slice.

## Por qué es necesario un planificador

REVE limita a cinco peticiones por hora por credencial. Un proxy en tiempo de petición es imposible — una carga fría del mapa consume la cuota de toda la hora. Un script de bootstrap único también es imposible — a la escala del proyecto hacen falta cientos de llamadas paginadas. Toda la forma del ETL (endpoints por etapas, tabla de cursores, presupuesto por tick) se deriva de esa regla de 5 peticiones/hora.

## Por qué cron frente a las alternativas

- *Planificador en proceso (APScheduler en el lifespan de FastAPI).* Los reinicios del contenedor y `uvicorn --reload` resetean el estado en memoria; un almacén de trabajos respaldado por BD duplicaría el papel de `reve_etl_cursor`.
- *Script de bootstrap único de larga duración.* O ignora el límite de peticiones (y se estrangula a base de 429) o duerme doce minutos entre llamadas durante doce días como punto único de fallo.
- *Programador de tareas de Windows.* Esquiva la suspensión de WSL pero no es reproducible desde el repositorio. Se mantiene como vía de mejora si las pérdidas por inactividad de WSL resultan significativas.

Cron es la primitiva más pequeña que cumple la restricción: planificación declarativa, persiste entre reinicios, un proceso independiente por tick, sin estado compartido.

## El contrato por tick

Cada tick está **acotado** (≤5 llamadas a REVE, elige el siguiente endpoint no completado en orden de dependencia `/cpos → /locations → /connectors/tariffs`, termina limpiamente ante un `429`) y es **idempotente** (las cuatro importaciones usan `INSERT … ON CONFLICT DO UPDATE` de Postgres con clave en el ID de origen; re-ejecutar una página ya descargada actualiza las filas en su sitio). Esa combinación es lo que convierte "un proceso corto por hora" en la abstracción correcta: los ticks perdidos los recupera el siguiente, y los ticks fallidos no cuestan nada.

## Operación

```bash
# Instalar (una sola vez) — se ejecuta en el minuto 30 de cada hora.
(crontab -l 2>/dev/null; echo "30 * * * * /usr/bin/docker compose -f /home/aaleexsnchz/tfm/docker-compose.yml exec -T backend uv run python -m scripts.seed_reve >> /home/aaleexsnchz/.reve-seed.log 2>&1") | crontab -

# Verificar
crontab -l

# Consultar progreso (sin llamada a la API)
cd backend && uv run python -m scripts.seed_reve --status
tail -n 20 ~/.reve-seed.log

# Detener
crontab -r            # elimina todas las entradas, o
crontab -e            # editar / comentar la línea
```

Cada tick añade una línea de auditoría JSON por endpoint tocado más un resumen final `calls used: N/5` a `~/.reve-seed.log`. El crontab persiste entre reinicios; cron arranca automáticamente porque `systemd=true` está configurado en `/etc/wsl.conf` y `cron.service` está habilitado.

## La salvedad de la inactividad en WSL2

Cuando no hay ninguna shell abierta contra la distro de WSL, el systemd de su interior se suspende y cron no se dispara. Un portátil cerrado ocho horas cuesta ocho ticks (~4.000 filas de catálogo de progreso) — el cursor queda intacto y el siguiente tick activo reanuda el trabajo. Aceptable para una tesis defendida desde un portátil personal; la mitigación, si hiciera falta, es el programador de tareas de Windows lanzando `wsl --distribution <nombre> docker compose …`.
