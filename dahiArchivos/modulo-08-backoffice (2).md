# Módulo 8 · Backoffice Administrativo

_Convertido desde `UADE_Flujo_de_Datos_Modulo8_Backoffice.xlsx` (hojas: Flujo de Datos, Dependencias, Datos maestros, API del portal, Notas y supuestos)._

## Hoja: Flujo de Datos

> Documentación de Flujo de Datos del Módulo 8 — Backoffice Administrativo
>
> UADEnet · Desarrollo de Aplicaciones II · Primera entrega (versión corregida 2026-10-04) · Contrato CORE v1 (2026-08-05)   |   Dirección = Salida: mi módulo inicia la llamada o publica el mensaje · Entrada: otro módulo llama a mi API o me entrega un mensaje

### CORE (Service Auth) · Salida — `POST /internal/v1/service-auth/token`

- **Canal:** Restful API
- **Identificador:** POST /internal/v1/service-auth/token

**Estructura**

```
Req: {"clientId": "string", "clientSecret": "string"}
Res 200: {"accessToken": "string", "expiresIn": number, "tokenType": "string"}
```

**Ejemplo**

```
Req: {"clientId": "backoffice-service", "clientSecret": "<env BACKOFFICE_CLIENT_SECRET>"}
Res: {"accessToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6...", "expiresIn": 900, "tokenType": "Bearer"}
```

### CORE (Auth) · Salida — `GET /.well-known/jwks.json`

- **Canal:** Restful API
- **Identificador:** GET /.well-known/jwks.json

**Estructura**

```
Res 200: {"keys": [{"kty": "RSA", "kid": "string", "alg": "RS256", "n": "string", "e": "string"}]}
```

**Ejemplo**

```
Res: {"keys": [{"kty": "RSA", "kid": "core-2026-08-a", "alg": "RS256", "n": "0vx7agoebGcQ...", "e": "AQAB"}]}
```

### CORE (Auth) · Salida — `POST /api/v1/auth/login`

- **Canal:** Restful API

**Identificador**

```
POST /api/v1/auth/login
(lo llama el frontend del portal de Backoffice, no el backend)
```

**Estructura**

```
Req: {"email": "string", "password": "string"}
Res 200: {"accessToken": "string", "expiresIn": number, "user": {"id": "uuid", "email": "string", "roles": ["string"], "permissions": ["string"], "status": "string"}}
+ cookie HttpOnly de refresh
```

**Ejemplo**

```
Req: {"email": "mrodriguez@uade.edu.ar", "password": "********"}
Res: {"accessToken": "eyJ...", "expiresIn": 900, "user": {"id": "7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b33", "email": "mrodriguez@uade.edu.ar", "roles": ["ADMIN_IT"], "permissions": ["backoffice:users:write", "backoffice:rates:write", "wallet:read:any"], "status": "ACTIVE"}}
```

### CORE (Gateway) · Entrada — `Headers de identidad inyectados en todo request a`

- **Canal:** Restful API

**Identificador**

```
Headers de identidad inyectados en todo request a
/api/v1/backoffice/*
```

**Estructura**

```
X-User-Id: uuid
X-User-Roles: csv
X-User-Permissions: csv
X-Correlation-Id: uuid
```

**Ejemplo**

```
X-User-Id: 7c2f1a90-3d55-4e21-9b8c-0a1f4d6e2b33
X-User-Roles: ADMIN_IT
X-User-Permissions: backoffice:users:write,wallet:read:any
X-Correlation-Id: f501201b-00bc-4200-99e0-6883500854f1
```

### CORE (Gateway) · Entrada — `GET /health/live`

- **Canal:** Restful API

**Identificador**

```
GET /health/live
GET /health/ready
```

**Estructura**

```
Res 200: {"status": "string", "checks": {"db": "string", "broker": "string"}}
```

**Ejemplo**

```
Res: {"status": "ok", "checks": {"db": "up", "broker": "up"}}
```

### CORE (Auth) · Salida — `PUT /internal/v1/identities/{userId}`

- **Canal:** Restful API

**Identificador**

```
PUT /internal/v1/identities/{userId}
(alta y modificación de identidad — camino elegido para el comando)
```

**Estructura**

```
Req: {"email": "string", "roles": ["STUDENT|TEACHER|ADMIN_IT|ADMIN_STAFF"], "permissions": ["string"]}
Res 200/201: {"userId": "uuid", "status": "string"}
Headers: Authorization (token de servicio), X-Service-Name: backoffice, X-Correlation-Id
No se envía status: el estado inicial lo asigna CORE, y los cambios de estado van por PATCH .../status.
```

**Ejemplo**

```
PUT /internal/v1/identities/ba310c57-a684-4dbf-a4a4-905fcfbefa08
{"email": "jperez@uade.edu.ar", "roles": ["STUDENT"], "permissions": ["wallet:read:self", "wallet:credit:self"]}
Res: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "status": "PENDING_ACTIVATION"}
```

### CORE (Auth) · Salida — `PATCH /internal/v1/identities/{userId}/status`

- **Canal:** Restful API

**Identificador**

```
PATCH /internal/v1/identities/{userId}/status
(suspensión, baja y rehabilitación)
```

**Estructura**

```
Req: {"status": "ACTIVE|SUSPENDED|DISABLED"}
Res 204: sin cuerpo
```

