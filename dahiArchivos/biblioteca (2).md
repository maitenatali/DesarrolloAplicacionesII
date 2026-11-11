# Biblioteca (Grupo 3)

_Convertido desde `UADEnet_Biblioteca_Grupo3.xlsx` (hojas: Flujo de Datos - Biblioteca)._

## Hoja: Flujo de Datos - Biblioteca

> Documentación de Flujo de Datos del Módulo Biblioteca

### CORE · Salida — `POST /api/v1/auth/login`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/login

**Estructura**

```
{
  "email": "string",
  "password": "string"
}
```

**Ejemplo**

```
{
  "email": "alumno@uade.edu.ar",
  "password": "********"
}
```

### CORE · Entrada — `/api/v1/library/*`

- **Canal:** RESTful API vía CORE Gateway
- **Identificador:** /api/v1/library/*

**Estructura**

```
Request HTTP + identidad validada por CORE:
X-User-Id, X-User-Roles,
X-User-Permissions,
X-Correlation-Id
```

**Ejemplo**

```
GET /api/v1/library/books?q=algoritmos

También cubre préstamos, devoluciones,
stock y sanciones del portal de Biblioteca.
```

### Backoffice · Entrada — `backoffice.rate.changed.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.rate.changed.v1

**Estructura**

```
{
  "rateType": "string",
  "amount": "string",
  "currency": "string",
  "effectiveFrom": "ISO-8601"
}
```

**Ejemplo**

```
{
  "rateType": "LIBRARY_LATE_FEE",
  "amount": "2500.00",
  "currency": "ARS",
  "effectiveFrom": "2026-08-01"
}
```

### Backoffice · Entrada — `backoffice.location.upserted.v1`

- **Canal:** Message Queue
- **Identificador:** backoffice.location.upserted.v1

**Estructura**

```
{
  "locationId": "UUID",
  "siteId": "UUID",
  "name": "string",
  "capacity": "number",
  "status": "string"
}
```

**Ejemplo**

```
{
  "locationId": "loc-001",
  "siteId": "sede-monserrat",
  "name": "Biblioteca - PB",
  "capacity": 120,
  "status": "ACTIVE"
}
```

### CORE · Salida — `POST /internal/v1/wallets/{userId}/debits`

- **Canal:** RESTful API
- **Identificador:** POST /internal/v1/wallets/{userId}/debits

**Estructura**

```
{
  "amount": "string",
  "currency": "ARS",
  "concept": "LIBRARY_FINE",
  "sourceModule": "library",
  "externalReference": "penalty/{penaltyId}"
}
```

**Ejemplo**

```
{
  "amount": "2500.00",
  "currency": "ARS",
  "concept": "LIBRARY_FINE",
  "sourceModule": "library",
  "externalReference": "penalty/abc-123"
}
```

### CORE · Salida — `POST /internal/v1/events`

- **Canal:** RESTful API

**Identificador**

```
POST /internal/v1/events
(eventType: library.penalty.applied.v1)
```

**Estructura**

```
{
  "eventType": "library.penalty.applied.v1",
  "source": "library",
  "subject": "user/{userId}",
  "data": {
    "userId": "UUID",
    "loanId": "UUID",
    "daysLate": "number",
    "amount": "string",
    "currency": "ARS"
  }
}
```

**Ejemplo**

```
{
  "eventType": "library.penalty.applied.v1",
  "source": "library",
  "data": {
    "userId": "ba310c57-...",
    "loanId": "c8ed9311-...",
    "daysLate": 8,
    "amount": "2500.00",
    "currency": "ARS"
  }
}
```

### CORRECCIONES 1ERA ENTREGA

- Faltan todos los endpoints /api/v1/library, por ejemplo a donde redirigen desde portal de estudiantes cuando quieren ver el detalle de un préstamo o sanción?

- Falta consumir las sedes disponibles para la carga del stock

**Fila 16 — celdas fuera de la estructura de la tabla (se transcriben tal cual, con su columna):**

- Columna A:

  ```
  - El formato del campo `effectiveFrom` del evento `backoffice.rate.changed.v1` no coincide con el emitido por Backoffice.
  ```

- Columna E:

  ```
  Biblioteca · Comedor · Eventos
  ```

- Columna F:

  ```
  Salida
  ```

- Columna G:

  ```
  Message Queue
  ```

- Columna H:

  ```
  backoffice.rate.changed.v1
  ```

- Columna I:

  ```
  Envelope estándar de CORE (ver hoja «Notas y supuestos») + data:
  {"rateType": "LIBRARY_LATE_FEE|DINING_RESERVATION|EVENT_REGISTRATION", "amount": "string decimal", "currency": "ARS", "effectiveFrom": "date-time ISO 8601 UTC (con hora, nunca sólo la fecha)"}
  Es un aviso de cambio: no trae siteId, fin de vigencia ni category (general / especial de eventos). El monto exacto (por sede, categoría y fecha) se re-consulta con GET /api/v1/backoffice/rates.
  ```

- Columna J:

  ```
  data: {"rateType": "LIBRARY_LATE_FEE", "amount": "2500.00", "currency": "ARS", "effectiveFrom": "2026-10-01T00:00:00.000Z"}
  ```

- Faltan consumir los datos del usuario (backoffice)

- Falta consumir el monto de la multa por prestamo tardío (backoffice)
