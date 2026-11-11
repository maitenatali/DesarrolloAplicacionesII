# Módulo 7 · Analítica Institucional

_Convertido desde `Flujo_de_Datos_Modulo_7_Analitica.xlsx` (hojas: Flujo de Datos)._

## Hoja: Flujo de Datos

> Documentación de Flujo de Datos del Módulo 7 — UADEnet · Analítica Institucional
>
> Alineado al contrato de integración CORE v1 (2026-08-05). Entrada = un módulo externo nos envía datos · Salida = este módulo entrega datos a otro.

### CORE (Auth) · Entrada — `POST /api/v1/auth/login (lo llama el frontend del portal de Analítica; no implementamos login propio)`

- **Canal:** Restful API
- **Identificador:** POST /api/v1/auth/login (lo llama el frontend del portal de Analítica; no implementamos login propio)

**Estructura**

```
Req: {"email": "string", "password": "string"} Res 200: {"accessToken": "string (JWT RS256, 15 min)", "expiresIn": "number", "user": {"id": "uuid", "email": "string", "roles": ["string"], "permissions": ["string"], "status": "string"}} + cookie HttpOnly de refresh (el frontend no la lee; el access token vive en memoria).
```

**Ejemplo**

```
Req: {"email": "mgarcia@uade.edu.ar", "password": "********"} Res: {"accessToken": "eyJhbGciOiJSUzI1NiIsImtpZCI6...", "expiresIn": 900, "user": {"id": "5d1e7c2a-8f43-4b9e-a6d0-2c7f9e1b3a58", "email": "mgarcia@uade.edu.ar", "roles": ["ACADEMIC_ADMIN"], "permissions": ["wallet:read:self", "wallet:credit:self", "academic:manage", "analytics:academic:read"], "status": "ACTIVE"}}
```

### CORE (Auth) · Entrada — `POST /api/v1/auth/refresh · POST /api/v1/auth/logout`

- **Canal:** Restful API
- **Identificador:** POST /api/v1/auth/refresh · POST /api/v1/auth/logout

**Estructura**

```
refresh: cookie de refresh → 200 {"accessToken": "string", "expiresIn": "number"} + cookie rotada. logout: 204. El frontend serializa el refresh porque el token rota en cada uso.
```

**Ejemplo**

```
POST /api/v1/auth/refresh → {"accessToken": "eyJ...", "expiresIn": 900} · POST /api/v1/auth/logout → 204
```

### CORE (Auth) · Entrada — `GET /api/v1/auth/me`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/auth/me

**Estructura**

```
Res 200: {"id": "uuid", "email": "string", "roles": ["string"], "permissions": ["string"], "status": "string"} — sesión activa del portal y qué tableros se muestran (por permisos). No es un directorio: el nombre sale de Backoffice.
```

**Ejemplo**

```
{"id": "5d1e7c2a-8f43-4b9e-a6d0-2c7f9e1b3a58", "email": "mgarcia@uade.edu.ar", "roles": ["ACADEMIC_ADMIN"], "permissions": ["wallet:read:self", "wallet:credit:self", "academic:manage", "analytics:academic:read"], "status": "ACTIVE"}
```

### CORE (Auth) · Entrada — `GET /.well-known/jwks.json`

- **Canal:** Restful API
- **Identificador:** GET /.well-known/jwks.json

**Estructura**

```
Res 200: {"keys": [{"kty": "RSA", "kid": "string", "alg": "RS256", "n": "string", "e": "string"}]} — validamos el JWT localmente (firma RS256, iss, aud, exp). Se cachea y se refresca sólo ante un kid desconocido; no llamamos a introspect por request.
```

**Ejemplo**

```
{"keys": [{"kty": "RSA", "kid": "core-2026-08-a", "alg": "RS256", "n": "0vx7agoebGcQ...", "e": "AQAB"}]}
```

### CORE (Gateway) · Entrada — `Headers de identidad inyectados en todo request a /api/v1/analytics/* (el gateway reescribe a /api/v1/*)`

