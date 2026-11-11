# Módulo 9 · Gestión Académica y Planificación

_Convertido desde `Flujo_de_Datos_Modulo_9_UADEnet.xlsx` (hojas: Flujo de Datos)._

## Hoja: Flujo de Datos

> Documentación de Flujo de Datos del Módulo 9
>
> UADEnet — Gestión Académica y Planificación

### Login (pantalla de inicio de sesión) · Entrada — `POST /api/usuarios/login`

- **Canal:** Restful API
- **Identificador:** POST /api/usuarios/login

**Estructura**

```
{"email": "string", "password": "string"}
```

**Ejemplo**

```
{"email": "admin@universidad.edu.ar", "password": "CambiarEstaClave123!"}
```

### Layout (cierre de sesión desde la barra superior) · Entrada — `POST /api/usuarios/logout`

- **Canal:** Restful API
- **Identificador:** POST /api/usuarios/logout

**Estructura**

```
(sin cuerpo)
```

**Ejemplo**

```
(sin cuerpo)
```

### App (sesión activa, guarda de rutas y datos de perfil) · Salida — `GET /api/usuarios/actual`

- **Canal:** Restful API
- **Identificador:** GET /api/usuarios/actual

**Estructura**

```
{"id": "number", "nombre": "string", "email": "string", "permiso": "ADMINISTRATIVO | USUARIO", "activo": "boolean"}
```

**Ejemplo**

```
{"id": 1, "nombre": "María López", "email": "admin@universidad.edu.ar", "permiso": "ADMINISTRATIVO", "activo": true}
```

### Gestión de Usuarios (módulo de administración, aún no implementado en la UI) · Entrada — `POST /api/usuarios`

- **Canal:** Restful API
- **Identificador:** POST /api/usuarios

**Estructura**

```
{"nombre": "string", "email": "string", "password": "string (min 8)", "permiso": "ADMINISTRATIVO | USUARIO"}
```

**Ejemplo**

```
{"nombre": "María López", "email": "mlopez@universidad.edu.ar", "password": "Secreta12345", "permiso": "ADMINISTRATIVO"}
```

### Gestión de Usuarios (módulo de administración, aún no implementado en la UI) · Salida — `GET /api/usuarios`

- **Canal:** Restful API
- **Identificador:** GET /api/usuarios

**Estructura**

```
[{"id": "number", "nombre": "string", "email": "string", "permiso": "string", "activo": "boolean"}]
```

**Ejemplo**

```
[{"id": 1, "nombre": "María López", "email": "admin@universidad.edu.ar", "permiso": "ADMINISTRATIVO", "activo": true}]
```

### Estructura Académica: Carreras · Entrada — `POST /api/academica/carreras`

- **Canal:** Restful API
- **Identificador:** POST /api/academica/carreras

**Estructura**

```
{"codigo": "string", "nombre": "string", "facultad": "string", "duracion": "string", "titulo": "string"}
```

**Ejemplo**

```
{"codigo": "ING-INF", "nombre": "Ingeniería en Informática", "facultad": "Facultad de Ingeniería", "duracion": "5 años", "titulo": "Ingeniero/a en Informática"}
```

### Estructura Académica: Carreras · Salida — `GET /api/academica/carreras`

- **Canal:** Restful API
- **Identificador:** GET /api/academica/carreras

**Estructura**

```
[{"id": "number", "codigo": "string", "nombre": "string", "facultad": "string", "duracion": "string", "titulo": "string", "estado": "ACTIVA | BORRADOR | INACTIVA"}]
```

**Ejemplo**

```
[{"id": 1, "codigo": "ING-INF", "nombre": "Ingeniería en Informática", "facultad": "Facultad de Ingeniería", "duracion": "5 años", "titulo": "Ingeniero/a en Informática", "estado": "ACTIVA"}]
```

### Estructura Académica: Carreras · Entrada — `PUT /api/academica/carreras/{id}`

- **Canal:** Restful API
- **Identificador:** PUT /api/academica/carreras/{id}

**Estructura**

```
{"codigo": "string", "nombre": "string", "facultad": "string", "duracion": "string", "titulo": "string"}
```

**Ejemplo**

```
{"codigo": "ING-INF", "nombre": "Ingeniería en Informática", "facultad": "Facultad de Ingeniería", "duracion": "5 años", "titulo": "Ingeniero/a en Informática"}
```

### Estructura Académica: Carreras · Entrada — `DELETE /api/academica/carreras/{id}`

- **Canal:** Restful API
- **Identificador:** DELETE /api/academica/carreras/{id}

**Estructura**

```
(sin cuerpo — baja lógica: pasa a estado INACTIVA)
```

**Ejemplo**

```
DELETE /api/academica/carreras/1
```

### Estructura Académica: Planes de estudio · Entrada — `POST /api/academica/carreras/{carreraId}/planes`

- **Canal:** Restful API
- **Identificador:** POST /api/academica/carreras/{carreraId}/planes

**Estructura**

```
{"codigo": "string", "nombre": "string", "vigenciaDesde": "date (YYYY-MM-DD)", "cantidadAsignaturas": "number"}
```

