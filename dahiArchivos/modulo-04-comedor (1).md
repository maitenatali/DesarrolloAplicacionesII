# Módulo 4 · Comedor

_Convertido desde `Flujo_de_Datos_Modulo_4_Comedor_Alineado.xlsx` (hojas: Flujo de Datos, Trazabilidad Backend)._

## Hoja: Flujo de Datos

> Documentación de Flujo de Datos — Módulo 4 · Sistema de Comedor
>
> Alineado al contrato oficial CORE v1 (05/08/2026). Dirección desde Comedor: Entrada = recibe/consume · Salida = envía/consume un servicio externo.
>
> Reglas compartidas: IDs UUID v4 · JSON camelCase · fechas ISO 8601 UTC · dinero como string decimal + currency · X-Correlation-Id · idempotencia en operaciones financieras.
>
> Los ejemplos son ilustrativos; los nombres de endpoints, eventos y campos son los del contrato CORE_INTEGRACION v1.

### CORE — Autenticación · Salida — `POST /api/v1/auth/login`

- **Canal:** Restful API
- **Identificador:** POST /api/v1/auth/login

**Estructura**

```
{ email: string; password: string } → { accessToken: string; expiresIn: number; user: { id: UUID; email: string; roles: string[]; permissions: string[]; status: string } }
```

**Ejemplo**

```
{ "email": "jperez@uade.edu.ar", "password": "..." } → { "accessToken": "<JWT>", "expiresIn": 900, "user": { "id": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "roles": ["STUDENT"], "status": "ACTIVE" } }
```

### CORE — Autenticación · Salida — `GET /api/v1/auth/me`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/auth/me

**Estructura**

```
Authorization: Bearer <jwt> → { id: UUID; email: string; roles: string[]; permissions: string[]; status: string }
```

**Ejemplo**

```
{ "id": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "email": "jperez@uade.edu.ar", "roles": ["STUDENT"], "permissions": ["wallet:read:self"], "status": "ACTIVE" }
```

### CORE — Wallet · Salida — `GET /api/v1/wallets/me`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/wallets/me

**Estructura**

```
Authorization: Bearer <jwt> → saldo propio. Dinero siempre como string decimal + currency.
```

**Ejemplo**

```
{ "amount": "12500.00", "currency": "ARS" }
```

### CORE — Wallet · Salida — `GET /api/v1/wallets/me/transactions?type=&from=&to=&cursor=&limit=`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/wallets/me/transactions?type=&from=&to=&cursor=&limit=

**Estructura**

```
{ items: [transacciones]; nextCursor: string|null }. Paginación por cursor.
```

**Ejemplo**

```
{ "items": [{ "type": "DEBIT", "concept": "DINING_RESERVATION", "amount": "1500.00", "currency": "ARS" }], "nextCursor": null }
```

### CORE — Gateway · Entrada — `/api/v1/dining/* → /api/v1/*`