- **Canal:** Restful API
- **Identificador:** Headers de identidad inyectados en todo request a /api/v1/analytics/* (el gateway reescribe a /api/v1/*)

**Estructura**

```
Authorization: Bearer <jwt original> · X-User-Id: uuid · X-User-Roles: csv · X-User-Permissions: csv · X-User-Career-Ids: csv · X-Correlation-Id: uuid · X-Core-Timestamp · X-Core-Signature (HMAC del gateway). La autorización sale del JWT validado con JWKS, no de los headers (la firma del gateway no cubre roles ni permisos). Permisos: analytics:academic:read → tablero académico y estadísticas de eventos; analytics:finance:read → tablero financiero. Se piden a CORE para los roles ACADEMIC_ADMIN y FINANCE_ADMIN (CORE es dueño del catálogo de roles y permisos). Sin permiso: 403 problem+json.
```

**Ejemplo**

```
X-User-Id: 5d1e7c2a-8f43-4b9e-a6d0-2c7f9e1b3a58 · X-User-Roles: ACADEMIC_ADMIN · X-User-Permissions: wallet:read:self,wallet:credit:self,academic:manage,analytics:academic:read · X-Correlation-Id: f501201b-00bc-4200-99e0-6883500854f1
```

### CORE (Service Auth) · Entrada — `POST /internal/v1/service-auth/token`

- **Canal:** Restful API
- **Identificador:** POST /internal/v1/service-auth/token

**Estructura**

```
Req: {"clientId": "string", "clientSecret": "string"} Res 200: {"accessToken": "string", "expiresIn": "number", "tokenType": "Bearer"} — token propio de Analítica (clientId analytics-service, asignado por CORE) para /internal/v1/* y para las consultas directas a otros módulos, que lo validan con el JWKS. Se cachea hasta poco antes de exp. El secret va en variables de entorno, nunca en Git.
```

**Ejemplo**

```
Req: {"clientId": "analytics-service", "clientSecret": "<env ANALYTICS_CLIENT_SECRET>"} Res: {"accessToken": "eyJ...", "expiresIn": 900, "tokenType": "Bearer"}
```

### CORE (Wallet) · Entrada — `GET /internal/v1/wallets/aggregates?groupBy=concept&from=&to=`

- **Canal:** Restful API
- **Identificador:** GET /internal/v1/wallets/aggregates?groupBy=concept&from=&to=

**Estructura**

```
Res 200: {"range": {"from": "date", "to": "date"}, "currency": "ARS", "outstandingBalance": "string decimal", "walletCount": "number", "groups": [{"key": "concept", "type": "CREDIT | DEBIT | REVERSAL", "count": "number", "total": "string decimal"}]} — Balances de saldo (outstandingBalance), ingresos y egresos por concepto, y gastos administrativos (key = PAYROLL). Se consulta mes a mes. Sin identificadores de persona.
```

**Ejemplo**

```
GET /internal/v1/wallets/aggregates?groupBy=concept&from=2026-08-01&to=2026-08-31 Res: {"range": {"from": "2026-08-01", "to": "2026-08-31"}, "currency": "ARS", "outstandingBalance": "8452300.00", "walletCount": 1834, "groups": [{"key": "STORE_PURCHASE", "type": "DEBIT", "count": 942, "total": "1847500.00"}, {"key": "PAYROLL", "type": "CREDIT", "count": 210, "total": "10080000.00"}]}
```

### CORE (Event Bus) · Entrada — `Cola analytics.all-events.v1 (exchange uadenet.events.v1, routingKeys ["#"], deadLetter uadenet.dlx.v1, maxRetries 3) — se pide a G10 (dueño, nombre, eventTypes, entorno y responsable); alternativa: webhooks por eventType (POST /internal/v1/subscriptions)`

- **Canal:** Message Queue

**Identificador**

```
Cola analytics.all-events.v1 (exchange uadenet.events.v1, routingKeys ["#"], deadLetter uadenet.dlx.v1, maxRetries 3) — se pide a G10 (dueño, nombre, eventTypes, entorno y responsable); alternativa: webhooks por eventType (POST /internal/v1/subscriptions)
```

**Estructura**

```
Envelope estándar de CORE: {"specVersion": "1.0", "eventId": "uuid", "eventType": "string (catálogo, sufijo .vN)", "source": "string", "occurredAt": "ISO 8601 UTC", "subject": "tipo/id", "correlationId": "uuid", "causationId": "uuid | null", "actor": {"type": "string", "id": "string"}, "data": {}} — ack manual después de persistir, prefetch 10-50, tabla inbox_messages con PK event_id para deduplicar reentregas. Los eventTypes que no figuran en esta hoja se ackean y se descartan.
```

**Ejemplo**

```
{"specVersion": "1.0", "eventId": "e3d28114-e52e-4db9-afeb-03399bcb27e7", "eventType": "dining.reservation.created.v1", "source": "dining", "occurredAt": "2026-09-15T14:02:11.004Z", "subject": "reservation/58df9fe3-4883-4dca-9d9f-4770c81543cf", "correlationId": "f501201b-00bc-4200-99e0-6883500854f1", "causationId": null, "actor": {"type": "service", "id": "dining-service"}, "data": {"reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "slotAt": "2026-09-15T15:00:00.000Z", "amount": "1500.00", "currency": "ARS"}}
```

### Backoffice Administrativo · Entrada — `backoffice.user.upserted.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.user.upserted.v1

**Estructura**

```
data: {"userId": "uuid", "email": "string", "status": "PENDING_ACTIVATION | ACTIVE | SUSPENDED | DISABLED", "roles": ["STUDENT | TEACHER | ADMIN | LIBRARIAN | STORE_ADMIN | OPERATIONS_ADMIN | ACADEMIC_ADMIN | FINANCE_ADMIN | IT_ADMIN"], "permissions": ["string"]} — aviso de alta o cambio de una persona (docentes = roles TEACHER): invalida el cache de nombres. No se copian datos de personas; el nombre se consulta a Backoffice por REST.
```

**Ejemplo**

```
data: {"userId": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "email": "agomez@uade.edu.ar", "status": "ACTIVE", "roles": ["TEACHER"], "permissions": ["teacher:courses:write"]}
```

### Backoffice Administrativo · Entrada — `backoffice.user.disabled.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.user.disabled.v1

**Estructura**

```
data: {"userId": "uuid", "reason": "string"} — aviso de baja de una persona: invalida el cache de nombres. Sus resultados históricos se siguen mostrando.
```

**Ejemplo**

```
data: {"userId": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "reason": "BAJA_LABORAL"}
```

### Backoffice Administrativo · Entrada — `backoffice.location.upserted.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.location.upserted.v1

**Estructura**

```
data: {"locationId": "uuid", "siteId": "uuid", "name": "string", "capacity": "number", "status": "ACTIVE | INACTIVE"} — resuelve la sede de los eventos académicos (events.event.created.v1 trae locationId, no siteId).
```

**Ejemplo**

```
data: {"locationId": "c41a77b2-9e0d-4f36-8b21-77aa1c9de405", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "name": "Aula Magna - Sede Monserrat", "capacity": 320, "status": "ACTIVE"}
```

### Backoffice Administrativo · Entrada — `GET {BACKOFFICE_URL}/api/v1/sites?status=ACTIVE · GET {BACKOFFICE_URL}/api/v1/sites/{siteId} — directo al backend de Backoffice (sin gateway), con token de servicio de CORE`

- **Canal:** Restful API

**Identificador**

```
GET {BACKOFFICE_URL}/api/v1/sites?status=ACTIVE · GET {BACKOFFICE_URL}/api/v1/sites/{siteId} — directo al backend de Backoffice (sin gateway), con token de servicio de CORE
```

**Estructura**

```
Res 200: {"items": [{"siteId": "uuid", "code": "string", "name": "string", "address": "string", "city": "string", "province": "string | null", "country": "string", "timezone": "IANA", "status": "ACTIVE | INACTIVE", "updatedAt": "ISO 8601 UTC"}], "nextCursor": "string | null"} — catálogo del filtro de sede. Las sedes no tienen evento: carga inicial al arrancar y cache. timezone se usa para agrupar por día/mes local.
```

**Ejemplo**

```
GET {BACKOFFICE_URL}/api/v1/sites?status=ACTIVE Res: {"items": [{"siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "code": "MONSERRAT", "name": "Sede Monserrat", "address": "Lima 775", "city": "CABA", "province": null, "country": "Argentina", "timezone": "America/Argentina/Buenos_Aires", "status": "ACTIVE", "updatedAt": "2026-09-10T13:00:00.000Z"}], "nextCursor": null}
```

### Backoffice Administrativo · Entrada — `GET {BACKOFFICE_URL}/api/v1/users/{userId} — directo al backend de Backoffice (sin gateway), con token de servicio de CORE`

- **Canal:** Restful API

**Identificador**

```
GET {BACKOFFICE_URL}/api/v1/users/{userId} — directo al backend de Backoffice (sin gateway), con token de servicio de CORE
```

**Estructura**

```
Res 200 (detalle): {"userId": "uuid", "firstName": "string", "lastName": "string", "roles": ["string"], "status": "string", "siteId": "uuid"} — nombre a mostrar del usuario logueado (userId = sub del JWT) y de los docentes del ranking. No se persiste: se consulta cuando hace falta, con cache corto.
```

**Ejemplo**

```
GET {BACKOFFICE_URL}/api/v1/users/5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034 Res: {"userId": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "firstName": "Ana", "lastName": "Gómez", "roles": ["TEACHER"], "status": "ACTIVE", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90"}
```

### Gestión Académica y Planificación · Entrada — `academic.course-result.published.v1 (nombre propuesto, a registrar en el catálogo de CORE)`

- **Canal:** Message Queue
- **Identificador:** academic.course-result.published.v1 (nombre propuesto, a registrar en el catálogo de CORE)

**Estructura**

```
data: {"studentId": "uuid", "courseId": "id del curso", "subjectId": "id de la asignatura", "periodId": "id del período", "siteId": "uuid (backofficeSiteId de la sede)", "finalGrade": "number (0-10)", "status": "APROBADO | DESAPROBADO", "resultDate": "date"} — un evento por alumno y curso cada vez que se carga o corrige la nota final (hoy G9 lo publica como resultado.publicado en su propia cola; tiene que pasar a POST /internal/v1/events de CORE). Cada publicación lleva un eventId nuevo; nos quedamos con el último resultado por alumno y curso. Alimenta la tasa de aprobación por materia, por docente y por cuatrimestre.
```

**Ejemplo**

```
data: {"studentId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "courseId": "42", "subjectId": "15", "periodId": "8", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "finalGrade": 8.0, "status": "APROBADO", "resultDate": "2026-09-30"}
```

### Gestión Académica y Planificación · Entrada — `academic.term-defined.v1`

- **Canal:** Message Queue
- **Identificador:** academic.term-defined.v1

**Estructura**

```
data: {"termId": "uuid", "startDate": "date", "endDate": "date"} — cuatrimestre vigente y anteriores, si G9 lo publica (está en el catálogo de CORE). Mientras tanto se toma de GET /periodos.
```

**Ejemplo**

```
data: {"termId": "d4e5f6a7-b8c9-4d0e-9f1a-2b3c4d5e6f70", "startDate": "2026-08-01", "endDate": "2026-11-30"}
```

### Gestión Académica y Planificación · Entrada — `GET {ACADEMIC_URL}/api/planificacion/cursos?periodoId={id} — directo al backend de Gestión Académica con token de servicio de CORE`

- **Canal:** Restful API

**Identificador**

```
GET {ACADEMIC_URL}/api/planificacion/cursos?periodoId={id} — directo al backend de Gestión Académica con token de servicio de CORE
```

**Estructura**

```
Res 200: [{"id": "number", "codigo": "string", "asignaturaId": "number", "periodoId": "number", "sedeId": "number", "sedeNombre": "string", "estado": "PLANIFICADO | EN_CURSO | FINALIZADO | CANCELADO", "cupoMaximo": "number", "inscriptosActivos": "number"}] — cursos del cuatrimestre. Materias en curso = asignaturaId distintas con estado EN_CURSO. IDs hoy numéricos (CORE pide UUID).
```

**Ejemplo**

```
GET {ACADEMIC_URL}/api/planificacion/cursos?periodoId=8 Res: [{"id": 42, "codigo": "DDA2-001", "asignaturaId": 15, "periodoId": 8, "sedeId": 2, "sedeNombre": "Sede Centro", "estado": "EN_CURSO", "cupoMaximo": 45, "inscriptosActivos": 30}]
```

### Gestión Académica y Planificación · Entrada — `GET {ACADEMIC_URL}/api/planificacion/cursos/{cursoId} — directo, con token de servicio de CORE`

- **Canal:** Restful API
- **Identificador:** GET {ACADEMIC_URL}/api/planificacion/cursos/{cursoId} — directo, con token de servicio de CORE

**Estructura**

```
Res 200: {"curso": {"id": "number", "asignatura": {"id": "number", "codigo": "string", "nombre": "string"}, "periodo": {"id": "number", "anio": "number", "numero": "number"}, "sedeId": "number", "estado": "string"}, "docentes": [{"docenteId": "string (UUID de Backoffice)", "rol": "TITULAR | ADJUNTO | AUXILIAR"}]} — docentes de cada curso, para la tasa de aprobación por docente (cruce courseId del resultado → docente).
```

**Ejemplo**

```
{"curso": {"id": 42, "asignatura": {"id": 15, "codigo": "DDA2-002", "nombre": "Desarrollo de Aplicaciones II"}, "periodo": {"id": 8, "anio": 2026, "numero": 2}, "sedeId": 2, "estado": "EN_CURSO"}, "docentes": [{"docenteId": "5f0a8e21-4c7b-4d19-9a3e-61b2c8d7f034", "rol": "TITULAR"}]}
```

### Gestión Académica y Planificación · Entrada — `GET {ACADEMIC_URL}/api/planificacion/periodos — directo, con token de servicio de CORE`

- **Canal:** Restful API
- **Identificador:** GET {ACADEMIC_URL}/api/planificacion/periodos — directo, con token de servicio de CORE

**Estructura**

```
Res 200: [{"id": "number", "anio": "number", "numero": "1 | 2", "fechaInicio": "date", "fechaFin": "date"}] — cuatrimestres para el filtro del tablero académico. La etiqueta AAAA-NC se arma con anio y numero.
```

**Ejemplo**

```
[{"id": 8, "anio": 2026, "numero": 2, "fechaInicio": "2026-08-01", "fechaFin": "2026-11-30"}]
```

### Gestión Académica y Planificación · Entrada — `GET {ACADEMIC_URL}/api/planificacion/sedes — directo, con token de servicio de CORE`

- **Canal:** Restful API
- **Identificador:** GET {ACADEMIC_URL}/api/planificacion/sedes — directo, con token de servicio de CORE

**Estructura**

```
Res 200: [{"id": "number", "backofficeSiteId": "uuid", "nombre": "string"}] — traduce el sedeId local de los cursos al siteId de Backoffice, que es el que usa el filtro de sede.
```

**Ejemplo**

```
[{"id": 2, "backofficeSiteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "nombre": "Sede Centro"}]
```

### Gestión Académica y Planificación · Entrada — `GET {ACADEMIC_URL}/api/academica/carreras · /carreras/{carreraId}/planes · /planes/{planId}/asignaturas — directo, con token de servicio de CORE`

- **Canal:** Restful API

**Identificador**

```
GET {ACADEMIC_URL}/api/academica/carreras · /carreras/{carreraId}/planes · /planes/{planId}/asignaturas — directo, con token de servicio de CORE
```

**Estructura**

```
Carrera: {"id": "number", "codigo": "string", "nombre": "string", "facultad": "string"} · Asignatura: {"id": "number", "codigo": "string", "nombre": "string", "planId": "number"} — código y nombre de cada materia y facultad de su carrera (tendencia por facultad). Carga inicial y cache.
```

**Ejemplo**

```
Carrera: {"id": 1, "codigo": "ING-001", "nombre": "Ingeniería en Informática", "facultad": "Facultad de Ingeniería"} · Asignatura: {"id": 15, "codigo": "DDA2-002", "nombre": "Desarrollo de Aplicaciones II", "planId": 3}
```

### Biblioteca Universitaria · Entrada — `library.penalty.applied.v1`

- **Canal:** Message Queue
- **Identificador:** library.penalty.applied.v1

**Estructura**

```
data: {"userId": "uuid", "loanId": "uuid", "daysLate": "number", "amount": "string decimal", "currency": "ARS"} — multas aplicadas por mes (complementa el concepto LIBRARY_FINE de los agregados de CORE).
```

**Ejemplo**

```
data: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "loanId": "c8ed9311-6a6b-40c6-a798-5066d290c13c", "daysLate": 8, "amount": "2500.00", "currency": "ARS"}
```

### Sistema de Comedor · Entrada — `dining.reservation.created.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.created.v1

**Estructura**

```
data: {"reservationId": "uuid", "userId": "uuid", "siteId": "uuid", "slotAt": "ISO 8601 UTC", "amount": "string decimal", "currency": "ARS"} — facturación de comedores por sede, cantidad de tickets y ticket promedio. Guardamos reservationId → siteId/amount para cruzar cancelaciones y asistencias.
```

**Ejemplo**

```
data: {"reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "slotAt": "2026-09-15T15:00:00.000Z", "amount": "1500.00", "currency": "ARS"}
```

### Sistema de Comedor · Entrada — `dining.reservation.cancelled.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.cancelled.v1

**Estructura**

```
data: {"reservationId": "uuid", "userId": "uuid", "slotAt": "ISO 8601 UTC", "cancelledAt": "ISO 8601 UTC"} — descuenta la reserva de la facturación; sede y monto se resuelven por reservationId.
```

**Ejemplo**

```
data: {"reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "slotAt": "2026-09-15T15:00:00.000Z", "cancelledAt": "2026-09-14T18:10:00.000Z"}
```

### Sistema de Comedor · Entrada — `dining.attendance.recorded.v1`

- **Canal:** Message Queue
- **Identificador:** dining.attendance.recorded.v1

**Estructura**

```
data: {"reservationId": "uuid", "userId": "uuid", "attendedAt": "ISO 8601 UTC"} — asistencia a la reserva. El monto restituido se toma de core.wallet.transaction-reversed.v1 (concept REFUND).
```

**Ejemplo**

```
data: {"reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "attendedAt": "2026-09-15T15:05:00.000Z"}
```

### Tienda del Campus · Entrada — `store.purchase.completed.v1`

- **Canal:** Message Queue
- **Identificador:** store.purchase.completed.v1

**Estructura**

```
data: {"purchaseId": "uuid", "userId": "uuid", "total": "string decimal", "currency": "ARS", "items": [{"productId": "uuid", "productName": "string (al momento de la compra)", "category": "string", "quantity": "number", "unitPrice": "string decimal", "subtotal": "string decimal"}], "siteId": "uuid (opcional)"} — productos más vendidos (unidades y facturación por producto). userId no se persiste. Campos de items[] a confirmar con Tienda.
```

**Ejemplo**

```
data: {"purchaseId": "93b28f67-e111-4a0d-b857-fdd015c4d3f1", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "total": "3500.00", "currency": "ARS", "items": [{"productId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "productName": "Buzo UADE azul", "category": "Indumentaria", "quantity": 1, "unitPrice": "3500.00", "subtotal": "3500.00"}], "siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90"}
```

### Eventos Académicos · Entrada — `events.event.created.v1`

- **Canal:** Message Queue
- **Identificador:** events.event.created.v1

**Estructura**

```
data: {"eventId": "uuid", "title": "string", "locationId": "uuid", "startAt": "ISO 8601 UTC", "endAt": "ISO 8601 UTC", "capacity": "number", "price": "string decimal | null", "currency": "ARS"} — frecuencia de eventos por mes y ocupación de cupo. La sede sale de locationId → siteId (backoffice.location.upserted.v1). Un evento cuenta como realizado cuando pasa endAt.
```

**Ejemplo**

```
data: {"eventId": "65a783d1-d407-442d-8d09-a6d2abfe9321", "title": "Jornada de Ingeniería", "locationId": "c41a77b2-9e0d-4f36-8b21-77aa1c9de405", "startAt": "2026-10-12T21:00:00.000Z", "endAt": "2026-10-13T00:00:00.000Z", "capacity": 200, "price": "1800.00", "currency": "ARS"}
```

### Eventos Académicos · Entrada — `events.registration.completed.v1`

- **Canal:** Message Queue
- **Identificador:** events.registration.completed.v1

**Estructura**

```
data: {"eventId": "uuid", "registrationId": "uuid", "userId": "uuid", "amount": "string decimal", "currency": "ARS"} — inscriptos por evento e ingresos por inscripción paga (amount = "0.00" si es gratuito).
```

**Ejemplo**

```
data: {"eventId": "65a783d1-d407-442d-8d09-a6d2abfe9321", "registrationId": "5e8d0b31-9c47-4a26-b18f-72e4c0d95a68", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "amount": "1800.00", "currency": "ARS"}
```

### Eventos Académicos · Entrada — `events.attendance.recorded.v1`

- **Canal:** Message Queue
- **Identificador:** events.attendance.recorded.v1

**Estructura**

```
data: {"eventId": "uuid", "userId": "uuid", "present": "boolean", "checkedAt": "ISO 8601 UTC"} — concurrencia (presentes) y tasa de presentismo (presentes / inscriptos).
```

**Ejemplo**

```
data: {"eventId": "65a783d1-d407-442d-8d09-a6d2abfe9321", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "present": true, "checkedAt": "2026-10-12T21:07:44.000Z"}
```

### CORE (Wallet) · Entrada — `core.wallet.transaction-posted.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-posted.v1

**Estructura**

```
data: {"transactionId": "uuid", "userId": "uuid", "type": "CREDIT | DEBIT | REVERSAL", "concept": "TOP_UP | PAYROLL | SCHOLARSHIP | ADJUSTMENT | LIBRARY_FINE | DINING_RESERVATION | STORE_PURCHASE | EVENT_REGISTRATION | REFUND", "amount": "string decimal", "currency": "ARS", "sourceModule": "string", "externalReference": "string", "status": "POSTED"} — movimientos del mes en curso por concepto (los totales oficiales salen de aggregates). No se persiste userId.
```

**Ejemplo**

```
data: {"transactionId": "386865f7-c8aa-4aba-a374-ec9e6f8a6300", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "type": "DEBIT", "concept": "STORE_PURCHASE", "amount": "3500.00", "currency": "ARS", "sourceModule": "store", "externalReference": "purchase/93b28f67-e111-4a0d-b857-fdd015c4d3f1", "status": "POSTED"}
```

### CORE (Wallet) · Entrada — `core.wallet.transaction-rejected.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-rejected.v1

**Estructura**

```
data: {"userId": "uuid", "type": "string", "concept": "string", "amount": "string decimal", "currency": "ARS", "sourceModule": "string", "externalReference": "string", "reasonCode": "string"} — cobros rechazados por concepto (p. ej. saldo insuficiente). Informativo.
```

**Ejemplo**

```
data: {"userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "type": "DEBIT", "concept": "DINING_RESERVATION", "amount": "1500.00", "currency": "ARS", "sourceModule": "dining", "externalReference": "reservation/58df9fe3-4883-4dca-9d9f-4770c81543cf", "reasonCode": "WALLET_INSUFFICIENT_FUNDS"}
```

### CORE (Wallet) · Entrada — `core.wallet.transaction-reversed.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-reversed.v1

**Estructura**

```
data: {"transactionId": "uuid", "originalTransactionId": "uuid", "userId": "uuid", "concept": "REFUND", "amount": "string decimal", "currency": "ARS"} — reintegros: restitución de reservas de comedor asistidas y reversas de cobros de Tienda y Eventos.
```

**Ejemplo**

```
data: {"transactionId": "0c3b6d21-9a44-4f7d-b2e8-15ac9f3d7e60", "originalTransactionId": "386865f7-c8aa-4aba-a374-ec9e6f8a6300", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "concept": "REFUND", "amount": "1500.00", "currency": "ARS"}
```

### — (consumo interno: portal de Analítica) · Salida — `GET /api/v1/analytics/dashboard/academic?siteId=&termId= (permiso analytics:academic:read)`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/analytics/dashboard/academic?siteId=&termId= (permiso analytics:academic:read)

**Estructura**

```
{"siteName": "string", "quarter": "string", "previousQuarter": "string", "kpis": [{"id": "string", "label": "string", "value": "number", "unit": "string", "delta": {"value": "number", "tone": "positive | negative | neutral"}}], "subjectApprovalRates": [{"code": "string", "name": "string", "approvalRate": "number", "series": [{"quarter": "string", "approvalRate": "number"}]}], "teacherApprovalRates": [{"teacherName": "string", "subjectName": "string", "approvalRate": "number"}], "facultyTrends": [{"facultyName": "string", "points": [{"quarter": "string", "approvalRate": "number"}]}], "lastIngestionAt": "ISO 8601 UTC"} — materias en curso, tasa de aprobación por materia y por docente.
```

**Ejemplo**

```
{"siteName": "Todas las sedes", "quarter": "2026-1C", "previousQuarter": "2025-2C", "kpis": [{"id": "subjects-in-progress", "label": "Materias en curso", "value": 148, "unit": "materias", "delta": {"value": 6, "tone": "positive"}}], "subjectApprovalRates": [{"code": "INF-302", "name": "Desarrollo de Aplicaciones II", "approvalRate": 0.78, "series": [{"quarter": "2025-2C", "approvalRate": 0.74}, {"quarter": "2026-1C", "approvalRate": 0.78}]}], "teacherApprovalRates": [{"teacherName": "Ana Gómez", "subjectName": "Desarrollo de Aplicaciones II", "approvalRate": 0.81}], "lastIngestionAt": "2026-10-20T22:14:00.000Z"}
```

### — (consumo interno: portal de Analítica) · Salida — `GET /api/v1/analytics/dashboard/financial?siteId=&month=AAAA-MM (permiso analytics:finance:read)`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/analytics/dashboard/financial?siteId=&month=AAAA-MM (permiso analytics:finance:read)

**Estructura**

```
{"siteName": "string", "month": "string", "kpis": ["KpiCard"], "monthlyBalance": [{"month": "string", "income": "string decimal", "expense": "string decimal", "result": "string decimal", "balance": "string decimal"}], "administrativeExpenses": [{"category": "string", "amount": "string decimal", "percentage": "number"}], "topSellingProducts": [{"productName": "string", "category": "string", "unitsSold": "number", "revenue": "string decimal"}], "diningRevenues": [{"siteName": "string", "revenue": "string decimal", "ticketsCount": "number", "averageTicket": "string decimal"}], "lastIngestionAt": "ISO 8601 UTC"} — balances de saldo, gastos administrativos (sueldos), productos más vendidos y facturación de comedores por sede.
```

**Ejemplo**

```
{"siteName": "Sede Monserrat", "month": "2026-08", "monthlyBalance": [{"month": "2026-08", "income": "4210500.00", "expense": "10080000.00", "result": "-5869500.00", "balance": "8452300.00"}], "administrativeExpenses": [{"category": "Sueldos (PAYROLL)", "amount": "10080000.00", "percentage": 1}], "topSellingProducts": [{"productName": "Buzo UADE azul", "category": "Indumentaria", "unitsSold": 212, "revenue": "742000.00"}], "diningRevenues": [{"siteName": "Sede Monserrat", "revenue": "186000.00", "ticketsCount": 124, "averageTicket": "1500.00"}]}
```

### — (consumo interno: portal de Analítica) · Salida — `GET /api/v1/analytics/events/stats?siteId=&month=AAAA-MM (permiso analytics:academic:read)`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/analytics/events/stats?siteId=&month=AAAA-MM (permiso analytics:academic:read)

**Estructura**

```
{"siteName": "string", "month": "string", "totalEvents": "number", "totalRegistered": "number", "totalAttendees": "number", "averageAttendanceRate": "number", "capacityOccupancy": "number", "monthlySeries": [{"month": "string", "eventsCount": "number", "attendeesCount": "number", "attendanceRate": "number"}], "lastIngestionAt": "ISO 8601 UTC"} — frecuencia, concurrencia, presentismo y ocupación de cupo.
```

**Ejemplo**

```
{"siteName": "Sede Monserrat", "month": "2026-10", "totalEvents": 9, "totalRegistered": 640, "totalAttendees": 512, "averageAttendanceRate": 0.8, "capacityOccupancy": 0.71, "monthlySeries": [{"month": "2026-10", "eventsCount": 9, "attendeesCount": 512, "attendanceRate": 0.8}]}
```

### — (consumo interno: portal de Analítica) · Salida — `GET /api/v1/analytics/filters`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/analytics/filters

**Estructura**

```
{"sites": [{"siteId": "uuid", "code": "string", "name": "string"}], "terms": [{"termId": "uuid", "label": "string", "startDate": "date", "endDate": "date"}], "months": ["AAAA-MM"], "defaults": {"siteId": "uuid | null", "termId": "uuid", "month": "AAAA-MM"}} — opciones de filtros: sedes de Backoffice, cuatrimestres de Gestión Académica y meses con datos.
```

**Ejemplo**

```
{"sites": [{"siteId": "3e9b0a12-55cc-4d77-9a01-6b2f8c4e1d90", "code": "MONSERRAT", "name": "Sede Monserrat"}], "terms": [{"termId": "d4e5f6a7-b8c9-4d0e-9f1a-2b3c4d5e6f70", "label": "2026-2C", "startDate": "2026-08-10", "endDate": "2026-12-12"}], "months": ["2026-08", "2026-09", "2026-10"], "defaults": {"siteId": null, "termId": "d4e5f6a7-b8c9-4d0e-9f1a-2b3c4d5e6f70", "month": "2026-10"}}
```

### CORE (Gateway) · Salida — `GET /health/live · GET /health/ready`

- **Canal:** Restful API
- **Identificador:** GET /health/live · GET /health/ready

**Estructura**

```
Res 200: {"status": "string", "checks": {"db": "string", "broker": "string"}}
```

**Ejemplo**

```
{"status": "ok", "checks": {"db": "up", "broker": "up"}}
```
