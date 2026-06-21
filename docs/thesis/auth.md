---
title: Autenticación
status: borrador (redacción de la memoria, nivel conceptual)
---

# Autenticación

Email/contraseña y Google OAuth mediante [`fastapi-users`](https://fastapi-users.github.io/fastapi-users/) — véase [decisions/auth-0001](../decisions/auth-0001-fastapi-users.md) para la elección de la librería. Los dos puntos en los que este proyecto se desvía deliberadamente de los valores por defecto de la librería están registrados en [decisions/auth-0002](../decisions/auth-0002-cookie-session.md) (transporte de la sesión) y [decisions/auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md) (modelo de amenazas de la vinculación de cuentas).

## Identidad

Claves primarias UUID v4 mediante `SQLAlchemyBaseUserTableUUID` de fastapi-users — no enumerables, 122 bits de entropía. Los emails se almacenan como `citext` (texto sin distinción de mayúsculas de PostgreSQL), normalizados a minúsculas y sin espacios en el esquema de entrada de Pydantic. La invariante de unicidad sin distinción de mayúsculas vive en la capa de base de datos, de modo que un código defectuoso no pueda permitir que `Alice@x.com` y `alice@x.com` se registren como cuentas distintas — el riesgo subyacente de apropiación de cuentas que crea la parte local sensible a mayúsculas del RFC 5321.

## Almacenamiento de contraseñas

Argon2id mediante [`pwdlib`](https://github.com/frankie567/pwdlib) (el sucesor moderno de `passlib`, incluido con fastapi-users) respaldado por `argon2-cffi`. Parámetros mínimos de OWASP (`memory_cost=19456`, `time_cost=2`, `parallelism=1`). El re-hash automático al verificar permite endurecer los parámetros de coste más adelante sin necesidad de migración. La política de contraseñas es solo de longitud (≥ 12 caracteres), alineada con NIST SP 800-63B § 5.1.1 — sin reglas de composición ni rotación forzada (ambas empujan a los usuarios hacia patrones predecibles).

Los fallos de autenticación devuelven un único `401 "Invalid credentials"` genérico con independencia de si el email existe; fastapi-users ejecuta un hash ficticio para el caso de usuario inexistente, de modo que el tiempo de respuesta no filtre la existencia de la cuenta (sin oráculo de enumeración de usuarios).

## Sesión

Un único JWT en una cookie `HttpOnly; Secure; SameSite=Lax` en la ruta `/`, con 14 días de vida, firmado con HS256 y audiencia `tfm:session`. Sin refresh tokens. Composición: `JWTStrategy + CookieTransport` en un único `AuthenticationBackend`. El patrón SPA de doble token se evita deliberadamente — justificación completa en [auth-0002](../decisions/auth-0002-cookie-session.md).

## OAuth (Google)

Integración del proveedor mediante [`httpx-oauth`](https://github.com/frankie567/httpx-oauth), expuesta a través del `get_oauth_router` de fastapi-users. Las identidades del proveedor viven en una tabla de unión separada `oauth_account` (mixin `SQLAlchemyBaseOAuthAccountTableUUID`) con una restricción de unicidad sobre `(oauth_name, account_id)` — escala a múltiples proveedores sin columnas dispersas por proveedor. `associate_by_email=True` permite a los usuarios recurrentes vincular Google a su cuenta de contraseña existente.

## Verificación de email y restablecimiento de contraseña

Los registros por contraseña quedan sin verificar por defecto y no pueden iniciar sesión hasta verificarse (`requires_verification=True` en el router de autenticación). Los usuarios de Google OAuth se verifican automáticamente (`is_verified_by_default=True`), puesto que Google ya ha demostrado el control de la dirección. Los tokens son los JWT de 1 hora por defecto de fastapi-users; la entrega se realiza mediante [Resend](https://resend.com). La combinación, junto con una sobreescritura de `UserManager.oauth_callback`, cierra el ataque de "cáscara" de pre-registro — justificación completa en [auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md).

## Registro de auditoría

Líneas en formato JSON en un logger `audit` dedicado hacia stdout (Docker las captura). Eventos cubiertos a día de hoy: `register`, `login_ok`, `verify_ok`, `reset_ok`, `email_send_failed`, `oauth_link_reset_password`. Dirigido por los hooks de `UserManager`. `login_fail` y `logout` carecen de hooks nativos y aún no están cubiertos.