**Ejemplo**

```
PATCH /internal/v1/identities/ba310c57-a684-4dbf-a4a4-905fcfbefa08/status
{"status": "SUSPENDED"}
Res: 204
```

### CORE (Event Bus) · Salida — `POST /internal/v1/events`

- **Canal:** Restful API

**Identificador**

```
POST /internal/v1/events
(transporte único de los 4 eventos que publico)
```

**Estructura**

```
Req: envelope {specVersion, eventId, eventType, source, occurredAt, subject, correlationId, causationId, actor:{type,id}, data}
Header Idempotency-Key = eventId
Res 202: {"eventId": "uuid", "status": "ACCEPTED"}
```

**Ejemplo**

```
{"specVersion": "1.0", "eventId": "9f1c2d3e-77aa-4b10-90ce-5c4d1e77a201", "eventType": "backoffice.rate.changed.v1", "source": "backoffice", "occurredAt": "2026-09-05T14:02:11.004Z", "subject": "rate/LIBRARY_LATE_FEE", "correlationId": "f501201b-00bc-4200-99e0-6883500854f1", "causationId": null, "actor": {"type": "service", "id": "backoffice-service"}, "data": { ... }}
Res: {"eventId": "9f1c2d3e-77aa-4b10-90ce-5c4d1e77a201", "status": "ACCEPTED"}
```

### Analítica · Portales (proyección de directorio) · CORE Auth · Salida — `backoffice.user.upserted.v1`

- **Canal:** Message Queue

**Identificador**

```
backoffice.user.upserted.v1
(routing key = eventType, exchange uadenet.events.v1)
```

**Estructura**

```
Envelope estándar de CORE (ver hoja «Notas y supuestos») + data:
{"userId": "uuid", "email": "string", "status": "PENDING_ACTIVATION|ACTIVE|SUSPENDED|DISABLED", "roles": ["STUDENT|TEACHER|ADMIN_IT|ADMIN_STAFF"], "permissions": ["string"]}
Trae el estado completo del usuario, no el delta. Nombre, legajo, sede y carrera NO viajan: se consultan con GET /api/v1/backoffice/users/{userId}.
```

**Ejemplo**

```
data: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "email": "jperez@uade.edu.ar", "status": "ACTIVE", "roles": ["STUDENT"], "permissions": ["wallet:read:self", "wallet:credit:self"]}
```

### CORE (Auth) · Analítica · Salida — `backoffice.user.disabled.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.user.disabled.v1

**Estructura**

```
Envelope estándar de CORE (ver hoja «Notas y supuestos») + data:
{"userId": "uuid", "reason": "string"}
```

**Ejemplo**

```
data: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "reason": "BAJA_ACADEMICA"}
```

### Biblioteca · Comedor · Eventos · Salida — `backoffice.rate.changed.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.rate.changed.v1

**Estructura**

```
Envelope estándar de CORE (ver hoja «Notas y supuestos») + data:
{"rateType": "LIBRARY_LATE_FEE|DINING_RESERVATION|EVENT_REGISTRATION", "amount": "string decimal", "currency": "ARS", "effectiveFrom": "date-time ISO 8601 UTC (con hora, nunca sólo la fecha)"}
Es un aviso de cambio: no trae siteId, fin de vigencia ni category (general / especial de eventos). El monto exacto (por sede, categoría y fecha) se re-consulta con GET /api/v1/backoffice/rates.
```

**Ejemplo**

```
data: {"rateType": "LIBRARY_LATE_FEE", "amount": "2500.00", "currency": "ARS", "effectiveFrom": "2026-10-01T00:00:00.000Z"}
```

### Biblioteca · Comedor · Eventos · Gestión Académica · Analítica · Salida — `backoffice.location.upserted.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.location.upserted.v1

**Estructura**

```
Envelope estándar de CORE (ver hoja «Notas y supuestos») + data:
{"locationId": "uuid", "siteId": "uuid", "name": "string", "capacity": number, "status": "ACTIVE|INACTIVE"}
No trae code, type ni eventCapable: si los necesitan, re-consultar GET /api/v1/backoffice/locations/{locationId}. Las sedes no tienen evento propio.
```

**Ejemplo**

```
data: {"locationId": "c41a77b2-9e0d-4f36-8b21-77aa1c9de405", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "name": "Aula Magna - Sede Monserrat", "capacity": 320, "status": "ACTIVE"}
```

### CORE (Wallet) · Salida — `POST /internal/v1/wallets/{userId}/credits`

- **Canal:** Restful API

**Identificador**

```
POST /internal/v1/wallets/{userId}/credits
concept = PAYROLL (liquidación de sueldos)
```

**Estructura**

```
Headers: Idempotency-Key (UUID v4), X-Correlation-Id
Req: {"amount": "string decimal", "currency": "ARS", "concept": "PAYROLL", "sourceModule": "backoffice", "externalReference": "payroll/{periodo}/user/{userId}"}
Res 201: {"transactionId": "uuid", "status": "POSTED", "type": "CREDIT", "amount": "...", "balanceAfter": "...", "createdAt": "..."}
Res 4xx (p. ej. 404 WALLET_NOT_FOUND): el ítem de la liquidación queda RECHAZADO.
Timeout: se reintenta con la misma Idempotency-Key y externalReference; 409 DUPLICATE_REFERENCE = ya procesado, se adopta el transactionId.
```

