---
status: borrador (redacción de la memoria, nivel conceptual)
---

# Skills de agente usadas en el desarrollo

El proyecto se ha desarrollado con asistencia de un agente de código (Claude Code). Una
**skill** es un conjunto de instrucciones empaquetado que el agente carga cuando la tarea lo
requiere: no añade capacidades nuevas al modelo, sino que fija *cómo* se aborda un tipo de tarea
concreto —qué comprobar, en qué orden, qué evitar—. En la práctica funcionan como procedimientos
de trabajo escritos: convierten en algo revisable y repetible criterios que de otro modo
quedarían implícitos.

Este capítulo deja constancia de cuáles se han usado y para qué, por dos razones:
**transparencia metodológica** —debe poder saberse cómo se construyó el trabajo— y
**reproducibilidad**, ya que las skills condicionan decisiones que se ven en el código.

## Skills usadas

| Skill | Cómo consta | Para qué se usa aquí |
| --- | --- | --- |
| `frontend-design` | Fijada en [skills-lock.json](../../skills-lock.json) el 2026-06-27 | Dirección visual y criterio tipográfico. Se incorporó al repositorio al adoptar el sistema de diseño oscuro *s-charge* y la arquitectura de información orientada a dashboard (fase 4). No se aplicó a la migración del frontend que se propuso y se descartó. |
| `documentation-and-adrs` | Invocada, 2026-08-01 | Gobierna cuándo y cómo se escribe documentación y registros de decisión. De ella sale la revisión que reorganizó [decisions/](../decisions/) y [tech-stack.md](../tech-stack.md); las reglas propias del proyecto —la única exclusión, el convenio local de identificadores— quedan en [decisions/README.md](../decisions/README.md), que registra solo las diferencias con la skill. |

El entorno del autor ofrece otras skills procedentes de trabajos distintos. **No se listan**: no han intervenido en este desarrollo, y enumerarlas daría una imagen falsa de la metodología. La lista crece cuando una skill se usa por primera vez, no antes — la regla operativa está en [AGENTS.md](../../AGENTS.md), y el procedimiento de instalación en un clon nuevo, en el [README](../../README.md).

Que el registro sea reproducible importa por lo mismo que importa un `lockfile` de dependencias: sin la versión exacta, "se usó tal skill" no es una afirmación verificable. Por eso el anclaje es un hash de contenido y no un nombre.

## Lectura para la defensa

Documentar las skills no pretende atribuir el trabajo a la herramienta; pretende lo contrario:
dejar explícito qué criterios estaban escritos y, por tanto, eran auditables. Un procedimiento
que dice "reproducir antes de arreglar" o "un ADR solo si la decisión condiciona la arquitectura"
es una decisión de ingeniería del autor, esté ejecutada por una persona o asistida por un agente.
Lo que no está escrito es lo que no se puede revisar.
