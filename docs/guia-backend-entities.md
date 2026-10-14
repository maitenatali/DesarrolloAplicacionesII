# Guía — Base de datos y entities del backend (Spring Boot)

Cómo crear las tablas en Supabase y pasarlas a entities JPA para el backend del Portal Docente.

- Script de tablas: [../db/schema.sql](../db/schema.sql)
- Datos de prueba: [../db/seed.sql](../db/seed.sql)
- Modelo explicado: [modelo-de-datos.md](modelo-de-datos.md)

## 1. Arquitectura: un microservicio `teacher`

UADEnet es un sistema de microservicios: cada módulo del TPO es uno. **El Portal Docente es un solo microservicio**, `teacher-service`, por tres motivos:

1. El gateway de CORE registra un solo destino por módulo: `/api/v1/teacher/...` se reenvía a una única URL.
2. Las tablas están relacionadas (un acta apunta a su examen final), y generar un acta tiene que ser una sola transacción.
3. Dividirlo más (asistencia por un lado, actas por otro) suma despliegues, configuración y comunicación entre servicios sin resolver nada del TPO.

Adentro del servicio, el código se separa por dominio (`asistencia`, `examen`, `acta`). Si algún día hiciera falta partirlo, esas carpetas son los cortes.

```
UADEnet
├── core-service          (CORE: login, gateway, eventos, saldo)
├── academic-service      (Gestión Académica)
├── teacher-service  ◄─── NOSOTROS: Spring Boot + Supabase
├── student-service
└── ...
```

## 2. Crear la base en Supabase