- **Canal:** Restful API
- **Identificador:** /api/v1/dining/* → /api/v1/*

**Estructura**

```
Headers inyectados por CORE: X-User-Id: UUID; X-User-Roles; X-User-Permissions; X-Correlation-Id. El módulo también valida el JWT.
```

**Ejemplo**

```
X-User-Id: ba310c57-a684-4dbf-a4a4-905fcfbefa08; X-User-Roles: STUDENT; X-Correlation-Id: <UUID>
```

### CORE — Service Auth · Salida — `POST /internal/v1/service-auth/token`

- **Canal:** Restful API
- **Identificador:** POST /internal/v1/service-auth/token

**Estructura**

```
{ clientId: string; clientSecret: string } → { accessToken: string; expiresIn: number; tokenType: "Bearer" }
```

**Ejemplo**

```
{ "clientId": "dining-service", "clientSecret": "..." } → { "accessToken": "<service-token>", "expiresIn": 900, "tokenType": "Bearer" }
```

### CORE — Wallet · Salida — `POST /internal/v1/wallets/{userId}/debits`

- **Canal:** Restful API
- **Identificador:** POST /internal/v1/wallets/{userId}/debits

**Estructura**

```
Headers: Authorization Service Token + Idempotency-Key + X-Correlation-Id. Body: { amount: string; currency:"ARS"; concept:"DINING_RESERVATION"; sourceModule:"dining"; externalReference:"reservation/{reservationId}"; description?; metadata? }
```

**Ejemplo**

```
{ "amount": "1500.00", "currency": "ARS", "concept": "DINING_RESERVATION", "sourceModule": "dining", "externalReference": "reservation/58df9fe3-4883-4dca-9d9f-4770c81543cf", "metadata": { "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf" } }
```

### CORE — Wallet · Salida — `POST /internal/v1/wallet-transactions/{transactionId}/reversals`

- **Canal:** Restful API
- **Identificador:** POST /internal/v1/wallet-transactions/{transactionId}/reversals

**Estructura**

```
Headers: Authorization Service Token + Idempotency-Key. Body recomendado: { reason: string } sin amount para restituir el total exacto.
```

**Ejemplo**

```
POST /internal/v1/wallet-transactions/386865f7-c8aa-4aba-a374-ec9e6f8a6300/reversals · { "reason": "Usuario se presentó a la reserva" }
```

### Backoffice Administrativo — Tarifas · Entrada — `backoffice.rate.changed.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.rate.changed.v1

**Estructura**

```
Envelope estándar CORE. data: { rateType; amount; currency; effectiveFrom }. Comedor filtra rateType="DINING_RESERVATION".
```

**Ejemplo**

```
{ "eventType": "backoffice.rate.changed.v1", "source": "backoffice", "data": { "rateType": "DINING_RESERVATION", "amount": "1500.00", "currency": "ARS", "effectiveFrom": "2026-09-01T00:00:00.000Z" } }
```

### Backoffice Administrativo — Sedes / Ubicaciones · Entrada — `backoffice.location.upserted.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.location.upserted.v1

**Estructura**

```
Envelope estándar CORE. data: { locationId; siteId; name; capacity; status }.
```

**Ejemplo**

```
{ "eventType": "backoffice.location.upserted.v1", "source": "backoffice", "data": { "locationId": "aa1a478f-7e59-463d-aeb5-5a34c07ddf07", "siteId": "1f1b4a14-690e-4c74-8721-4e1f52e9fb59", "name": "Comedor Monserrat", "capacity": 120, "status": "ACTIVE" } }
```

### CORE — Wallet Events · Entrada — `core.wallet.transaction-posted.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-posted.v1

**Estructura**

```
data: { transactionId; userId; type; concept; amount; currency; sourceModule; externalReference; status }.
```

**Ejemplo**

```
{ "transactionId": "386865f7-c8aa-4aba-a374-ec9e6f8a6300", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "type": "DEBIT", "concept": "DINING_RESERVATION", "amount": "1500.00", "currency": "ARS", "sourceModule": "dining", "externalReference": "reservation/58df9fe3-4883-4dca-9d9f-4770c81543cf", "status": "POSTED" }
```

### CORE — Wallet Events · Entrada — `core.wallet.transaction-rejected.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-rejected.v1

**Estructura**

```
data: { userId; type; concept; amount; currency; sourceModule; externalReference; reasonCode }.
```

**Ejemplo**

```
{ "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "type": "DEBIT", "concept": "DINING_RESERVATION", "amount": "1500.00", "currency": "ARS", "sourceModule": "dining", "externalReference": "reservation/58df9fe3-4883-4dca-9d9f-4770c81543cf", "reasonCode": "WALLET_INSUFFICIENT_FUNDS" }
```

### CORE — Wallet Events · Entrada — `core.wallet.transaction-reversed.v1`

- **Canal:** Message Queue
- **Identificador:** core.wallet.transaction-reversed.v1

**Estructura**

```
data: { transactionId; originalTransactionId; userId; concept; amount; currency }.
```

**Ejemplo**

```
{ "transactionId": "<reversal-uuid>", "originalTransactionId": "386865f7-c8aa-4aba-a374-ec9e6f8a6300", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "concept": "REFUND", "amount": "1500.00", "currency": "ARS" }
```

### Portal del Estudiante — Calendario · Salida — `dining.reservation.created.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.created.v1

**Estructura**

```
Envelope estándar CORE. data: { reservationId; userId; siteId; slotAt; amount; currency }.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "siteId": "1f1b4a14-690e-4c74-8721-4e1f52e9fb59", "slotAt": "2026-09-15T15:00:00.000Z", "amount": "1500.00", "currency": "ARS" }
```

### Portal del Docente — Calendario · Salida — `dining.reservation.created.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.created.v1

**Estructura**

```
Mismo evento publicado por Comedor. El backend del portal arma su calendario consumiendo este evento.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "siteId": "1f1b4a14-690e-4c74-8721-4e1f52e9fb59", "slotAt": "2026-09-15T15:00:00.000Z", "amount": "1500.00", "currency": "ARS" }
```

### Analítica Institucional · Salida — `dining.reservation.created.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.created.v1

**Estructura**

```
data: { reservationId; userId; siteId; slotAt; amount; currency }. Analítica usa siteId para facturación del comedor por sede.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "siteId": "1f1b4a14-690e-4c74-8721-4e1f52e9fb59", "slotAt": "2026-09-15T15:00:00.000Z", "amount": "1500.00", "currency": "ARS" }
```

### Portal del Estudiante — Calendario · Salida — `dining.reservation.cancelled.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.cancelled.v1

**Estructura**

```
data: { reservationId; userId; slotAt; cancelledAt }.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "slotAt": "2026-09-15T15:00:00.000Z", "cancelledAt": "2026-09-14T18:10:00.000Z" }
```

### Portal del Docente — Calendario · Salida — `dining.reservation.cancelled.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.cancelled.v1

**Estructura**

```
Mismo evento publicado por Comedor para que el portal mantenga consistente su calendario.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "slotAt": "2026-09-15T15:00:00.000Z", "cancelledAt": "2026-09-14T18:10:00.000Z" }
```

### Analítica Institucional · Salida — `dining.reservation.cancelled.v1`

- **Canal:** Message Queue
- **Identificador:** dining.reservation.cancelled.v1

**Estructura**

```
data: { reservationId; userId; slotAt; cancelledAt }.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "slotAt": "2026-09-15T15:00:00.000Z", "cancelledAt": "2026-09-14T18:10:00.000Z" }
```

### Analítica Institucional · Salida — `dining.attendance.recorded.v1`

- **Canal:** Message Queue
- **Identificador:** dining.attendance.recorded.v1

**Estructura**

```
data: { reservationId; userId; attendedAt }.
```

**Ejemplo**

```
{ "reservationId": "58df9fe3-4883-4dca-9d9f-4770c81543cf", "userId": "ba310c57-a684-4dbf-a4a4-905fcfbefa08", "attendedAt": "2026-09-15T15:05:00.000Z" }
```

## Hoja: Trazabilidad Backend

> Ajustes necesarios para alinear el backend del Comedor con los demás grupos
>
> Esta hoja señala las diferencias entre el mock/backend que veníamos documentando y el contrato oficial CORE v1. La hoja 'Flujo de Datos' refleja el contrato compartido que debe acordarse entre grupos.

| Tema | Antes / Mock actual | Contrato oficial compartido | Acción | Observación |
|---|---|---|---|---|
| Identidad de usuario | IDs numéricos/locales | UUID v4 generado por Backoffice; usar userId de token/X-User-Id | Modificar | No inventar ID propio ni usar email/legajo como clave. |
| Login | Login local del módulo / POST /auth/login | CORE: POST /api/v1/auth/login | Modificar | El portal no implementa login propio. |
| Gateway | Frontend llama backend del comedor directo | CORE enruta /api/v1/dining/* → /api/v1/* | Modificar | Backend recibe X-User-Id, X-User-Roles, X-User-Permissions y X-Correlation-Id. |
| Autenticación backend→CORE | Sin token de servicio formal | POST /internal/v1/service-auth/token | Agregar | clientId/clientSecret por módulo; credenciales fuera de Git. |
| Dinero | number/float | string decimal con 2 decimales + currency, ej. "1500.00" + "ARS" | Modificar | CORE prohíbe float para dinero. |
| Tarifa de reserva | reservationCost local/constante | Consumir backoffice.rate.changed.v1 con rateType=DINING_RESERVATION | Modificar | Backoffice es fuente de verdad de la tarifa. |
| Sedes / ubicaciones | GET /campuses local / datos propios | Consumir backoffice.location.upserted.v1 | Modificar | Backoffice mantiene catálogo de sedes/espacios. |
| Cobro de reserva | Débito local / WalletDebited custom | POST /internal/v1/wallets/{userId}/debits | Modificar | concept=DINING_RESERVATION; externalReference=reservation/{reservationId}; Idempotency-Key obligatorio. |
| Persistencia cobro | No necesariamente guarda transactionId de CORE | Guardar transactionId junto a la reserva | Agregar | Se necesita para reversa y reconciliación. |
| Reintegro por asistencia | Crédito local / WalletCredited | POST /internal/v1/wallet-transactions/{transactionId}/reversals sin amount | Modificar | No es CREDIT: es REVERSAL con concept=REFUND. |
| Reserva creada | DiningReservationCreated | dining.reservation.created.v1 | Modificar | Campos exactos: reservationId,userId,siteId,slotAt,amount,currency. |
| Reserva cancelada | No estaba documentada | dining.reservation.cancelled.v1 | Agregar | La consumen Analítica y calendarios de portales. |
| Asistencia | DiningAttendanceRegistered | dining.attendance.recorded.v1 | Modificar | Campos: reservationId,userId,attendedAt. |
| Eventos wallet | WalletDebited / WalletCredited | core.wallet.transaction-posted.v1 / rejected.v1 / reversed.v1 | Modificar | Usar los nombres y schemas oficiales. |
| Publicación de eventos | Eventos conceptuales/locales | POST /internal/v1/events + envelope estándar; CORE publica en RabbitMQ | Agregar | Usar eventId como Idempotency-Key; propagar correlationId. |
| Compra de comida | DiningPurchaseCreated / pago de compras local | NO existe concept DINING_PURCHASE ni evento dining.purchase.* en CORE v1 | Pendiente con CORE/profesor | No inventar contrato. El TPO pide pagar compras, pero CORE v1 sólo define DINING_RESERVATION para Comedor. |
| Idempotencia financiera | No formalizada | Idempotency-Key + externalReference estable | Agregar | Para reserva: externalReference=reservation/{reservationId}. |
| Errores | Formato propio | application/problem+json + code estable | Modificar | Ej.: 422 WALLET_INSUFFICIENT_FUNDS; 409 ALREADY_REVERSED se trata como éxito en check-in repetido. |
