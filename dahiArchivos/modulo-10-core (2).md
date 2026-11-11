# Módulo 10 · CORE

_Convertido desde `Flujo_de_Datos_del_Modulo_10_CORE_v5.xlsx` (hojas: Hoja1)._

## Hoja: Hoja1

> Documentación de Flujo de Datos del Módulo 10 - CORE

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/auth/login`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/login

**Estructura**

```
{"email": "string", "password": "string"}
```

**Ejemplo**

```
{"email": "jperez@uade.edu.ar", "password": "..."}
```

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/auth/refresh`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/refresh

**Estructura**

```
N/A (usa refreshToken en cookie httpOnly, no en el body)
```

**Ejemplo**

```
Rota el refresh token (7 días) y emite un nuevo access token (15 min) sin pedir credenciales de nuevo
```

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/auth/logout`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/logout

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
204 - revoca la sesión actual (denylist) y limpia la cookie de refresh
```

### Portales (Estud./Doc.) · Entrada — `GET /api/v1/auth/me`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/auth/me

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
{"id": "...", "email": "...", "roles": ["STUDENT"], "permissions": [...], "status": "ACTIVE"}
```

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/auth/password/forgot`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/password/forgot

**Estructura**

```
{"email": "string"}
```

**Ejemplo**

```
Dispara el flujo - alimenta el mock "Recuperar Acceso"
```

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/auth/password/reset`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/password/reset

**Estructura**

```
{"token": "string", "password": "string"}
```

**Ejemplo**

```
Aplica la nueva contraseña - alimenta el mock "Nueva Contraseña"
```

### Todos los Módulos · Entrada — `GET /.well-known/jwks.json`

- **Canal:** RESTful API
- **Identificador:** GET /.well-known/jwks.json

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
Es una "libreta pública" de firmas criptográficas. Permite que los otros módulos (Comedor, Biblioteca, etc.) validen que un pase de seguridad (token) es legítimo sin tener que consultarle al CORE a cada segundo.
```

### Todos los Módulos · Entrada — `POST /internal/v1/service-auth/token`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/service-auth/token

**Estructura**

```
{"clientId": "string", "clientSecret": "string"}
```

**Ejemplo**

```
Emite el token de servicio que cada módulo usa para llamar a los endpoints internos de CORE
```

### Todos los Módulos · Entrada — `POST /internal/v1/auth/introspect`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/auth/introspect

**Estructura**

```
{"token": "string"}
```

**Ejemplo**

```
{"active": true, ...} - reservado para operaciones sensibles/irreversibles, no reemplaza la validación local del JWT
```

### Backoffice · Entrada — `PUT /internal/v1/identities/{userId}`

- **Canal:** RESTful API
- **Identificador:** PUT /internal/v1/identities/{userId}

**Estructura**

```
{"email": "string", "roles": "array", "permissions": "array"}
```

**Ejemplo**

```
{"email": "jperez@...", "roles": ["STUDENT"], "permissions": ["wallet:read:self"]}
```

### Backoffice · Entrada — `PATCH /internal/v1/identities/{userId}/status`

- **Canal:** RESTful API
- **Identificador:** PATCH /internal/v1/identities/{userId}/status

**Estructura**

```
{"status": "INVITED | ACTIVE | SUSPENDED | DISABLED"}
```

**Ejemplo**

```
Cambia el estado de una identidad; mover a SUSPENDED revoca todas las sesiones activas de inmediato - alimenta el mock 'Login - Cuenta Suspendida'
```

### Backoffice · Entrada — `backoffice.user.upserted.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.user.upserted.v1

**Estructura**

```
{"userId": "string", "email": "string", "status": "string", "roles": "array"}
```

**Ejemplo**