1. Crear el proyecto en [supabase.com](https://supabase.com). Guardar la contraseña de la base.
2. **SQL Editor** → pegar [schema.sql](../db/schema.sql) → **Run**.
3. **SQL Editor** → pegar [seed.sql](../db/seed.sql) → **Run**.
4. Verificar en **Table Editor** que estén las 6 tablas con datos y, en el SQL Editor:
   ```sql
   select * from asistencia_por_alumno;   -- 3 filas: 456 y 458 REGULAR, 457 LIBRE
   select * from resultado_por_alumno;    -- 3 filas del acta 2026-001
   ```
5. Botón **Connect** (arriba) → pestaña **Session pooler** → copiar los datos de conexión. Usar el *pooler* y no la conexión directa: la directa solo funciona con IPv6.

Para volver a crear todo desde cero, al principio de `schema.sql` hay dos líneas `drop` comentadas.

## 3. Crear el proyecto Spring Boot

En [start.spring.io](https://start.spring.io):

| Opción | Valor |
| --- | --- |
| Project | Maven |
| Language | Java 21 |
| Group / Artifact | `ar.edu.uade.uadenet` / `teacher-service` |
| Packaging | Jar |

Dependencias:

| Dependencia | Para qué |
| --- | --- |
| Spring Web | API REST |
| Spring Data JPA | Entities y repositorios |
| PostgreSQL Driver | Conexión a Supabase |
| Validation | Validar los cuerpos de los pedidos (`@NotNull`, `@DecimalMax`, etc.) |
| OAuth2 Resource Server | Validar el token de CORE |
| Lombok (opcional) | Menos código repetido (getters, setters) |

A mano en el `pom.xml`, para Swagger (lo pide el TPO):

```xml
<dependency>
  <groupId>org.springdoc</groupId>
  <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
  <version><!-- última versión compatible con tu Spring Boot --></version>
</dependency>
```

## 4. Configuración

`src/main/resources/application.yml`. Los datos sensibles van en variables de entorno, nunca en el repo.

```yaml
server:
  port: 8080

spring:
  application:
    name: teacher-service
  datasource:
    url: ${DB_URL}            # jdbc:postgresql://aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
    username: ${DB_USER}      # postgres.<id-del-proyecto>
    password: ${DB_PASSWORD}
  jpa:
    open-in-view: false
    hibernate:
      ddl-auto: validate      # las tablas las crea schema.sql; Hibernate solo verifica que coincidan
    properties:
      hibernate.jdbc.time_zone: UTC
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: https://core-api-production-e458.up.railway.app/.well-known/jwks.json

app:
  integrations:
    mode: ${INTEGRATIONS_MODE:mock}   # mock | live
    core-url: https://core-api-production-e458.up.railway.app
    academic-url: ${ACADEMIC_URL:}
```

**`ddl-auto: validate`**: al arrancar, Hibernate compara cada entity con su tabla y frena si falta una columna o un tipo no coincide. Sirve para detectar errores de tipeo. Nunca usar `create` o `update`: modificarían las tablas de Supabase.

## 5. Estructura de paquetes

```
ar.edu.uade.uadenet.teacher
├── TeacherServiceApplication.java
├── config/            seguridad, Swagger, clientes HTTP
├── common/            manejo de errores, clases compartidas
├── asistencia/
│   ├── Clase.java, Asistencia.java, EstadoAsistencia.java
│   ├── AsistenciaPorAlumno.java              (vista)
│   ├── ClaseRepository.java, AsistenciaPorAlumnoRepository.java
│   ├── AsistenciaService.java
│   ├── AsistenciaController.java
│   └── dto/
├── examen/
│   ├── Examen.java, Calificacion.java, ModalidadExamen.java, EstadoExamen.java
│   ├── ExamenRepository.java, CalificacionRepository.java
│   ├── ExamenService.java, CalificacionService.java
│   ├── ExamenController.java
│   └── dto/
├── acta/
│   ├── Acta.java, ActaDetalle.java, TipoActa.java, EstadoActa.java, ResultadoActa.java
│   ├── ResultadoPorAlumno.java               (vista)
│   ├── ActaRepository.java, ResultadoPorAlumnoRepository.java
│   ├── ActaService.java
│   ├── ActaController.java
│   └── dto/
└── integration/       clientes de CORE y Gestión Académica (real y mock)
```

**Las entities nunca se devuelven directo en la API.** Cada controller recibe y devuelve DTOs (`record` de Java). Así un cambio en la tabla no rompe el contrato con el frontend.

## 6. Tipos: de PostgreSQL a Java

| PostgreSQL | Java | Anotación |
| --- | --- | --- |
| `bigint generated ... as identity` | `Long` | `@Id @GeneratedValue(strategy = GenerationType.IDENTITY)` |
| `bigint` (referencia externa) | `Long` | `@Column(name = "curso_id", nullable = false)` |
| `varchar(n)` | `String` | `@Column(length = n)` |
| `varchar` con `check (... in (...))` | `enum` | `@Enumerated(EnumType.STRING) @Column(length = n)` |
| `text` | `String` | `@Column(columnDefinition = "text")` |
| `integer` | `Integer` | |
| `numeric(4,2)` | `BigDecimal` | `@Column(precision = 4, scale = 2)` |
| `boolean` | `Boolean` | |
| `date` | `LocalDate` | |
| `time` | `LocalTime` | |
| `timestamptz` | `OffsetDateTime` | `@CreationTimestamp` / `@UpdateTimestamp` donde corresponda |

Las columnas en la base van en `snake_case` (`curso_id`) y en Java en `camelCase` (`cursoId`). Spring Boot hace la conversión solo, pero conviene poner `@Column(name = "...")` igual, para que se lea claro.

## 7. Enums

Los valores tienen que ser **exactamente** los del `check` de la tabla.

| Enum Java | Valores | Columna |
| --- | --- | --- |
| `EstadoAsistencia` | `PRESENTE`, `AUSENTE`, `JUSTIFICADO` | `asistencia.estado` |
| `ModalidadExamen` | `PRESENCIAL`, `VIRTUAL` | `examen.modalidad` |
| `EstadoExamen` | `PROGRAMADO`, `CANCELADO` | `examen.estado` |
| `TipoActa` | `CURSADA`, `FINAL` | `acta.tipo` |
| `EstadoActa` | `GENERADA`, `ANULADA` | `acta.estado` |
| `ResultadoActa` | `APROBADO`, `DESAPROBADO`, `REGULAR`, `LIBRE`, `AUSENTE` | `acta_detalle.resultado` |
| `CondicionAsistencia` | `REGULAR`, `LIBRE` | vista `asistencia_por_alumno.condicion` |

`examen.tipo` **no es enum**: es texto libre (`String`), para poder sumar tipos de examen sin cambiar el código.

## 8. Entities por tabla

### `clase` → `Clase`

| Columna | Campo | Tipo | Notas |
| --- | --- | --- | --- |
| `id` | `id` | `Long` | PK identity |
| `curso_id` | `cursoId` | `Long` | |
| `fecha` | `fecha` | `LocalDate` | |
| `observaciones` | `observaciones` | `String` | `text` |
| `creado_por` | `creadoPor` | `String` | Id del docente, sale del token |
| `creado_en` | `creadoEn` | `OffsetDateTime` | `@CreationTimestamp` |
| `actualizado_en` | `actualizadoEn` | `OffsetDateTime` | `@UpdateTimestamp` |
| — | `asistencias` | `List<Asistencia>` | `@OneToMany(mappedBy = "clase", cascade = ALL, orphanRemoval = true)` |

### `asistencia` → `Asistencia`

| Columna | Campo | Tipo | Notas |
| --- | --- | --- | --- |
| `id` | `id` | `Long` | PK identity |
| `clase_id` | `clase` | `Clase` | `@ManyToOne(fetch = LAZY, optional = false) @JoinColumn(name = "clase_id")` |
| `alumno_id` | `alumnoId` | `String` | `length = 50` |
| `estado` | `estado` | `EstadoAsistencia` | enum |
| `observacion` | `observacion` | `String` | `length = 255` |

### `examen` → `Examen`

| Columna | Campo | Tipo | Notas |
| --- | --- | --- | --- |
| `id` | `id` | `Long` | PK identity |
| `curso_id` | `cursoId` | `Long` | |
| `tipo` | `tipo` | `String` | `length = 50`, texto libre |
| `nombre` | `nombre` | `String` | `length = 100` |
| `descripcion` | `descripcion` | `String` | `length = 500` |
| `fecha` | `fecha` | `LocalDate` | |
| `hora_inicio` | `horaInicio` | `LocalTime` | |
| `duracion_minutos` | `duracionMinutos` | `Integer` | |
| `modalidad` | `modalidad` | `ModalidadExamen` | enum |
| `estado` | `estado` | `EstadoExamen` | enum, arranca en `PROGRAMADO` |
| `creado_por` | `creadoPor` | `String` | |
| `creado_en` | `creadoEn` | `OffsetDateTime` | `@CreationTimestamp` |
| `actualizado_en` | `actualizadoEn` | `OffsetDateTime` | `@UpdateTimestamp` |

No lleva la lista de calificaciones: se consultan con `CalificacionRepository.findByExamenId(...)`. Así cargar un examen no trae todas sus notas.

### `calificacion` → `Calificacion`

| Columna | Campo | Tipo | Notas |
| --- | --- | --- | --- |
| `id` | `id` | `Long` | PK identity |
| `examen_id` | `examen` | `Examen` | `@ManyToOne(fetch = LAZY, optional = false)` |
| `alumno_id` | `alumnoId` | `String` | `length = 50` |
| `nota` | `nota` | `BigDecimal` | `precision = 4, scale = 2`, puede ser `null` |
| `ausente` | `ausente` | `Boolean` | |
| `cargada_por` | `cargadaPor` | `String` | |
| `cargada_en` | `cargadaEn` | `OffsetDateTime` | `@UpdateTimestamp`: cambia cada vez que se guarda |

### `acta` → `Acta`

| Columna | Campo | Tipo | Notas |
| --- | --- | --- | --- |
| `id` | `id` | `Long` | PK identity |
| `numero` | `numero` | `String` | `length = 20`, único. Lo genera `ActaService` (`AÑO-001`) |
| `tipo` | `tipo` | `TipoActa` | enum |
| `curso_id` | `cursoId` | `Long` | |
| `asignatura_id` | `asignaturaId` | `Long` | |
| `periodo_id` | `periodoId` | `Long` | |
| `examen_id` | `examen` | `Examen` | `@ManyToOne(fetch = LAZY)`, `null` en actas de cursada |
| `materia` | `materia` | `String` | `length = 150`, copia |
| `comision` | `comision` | `String` | `length = 50`, copia |
| `periodo` | `periodo` | `String` | `length = 50`, copia |
| `docente_id` | `docenteId` | `String` | |
| `docente_nombre` | `docenteNombre` | `String` | `length = 150`, copia |
| `fecha` | `fecha` | `LocalDate` | |
| `observaciones` | `observaciones` | `String` | `text` |
| `estado` | `estado` | `EstadoActa` | enum |
| `generada_en` | `generadaEn` | `OffsetDateTime` | `@CreationTimestamp` |
| `anulada_en` | `anuladaEn` | `OffsetDateTime` | Se completa al anular |
| `motivo_anulacion` | `motivoAnulacion` | `String` | `text` |
| `sync_ok` | `syncOk` | `Integer` | |
| `sync_error` | `syncError` | `Integer` | |
| `sync_en` | `syncEn` | `OffsetDateTime` | |
| — | `detalles` | `List<ActaDetalle>` | `@OneToMany(mappedBy = "acta", cascade = ALL, orphanRemoval = true) @OrderBy("orden")` |

### `acta_detalle` → `ActaDetalle`

| Columna | Campo | Tipo | Notas |
| --- | --- | --- | --- |
| `id` | `id` | `Long` | PK identity |
| `acta_id` | `acta` | `Acta` | `@ManyToOne(fetch = LAZY, optional = false)` |
| `orden` | `orden` | `Integer` | |
| `alumno_id` | `alumnoId` | `String` | |
| `alumno_nombre` | `alumnoNombre` | `String` | `length = 150` |
| `alumno_legajo` | `alumnoLegajo` | `String` | `length = 20` |
| `nota` | `nota` | `BigDecimal` | `precision = 4, scale = 2` |
| `resultado` | `resultado` | `ResultadoActa` | enum |

### Vistas → entities de solo lectura

Las vistas se mapean como entities con `@Immutable` (Hibernate no permite escribirlas). No tienen columna `id`, así que la clave es compuesta, con `@IdClass`.

| Vista | Entity | Clave (`@IdClass`) |
| --- | --- | --- |
| `asistencia_por_alumno` | `AsistenciaPorAlumno` | `cursoId` + `alumnoId` |
| `resultado_por_alumno` | `ResultadoPorAlumno` | `cursoId` + `alumnoId` |

En la vista de asistencia, `porcentaje_asistencia` es `BigDecimal` y `condicion` es `CondicionAsistencia`.

## 9. Ejemplo completo: `Clase` y `Asistencia`

Este es el patrón para todas las demás. Si usan Lombok, los getters y setters se reemplazan por `@Getter @Setter`.

```java
package ar.edu.uade.uadenet.teacher.asistencia;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "clase")
public class Clase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "curso_id", nullable = false)
    private Long cursoId;

    @Column(nullable = false)
    private LocalDate fecha;

    @Column(columnDefinition = "text")
    private String observaciones;

    @Column(name = "creado_por", nullable = false, length = 50)
    private String creadoPor;

    @CreationTimestamp
    @Column(name = "creado_en", nullable = false, updatable = false)
    private OffsetDateTime creadoEn;

    @UpdateTimestamp
    @Column(name = "actualizado_en", nullable = false)
    private OffsetDateTime actualizadoEn;

    @OneToMany(mappedBy = "clase", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Asistencia> asistencias = new ArrayList<>();

    /** Mantiene los dos lados de la relación sincronizados. */
    public void agregarAsistencia(Asistencia asistencia) {
        asistencias.add(asistencia);
        asistencia.setClase(this);
    }

    // getters y setters
}
```

```java
package ar.edu.uade.uadenet.teacher.asistencia;

import jakarta.persistence.*;

@Entity
@Table(name = "asistencia")
public class Asistencia {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "clase_id", nullable = false)
    private Clase clase;

    @Column(name = "alumno_id", nullable = false, length = 50)
    private String alumnoId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 15)
    private EstadoAsistencia estado;

    @Column(length = 255)
    private String observacion;

    // getters y setters
}
```

```java
package ar.edu.uade.uadenet.teacher.asistencia;

public enum EstadoAsistencia { PRESENTE, AUSENTE, JUSTIFICADO }
```

## 10. Reglas que controla la base

Estas reglas están en `schema.sql`. El service las tiene que validar antes de guardar, para devolver un error claro. Si alguna se escapa, la base la frena con `DataIntegrityViolationException`, y el manejo global de errores la convierte en `409 Conflict`.

| Regla | Dónde está en la base | Error sugerido |
| --- | --- | --- |
| Una sola toma de asistencia por curso y fecha | `clase_curso_fecha_uk` | 409 |
| Un alumno una sola vez por clase | `asistencia_clase_alumno_uk` | 400 |
| Un examen activo de cada tipo por curso | `examen_curso_tipo_activo_uk` | 409 "Ya existe un examen de este tipo" |
| Nota entre 0 y 10 | `check (nota between 0 and 10)` | 400 |
| Ausente sin nota | `calificacion_ausente_sin_nota_ck` | 400 |
| Acta final con examen; de cursada sin examen | `acta_examen_segun_tipo_ck` | 400 |
| Un acta vigente por curso y tipo | `acta_vigente_uk` | 409 "Ya existe un acta generada" |
| Acta anulada con fecha de anulación | `acta_anulacion_ck` | — (lo garantiza el service) |

## 11. Integraciones mockeadas

Es lo que pide la segunda entrega. Cada integración es una **interfaz** con dos implementaciones, y la configuración elige cuál usar:

| Interfaz | Implementación `mock` | Implementación `live` |
| --- | --- | --- |
| `AcademicClient` | Devuelve el curso 42, sus inscriptos y períodos con los datos del contrato | Llama a Gestión Académica por el gateway de CORE |
| `CoreEventsClient` | Escribe el evento en el log | Pide token de servicio y publica en `POST /internal/v1/events` |
| `StudentDirectoryClient` | Devuelve nombre y legajo de ejemplo | Módulo que tenga los datos personales (a confirmar) |

```java
@Service
@ConditionalOnProperty(name = "app.integrations.mode", havingValue = "mock", matchIfMissing = true)
public class MockAcademicClient implements AcademicClient { ... }

@Service
@ConditionalOnProperty(name = "app.integrations.mode", havingValue = "live")
public class HttpAcademicClient implements AcademicClient { ... }
```

Los services usan solo la interfaz. Para la entrega final se cambia `INTEGRATIONS_MODE=live` y no se toca más código.

## 12. Orden de trabajo sugerido

- [ ] Correr `schema.sql` y `seed.sql` en Supabase (paso 2)
- [ ] Crear el proyecto y la configuración (pasos 3 y 4)
- [ ] Entities y enums de `asistencia` → arrancar la app y ver que `validate` no tire errores
- [ ] Entities de `examen` y `acta`, y las dos vistas
- [ ] Repositorios (`JpaRepository<Entidad, Long>`)
- [ ] Interfaces de integración con su versión `mock`
- [ ] Services y controllers, un dominio por vez: exámenes → asistencia → calificaciones → actas
- [ ] Seguridad con el token de CORE
- [ ] Swagger en `/swagger-ui.html`
- [ ] Manejo global de errores (`@RestControllerAdvice`)

## Problemas frecuentes

| Error al arrancar | Causa probable |
| --- | --- |
| `Schema-validation: missing table [...]` | No se corrió `schema.sql`, o el nombre en `@Table` no coincide |
| `Schema-validation: missing column [...]` | El nombre en `@Column(name = ...)` no coincide con la tabla |
| `Schema-validation: wrong column type ...` | El tipo Java no coincide (ver la tabla del paso 6) |
| `Connection refused` o timeout | Se usó la conexión directa en lugar del Session pooler, o falta `sslmode=require` |
| `password authentication failed` | El usuario del pooler es `postgres.<id-del-proyecto>`, no solo `postgres` |