**Ejemplo**

```
{"amount": "480000.00", "currency": "ARS", "concept": "PAYROLL", "sourceModule": "backoffice", "externalReference": "payroll/2026-09/user/ba310c57-a684-4dbf-a4a4-905fcfbefa08"}
Res: {"transactionId": "386865f7-c8aa-4aba-a374-ec9e6f8a6300", "status": "POSTED", "type": "CREDIT", "balanceAfter": "492750.00"}
```

### CORE (Wallet) · Salida — `POST /internal/v1/wallet-transactions/{transactionId}/reversals`

- **Canal:** Restful API

**Identificador**

```
POST /internal/v1/wallet-transactions/{transactionId}/reversals
(reversa de un sueldo mal liquidado)
```

**Estructura**

```
Headers: Idempotency-Key
Req: {"reason": "string"}  — amount se omite: revierte el total
Res 201: {"transactionId": "uuid", "originalTransactionId": "uuid", "type": "REVERSAL", "concept": "REFUND", "amount": "...", "balanceAfter": "..."}
La reversa se confirma con este 201 síncrono.
```

**Ejemplo**

```
POST /internal/v1/wallet-transactions/386865f7-c8aa-4aba-a374-ec9e6f8a6300/reversals
{"reason": "Liquidación duplicada del período 2026-09 — ticket OPS-1902"}
Res: {"transactionId": "0c3b6d21-9a44-4f7d-b2e8-15ac9f3d7e60", "originalTransactionId": "386865f7-...", "type": "REVERSAL", "concept": "REFUND", "amount": "480000.00"}
```

### CORE (Wallet) · Salida — `GET /internal/v1/wallets/{userId}`

- **Canal:** Restful API

**Identificador**

```
GET /internal/v1/wallets/{userId}
(saldo de un tercero — requiere wallet:read:any)
```

**Estructura**

```
Res 200: {"userId": "uuid", "balance": "string decimal", "currency": "ARS", "updatedAt": "ISO 8601"}
```

**Ejemplo**

```
Res: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "balance": "12750.00", "currency": "ARS", "updatedAt": "2026-09-05T14:20:03.117Z"}
```

### CORE (Wallet) · Entrada — `core.wallet.transaction-posted.v1`

- **Canal:** Message Queue

**Identificador**

```
core.wallet.transaction-posted.v1
cola backoffice.wallet-feedback.v1 (filtro sourceModule = backoffice)
Único evento de feedback de wallet que especifica CORE
```

**Estructura**

```
Envelope estándar de CORE (ver hoja «Notas y supuestos») + data:
{"transactionId": "uuid", "userId": "uuid", "type": "string", "concept": "string", "amount": "string", "currency": "ARS", "sourceModule": "string", "externalReference": "string", "status": "string"}
```

**Ejemplo**

```
data: {"transactionId": "386865f7-c8aa-4aba-a374-ec9e6f8a6300", "userId": "ba310c57-...", "type": "CREDIT", "concept": "PAYROLL", "amount": "480000.00", "currency": "ARS", "sourceModule": "backoffice", "externalReference": "payroll/2026-09/user/ba310c57-...", "status": "POSTED"}
→ marco el ítem de la liquidación como ACREDITADO
```

### Portal Estudiante · Portal Docente · Biblioteca · Comedor · Tienda · Eventos · Analítica · Entrada — `GET /api/v1/backoffice/users/{userId}`

- **Canal:** Restful API

**Identificador**

```
GET /api/v1/backoffice/users/{userId}
(mi backend recibe GET /api/v1/users/{userId})
Usuario logueado: userId = header X-User-Id = sub del JWT
```

**Estructura**

```
Res 200: {"userId": "uuid", "email": "string", "firstName": "string", "lastName": "string", "documentId": "string", "fileNumber": "string", "roles": ["STUDENT|TEACHER|ADMIN_IT|ADMIN_STAFF"], "status": "PENDING_ACTIVATION|ACTIVE|SUSPENDED|DISABLED", "siteId": "uuid", "careerId": "uuid|null"}
careerId referencia el catálogo de Gestión Académica. Res 404 si el userId no existe.
```

**Ejemplo**

```
Res: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "email": "jperez@uade.edu.ar", "firstName": "Juan", "lastName": "Pérez", "documentId": "40123456", "fileNumber": "1102345", "roles": ["STUDENT"], "status": "ACTIVE", "siteId": "3e9b0a12-...", "careerId": "a77c1e40-..."}
```

### Portales · Analítica · Gestión Académica · Entrada — `GET /api/v1/backoffice/users?role=&siteId=&status=&cursor=&limit=`

- **Canal:** Restful API

**Identificador**

```
GET /api/v1/backoffice/users?role=&siteId=&status=&cursor=&limit=
(directorio paginado)
```

**Estructura**

```
Res 200: {"items": [ {ficha de usuario} ], "nextCursor": "string|null"}  — límite 100
```

**Ejemplo**

```
GET /api/v1/backoffice/users?role=TEACHER&siteId=3e9b0a12-...&limit=20
Res: {"items": [{"userId": "5f0a...", "firstName": "Ana", "lastName": "Gómez", "roles": ["TEACHER"], "status": "ACTIVE"}], "nextCursor": null}
```

