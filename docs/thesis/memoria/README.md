# Memoria del TFM

> **S-Charge: PWA para la gestión unificada de la recarga de vehículo eléctrico en España**

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
| 4 | [04_Arquitectura_del_sistema.md](04_Arquitectura_del_sistema.md) | Visión de conjunto, capas, contrato de API y stack |
| 5 | [05_Modelo_de_datos_y_fuentes.md](05_Modelo_de_datos_y_fuentes.md) | OCPI, espejo de REVE, siembra, precios y vehículos |
| 6 | [06_Autenticacion_y_seguridad.md](06_Autenticacion_y_seguridad.md) | Identidad, sesión, OAuth, límites de tasa y modelo de amenazas |
| 7 | [07_Funcionalidades_de_la_aplicacion.md](07_Funcionalidades_de_la_aplicacion.md) | Mapa, detalle, simulación, frontera de la simulación, funcionalidades de plataforma, **optimización de la carga** y **asistente de IA** |
| 8 | [08_Despliegue_operacion_y_escalado.md](08_Despliegue_operacion_y_escalado.md) | Producción, cadena de entrega, escalado argumentado y costes |
| 9 | [09_Validacion_y_resultados.md](09_Validacion_y_resultados.md) | Pruebas, medidas y verificación |
| 10 | [10_Marco_regulador.md](10_Marco_regulador.md) | AFIR, PVPC, RGPD, derechos sobre los datos y accesibilidad |
| 11 | [11_Entorno_socioeconomico.md](11_Entorno_socioeconomico.md) | Modelo de negocio, viabilidad, presupuesto y planificación |
| 12 | [12_Uso_de_IA_generativa.md](12_Uso_de_IA_generativa.md) | Uso de IA generativa en la elaboración del trabajo |
| 13 | [13_Conclusiones.md](13_Conclusiones.md) | Resultados, aprendizajes y trabajo futuro |
| — | [90_Bibliografia.md](90_Bibliografia.md) | Referencias en formato IEEE |
| — | [91_Anexos.md](91_Anexos.md) | Anexos |

## Convenciones

- **Citas en IEEE numerado**, ya resueltas: `[1]`, `[2]`… en orden de primera aparición contra
  [90_Bibliografia.md](90_Bibliografia.md), que tiene 60 entradas, todas citadas al menos una vez.
  Si se añade una fuente nueva hay que renumerar desde su punto de inserción, y revisar los rangos
  de la nota de verificación al final de la bibliografía.
- **Separador decimal coma, miles punto** — `0,22 €/kWh`, `13.700 puntos`.
- **Figuras y capturas** aparecen como marcadores `> **[FIGURA N.M]**` con la instrucción de qué
  debe mostrar cada una y cómo obtenerla. Hay 29 y hay que sustituirlos por la imagen real antes
  de entregar. Los cuatro de los capítulos 1 y 2 llevan solo el pie, porque la imagen ya existe
  en el documento del autor.
- **`> **PENDIENTE:**`** marca lo que queda por rellenar: medidas aún no tomadas y afirmaciones
  cuya fuente no se pudo verificar. Hay 21, contando los dos del guion de anexos. Buscar esa
  palabra antes de dar la memoria por cerrada.

## Estado

Borrador completo de los trece capítulos, escrito contra el estado real del proyecto a 5 de
agosto de 2026: aplicación desplegada en `https://s-charge.app`, fases 1 a 5 terminadas y las
restantes diseñadas pero no construidas. Los capítulos distinguen en todo momento lo implementado
de lo diseñado; ninguno describe como funcionando algo que no lo está.

Pendiente de la revisión manual del autor, que es la que convierte el borrador en texto propio.
