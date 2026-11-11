# Portal Docente

_Convertido desde `FlujoDatos_-_PortalDocente.xlsx` (hojas: Flujo de Datos - Portal Docente)._

## Hoja: Flujo de Datos - Portal Docente

> Documentación de Flujo de Datos: Portal del Docente

### CORE · Entrada — `POST /api/v1/auth/login`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/auth/login

**Estructura**

```
{"email": "string", "password": "string"}
```

**Ejemplo**

```
{"email": "docente@uade.edu.ar", "password": "<password>"}
```

### CORE · Entrada — `GET /api/v1/wallets/{userId}/balance`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/wallets/{userId}/balance

**Estructura**

```
{"userId": "string"}
```

**Ejemplo**

```
{"userId": "D-404"}
```

### CORE · Salida — `GET /api/v1/wallets/{userId}/balance`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/wallets/{userId}/balance

**Estructura**

```
{"userId": "string", "balance": "number", "currency": "string"}
```

**Ejemplo**

```
{"userId": "D-404", "balance": 85000, "currency": "ARS"}
```

### CORE · Salida — `notification.send`

- **Canal:** Message Queue
- **Identificador:** notification.send

**Estructura**

```
{"recipientId": "string", "type": "string", "message": "string", "link": "string"}
```

**Ejemplo**

```
{"recipientId": "D-404", "type": "EXAM_UPDATED", "message": "Se actualizó un examen", "link": "/examenes/EX-02"}
```

### CORE · Entrada — `balance.updated`

- **Canal:** Message Queue
- **Identificador:** balance.updated

**Estructura**

```
{"userId": "string", "operation": "string", "amount": "number", "balance": "number"}
```

**Ejemplo**

```
{"userId": "D-404", "operation": "credit", "amount": 25000, "balance": 85000}
```

### CORE · Salida — `POST /api/v1/gateway/academic/courses`

- **Canal:** RESTful API
- **Identificador:** POST /api/v1/gateway/academic/courses

**Estructura**

```
{"teacherId": "string", "subjectId": "string", "periodId": "string"}
```

**Ejemplo**

```
{"teacherId": "D-404", "subjectId": "SUB-101", "periodId": "PER-2026-2"}
```

### Portal Estudiante · Salida — `asistencia.registrada`

- **Canal:** Message Queue
- **Identificador:** asistencia.registrada

**Estructura**

```
{"courseId": "string", "studentId": "string", "date": "date", "status": "string"}
```

**Ejemplo**

```
{"courseId": "C-101", "studentId": "E-9912", "date": "2026-09-16", "status": "presente"}
```

### Portal Estudiante · Salida — `nota.publicada`

- **Canal:** Message Queue
- **Identificador:** nota.publicada

**Estructura**

```
{"examId": "string", "studentId": "string", "grade": "number", "status": "string"}
```

**Ejemplo**

```
{"examId": "EX-02", "studentId": "E-9912", "grade": 8.5, "status": "aprobado"}
```

### Portal Estudiante · Salida — `acta.cerrada`

- **Canal:** Message Queue
- **Identificador:** acta.cerrada

**Estructura**

```
{"actId": "string", "courseId": "string", "studentResults": "array"}
```

**Ejemplo**

```
{"actId": "ACT-001", "courseId": "C-101", "studentResults": [{"studentId": "E-9912", "finalGrade": 8}]}
```

### Eventos Académicos · Entrada — `GET /api/v1/events`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/events

**Estructura**

```
{"events": [{"id": "string", "name": "string", "description": "string", "location": "string", "date": "date", "time": "time"}]}
```

**Ejemplo**

```
{"events": [{"id": "EV-10", "name": "Congreso de Tecnología", "description": "Charlas y talleres", "location": "Auditorio Central", "date": "2026-10-05", "time": "18:00"}]}
```

### Eventos Académicos · Entrada — `event.reminder`

- **Canal:** Message Queue
- **Identificador:** event.reminder

**Estructura**

```
{"eventId": "string", "recipientId": "string", "title": "string", "startsAt": "datetime", "message": "string"}
```

**Ejemplo**

```
{"eventId": "EV-10", "recipientId": "D-404", "title": "Congreso de Tecnología", "startsAt": "2026-10-05T18:00:00Z", "message": "El evento comienza mañana"}
```

### CORE · Entrada — `GET /api/v1/users/{userId}`

- **Canal:** RESTful API
- **Identificador:** GET /api/v1/users/{userId}

**Estructura**

```
{"userId": "string", "firstName": "string", "lastName": "string", "email": "string", "role": "string"}
```

**Ejemplo**

```
{"userId": "D-404", "firstName": "Laura", "lastName": "Gómez", "email": "docente@uade.edu.ar", "role": "docente"}
```
