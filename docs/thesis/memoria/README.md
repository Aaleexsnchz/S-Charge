# Memoria del TFM

Los capítulos de la memoria que se entrega y se defiende. Un fichero por capítulo, en español,
numerados en el orden de lectura.

Estos documentos son **independientes** de los de [`docs/thesis/`](../), que son notas
conceptuales de trabajo escritas durante el desarrollo. Aquellas siguen siendo la materia prima
y no se borran; estas son el texto que lee el tribunal.

## Capítulos

| # | Fichero | Contenido |
| --- | --- | --- |
| 0 | [00_Resumen.md](00_Resumen.md) | Resumen, *abstract*, palabras clave |
| 1 | [01_Introduccion.md](01_Introduccion.md) | Contexto, problema, motivación, objetivos y alcance |
| 2 | [02_Estado_del_arte.md](02_Estado_del_arte.md) | REVE, apps de operador, agregadores, estándares y el hueco |
| 3 | [03_Analisis_y_requisitos.md](03_Analisis_y_requisitos.md) | Roles, casos de uso, requisitos y metodología |
| 4 | [04_Arquitectura_del_sistema.md](04_Arquitectura_del_sistema.md) | Visión de conjunto, stack y decisiones revisadas |
| 5 | [05_Modelo_de_datos_y_fuentes.md](05_Modelo_de_datos_y_fuentes.md) | OCPI, espejo de REVE, siembra, precios y vehículos |
| 6 | [06_Autenticacion_y_seguridad.md](06_Autenticacion_y_seguridad.md) | Identidad, sesión, OAuth, límites de tasa y modelo de amenazas |
| 7 | [07_Funcionalidades_de_la_aplicacion.md](07_Funcionalidades_de_la_aplicacion.md) | Mapa, detalle, simulación y las funcionalidades de plataforma |
| 8 | [08_Optimizacion_de_la_carga.md](08_Optimizacion_de_la_carga.md) | Formulación del optimizador sobre la curva PVPC |
| 9 | [09_Asistente_de_IA.md](09_Asistente_de_IA.md) | Capa de IA sobre las APIs propias |
| 10 | [10_Despliegue_operacion_y_escalado.md](10_Despliegue_operacion_y_escalado.md) | Producción, cadena de entrega, escalado argumentado y costes |
| 11 | [11_Validacion_y_resultados.md](11_Validacion_y_resultados.md) | Pruebas, medidas y verificación |
| 12 | [12_Marco_regulador.md](12_Marco_regulador.md) | AFIR, PVPC, RGPD, derechos sobre los datos y accesibilidad |
| 13 | [13_Entorno_socioeconomico.md](13_Entorno_socioeconomico.md) | Modelo de negocio, viabilidad, presupuesto y planificación |
| 14 | [14_Uso_de_IA_generativa.md](14_Uso_de_IA_generativa.md) | Uso de IA generativa en la elaboración del trabajo |
| 15 | [15_Conclusiones.md](15_Conclusiones.md) | Resultados, aprendizajes y trabajo futuro |
| — | [90_Bibliografia.md](90_Bibliografia.md) | Referencias en formato IEEE |
| — | [91_Anexos.md](91_Anexos.md) | Anexos |

## Convenciones

- **Citas en IEEE numerado**, ya resueltas: `[1]`, `[2]`… en orden de primera aparición contra
  [90_Bibliografia.md](90_Bibliografia.md), que tiene 55 entradas. Si se añade una fuente nueva
  hay que renumerar desde su punto de inserción.
- **Separador decimal coma, miles punto** — `0,22 €/kWh`, `13.700 puntos`.
- **Figuras y capturas** aparecen como marcadores `> **[FIGURA N.M]**` con la instrucción de qué
  debe mostrar cada una y cómo obtenerla. Hay 29 y hay que sustituirlos por la imagen real antes
  de entregar.
- **`> **PENDIENTE:**`** marca lo que queda por rellenar: medidas aún no tomadas y afirmaciones
  cuya fuente no se pudo verificar. Hay 19. Buscar esa palabra antes de dar la memoria por
  cerrada.

## Estado

Borrador completo de los quince capítulos, escrito contra el estado real del proyecto a 5 de
agosto de 2026: aplicación desplegada en `https://s-charge.app`, fases 1 a 5 terminadas y fases
6 a 13 diseñadas pero no construidas. Los capítulos distinguen en todo momento lo implementado
de lo diseñado; ninguno describe como funcionando algo que no lo está.

Pendiente de la revisión manual del autor, que es la que convierte el borrador en texto propio.
