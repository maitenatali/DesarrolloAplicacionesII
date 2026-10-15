# teacher-service — Backend del Portal Docente

Microservicio `teacher` de UADEnet. Spring Boot 3.5 + Java 21 + PostgreSQL (Supabase).

Hoy incluye la base del proyecto: **entities, enums, vistas y repositorios**. Faltan los services, controllers, DTOs, seguridad e integraciones (ver [Qué falta](#qué-falta)).

## Requisitos

- JDK 21
- Maven 3.9+, o IntelliJ IDEA (trae Maven incluido)
- La base creada en Supabase con [../db/schema.sql](../db/schema.sql) y [../db/seed.sql](../db/seed.sql)

## Cómo correrlo

1. Copiar `.env.example` como `.env` en esta carpeta y completar los datos de Supabase (botón **Connect** → **Session pooler**).
2. Desde la carpeta `backend/`:
   ```bash
   mvn spring-boot:run
   ```
   En IntelliJ: abrir la carpeta `backend/` como proyecto y ejecutar `TeacherServiceApplication`.
3. Si arranca sin errores, las entities coinciden con las tablas: `ddl-auto: validate` lo verifica al inicio.
4. Swagger: http://localhost:8080/swagger-ui.html (vacío hasta que haya controllers).

`.env` no se sube al repo: tiene la contraseña de la base.

## Estructura

```
src/main/java/ar/edu/uade/uadenet/teacher/
├── TeacherServiceApplication.java
├── asistencia/
│   ├── Clase.java                       tabla clase
│   ├── Asistencia.java                  tabla asistencia
│   ├── EstadoAsistencia.java            PRESENTE | AUSENTE | JUSTIFICADO
│   ├── CondicionAsistencia.java         REGULAR | LIBRE
│   ├── AsistenciaPorAlumno(+Id).java    vista asistencia_por_alumno (solo lectura)
│   ├── ClaseRepository.java
│   └── AsistenciaPorAlumnoRepository.java
├── examen/
│   ├── Examen.java                      tabla examen
│   ├── Calificacion.java                tabla calificacion
│   ├── ModalidadExamen.java             PRESENCIAL | VIRTUAL
│   ├── EstadoExamen.java                PROGRAMADO | CANCELADO
│   ├── ExamenRepository.java
│   └── CalificacionRepository.java
└── acta/
    ├── Acta.java                        tabla acta
    ├── ActaDetalle.java                 tabla acta_detalle
    ├── TipoActa.java                    CURSADA | FINAL
    ├── EstadoActa.java                  GENERADA | ANULADA
    ├── ResultadoActa.java               APROBADO | DESAPROBADO | REGULAR | LIBRE | AUSENTE
    ├── ResultadoPorAlumno(+Id).java     vista resultado_por_alumno (solo lectura)
    ├── ActaRepository.java
    └── ResultadoPorAlumnoRepository.java
```

Detalle de cada columna y por qué está mapeada así: [../docs/guia-backend-entities.md](../docs/guia-backend-entities.md).

## Convenciones

- **Las tablas las crea `db/schema.sql`**, no Hibernate. Si cambia una tabla, se cambia primero el SQL y después la entity.
- **Las entities no salen por la API.** Los controllers reciben y devuelven DTOs (`record`).
- **Relaciones:** `Clase` → `Asistencia` y `Acta` → `ActaDetalle` se guardan en cascada (se usan `agregarAsistencia` y `agregarDetalle`). `Examen` no carga sus calificaciones: se piden con `CalificacionRepository`.
- **Lombok:** solo `@Getter`, `@Setter` y constructores. No usar `@Data` en entities: genera `equals` y `toString` que recorren las relaciones.
- **Columnas `timestamptz`** llevan `columnDefinition = "timestamptz"` para que la validación de Hibernate las reconozca.

## Qué falta

- [ ] DTOs, services y controllers: exámenes → asistencia → calificaciones → actas
- [ ] Manejo global de errores (`@RestControllerAdvice`), con 409 para las reglas únicas de la base
- [ ] Seguridad con el token de CORE (`spring-boot-starter-oauth2-resource-server` + JWKS)
- [ ] Integraciones con versión `mock` y `live` (Gestión Académica, eventos de CORE, datos de alumnos)
- [ ] Ruta de resultados por alumno para el Portal del Estudiante