**Ejemplo**

```
{"codigo": "PLAN-2026", "nombre": "Plan de estudio 2026", "vigenciaDesde": "2026-03-01", "cantidadAsignaturas": 42}
```

### Estructura Académica: Planes de estudio · Salida — `GET /api/academica/carreras/{carreraId}/planes`

- **Canal:** Restful API
- **Identificador:** GET /api/academica/carreras/{carreraId}/planes

**Estructura**

```
[{"id": "number", "codigo": "string", "nombre": "string", "vigenciaDesde": "date", "cantidadAsignaturas": "number", "estado": "string", "carreraId": "number"}]
```

**Ejemplo**

```
[{"id": 1, "codigo": "PLAN-2026", "nombre": "Plan de estudio 2026", "vigenciaDesde": "2026-03-01", "cantidadAsignaturas": 42, "estado": "ACTIVA", "carreraId": 1}]
```

### Estructura Académica: Planes de estudio (descarga de PDF) · Salida — `GET /api/academica/planes/{planId}/pdf`

- **Canal:** Restful API
- **Identificador:** GET /api/academica/planes/{planId}/pdf

**Estructura**

```
application/pdf (binario)
```

**Ejemplo**

```
plan-estudio-PLAN-2026.pdf
```

### Estructura Académica: Asignaturas · Entrada — `POST /api/academica/planes/{planId}/asignaturas`

- **Canal:** Restful API
- **Identificador:** POST /api/academica/planes/{planId}/asignaturas

**Estructura**

```
{"codigo": "string", "nombre": "string", "anio": "string", "creditos": "number", "cargaHoraria": "number"}
```

**Ejemplo**

```
{"codigo": "INF-302", "nombre": "Desarrollo de Aplicaciones II", "anio": "3.º año", "creditos": 6, "cargaHoraria": 96}
```

### Estructura Académica: Asignaturas · Salida — `GET /api/academica/planes/{planId}/asignaturas`

- **Canal:** Restful API
- **Identificador:** GET /api/academica/planes/{planId}/asignaturas

**Estructura**

```
[{"id": "number", "codigo": "string", "nombre": "string", "anio": "string", "creditos": "number", "cargaHoraria": "number", "estado": "string", "planId": "number"}]
```

**Ejemplo**

```
[{"id": 1, "codigo": "INF-302", "nombre": "Desarrollo de Aplicaciones II", "anio": "3.º año", "creditos": 6, "cargaHoraria": 96, "estado": "ACTIVA", "planId": 1}]
```

### Estructura Académica: Correlatividades · Entrada — `POST /api/academica/asignaturas/{asignaturaId}/correlatividades`

- **Canal:** Restful API
- **Identificador:** POST /api/academica/asignaturas/{asignaturaId}/correlatividades

**Estructura**

```
{"correlativaId": "number", "tipo": "REGULAR | APROBADA"}
```

**Ejemplo**

```
{"correlativaId": 2, "tipo": "APROBADA"}
```

### Estructura Académica: Correlatividades · Salida — `GET /api/academica/asignaturas/{asignaturaId}/correlatividades`

- **Canal:** Restful API
- **Identificador:** GET /api/academica/asignaturas/{asignaturaId}/correlatividades

**Estructura**

```
[{"id": "number", "asignaturaId": "number", "correlativaId": "number", "tipo": "REGULAR | APROBADA"}]
```

**Ejemplo**

```
[{"id": 7, "asignaturaId": 1, "correlativaId": 2, "tipo": "APROBADA"}]
```

### Planificación: Sedes y aulas · Entrada — `POST /api/planificacion/sedes`

- **Canal:** Restful API
- **Identificador:** POST /api/planificacion/sedes

**Estructura**

```
{"nombre": "string", "direccion": "string"}
```

**Ejemplo**

```
{"nombre": "Monserrat", "direccion": "Lima 717, CABA"}
```

### Planificación: Sedes y aulas · Salida — `GET /api/planificacion/sedes`

- **Canal:** Restful API
- **Identificador:** GET /api/planificacion/sedes

**Estructura**

```
[{"id": "number", "nombre": "string", "direccion": "string"}]
```

**Ejemplo**

```
[{"id": 1, "nombre": "Monserrat", "direccion": "Lima 717, CABA"}]
```

### Planificación: Sedes y aulas · Entrada — `POST /api/planificacion/sedes/{sedeId}/aulas`

- **Canal:** Restful API
- **Identificador:** POST /api/planificacion/sedes/{sedeId}/aulas

**Estructura**

```
{"codigo": "string", "capacidadMaxima": "number"}
```

**Ejemplo**

```
{"codigo": "Aula 204", "capacidadMaxima": 42}
```

### Planificación: Sedes y aulas · Salida — `GET /api/planificacion/sedes/{sedeId}/aulas`

- **Canal:** Restful API
- **Identificador:** GET /api/planificacion/sedes/{sedeId}/aulas

**Estructura**