### Biblioteca · Comedor · Eventos · Entrada — `GET /api/v1/backoffice/rates?rateType=&category=&siteId=&at=`

- **Canal:** Restful API

**Identificador**

```
GET /api/v1/backoffice/rates?rateType=&category=&siteId=&at=
(carga inicial y monto exacto: el evento sólo avisa que cambió)
```

**Estructura**

```
Res 200: lista [{"rateId": "uuid", "rateType": "LIBRARY_LATE_FEE|DINING_RESERVATION|EVENT_REGISTRATION", "category": "GENERAL|SPECIAL|null", "siteId": "uuid|null (null = tarifa global)", "amount": "string decimal", "currency": "ARS", "effectiveFrom": "date-time UTC", "effectiveTo": "date-time UTC|null", "status": "PROGRAMADA|VIGENTE|DEROGADA"}]
Con rateType + at devuelve 0 o 1 elemento. Lista vacía = no hay tarifa vigente a esa fecha. Con siteId devuelve la de la sede si existe; si no, la global.
category sólo aplica a EVENT_REGISTRATION: es la categoría de precio del evento (general / especial). Sin category devuelve las dos.
```

**Ejemplo**

```
GET /api/v1/backoffice/rates?rateType=EVENT_REGISTRATION&category=SPECIAL&at=2026-10-05T12:00:00.000Z
Res: [{"rateId": "e2a9c4f1-6b3d-4a87-9c10-5d2e8f7a1b44", "rateType": "EVENT_REGISTRATION", "category": "SPECIAL", "siteId": null, "amount": "8000.00", "currency": "ARS", "effectiveFrom": "2026-09-01T00:00:00.000Z", "effectiveTo": null, "status": "VIGENTE"}]
```

### Biblioteca · Entrada — `GET /api/v1/backoffice/rates/library-late-fee?at=`

- **Canal:** Restful API

**Identificador**

```
GET /api/v1/backoffice/rates/library-late-fee?at=
(multa por devolución tardía: las dos piezas juntas)
```

**Estructura**

```
Res 200: {"base": {Rate}, "daily": {Rate}}  — mismo objeto Rate que GET /rates.
Cálculo a cargo de Biblioteca: multa = base + daily × (díasDeAtraso − 7), sólo si díasDeAtraso > 7 (7 días de tolerancia, TPO §3). Global: no varía por sede ni por material.
```

**Ejemplo**

```
GET /api/v1/backoffice/rates/library-late-fee?at=2026-10-05T12:00:00.000Z
Res: {"base": {"rateId": "1b7d...", "rateType": "LIBRARY_LATE_FEE", "siteId": null, "amount": "5000.00", "currency": "ARS", "effectiveFrom": "2026-08-01T00:00:00.000Z", "effectiveTo": null, "status": "VIGENTE"}, "daily": {"rateId": "9c42...", "rateType": "LIBRARY_LATE_FEE", "siteId": null, "amount": "500.00", "currency": "ARS", "effectiveFrom": "2026-08-01T00:00:00.000Z", "effectiveTo": null, "status": "VIGENTE"}}
→ 10 días de atraso: 5000.00 + 500.00 × 3 = 6500.00
```

### Biblioteca · Comedor · Eventos · Gestión Académica · Tienda · Analítica · Entrada — `GET /api/v1/backoffice/sites?status=&cursor=&limit=`

- **Canal:** Restful API

**Identificador**

```
GET /api/v1/backoffice/sites?status=&cursor=&limit=
GET /api/v1/backoffice/sites/{siteId}
(las sedes no tienen evento: se consultan y se cachean)
```

**Estructura**

```
Res 200 (lista): {"items": [{"siteId": "uuid", "code": "string", "name": "string", "address": "string", "city": "string", "province": "string|null", "country": "string", "timezone": "IANA", "status": "ACTIVE|INACTIVE", "updatedAt": "date-time UTC"}], "nextCursor": "string|null"}  — límite 100
Res 200 (detalle): el mismo objeto sede, sin lista. Baja siempre lógica (status = INACTIVE).
```

**Ejemplo**

```
GET /api/v1/backoffice/sites?status=ACTIVE
Res: {"items": [{"siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "code": "MONSERRAT", "name": "Sede Monserrat", "address": "Lima 775", "city": "CABA", "province": null, "country": "Argentina", "timezone": "America/Argentina/Buenos_Aires", "status": "ACTIVE", "updatedAt": "2026-09-10T13:00:00.000Z"}], "nextCursor": null}
```

### Gestión Académica · Comedor · Eventos · Biblioteca · Entrada — `GET /api/v1/backoffice/locations?siteId=&type=&eventCapable=&status=&cursor=&limit=`

- **Canal:** Restful API

**Identificador**

```
GET /api/v1/backoffice/locations?siteId=&type=&eventCapable=&status=&cursor=&limit=
GET /api/v1/backoffice/sites/{siteId}/locations?type=&eventCapable= (los espacios de una sede)
GET /api/v1/backoffice/locations/{locationId}
```

**Estructura**

