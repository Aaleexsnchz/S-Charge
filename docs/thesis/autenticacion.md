---
title: Autenticación
status: borrador (redacción de la memoria, nivel conceptual)
---

# Autenticación

Email/contraseña y Google OAuth mediante [`fastapi-users`](https://fastapi-users.github.io/fastapi-users/) — véase [decisions/auth-0001](../decisions/auth-0001-fastapi-users.md) para la elección de la librería. Los dos puntos en los que este proyecto se desvía deliberadamente de los valores por defecto de la librería están registrados en [decisions/auth-0002](../decisions/auth-0002-cookie-session.md) (transporte de la sesión) y [decisions/auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md) (modelo de amenazas de la vinculación de cuentas).

## Identidad

Claves primarias UUID v4 mediante `SQLAlchemyBaseUserTableUUID` de fastapi-users — no enumerables, 122 bits de entropía. Los emails se almacenan como `citext` (texto sin distinción de mayúsculas de PostgreSQL), normalizados a minúsculas y sin espacios en el esquema de entrada de Pydantic. La invariante de unicidad sin distinción de mayúsculas vive en la capa de base de datos, de modo que un código defectuoso no pueda permitir que `Alice@x.com` y `alice@x.com` se registren como cuentas distintas — el riesgo subyacente de apropiación de cuentas que crea la parte local sensible a mayúsculas del RFC 5321.

## Almacenamiento de contraseñas

Argon2id mediante [`pwdlib`](https://github.com/frankie567/pwdlib) (el sucesor moderno de `passlib`, incluido con fastapi-users) respaldado por `argon2-cffi`. Parámetros mínimos de OWASP (`memory_cost=19456`, `time_cost=2`, `parallelism=1`). El re-hash automático al verificar permite endurecer los parámetros de coste más adelante sin necesidad de migración. La política de contraseñas es solo de longitud (≥ 15 caracteres), sin reglas de composición ni rotación forzada — ambas prohibidas por NIST SP 800-63B-4 § 3.1.1, porque empujan a los usuarios hacia patrones predecibles. Los 15 son el mínimo que esa misma sección exige para una contraseña usada como **factor único**, que es este caso; ocho solo sería admisible dentro de una autenticación multifactor.

Los fallos de autenticación devuelven un único `401 "Invalid credentials"` genérico con independencia de si el email existe; fastapi-users ejecuta un hash ficticio para el caso de usuario inexistente, de modo que el tiempo de respuesta no filtre la existencia de la cuenta (sin oráculo de enumeración de usuarios).

## Sesión

Un único JWT en una cookie `HttpOnly; Secure; SameSite=Lax` en la ruta `/`, con 14 días de vida, firmado con HS256 y audiencia `s-charge:session`. Sin refresh tokens. Composición: `JWTStrategy + CookieTransport` en un único `AuthenticationBackend`. El patrón SPA de doble token se evita deliberadamente — justificación completa en [auth-0002](../decisions/auth-0002-cookie-session.md).

## OAuth (Google)

Integración del proveedor mediante [`httpx-oauth`](https://github.com/frankie567/httpx-oauth), expuesta a través del `get_oauth_router` de fastapi-users. Las identidades del proveedor viven en una tabla de unión separada `oauth_account` (mixin `SQLAlchemyBaseOAuthAccountTableUUID`) con una restricción de unicidad sobre `(oauth_name, account_id)` — escala a múltiples proveedores sin columnas dispersas por proveedor. `associate_by_email=True` permite a los usuarios recurrentes vincular Google a su cuenta de contraseña existente.

## Verificación de email y restablecimiento de contraseña

Los registros por contraseña quedan sin verificar por defecto y no pueden iniciar sesión hasta verificarse (`requires_verification=True` en el router de autenticación). Los usuarios de Google OAuth se verifican automáticamente (`is_verified_by_default=True`), puesto que Google ya ha demostrado el control de la dirección. Los tokens son los JWT de 1 hora por defecto de fastapi-users; la entrega se realiza mediante [Resend](https://resend.com). La combinación, junto con una sobreescritura de `UserManager.oauth_callback`, cierra el ataque de "cáscara" de pre-registro — justificación completa en [auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md).

## Registro de auditoría

Líneas en formato JSON en un logger `audit` dedicado hacia stdout (Docker las captura). Eventos cubiertos a día de hoy: `register`, `login_ok`, `verify_ok`, `reset_ok`, `email_send_failed`, `oauth_link_reset_password`. Dirigido por los hooks de `UserManager`. `login_fail` y `logout` carecen de hooks nativos y aún no están cubiertos.

## Límites de tasa y la identidad del cliente

Verificar el email frena el registro indiscriminado, pero no dice nada sobre los intentos contra cuentas que ya existen, y `/forgot-password` es un endpoint que envía correo a quien lo encuentre. Los límites son, por tanto, por IP y por ruta, con un criterio explícito: **el coste de un endpoint decide su ventana**. Login se limita por minuto, porque lo que se defiende es CPU y fuerza bruta; los endpoints que envían correo se limitan por hora, porque su coste no lo paga este servidor sino la bandeja de entrada de otra persona y la cuota del proveedor.

Detrás hay una dependencia que no es evidente: **un límite por IP no vale más que la IP en la que se apoya**. Tras un proxy inverso, la dirección que ve la aplicación es la del proxy, de modo que todo internet comparte un único contador y el primer atacante que alcanza el límite deja fuera a todos los usuarios a la vez. La protección se convierte en una denegación de servicio contra uno mismo. Arreglar el límite sin arreglar antes la cabecera reenviada no es un arreglo parcial: es peor que no hacer nada.

El *camino no tomado* fue confiar en las cabeceras reenviadas con un comodín. Es la receta habitual y se justifica diciendo que el backend no publica puertos, así que solo el proxy puede alcanzarlo. El razonamiento confunde dos cosas: impedir que alguien **rodee** el proxy no impide que envíe una cabecera **a través** de él. Con comodín, el servidor ASGI deja de recorrer la cadena `X-Forwarded-For` y toma su primer elemento, que es precisamente el que un cliente puede fijar; restringiendo la confianza a la subred del proxy, en cambio, recorre la cadena y se queda con el primer salto no confiable. Aquí el comodín resultaba seguro solo porque el proxy descarta lo que envíe el cliente — un valor por defecto de otro componente, que cambia en cuanto se antepone una CDN. Escribir la subred costaba lo mismo.

## Dónde está realmente la frontera

Durante buena parte del desarrollo la aplicación tuvo dos respuestas distintas a la misma pregunta. El cliente envolvía todas sus páginas en un guardia de ruta que redirige a `/login` sin sesión; la API, en cambio, servía el catálogo, los precios, el simulador y el listado de vehículos a cualquiera que conociera la URL. Nadie había decidido eso: la interfaz llevaba la decisión tomada desde el principio y el backend simplemente nunca la aplicó.

El error de razonamiento que lo sostiene merece nombrarse, porque es común. **Un guardia de ruta en el cliente no es control de acceso**: es navegación. Decide qué se pinta, no qué se sirve. El código que lo evalúa se ejecuta en el navegador del usuario, que puede ignorarlo, y de todos modos las URLs que la propia aplicación consulta son visibles en cualquier inspector. Todo lo que el navegador puede pedir, puede pedirlo también `curl`, y el servidor no dispone de ningún medio para distinguir "esta petición viene de mi frontend" de "esta petición viene de otro sitio": cualquier cabecera o valor que el cliente lleve consigo es igualmente visible y reproducible. La única frontera que existe es la que el servidor comprueba.

Un segundo razonamiento, más específico del despliegue, empujaba en la misma dirección equivocada: el contenedor del backend no publica puertos, luego "no está expuesto". Es cierto y es insuficiente. No publicar puertos impide **rodear** el proxy inverso; no impide llegar **a través** de él, que es exactamente lo que hace el navegador de cualquier usuario legítimo. Si esa ruta estuviera cerrada, la aplicación no funcionaría.

La corrección consiste en montar la dependencia de sesión sobre los routers completos y no endpoint a endpoint, de modo que un endpoint nuevo dentro de uno de ellos no pueda nacer sin protección. La prueba de regresión no enumera rutas a mano: las deriva del propio esquema de la aplicación y exige un `401` en todas salvo las deliberadamente públicas —comprobación de salud y la propia superficie de autenticación—. Enumerarlas a mano habría convertido la prueba en una lista que envejece, y su fallo silencioso sería precisamente el que no se quiere.

## La IP como dato personal

Registrar la IP del cliente introduce datos personales en los logs. El RGPD lo considera así incluso cuando la dirección es dinámica, porque identifica a una persona para quien pueda exigir legalmente la identidad del abonado (*Breyer*, TJUE C-582/14). La base jurídica es el interés legítimo del art. 6.1.f, y el considerando 49 menciona expresamente la seguridad de las redes y de la información: un registro de auditoría de autenticación y una clave de límite de tasa son ese caso, no una zona gris. Lo que obliga no es el consentimiento, sino informar, no reutilizar el dato para otros fines y **acotar la conservación**.

Ese último punto es el que revela algo interesante, porque el valor por defecto fallaba en la dirección insegura: Docker conserva los logs de los contenedores indefinidamente. El mismo descuido era a la vez un almacén de datos personales sin plazo y el riesgo de llenado de disco que nadie había limitado — una coincidencia frecuente entre protección de datos y operación. La rotación acota el **volumen**; la limitación del plazo exige acotar el **tiempo**, y eso queda pendiente junto al resto de obligaciones que este trabajo reconoce sin resolver. Registrarlo no lo resuelve; lo convierte en una decisión tomada en lugar de una omisión.

Se descartó llevar los eventos a una tabla de PostgreSQL, pese a que haría trivial el borrado por plazo: metería una escritura en la ruta de autenticación y empujaría datos personales hacia las copias de seguridad, cuya conservación es más larga y menos granular que la de los logs. Una tabla se justificaría si el historial de accesos llegara a mostrarse al usuario, pero eso sería una funcionalidad del producto y no un registro de seguridad — dos cosas que conviene no confundir por compartir los mismos campos.
