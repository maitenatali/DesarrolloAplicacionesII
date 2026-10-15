# Plan — Segunda entrega (Portal Docente)

Objetivo de la entrega: **módulo completamente funcional con las integraciones mockeadas**.

Estado al 14/10/2026. Marcar cada punto al terminarlo.

## 1. Repositorio

- [x] Prototipos HTML de la primera entrega
- [x] Quitar "Crear curso" (corrección del profe)
- [ ] Subir el frontend del zip (`portal-docente-uadenet.zip`) al repo, en una carpeta `frontend/`
- [ ] Mover los HTML de la primera entrega a una carpeta `prototipos/`
- [ ] Corregir el documento de flujo de datos con las correcciones del profe y subirlo a `docs/` (hoy no está en el repo)

## 2. Base de datos (Supabase)

- [x] Modelo de datos: [modelo-de-datos.md](modelo-de-datos.md)
- [x] Script de tablas: [../db/schema.sql](../db/schema.sql)
- [x] Datos de prueba: [../db/seed.sql](../db/seed.sql)
- [x] Agregar a `acta` las copias (materia, comisión, período, docente), anulación y resultado del envío a Gestión Académica
- [x] Vista `resultado_por_alumno` para el Portal del Estudiante
- [x] Guía para pasar las tablas a entities: [guia-backend-entities.md](guia-backend-entities.md)
- [x] Actualizar `modelo-de-datos.md` con las últimas decisiones (tipo de examen flexible, regularidad 75%, actas nuestras)
- [ ] Crear el proyecto en Supabase y ejecutar `schema.sql` y `seed.sql`

## 3. Backend propio (módulo `teacher`)

Hoy no existe: el frontend guarda todo en el localStorage del navegador.

- [x] Elegir tecnología: Java + Spring Boot, un microservicio `teacher-service` (ver [guia-backend-entities.md](guia-backend-entities.md))
- [x] Proyecto base en [../backend/](../backend/): entities, enums, vistas y repositorios
- [ ] Compilar y arrancar el backend contra Supabase (verifica que las entities coincidan con las tablas)
- [ ] Ruta de resultados por alumno para el Portal del Estudiante (vista `resultado_por_alumno`)
- [ ] Rutas bajo `/api/v1/...`. CORE las publica como `/api/v1/teacher/...` a través de su gateway
- [ ] Validar el token de CORE (claves públicas en `GET /.well-known/jwks.json`)
- [ ] Exámenes: listar por curso, crear, editar, cancelar
- [ ] Asistencia: listar clases de un curso, guardar la asistencia de una clase
- [ ] Regularidad: asistencia y condición por alumno (vista `asistencia_por_alumno`, 75%)
- [ ] Calificaciones: listar por curso, guardar notas de un examen
- [ ] Actas: listar, ver detalle, generar (con número `AÑO-correlativo`)
- [ ] Al generar el acta: enviar los resultados a Gestión Académica (`PUT .../inscripciones/{alumnoId}`)
- [ ] Publicar eventos a CORE (ver punto 4)
- [ ] Documentación Swagger (lo pide el TPO)
- [ ] README con cómo instalar y correr

## 4. Integración con CORE