```
Res 200: {"items": [{"locationId": "uuid", "siteId": "uuid", "code": "string", "name": "string", "type": "AULA|LABORATORIO|AUDITORIO|SALA_EVENTOS|COMEDOR|BIBLIOTECA|OFICINA|DEPOSITO|OTRO", "capacity": number, "eventCapable": boolean, "status": "ACTIVE|INACTIVE|MAINTENANCE"}], "nextCursor": "string|null"}
capacity = límite físico del espacio. El cupo de cada uso (comisión, evento, turno) lo fija cada módulo y debe ser ≤ capacity. Para eventos: filtrar con eventCapable=true y status=ACTIVE.
```

**Ejemplo**

```
GET /api/v1/backoffice/sites/3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90/locations?eventCapable=true
Res: {"items": [{"locationId": "c41a77b2-9e0d-4f36-8b21-77aa1c9de405", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "code": "AM-01", "name": "Aula Magna - Sede Monserrat", "type": "SALA_EVENTOS", "capacity": 320, "eventCapable": true, "status": "ACTIVE"}], "nextCursor": null}
```

## Hoja: Dependencias

> Mapa de dependencias — Módulo 8: Backoffice Administrativo

| Módulo | Relación | Qué dato o servicio | Canal | Criticidad |
|---|---|---|---|---|
| CORE — Auth | Depende de mí | Identidades: userId (UUID v4 que genero yo), email, roles, permisos y estado. Sin esto nadie puede loguearse a ningún módulo. | REST /internal/v1/identities + backoffice.user.upserted.v1 | Crítica |
| CORE — Wallet | Depende de mí | Existencia de la identidad: sin identidad provisionada no hay wallet y todo débito devuelve 404 WALLET_NOT_FOUND. | REST /internal/v1/identities | Crítica |
| Biblioteca | Depende de mí | Monto de la multa por devolución tardía (base + diaria, rateType = LIBRARY_LATE_FEE), catálogo de sedes para asociar el stock y ficha del usuario. | backoffice.rate.changed.v1 · backoffice.location.upserted.v1 · GET /rates/library-late-fee · GET /sites · GET /users/{userId} | Crítica |
| Comedor | Depende de mí | Costo de la reserva por sede (rateType = DINING_RESERVATION), sedes y espacio de comedor con su capacidad. El costo debe figurar al reservar. | backoffice.rate.changed.v1 · backoffice.location.upserted.v1 · GET /rates?rateType=DINING_RESERVATION&siteId= · GET /sites · GET /locations?type=COMEDOR · GET /users/{userId} | Crítica |
| Eventos Académicos | Depende de mí | Precio de inscripción paga por categoría del evento (rateType = EVENT_REGISTRATION, category = GENERAL / SPECIAL), locaciones aptas para eventos (eventCapable) con su capacidad física, nombre de la sede y ficha del usuario. | backoffice.rate.changed.v1 · backoffice.location.upserted.v1 · GET /rates?rateType=EVENT_REGISTRATION&category= · GET /locations · GET /sites · GET /users/{userId} | Crítica |
| Gestión Académica | Depende de mí | Catálogo de sedes y aulas físicas con su capacidad, para planificar horarios y asignaciones. | backoffice.location.upserted.v1 · GET /sites · GET /locations?type=AULA\|LABORATORIO | Crítica |
| Analítica Institucional | Depende de mí | Altas, bajas y roles de usuarios para segmentar los dashboards; sedes para agrupar. Los gastos administrativos los obtiene de CORE por concept = PAYROLL, no de mí. | backoffice.user.upserted.v1 · backoffice.user.disabled.v1 · backoffice.location.upserted.v1 · GET /users · GET /sites (carga inicial) | Media |
| Portal del Estudiante / Portal del Docente | Depende de mí | Ficha de la persona para mostrar en pantalla: nombre, apellido, legajo, carrera. GET /auth/me de CORE no es un directorio. | backoffice.user.upserted.v1 + GET /api/v1/backoffice/users/{userId} (para el usuario logueado, userId = X-User-Id) | Media |
| Tienda del Campus | Depende de mí | Catálogo de sedes para el inventario por sede, y rol/permisos del administrativo de tienda habilitado a gestionar stock. | GET /sites · backoffice.user.upserted.v1 | Media |
| CORE — Gateway | Yo dependo | Enrutamiento de /api/v1/backoffice/* hacia BACKOFFICE_SERVICE_URL y headers X-User-* con la identidad ya verificada. | REST (gateway) | Crítica |
| CORE — Auth | Yo dependo | Login del portal de Backoffice, emisión y rotación de tokens, JWKS para validar el JWT localmente, y el flujo de activación de contraseña del usuario nuevo. | REST /api/v1/auth/* · GET /.well-known/jwks.json | Crítica |
| CORE — Service Auth | Yo dependo | clientId y clientSecret propios para poder hablar con /internal/v1/*. | REST /internal/v1/service-auth/token | Crítica |
| CORE — Wallet | Yo dependo | Único lugar donde se mueve plata: créditos de sueldos (PAYROLL), reversas y consulta de saldo de terceros. No puedo fijar un saldo. | REST /internal/v1/wallets/* | Crítica |
| CORE — Event Bus | Yo dependo | Publicación de mis 4 eventos (outbox de CORE) y entrega de core.wallet.transaction-posted.v1 a mi cola. | REST /internal/v1/events · RabbitMQ | Crítica |
| Otros módulos de negocio | Yo dependo | De ninguno. Backoffice es fuente de datos maestros, no consumidor de negocio: el único feedback que consumo es el de las transacciones que yo mismo originé. | — | — |

## Hoja: Datos maestros

> Datos maestros que administra Backoffice (soy el dueño de estos datos)

| Entidad | Campos | Se publica como | Quién lo consume | Observación |
|---|---|---|---|---|
| Identidad / Usuario | userId (UUID v4, lo genero yo) · email institucional · firstName · lastName · documentId · fileNumber (legajo) · roles[] (STUDENT / TEACHER / ADMIN_IT / ADMIN_STAFF) · permissions[] · status (PENDING_ACTIVATION / ACTIVE / SUSPENDED / DISABLED) · siteId · careerId | backoffice.user.upserted.v1 + PUT /internal/v1/identities + GET /users/{userId} | CORE Auth, Analítica, todos los portales | Nunca almaceno hashes de contraseña: la contraseña la fija el usuario contra CORE (POST /api/v1/auth/activate). |
| Rol y permiso | roleId · name · module · permissions[] con formato {modulo}:{recurso}:{acción} | Embebido en backoffice.user.upserted.v1 | CORE Auth (autorización), cada módulo al validar el JWT | El catálogo de permisos hay que acordarlo con los 9 módulos: si un módulo espera un permiso que yo no emito, su endpoint queda inaccesible. |
| Tarifa | rateId · rateType (LIBRARY_LATE_FEE / DINING_RESERVATION / EVENT_REGISTRATION) · category (GENERAL / SPECIAL, sólo eventos) · siteId (null = global) · amount (string decimal) · currency (ARS) · effectiveFrom · effectiveTo · status (PROGRAMADA / VIGENTE / DEROGADA) · createdBy | backoffice.rate.changed.v1 + GET /rates + GET /rates/library-late-fee | Biblioteca, Comedor, Eventos | Guardo el histórico completo con vigencias: una reserva vieja tiene que poder auditarse con la tarifa que regía ese día. |
| Sede | siteId · code · name · address · city · province · country · timezone (IANA) · status (ACTIVE / INACTIVE) · updatedAt | Sin evento propio: GET /sites y GET /sites/{siteId} | Biblioteca, Comedor, Eventos, Académica, Tienda, Analítica | CORE no conoce sedes: la dimensión «sede» de los dashboards sale de mí y de los eventos de cada módulo. |
| Ubicación / Espacio | locationId · siteId · code · name · type (AULA / LABORATORIO / AUDITORIO / SALA_EVENTOS / COMEDOR / BIBLIOTECA / OFICINA / DEPOSITO / OTRO) · capacity (física) · eventCapable · status (ACTIVE / INACTIVE / MAINTENANCE) | backoffice.location.upserted.v1 + GET /locations | Académica (aulas), Eventos (locaciones), Comedor, Biblioteca | Yo soy dueño del catálogo físico. capacity es el límite físico: el cupo de cada uso lo fija el módulo y debe ser ≤ capacity. La asignación de horarios es de Académica y la reserva de locación para un evento es de Eventos: yo no valido superposiciones. |
| Legajo salarial | userId · position · baseSalary {amount, currency} · hireDate · payrollStatus | No se publica en ningún evento | Sólo mi módulo | Dato sensible. Sólo se materializa hacia afuera como un crédito PAYROLL en la wallet; Analítica lo ve agregado por concept, nunca por persona. |
| Liquidación (payroll run) | payrollRunId · period (AAAA-MM) · status · items[] {userId, amount, transactionId, status} | No se publica | Sólo mi módulo | Guardo el transactionId que devuelve CORE junto a cada ítem: es lo que me permite revertir y reconciliar. |

## Hoja: API del portal

> API expuesta al portal de Backoffice (frontend propio → gateway de CORE → mi backend)
>
> Ruta pública por el gateway: /api/v1/backoffice/*  →  mi backend recibe /api/v1/*. El portal nunca llama al backend directo.

| Vista del portal | Endpoint (ruta pública) | Qué hace | Efecto hacia afuera |
|---|---|---|---|
| Login | POST /api/v1/auth/login (CORE) | Autentica al administrativo. No implemento login propio. | — |
| ABM de usuarios — listado | GET /api/v1/backoffice/users?role=&siteId=&status=&q=&sort=&cursor=&limit=<br>POST /api/v1/backoffice/users/searches | Directorio paginado con filtros y orden; q busca por nombre. La búsqueda por documento o email va en el body (POST), nunca en la URL. | — |
| ABM de usuarios — alta | POST /api/v1/backoffice/users | Genero el userId (UUID v4) y persisto la ficha. | PUT /internal/v1/identities/{userId} + backoffice.user.upserted.v1 |
| ABM de usuarios — edición | PATCH /api/v1/backoffice/users/{userId} | Actualizo datos personales, sede o carrera. | backoffice.user.upserted.v1 (y PUT si cambian email/roles/permisos) |
| ABM de usuarios — estado | PUT /api/v1/backoffice/users/{userId}/status | Suspende, da de baja o rehabilita. | PATCH /internal/v1/identities/{userId}/status + backoffice.user.disabled.v1 |
| Roles y permisos | PUT /api/v1/backoffice/users/{userId}/roles<br>GET /api/v1/backoffice/roles | Asigna roles y permisos específicos por módulo. | PUT /internal/v1/identities/{userId} + backoffice.user.upserted.v1 |
| Parametrización tarifaria | GET /api/v1/backoffice/rates<br>POST /api/v1/backoffice/rates | Alta de una tarifa con fecha de vigencia. | backoffice.rate.changed.v1 |
| Sedes y espacios | GET/POST /api/v1/backoffice/sites<br>GET/PATCH /api/v1/backoffice/sites/{siteId}<br>PUT /api/v1/backoffice/sites/{siteId}/status<br>GET /api/v1/backoffice/sites/{siteId}/locations<br>GET/POST /api/v1/backoffice/locations<br>GET/PATCH /api/v1/backoffice/locations/{locationId} | Catálogo de sedes y espacios con capacidad. Baja siempre lógica, nunca DELETE. | backoffice.location.upserted.v1 (sólo espacios: las sedes no tienen evento) |
| Liquidación de sueldos — armado | POST /api/v1/backoffice/payroll-runs | Crea el período y calcula los ítems. Todavía no mueve plata. | — |
| Liquidación de sueldos — aprobación | POST /api/v1/backoffice/payroll-runs/{payrollRunId}/approve | Pasa la corrida de EN_REVISION a APROBADA. No la puede aprobar quien la generó (segregación de funciones). | — |
| Liquidación de sueldos — ejecución | POST /api/v1/backoffice/payroll-runs/{payrollRunId}/execute | Dispara un crédito PAYROLL por cada ítem, con Idempotency-Key propia. | POST /internal/v1/wallets/{userId}/credits (N llamadas) |
| Liquidación de sueldos — seguimiento | GET /api/v1/backoffice/payroll-runs/{payrollRunId}/items | Estado por persona: PENDIENTE / ACREDITADO / RECHAZADO. | Respuesta síncrona del crédito (201 = ACREDITADO, 4xx = RECHAZADO) + core.wallet.transaction-posted.v1 |
| Consulta de saldo de un usuario | GET /api/v1/backoffice/users/{userId}/wallet | Muestra el saldo de un tercero (requiere wallet:read:any). | GET /internal/v1/wallets/{userId} |

## Hoja: Notas y supuestos

> Notas, reglas del contrato CORE v1 y supuestos a confirmar

| Tipo | Tema | Detalle |
|---|---|---|
| Convención | Lectura de la columna «Dirección» | Salida = mi módulo inicia la llamada HTTP o publica el mensaje. Entrada = otro módulo llama a mi API por el gateway o el broker me entrega un mensaje. En las filas REST de salida, «Estructura» muestra request y response porque el dato viaja en los dos sentidos. |
| Convención | Eventos = aviso, REST = dato completo | Los eventos llevan sólo el data que fija el catálogo de CORE. rate.changed.v1 no trae siteId ni fin de vigencia; location.upserted.v1 no trae code, type ni eventCapable; las sedes no tienen evento. Patrón para todos los consumidores: carga inicial por REST, cambios por evento y, al recibir el evento, re-consulta por REST si necesitan el detalle. |
| Convención | Datos del usuario logueado | El userId del usuario logueado es el header X-User-Id que inyecta el gateway: es el mismo UUID que el sub del JWT y que el userId de Backoffice. La ficha (nombre, legajo, sede, carrera) se pide con GET /api/v1/backoffice/users/{userId}. Roles del contrato: STUDENT, TEACHER, ADMIN_IT, ADMIN_STAFF. |
| Regla CORE | El userId lo genero yo | Es un UUID v4 y es la clave con la que todo el ecosistema referencia personas. Ningún módulo puede inventar su propio id ni referenciar gente por email o legajo. |
| Regla CORE | Ruteo por gateway | El portal pide https://core/api/v1/backoffice/users/123 y mi backend recibe GET /api/v1/users/123. El gateway no transforma la respuesta, tiene timeout de 10 s y no reintenta POST/PATCH/DELETE. |
| Regla CORE | Dos identidades distintas | El token del usuario nunca se usa para /internal/v1/*, y el token de servicio nunca se usa para operar en nombre de un usuario. Mi backend valida igual el JWT contra el JWKS cacheado (defensa en profundidad), sin llamar a introspect en cada request. |
| Regla CORE | Envelope de eventos | {"specVersion": "1.0", "eventId": uuid v4, "eventType": del catálogo con sufijo de versión, "source": "backoffice", "occurredAt": cuándo pasó el hecho de negocio, "subject": "tipo/id", "correlationId": el que venía propagando, "causationId": eventId disparador o null, "actor": {"type": "service", "id": "backoffice-service"}, "data": {...}}. La routing key es idéntica al eventType. |
| Regla CORE | Idempotencia financiera | Toda escritura de plata lleva Idempotency-Key (UUID v4, una por intento lógico) y una externalReference estable derivada de mi entidad. Nunca un timestamp, un random ni un contador local. |
| Regla CORE | Timeout en un crédito | CORE no especifica una consulta por referencia. Ante un timeout se reintenta con la misma Idempotency-Key y la misma externalReference, nunca con nuevas: si el crédito ya se había procesado, CORE responde 409 DUPLICATE_REFERENCE con el transactionId original y lo adopto. |
| Regla CORE | 409 y 422 no son errores inesperados | 409 DUPLICATE_REFERENCE → adopto el transactionId que viene en la respuesta. 409 IDEMPOTENCY_CONFLICT → bug mío, estoy reusando una key. 422 WALLET_INSUFFICIENT_FUNDS → caso de negocio, se informa y no se reintenta. Programo contra `code`, nunca contra `detail`. |
| Riesgo | Reversa de un sueldo ya gastado | Revertir un crédito debita, así que puede dar 422 por saldo insuficiente si la persona ya usó la plata. No es un error del sistema: queda como saldo a compensar en la liquidación siguiente. |
| Regla CORE | Consumo de eventos | Cola propia backoffice.wallet-feedback.v1, pedida por PR sobre contracts/topology.yaml (durable, deadLetter uadenet.dlx.v1, maxRetries 3). No declaro exchanges ni queues desde el código. Ack manual recién después de persistir, prefetch 10-50, y tabla inbox_messages con PK event_id para deduplicar reentregas. |
| Regla CORE | Datos sensibles fuera de los eventos | Los sueldos no viajan en ningún evento. Analítica ve los gastos administrativos agregados con GET /internal/v1/wallets/aggregates?groupBy=concept filtrando PAYROLL, sin identificador de persona. |
| Regla CORE | Lo que no puedo hacer | No almaceno hashes de contraseña, no puedo fijar un saldo directamente (sólo CREDIT / DEBIT / REVERSAL) y no puedo cobrar en nombre de otro módulo: el sourceModule tiene que coincidir con mi token o CORE devuelve 403. |
| Regla CORE | Formatos | JSON UTF-8 en camelCase · IDs UUID v4 · fechas ISO 8601 en UTC · dinero como string decimal de dos decimales con la moneda aparte, nunca float · paginación ?cursor=&limit= (máx. 100) · errores con HTTP status + código interno (code) en application/problem+json · auth OAuth 2.0 con JWT · X-Correlation-Id propagado en llamadas, eventos y logs. |
| Decisión | Un solo camino de provisioning | El contrato pide elegir entre PUT /internal/v1/identities/{userId} y publicar backoffice.user.upserted.v1, y no usar los dos para el mismo comando. Elegimos el PUT como comando, porque necesitamos confirmación sincrónica antes de poder acreditar un sueldo (sin identidad, el crédito devuelve 404 WALLET_NOT_FOUND) y porque el ABM necesita responderle algo al operador en pantalla. |
| A confirmar con CORE | El evento junto con el PUT | Aun usando el PUT, Analítica y los portales necesitan backoffice.user.upserted.v1, que en el catálogo también lo consume CORE Auth. Hay que preguntarle al equipo de CORE si Auth ignora el evento cuando ya recibió el PUT (upsert idempotente por userId) o si conviene pasar todo al camino por evento. Es la única ambigüedad que no resolvimos por nuestra cuenta. |
| Supuesto | Body de PUT /internal/v1/identities/{userId} | Enviamos email, roles y permissions. CORE no especifica status en este body: el estado inicial lo asigna CORE y los cambios de estado van por PATCH /internal/v1/identities/{userId}/status. |
| Supuesto | rateType EVENT_REGISTRATION | El contrato sólo nombra explícitamente LIBRARY_LATE_FEE y DINING_RESERVATION, pero el enunciado nos pide parametrizar también el precio de las inscripciones a eventos. Proponemos EVENT_REGISTRATION, alineado con el concept homónimo de la wallet. Acordado con Eventos: dos categorías de precio, GENERAL y SPECIAL. La categoría es del evento, no de quien se inscribe; un evento gratuito no lleva tarifa. Por REST viaja en el campo category; el evento rate.changed.v1 no la trae. |
| Supuesto | Catálogo de permisos | Formato {modulo}:{recurso}:{acción}, por ejemplo backoffice:users:write, library:stock:write, store:stock:write, events:manage, analytics:finance:read, wallet:read:any. Hay que acordarlo con los otros ocho grupos: es el contrato más transversal del sistema. |
| Regla de negocio | Multa de biblioteca | Backoffice define dos montos globales bajo LIBRARY_LATE_FEE: base y diaria. multa = base + diaria × (díasDeAtraso − 7), sólo si díasDeAtraso > 7. Detectar el atraso, calcular y debitar (concept LIBRARY_FINE) es de Biblioteca. Como el evento tiene un solo rateType, no distingue cuál de los dos cambió: Biblioteca lo usa como disparador y re-consulta GET /rates/library-late-fee. |
| Límite acordado | Espacios físicos | Yo soy dueño del catálogo (sede, ubicación, capacidad, estado). La planificación de horarios y la asignación de aulas es de Gestión Académica, y la reserva de una locación para un evento con su control de superposición es de Eventos. Yo no valido disponibilidad. |
| Límite acordado | Carreras y planes | El catálogo de carreras y planes de estudio es de Gestión Académica. En la ficha del usuario guardo careerId como referencia a ese catálogo, no como dato propio. |
| Límite acordado | Multas y cobros | Yo defino el monto de la multa de biblioteca, pero el débito lo hace Biblioteca con concept LIBRARY_FINE. Backoffice nunca cobra en nombre de otro módulo. |
| Límite acordado | Alcance financiero: sólo sueldos | La wallet de CORE también acepta concept SCHOLARSHIP (becas) y ADJUSTMENT (ajustes), pero no son responsabilidad de Backoffice (decisión del PO). Mi única escritura de plata es el crédito PAYROLL de cada liquidación, más su reversa si estuvo mal liquidado. |
