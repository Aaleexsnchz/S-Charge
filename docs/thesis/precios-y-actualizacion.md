---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Precios de recarga: frescura del catálogo y estimación

## El problema

REVE se siembra una sola vez en Postgres bajo el límite de 5 peticiones/hora
(véase [seed-scheduling.md](seed-scheduling.md)). De ahí surgían tres dudas
sobre el precio que mostramos:

1. Si la tarifa se obtiene una vez, ¿no quedará permanentemente desactualizada?
2. El precio mayorista (PVPC) varía cada hora; ¿deberíamos perseguir un precio
   "en tiempo real" del CPO?
3. ¿Merece la pena gastar parte de la cuota en el estado operativo de los EVSE?

## Lo que dicen los datos

Una muestra re-descargada de REVE y el catálogo ya sembrado resuelven las dudas:

- **La tarifa de REVE es un precio comercial plano, no un precio horario.** Cientos
  de tarifas coinciden en valores redondos idénticos (0.2975, 0.4545…). Los CPO
  reprecian en lotes esporádicos (meses entre cambios), de forma **desacoplada del
  PVPC** — no existe un precio de REVE "en tiempo real" que perseguir.
- **El margen del CPO es estable por tipo de recarga.** Frente a un PVPC de
  referencia de ~0.12 €/kWh: AC ≈ +0.22 €/kWh, DC ≈ +0.32 €/kWh (mediana sobre
  ~27 000 tarifas reales). Varía entre CPO, pero el valor por tipo basta como
  estimación.
- **El estado operativo no aporta valor:** la disponibilidad se simula (Fase 4),
  así que gastar cuota en `/evses/operational_status` no se justifica.

## La solución

**1. Servir el precio real almacenado.** La app nunca llama a REVE al abrir un
punto: sirve siempre desde Postgres, con su fecha de actualización. La cuota se
gasta solo en la ingesta de fondo, nunca en el tráfico de usuario.

**2. Refresco incremental tras la siembra** ([refresh_reve.py](../../backend/scripts/refresh_reve.py)).
Una vez completada la siembra inicial, cada tick refresca por ventana temporal
`[date_from, date_to]`: `date_from` es la marca de agua del último ciclo drenado;
`date_to` se congela al iniciar el ciclo para que la paginación sea estable entre
ticks. Como REVE permite filtrar por fecha de actualización, cada ciclo trae solo
lo que cambió — decenas de tarifas al día frente a una capacidad de ~12 000/día.
La marca de agua solo avanza cuando la ventana se drena por completo, así que un
pico (p. ej. 600 cambios) simplemente se reparte en varios ticks sin perder nada;
los `upsert` idempotentes absorben cualquier reproceso en el borde. El diseño es
correcto aunque REVE ignore `date_to` o no ordene los resultados: lo que se escape
de un ciclo lo recoge el siguiente, que arranca donde terminó el anterior.

**3. Estimación de respaldo.** Para un conector sin tarifa, el precio se estima
como `PVPC(hora) + margen[tipo]` (AC +0.22 / DC +0.32 €/kWh) y se etiqueta como
*estimado*. Dos constantes calibradas con el mercado real cubren también los
puntos privados de usuario, que no tienen CPO. Este margen es solo el valor
**recomendado**: en la aplicación, el propietario de un punto fija el precio o el
margen que quiera (PVPC + margen, o precio fijo).

**4. Estado operativo frente a disponibilidad.** Son cosas distintas. El *estado
operativo* (funciona / averiado) se asume siempre operativo y no se modela: se
elimina `/evses/operational_status` del ETL y su cursor. La *disponibilidad*
(libre / en uso) la da en REVE el endpoint por EVSE `/evses/{evse_id}/status`,
que tampoco se consulta — es justo lo que vamos a simular (Fase 4). El EVSE guarda
esa disponibilidad en la columna `status` (valor OCPI, p. ej. `AVAILABLE`); el
mapa la agrega a *disponible* / *ocupado* / *desconocido*.

## Operación

El cron sigue lanzando `seed_reve` hasta que las tres fuentes del catálogo
(`/cpos`, `/locations`, `/connectors/tariffs`) quedan completas. A partir de ese
momento, `seed_reve` no hace nada y la línea de cron se cambia para invocar
`refresh_reve`; ambos comparten cursor, presupuesto y patrón de tick. `refresh_reve`
es un no-op mientras la siembra no esté completa, de modo que el cambio es seguro
en cualquier orden.
