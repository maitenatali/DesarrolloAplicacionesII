# Módulo 6 · Eventos Académicos

_Convertido desde `Flujo_de_Datos_-_Modulo_6_-_UADEnet.xlsx` (hojas: Flujo de Datos, CORRECIONES PROFESOR)._

## Hoja: Flujo de Datos

> Documentación de Flujo de Datos del Módulo 6
>
> UADEnet — Eventos Académicos

### CORE · Entrada — `Header Authorization: Bearer {JWT} — en todo request a /api/v1/**`

- **Canal:** Restful API
- **Identificador:** Header Authorization: Bearer {JWT} — en todo request a /api/v1/**

**Estructura**

```
{"sub": "string (id de usuario en CORE)", "nombre": "string", "email": "string", "rol": "estudiante | docente | administrativo", "exp": "number (epoch en segundos)"} — claims que consume nuestro guard; el usuario se cachea localmente por "sub" (ver modelo-dominio.md)
```

**Ejemplo**

```
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1LTEwNDMyIn0 → claims: {"sub": "u-10432", "nombre": "María López", "email": "mlopez@uade.edu.ar", "rol": "administrativo", "exp": 1789084800}
```

### — (consumo interno) · Entrada — `POST /api/v1/eventos`

- **Canal:** Restful API
- **Identificador:** POST /api/v1/eventos

**Estructura**

```
{"titulo": "string", "descripcion": "string", "locacionId": "uuid", "cupoMaximo": "number (entero > 0)", "fechaInicio": "datetime ISO 8601", "fechaFin": "datetime ISO 8601 (posterior a fechaInicio)", "esPago": "boolean", "categoriaPrecio": "general | especial | null — obligatorio si esPago = true, resuelto contra la tarifa vigente de Backoffice"} — responde 409 si la locación ya tiene un evento solapado en ese rango horario, o si la locación no está aptoEventos
```

**Ejemplo**

```
{"titulo": "Charla: Arquitectura de Software", "descripcion": "Charla abierta sobre patrones de arquitectura.", "locacionId": "c1a4e8d2-7b36-4f90-8e52-1d0a9c3b6f47", "cupoMaximo": 80, "fechaInicio": "2026-10-15T18:00:00-03:00", "fechaFin": "2026-10-15T20:00:00-03:00", "esPago": false, "categoriaPrecio": null}
```

### Portal del Estudiante / Portal del Docente · Salida — `GET /api/v1/eventos?desde=&hasta=`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/eventos?desde=&hasta=

**Estructura**

```
[{"id": "uuid", "titulo": "string", "descripcion": "string", "locacionId": "uuid", "cupoMaximo": "number", "fechaInicio": "datetime", "fechaFin": "datetime", "esPago": "boolean", "categoriaPrecio": "general | especial | null", "creadoPor": "string (id de usuario en CORE)", "locacion": {"nombre": "string", "sede": "string"}, "inscriptos": "number", "disponibles": "number", "yaInscripto": "boolean", "precio": "number | null — resuelto contra la tarifa vigente de Backoffice"}] — ordenado por fechaInicio. desde/hasta son ISO 8601 opcionales y filtran por solapamiento con la ventana. Locación resuelta y cupo calculado para el calendario de los portales; yaInscripto se calcula contra el usuario del JWT
```

**Ejemplo**

```
[{"id": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "titulo": "Charla: Arquitectura de Software", "descripcion": "Charla abierta sobre patrones de arquitectura.", "locacionId": "c1a4e8d2-7b36-4f90-8e52-1d0a9c3b6f47", "cupoMaximo": 80, "fechaInicio": "2026-10-15T18:00:00-03:00", "fechaFin": "2026-10-15T20:00:00-03:00", "esPago": false, "categoriaPrecio": null, "creadoPor": "u-10432", "locacion": {"nombre": "Aula Magna", "sede": "Monserrat"}, "inscriptos": 63, "disponibles": 17, "yaInscripto": false, "precio": null}]
```

### Portal del Estudiante / Portal del Docente · Salida — `GET /api/v1/eventos/{id}`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/eventos/{id}

**Estructura**

```
{"id": "uuid", "titulo": "string", "descripcion": "string", "locacionId": "uuid", "cupoMaximo": "number", "fechaInicio": "datetime", "fechaFin": "datetime", "esPago": "boolean", "categoriaPrecio": "general | especial | null", "creadoPor": "string", "locacion": {"nombre": "string", "sede": "string"}, "inscriptos": "number", "disponibles": "number", "yaInscripto": "boolean", "precio": "number | null — resuelto contra la tarifa vigente de Backoffice"} — destino del link que enviamos en el recordatorio. Mismo objeto que el listado, sin array
```

**Ejemplo**

```
{"id": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "titulo": "Workshop de Testing", "descripcion": "Taller práctico de testing automatizado.", "locacionId": "c1a4e8d2-7b36-4f90-8e52-1d0a9c3b6f47", "cupoMaximo": 40, "fechaInicio": "2026-10-22T18:00:00-03:00", "fechaFin": "2026-10-22T21:00:00-03:00", "esPago": true, "categoriaPrecio": "especial", "creadoPor": "u-10432", "locacion": {"nombre": "Aula Magna", "sede": "Monserrat"}, "inscriptos": 63, "disponibles": 17, "yaInscripto": false, "precio": 4500}
```

### — (consumo interno) · Salida — `GET /api/v1/locaciones`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/locaciones

**Estructura**

```
[{"id": "uuid", "nombre": "string", "sede": "string", "capacidad": "number", "aptoEventos": "boolean"}] — catálogo sincronizado desde Backoffice Administrativo (ver ADR 0013)
```

**Ejemplo**

```
[{"id": "c1a4e8d2-7b36-4f90-8e52-1d0a9c3b6f47", "nombre": "Aula Magna", "sede": "Monserrat", "capacidad": 120, "aptoEventos": true}]
```

### — (consumo interno) · Entrada — `POST /api/v1/inscripciones`

- **Canal:** Restful API
- **Identificador:** POST /api/v1/inscripciones

**Estructura**

```
{"eventoId": "uuid"} — el usuario se toma del JWT de CORE, no viaja en el body. Rechaza con 409 si no hay cupo, si el usuario ya tiene una inscripción superpuesta, o si el saldo es insuficiente
```

**Ejemplo**

```
{"eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03"}
```

### — (consumo interno) · Salida — `GET /api/v1/inscripciones`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/inscripciones

**Estructura**

```
[{"id": "uuid", "eventoId": "uuid", "usuarioId": "string", "fechaInscripcion": "datetime", "estado": "inscripto", "pagoConfirmado": "boolean", "montoCobrado": "number | null — congelado al confirmarse"}] — devuelve las del usuario del JWT. La cancelación de inscripción no está en el alcance del TP, por eso estado tiene un único valor
```

**Ejemplo**

```
[{"id": "5e8d0b31-9c47-4a26-b18f-72e4c0d95a68", "eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "usuarioId": "u-10432", "fechaInscripcion": "2026-09-30T14:22:10-03:00", "estado": "inscripto", "pagoConfirmado": true, "montoCobrado": 12500}]
```

### — (consumo interno) · Entrada — `POST /api/v1/asistencia`

- **Canal:** Restful API
- **Identificador:** POST /api/v1/asistencia

**Estructura**

```
{"inscripcionId": "uuid", "metodo": "qr | manual"} — los dos métodos son los que ya cubre el mock de /asistencia (se descartó "código en sala" por ser el más débil en seguridad). Responde 409 si no existe una inscripción activa para esa inscripcionId
```

**Ejemplo**

```
{"inscripcionId": "5e8d0b31-9c47-4a26-b18f-72e4c0d95a68", "metodo": "qr"}
```

### — (consumo interno) · Salida — `GET /api/v1/eventos/{id}/cupo`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/eventos/{id}/cupo

**Estructura**

```
{"eventoId": "uuid", "cupoMaximo": "number", "inscriptos": "number", "disponibles": "number"}
```

**Ejemplo**

```
{"eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "cupoMaximo": 80, "inscriptos": 63, "disponibles": 17}
```

### CORE · Salida — `POST {CORE_BASE_URL}/saldo/descontar`

- **Canal:** Restful API
- **Identificador:** POST {CORE_BASE_URL}/saldo/descontar

**Estructura**

```
{"usuarioId": "string", "monto": "number (entero, en pesos)", "concepto": "string", "referenciaId": "uuid (id de la inscripción)"} — se llama antes de persistir la inscripción; si el descuento falla, la inscripción no se crea
```

**Ejemplo**

```
{"usuarioId": "u-10432", "monto": 4500, "concepto": "Inscripción a evento: Workshop de Testing", "referenciaId": "5e8d0b31-9c47-4a26-b18f-72e4c0d95a68"}
```

### CORE · Entrada — `POST {CORE_BASE_URL}/saldo/descontar (respuesta)`

- **Canal:** Restful API
- **Identificador:** POST {CORE_BASE_URL}/saldo/descontar (respuesta)

**Estructura**

```
{"aprobado": "boolean", "saldoRestante": "number", "motivo": "string | null"} — si aprobado = false devolvemos 409 al cliente con el motivo y no se persiste la inscripción
```

**Ejemplo**

```
{"aprobado": false, "saldoRestante": 1200, "motivo": "SALDO_INSUFICIENTE"}
```

### CORE · Salida — `evento.recordatorio — cola de notificaciones de CORE`

- **Canal:** Message Queue
- **Identificador:** evento.recordatorio — cola de notificaciones de CORE

**Estructura**

```
{"tipo": "evento.recordatorio", "usuarioId": "string", "eventoId": "uuid", "titulo": "string", "fechaInicio": "datetime", "locacion": "string", "url": "string (link al detalle del evento)"} — lo publica el worker diario cuando fechaInicio - hoy = 7 días, una vez por inscripción activa
```

**Ejemplo**

```
{"tipo": "evento.recordatorio", "usuarioId": "u-10432", "eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "titulo": "Workshop de Testing", "fechaInicio": "2026-10-22T18:00:00-03:00", "locacion": "Aula Magna — Monserrat", "url": "https://uadenet-eventos.vercel.app/eventos/9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03"}
```

### Analítica Institucional · Salida — `evento.creado`

- **Canal:** Message Queue
- **Identificador:** evento.creado

**Estructura**

```
{"tipo": "evento.creado", "eventoId": "uuid", "titulo": "string", "locacionId": "uuid", "sede": "string", "cupoMaximo": "number", "fechaInicio": "datetime", "fechaFin": "datetime", "esPago": "boolean", "categoriaPrecio": "general | especial | null", "emitidoEn": "datetime"} — alimenta la métrica de frecuencia de eventos
```

**Ejemplo**

```
{"tipo": "evento.creado", "eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "titulo": "Workshop de Testing", "locacionId": "c1a4e8d2-7b36-4f90-8e52-1d0a9c3b6f47", "sede": "Monserrat", "cupoMaximo": 40, "fechaInicio": "2026-10-22T18:00:00-03:00", "fechaFin": "2026-10-22T21:00:00-03:00", "esPago": true, "categoriaPrecio": "especial", "emitidoEn": "2026-09-20T11:05:00-03:00"}
```

### Analítica Institucional · Salida — `inscripcion.registrada`

- **Canal:** Message Queue
- **Identificador:** inscripcion.registrada

**Estructura**

```
{"tipo": "inscripcion.registrada", "inscripcionId": "uuid", "eventoId": "uuid", "usuarioId": "string", "rol": "estudiante | docente | administrativo", "pagoConfirmado": "boolean", "emitidoEn": "datetime"} — alimenta la métrica de concurrencia
```

**Ejemplo**

```
{"tipo": "inscripcion.registrada", "inscripcionId": "5e8d0b31-9c47-4a26-b18f-72e4c0d95a68", "eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "usuarioId": "u-10432", "rol": "estudiante", "pagoConfirmado": true, "emitidoEn": "2026-09-30T14:22:10-03:00"}
```

### Analítica Institucional · Salida — `asistencia.confirmada`

- **Canal:** Message Queue
- **Identificador:** asistencia.confirmada

**Estructura**

```
{"tipo": "asistencia.confirmada", "inscripcionId": "uuid", "eventoId": "uuid", "usuarioId": "string", "confirmadaEn": "datetime", "emitidoEn": "datetime"} — alimenta la métrica de presentismo
```

**Ejemplo**

```
{"tipo": "asistencia.confirmada", "inscripcionId": "5e8d0b31-9c47-4a26-b18f-72e4c0d95a68", "eventoId": "9f2b7c14-3d5a-4e88-9a10-6c2d5e7f1b03", "usuarioId": "u-10432", "confirmadaEn": "2026-10-22T18:07:44-03:00", "emitidoEn": "2026-10-22T18:07:45-03:00"}
```

### Backoffice Administrativo · Entrada — `GET /api/v1/backoffice/sedes/{sedeId}/espacios?aptoEventos=true`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/backoffice/sedes/{sedeId}/espacios?aptoEventos=true

**Estructura**

```
{"id": "uuid", "sedeId": "uuid", "codigo": "string", "nombre": "string", "tipo": "string (ej. SALA_EVENTOS)", "capacidad": "number", "aptoEventos": "boolean", "estado": "string (ej. ACTIVO)"} — se pide por sede, no hay listado global. La sede llega como sedeId (uuid), no como nombre: para la cartelera hay que resolverlo con GET /api/v1/backoffice/sedes (y cachearlo) o pedirle a Backoffice que lo embeba
```

**Ejemplo**

```
{"id": "uuid", "sedeId": "uuid", "codigo": "A-305", "nombre": "Auditorio Principal", "tipo": "SALA_EVENTOS", "capacidad": 200, "aptoEventos": true, "estado": "ACTIVO"}
```

### Backoffice Administrativo · Entrada — `GET /api/v1/backoffice/tarifas/vigente?concepto=EVENTO_INSCRIPCION_GENERAL|EVENTO_INSCRIPCION_ESPECIAL&fecha=`

- **Canal:** Restful API
- **Identificador:** GET /api/v1/backoffice/tarifas/vigente?concepto=EVENTO_INSCRIPCION_GENERAL|EVENTO_INSCRIPCION_ESPECIAL&fecha=

**Estructura**

```
{"concepto": "EVENTO_INSCRIPCION_GENERAL | EVENTO_INSCRIPCION_ESPECIAL", "sede": "string | null", "ambitoResuelto": "string (ej. GLOBAL)", "monto": "number (decimal)", "moneda": "string (ej. ARS)", "unidad": "string (ej. MONTO_FIJO)", "vigencia": {"desde": "date", "hasta": "date | null"}, "tarifaId": "uuid"} — se resuelve al momento del cobro, no al crear el evento, para tomar siempre la versión vigente. 404 si no hay ninguna vigente para esa fecha; el fallback ante ese caso lo define este módulo
```

**Ejemplo**

```
{"concepto": "EVENTO_INSCRIPCION_GENERAL", "sede": null, "ambitoResuelto": "GLOBAL", "monto": 1800.00, "moneda": "ARS", "unidad": "MONTO_FIJO", "vigencia": {"desde": "2026-10-01", "hasta": null}, "tarifaId": "8f1e2d3c-4b5a-6789-0abc-def123456789"}
```

Dirección: Entrada = un módulo externo envía datos a este módulo · Salida = este módulo entrega datos a un módulo externo.

Base de la API: /api/v1 (prefijo global «api» + versionado por URI). Estructuras y ejemplos generados desde los schemas Zod de packages/contracts y el modelo de dominio (docs/02-arquitectura/modelo-dominio.md).

«— (consumo interno)» = endpoint que hoy consume solo nuestro propio frontend (apps/web). Queda publicado igual, por si otro módulo lo necesita.

Las estructuras publicadas acá son las que implementa nuestro módulo. Falta que CORE confirme el mecanismo de firma del JWT y el canal del recordatorio (cola vs REST), y que Analítica confirme los tres eventos — seguimiento en docs/02-arquitectura/integraciones.md. Backoffice ya confirmó path y shape de espacios y tarifa vigente; queda pendiente de nuestro lado definir cómo resolvemos el nombre de sede a partir de sedeId, y el fallback ante un 404 de tarifa vigente.

Implementado en apps/api: todos los endpoints /api/v1 de esta planilla, con tests. El descuento de saldo de CORE está mockeado con saldo fijo (saldo.service.ts); la tarifa de inscripción de Backoffice está mockeada con valores fijos en tarifas.service.ts pero todavía no refleja el shape real que confirmó Backoffice (concepto, vigencia, tarifaId) — pendiente de actualizar cuando se implemente la integración real; el recordatorio y los tres eventos hacia Analítica todavía no se emiten.

## Hoja: CORRECIONES PROFESOR

El endpoint de Core para descontar saldo no es el especificado por Core (/saldo/descontar)


- Analítica Institucional no consume los eventos listados


- Los endpoints de Backoffice Administrativo no son los especificados (/api/v1/backoffice/sedes/{sedeId}/espacios y /api/v1/backoffice/tarifas/vigente) por Backoffice Administrativo


- Falta consumir los datos del usuario logueado (Backoffice)


- Falta consumir el listado de Sedes (Backoffice)