```
{"userId": "ba310c57...", "email": "jperez@...", "status": "ACTIVE"}
```

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/wallets/me/top-ups`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/wallets/me/top-ups

**Estructura**

```
{"amount": "string", "currency": "string", "paymentMethodToken": "string"}
```

**Ejemplo**

```
{"amount": "5000.00", "currency": "ARS", "paymentMethodToken": "mock-approved"}
```

### Portales (Estud./Doc.) · Entrada — `GET /api/v1/wallets/me`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/wallets/me

**Estructura**

```
{"balance": "string", "currency": "string"}
```

**Ejemplo**

```
Consulta el saldo propio - alimenta la tarjeta "Saldo disponible" del mock
```

### Portales (Estud./Doc.) · Entrada — `GET /api/v1/wallets/me/transactions`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/wallets/me/transactions

**Estructura**

```
Lista paginada de movimientos propios
```

**Ejemplo**

```
Alimenta la tabla "Movimientos recientes" del mock
```

### Módulos de Cobro · Entrada — `POST /internal/v1/wallets/{userId}/debits`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/wallets/{userId}/debits

**Estructura**

```
{"amount": "string", "currency": "string", "concept": "string", "sourceModule": "string", "externalReference": "string"}
```

**Ejemplo**

```
{"amount": "1200.00", "currency": "ARS", "concept": "DINING_RESERVATION", "externalReference": "reservation/42"}
```

### Módulos de Cobro · Entrada — `POST /internal/v1/wallet-transactions/{id}/reversals`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/wallet-transactions/{id}/reversals

**Estructura**

```
{"reason": "string", "amount": "string?"}
```

**Ejemplo**

```
{"reason": "Usuario se presentó a la reserva"}
```

### Backoffice · Entrada — `POST /internal/v1/wallets/{userId}/credits`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/wallets/{userId}/credits

**Estructura**

```
{"amount": "string", "currency": "string", "concept": "string", "sourceModule": "string", "externalReference": "string"}
```

**Ejemplo**

```
{"amount": "480000.00", "currency": "ARS", "concept": "PAYROLL"}
```

### Todos los Módulos · Entrada — `POST /internal/v1/events`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/events

**Estructura**

```
{"eventId": "string", "eventType": "string", "source": "string", "data": "object"}
```

**Ejemplo**

```
{"eventId": "e3d2...", "eventType": "library.penalty.applied.v1", "data": {"amount": "2500.00"}}
```

### Módulos (Webhooks) · Entrada — `POST /internal/v1/subscriptions`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/subscriptions

**Estructura**

```
{"eventType": "string", "callbackUrl": "string"}
```

**Ejemplo**

```
{"eventType": "events.reminder.requested.v1", "callbackUrl": "https://events/callback"}
```

### Módulos (Webhooks) · Entrada — `GET /internal/v1/subscriptions`

- **Canal:** RESTful API
- **Identificador:** GET /internal/v1/subscriptions

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
Lista las suscripciones propias del módulo (scope por service-token)
```

### Módulos (Webhooks) · Entrada — `DELETE /internal/v1/subscriptions/{id}`

- **Canal:** RESTful API
- **Identificador:** DELETE /internal/v1/subscriptions/{id}

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
200 al dar de baja (respuesta vacía)
```

### Módulos (Webhooks) · Salida — `GET {callbackUrl}?topic=...&challenge=...`

- **Canal:** Webhook (callback HTTP)
- **Identificador:** GET {callbackUrl}?topic=...&challenge=...

**Estructura**

```
N/A (verificación de intención al suscribirse)
```

**Ejemplo**

```
GET https://library.uadenet.local/webhooks/uadenet?topic=library.penalty.applied.v1&challenge=abc123 → el módulo debe devolver el challenge en el body
```

### Módulos (Webhooks) · Salida — `POST {callbackUrl}`

- **Canal:** Webhook (callback HTTP)
- **Identificador:** POST {callbackUrl}

**Estructura**

```
Envelope completo + headers X-UADEnet-Event-Id, X-UADEnet-Signature: sha256=<hmac>
```

**Ejemplo**

```
{"eventId":"e3d2...","eventType":"library.penalty.applied.v1","data":{...}} - reintenta ante timeout/5xx/429
```

### Analítica Institucional · Entrada — `GET /internal/v1/wallets/aggregates`

- **Canal:** RESTful API
- **Identificador:** GET /internal/v1/wallets/aggregates

**Estructura**

```
{"range": "object", "currency": "string", "outstandingBalance": "string", "groups": "array"}
```

**Ejemplo**

```
{"outstandingBalance": "8452300.00", "groups": [{"key": "PAYROLL", "total": "10080000.00"}]}
```

### Analítica / Originante · Salida — `core.wallet.transaction-posted.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-posted.v1

**Estructura**

```
{"transactionId": "string", "userId": "string", "type": "string", "concept": "string", "amount": "string", "currency": "string"}
```

**Ejemplo**

```
{"transactionId": "386...", "type": "DEBIT", "concept": "STORE_PURCHASE", "amount": "3500.00"}
```

### Portales (Estud./Doc.) · Entrada — `GET /api/v1/notifications`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/notifications

**Estructura**

```
Query param opcional (read=true/false)
```

**Ejemplo**

```
Lista paginada - alimenta el historial del Centro de Notificaciones (el WebSocket solo empuja las nuevas)
```

### Portales (Estud./Doc.) · Entrada — `GET /api/v1/notifications/unread-count`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/notifications/unread-count

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
{"count": 2} - respalda el indicador de no leídas
```

### Portales (Estud./Doc.) · Entrada — `PATCH /api/v1/notifications/{id}`

- **Canal:** RESTful API
- **Identificador:** PATCH /api/v1/notifications/{id}

**Estructura**

```
{"read": "boolean"}
```

**Ejemplo**

```
Marca una notificación como leída al hacer click sobre ella
```

### Portales (Estud./Doc.) · Entrada — `POST /api/v1/notifications/read-all`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/notifications/read-all

**Estructura**

```
N/A (Sin body)
```

**Ejemplo**

```
204 - marca todas las notificaciones del usuario como leídas
```

### Portales (Estud./Doc.) · Salida — `notification.created`

- **Canal:** WebSocket
- **Identificador:** notification.created

**Estructura**

```
{"type": "string", "title": "string", "message": "string", "actionUrl": "string"}
```

**Ejemplo**

```
{"type": "LIBRARY_PENALTY_APPLIED", "title": "Sanción aplicada..."}
```