Fuente: [API de CORE](https://core-api-production-e458.up.railway.app/docs).

- [x] Login, sesión, logout, recuperar contraseña (frontend, conectado de verdad)
- [x] Saldo, movimientos y carga de saldo: `/api/v1/wallets/me...` (frontend)
- [x] Notificaciones del docente: `/api/v1/notifications...` (frontend)
- [ ] **Pedir al equipo de CORE:**
    - [ ] Registrar la URL de nuestro backend en el gateway como módulo `teacher`
    - [ ] Credenciales de servicio (`clientId` y `clientSecret`) para el módulo `teacher`
    - [ ] Dar de alta nuestros tipos de evento en su catálogo (CORE rechaza tipos que no conoce)
    - [ ] Confirmar cómo se relaciona el usuario de CORE (UUID) con `docenteId` y `alumnoId` de Gestión Académica
- [ ] Backend: pedir token de servicio con `POST /internal/v1/service-auth/token` (dura 15 minutos)
- [ ] Backend: publicar eventos con `POST /internal/v1/events` y `source: "teacher"`
- [ ] Backend: validar las cabeceras firmadas (HMAC) que agrega el gateway

## 5. Integración con Gestión Académica

Pendientes detallados en el documento [Portal Docente — Pendientes con Gestión Académica](https://claude.ai/code/artifact/a97b2d02-827f-426f-976a-0f5101196435).

- [x] Rutas del contrato en el frontend (`/planificacion/cursos`, `/periodos`, `/turnos-examen`, correlatividades)
- [x] Datos de ejemplo cuando el módulo no responde (mock)
- [ ] Enviar el documento de pendientes al equipo de Gestión Académica
- [ ] **Hablar sobre el cierre de actas.** Decidido: el acta y su cierre los guarda el Portal Docente. Acordar con ellos:
    - [ ] Qué les enviamos al cerrar el acta: el `PUT .../inscripciones/{alumnoId}` por alumno (lo que hace hoy el frontend), un evento `teacher.acta-generated.v1`, o ambos
    - [ ] Qué estado mandamos para un alumno ausente en el final (hoy no se envía nada)
    - [ ] Si necesitan el número de acta como referencia en la inscripción
    - [ ] Si un acta anulada tiene que revertir el resultado en su sistema
    - [ ] Qué resultado y en qué formato espera su motor de regularidad de la asistencia (nosotros la calculamos con el 75%)
- [ ] Confirmar la ruta final: el gateway de CORE manda `/api/v1/academic/X` a `/api/v1/X` de su servicio, pero su contrato usa `/api/X` (sin `v1`)
- [ ] Filtro de cursos por docente (hoy el frontend pide el detalle de cada curso para encontrar los propios)
- [ ] Rol con el que llama el Portal Docente (el contrato pide `ROLE_ADMINISTRATIVO`)

## 6. Otros módulos (hoy son rutas inventadas con datos de ejemplo)

Para cada uno: conseguir su contrato o Swagger y reemplazar la ruta en `frontend/src/api/endpoints.ts`.

- [ ] Comedor: turnos para el calendario (el profe marcó que `/api/v1/dining/shifts` no existe)
- [ ] Tienda: compras del docente (el profe marcó que `/api/v1/store/purchases/teacher` no existe)
- [ ] Eventos académicos: listado con filtros y recordatorios (el profe marcó que faltan los filtros y el formato)
- [ ] Datos personales de alumnos (nombre, DNI, legajo, mail): averiguar quién los tiene (¿Backoffice?)
- [ ] Perfil del docente: averiguar quién lo tiene (¿Backoffice?)

## 7. Eventos que publicamos

El nombre tiene que coincidir con el que esperan Analítica y Portal del Estudiante, y estar dado de alta en CORE.

| Evento (nombre provisorio) | Cuándo | Lo consumen | Confirmado |
| --- | --- | --- | --- |
| `teacher.attendance-recorded.v1` | Se guarda la asistencia de una clase | Analítica | No |
| `teacher.grade-published.v1` | Se carga una nota | Portal del Estudiante, Analítica | No |
| `teacher.exam-created.v1` | Se crea un examen | Analítica (¿Portal del Estudiante para el calendario?) | No |
| `teacher.acta-generated.v1` | Se genera un acta | Analítica | No |

- [ ] Confirmar nombres y datos con Analítica
- [ ] Confirmar con Portal del Estudiante qué evento usa para la notificación de nota (Gestión Académica propone `academica.resultado.publicado`)

## 8. Frontend

- [ ] Reemplazar el localStorage por llamadas al backend (`frontend/src/store/teacherStore.ts`)
- [ ] Notas por examen en lugar de columnas fijas (hoy el recuperatorio pisa la nota del parcial)
- [ ] Tipos de examen flexibles (hoy hay una lista fija de 7)
- [ ] Mostrar la regularidad por asistencia (75%)
- [ ] Sacar la publicación de eventos del navegador (la hace el backend)

## 9. Entrega final (después)

- [ ] Integración real con todos los módulos
- [ ] Diagrama de arquitectura general del sistema
- [ ] README final