```
[{"id": "number", "codigo": "string", "capacidadMaxima": "number", "sedeId": "number"}]
```

**Ejemplo**

```
[{"id": 1, "codigo": "Aula 204", "capacidadMaxima": 42, "sedeId": 1}]
```

### Planificación: Asignaciones · Entrada — `POST /api/planificacion/asignaciones`

- **Canal:** Restful API
- **Identificador:** POST /api/planificacion/asignaciones

**Estructura**

```
{"aulaId": "number", "asignaturaId": "number", "fecha": "date (YYYY-MM-DD)", "horaInicio": "time (HH:mm)", "horaFin": "time (HH:mm)", "cantidadEstudiantes": "number"}
```

**Ejemplo**

```
{"aulaId": 1, "asignaturaId": 1, "fecha": "2026-08-17", "horaInicio": "08:00", "horaFin": "10:00", "cantidadEstudiantes": 35}
```

### Planificación: Agenda · Salida — `GET /api/planificacion/aulas/{aulaId}/agenda?fecha=YYYY-MM-DD`

- **Canal:** Restful API
- **Identificador:** GET /api/planificacion/aulas/{aulaId}/agenda?fecha=YYYY-MM-DD

**Estructura**

```
[{"id": "number", "aulaId": "number", "asignaturaId": "number", "fecha": "date", "horaInicio": "time", "horaFin": "time", "cantidadEstudiantes": "number"}]
```

**Ejemplo**

```
[{"id": 5, "aulaId": 1, "asignaturaId": 1, "fecha": "2026-08-17", "horaInicio": "08:00", "horaFin": "10:00", "cantidadEstudiantes": 35}]
```

### Ciclo Académico: Períodos · Entrada — `POST /api/planificacion/periodos`

- **Canal:** Restful API
- **Identificador:** POST /api/planificacion/periodos

**Estructura**

```
{"anio": "number (>= 2000)", "numero": "number (1 | 2)", "fechaInicio": "date", "fechaFin": "date"}
```

**Ejemplo**

```
{"anio": 2026, "numero": 2, "fechaInicio": "2026-08-10", "fechaFin": "2026-12-12"}
```

### Ciclo Académico: Períodos · Salida — `GET /api/planificacion/periodos`

- **Canal:** Restful API
- **Identificador:** GET /api/planificacion/periodos

**Estructura**

```
[{"id": "number", "anio": "number", "numero": "number", "fechaInicio": "date", "fechaFin": "date"}]
```

**Ejemplo**

```
[{"id": 1, "anio": 2026, "numero": 2, "fechaInicio": "2026-08-10", "fechaFin": "2026-12-12"}]
```

### Ciclo Académico: Turnos de examen · Entrada — `POST /api/planificacion/turnos-examen`

- **Canal:** Restful API
- **Identificador:** POST /api/planificacion/turnos-examen

**Estructura**

```
{"nombre": "string", "fechaInicio": "date", "fechaFin": "date", "inscripcionDesde": "date", "inscripcionHasta": "date"}
```

**Ejemplo**

```
{"nombre": "Turno diciembre 2026", "fechaInicio": "2026-12-01", "fechaFin": "2026-12-12", "inscripcionDesde": "2026-11-10", "inscripcionHasta": "2026-11-21"}
```

### Ciclo Académico: Turnos de examen · Salida — `GET /api/planificacion/turnos-examen`

- **Canal:** Restful API
- **Identificador:** GET /api/planificacion/turnos-examen

**Estructura**

```
[{"id": "number", "nombre": "string", "fechaInicio": "date", "fechaFin": "date", "inscripcionDesde": "date", "inscripcionHasta": "date"}]
```

**Ejemplo**

```
[{"id": 2, "nombre": "Turno diciembre 2026", "fechaInicio": "2026-12-01", "fechaFin": "2026-12-12", "inscripcionDesde": "2026-11-10", "inscripcionHasta": "2026-11-21"}]
```

### Ciclo Académico: Regularidad · Entrada — `POST /api/regularidad/validar`

- **Canal:** Restful API
- **Identificador:** POST /api/regularidad/validar

**Estructura**

```
{"asistencia": "number (0-100)", "promedio": "number (0-10)", "asistenciaMinima": "number (0-100)", "promedioMinimo": "number (0-10)"}
```

**Ejemplo**

```
{"asistencia": 80, "promedio": 7, "asistenciaMinima": 75, "promedioMinimo": 6}
```

### Ciclo Académico: Regularidad · Salida — `POST /api/regularidad/validar (respuesta)`

- **Canal:** Restful API
- **Identificador:** POST /api/regularidad/validar (respuesta)

**Estructura**

```
{"regular": "boolean", "habilitadoParaFinal": "boolean", "motivos": ["string"]}
```

**Ejemplo**

```
{"regular": true, "habilitadoParaFinal": true, "motivos": []}
```

Dirección: Entrada = un módulo externo envía datos a este módulo · Salida = este módulo entrega datos a un módulo externo.

Estructuras y ejemplos generados desde los DTOs del backend (Spring Boot). Completar la columna «Módulo Externo».
