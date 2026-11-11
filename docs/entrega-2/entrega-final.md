# DESARROLLO DE APLICACIONES II

**[NOMBRE DE LA ENTREGA] - Portal del Docente**

Integrantes:

- Gorrini Rech, Tomas - 1165821
- Natali, Maite - 1197675
- Poggi Toledo, Dahiana Romina - 1151380
- Regueira, Tomas - 1150229
- Suazo Verger, Juan - 1152309
- Varone, Maximo - 1152377

---

## Índice

- A. Vistas del sistema
  - A.1 Login
  - A.2 Recuperar contraseña
  - A.3 Inicio / Dashboard
  - A.4 Mis cursos
  - A.5 Detalle de curso
  - A.6 Estudiantes
  - A.7 Gestión de asistencia
  - A.8 Historial de asistencia
  - A.9 Calificaciones
  - A.10 Exámenes
  - A.11 Nuevo examen
  - A.12 Detalle de examen
  - A.13 Actas
  - A.14 Nueva acta
  - A.15 Detalle de acta
  - A.16 Calendario académico
  - A.17 Notificaciones
  - A.18 Mis compras
  - A.19 Detalle de compra
  - A.20 Cuenta institucional
  - A.21 Cargar saldo
  - A.22 Mi perfil
- B. Arquitectura del módulo
  - B.1 Stack tecnológico y por qué lo elegimos
  - B.2 Estructura de carpetas
  - B.3 Manejo de estado y datos
  - B.4 Integración con CORE y con los otros módulos
  - B.5 Integraciones con terceros
  - B.6 Diagrama de arquitectura
- C. Puntos que no pudimos verificar

---

## A. Vistas del sistema

A continuación se documentan las 22 vistas del Portal del Docente. Para cada una se indica su objetivo, forma de acceso, elementos principales, flujo, datos utilizados, navegación y pantalla.

Todas las vistas, salvo Login y Recuperar contraseña, comparten el mismo encabezado y la misma barra lateral:

- **Encabezado:** logo UADEnet, campana de notificaciones con la cantidad de no leídas (se actualiza cada 30 segundos), chip con el saldo de la cuenta institucional y menú del usuario.
- **Barra lateral:** Inicio, Mis cursos, Actas, Calendario académico, Notificaciones, Mis compras, Cuenta institucional, Perfil y Cerrar sesión.

Los cursos ya no se crean desde el portal: los asigna Gestión Académica y el docente ve solamente los que tiene a cargo.

### A.1 Login

**Objetivo:** Permite que el docente ingrese al portal con su cuenta institucional.

**Acceso:** Es la pantalla inicial para cualquier usuario sin sesión. Si alguien intenta abrir una página interna sin haber iniciado sesión, se lo redirige acá.

**Elementos principales:** Email institucional, contraseña con botón para mostrar u ocultar, enlace "¿Olvidaste tu contraseña?" y botón "Iniciar sesión".

**Flujo:** Se valida que el email termine en @uade.edu.ar y que la contraseña no esté vacía. Si los datos son válidos, se envían a CORE. Si CORE los rechaza, se muestra "El email o la contraseña son incorrectos". Si el usuario existe pero no tiene un rol habilitado para el portal (docente o personal administrativo académico), se muestra "Tu cuenta no tiene acceso al Portal del Docente". Si todo está bien, se entra a Inicio o a la página que el usuario había intentado abrir.

**Datos utilizados:** Login de CORE (`POST /api/v1/auth/login`, simulado localmente). El token de acceso se guarda solo en memoria y la sesión se renueva con una cookie segura (httpOnly).

**Navegación:** Inicio y Recuperar contraseña.

**Capturas:**

- [01-login.png] Pantalla de inicio de sesión con email y contraseña cargados
- [03-login-invalido.png] Mensajes de error por email institucional inválido y contraseña vacía

### A.2 Recuperar contraseña

**Objetivo:** Permite pedir un enlace para restablecer la contraseña.

**Acceso:** Desde Login > ¿Olvidaste tu contraseña?

**Elementos principales:** Email institucional, botón "Enviar enlace", pantalla de confirmación "Revisá tu email", botón "Volver a iniciar sesión" y enlace "Reenviar enlace".

**Flujo:** Se valida el formato del email institucional y se envía el pedido a CORE. La confirmación se muestra siempre igual, exista o no la cuenta, para no revelar qué emails están registrados. "Reenviar enlace" se habilita de nuevo después de 30 segundos.

**Datos utilizados:** Recuperación de contraseña de CORE (`POST /api/v1/auth/password/forgot`, simulado; en esta entrega no se envía un email real).

**Navegación:** Login.

**Capturas:**

- [02-recuperar-contrasena.png] Pantalla inicial de recuperación de contraseña sin datos cargados
- [04-recuperar-enviado.png] Confirmación de envío del enlace de recuperación al email ingresado

### A.3 Inicio / Dashboard

**Objetivo:** Centraliza la información operativa del docente.

**Acceso:** Después del login y desde Inicio.

**Elementos principales:** Saludo con el nombre del docente y la fecha del día, tarjeta con la cantidad de cursos activos, accesos rápidos (Nueva acta y Ver calendario) y panel "Notificaciones recientes" con las cuatro actividades más próximas (exámenes, eventos académicos, turnos de comedor y feriados). El saldo se ve en el chip del encabezado.

**Flujo:** Actúa como punto de partida para entrar a los cursos, generar una nueva acta y consultar el calendario. Al seleccionar una actividad se abre un detalle; si es un examen, desde ahí se puede ir al detalle del examen.

**Datos utilizados:** Cursos asignados al docente y calendario de los próximos 120 días (exámenes del portal, eventos y comedor). El saldo sale de la cuenta institucional de CORE.

**Navegación:** Mis cursos, Nueva acta, Calendario académico, Detalle de examen y Notificaciones.

### A.4 Mis cursos

**Objetivo:** Lista los cursos que el docente tiene asignados y permite filtrarlos.

**Acceso:** Desde la barra lateral > Mis cursos, o desde la tarjeta "Cursos activos" de Inicio.

**Elementos principales:** Buscador, filtro por período, filtro por estado (Activo, Próximo, Finalizado, Cancelado), botón "Limpiar filtros", tabla con materia, comisión, período, sede, horario, cantidad de estudiantes y estado, y paginación de 6 cursos.

**Flujo:** El docente no crea cursos: se le asignan desde Gestión Académica. Seleccionar un curso abre su detalle.

**Datos utilizados:** Cursos de Gestión Académica en los que el docente figura como responsable (simulado). Los nombres de sede salen de un catálogo local mientras Gestión Académica no publique el suyo.

**Navegación:** Detalle de curso.

**Capturas:**

- [05-mis-cursos.png] Pantalla inicial de "Mis cursos" con los cursos asignados al docente

### A.5 Detalle de curso

**Objetivo:** Presenta la información general del curso seleccionado.

**Acceso:** Desde Mis cursos al seleccionar un curso.

**Elementos principales:** Encabezado del curso, pestañas (Información general, Estudiantes, Asistencia, Calificaciones y Exámenes), materia, comisión, período académico, estado, día y horario, sede, aula, cantidad de estudiantes inscriptos y hasta tres próximos exámenes.

**Flujo:** Es el contexto desde el cual se accede a las pestañas operativas del curso.

**Datos utilizados:** Curso seleccionado (Gestión Académica) y exámenes del curso (portal).

**Navegación:** Mis cursos, Estudiantes, Asistencia, Calificaciones, Exámenes y Detalle de examen.

**Capturas:**

- Pantalla inicial de detalles de curso con datos precargados en la seccion de informacion general

### A.6 Estudiantes

**Objetivo:** Presenta el listado de estudiantes del curso seleccionado.

**Acceso:** Desde Detalle de curso > Estudiantes.

**Elementos principales:** Cantidad de estudiantes, búsqueda por nombre, apellido o DNI, filtro por condición (Regular o Libre), tabla con estudiante, DNI, legajo, email y condición, y paginación de 10 estudiantes.

**Flujo:** El contenido depende del curso seleccionado. La condición se calcula con la asistencia: es Regular con 75 % o más (las ausencias justificadas cuentan como presentes) y Libre por debajo de ese valor.

**Datos utilizados:** Inscripciones del curso (Gestión Académica), datos personales de cada estudiante (Backoffice) y resumen de asistencia (portal).

**Navegación:** Pestañas del curso.

**Capturas:**

- Pantalla de detalles de curso con datos precargados en la seccion de estudiantes inscriptos
- Aplicacion de filtro de busqueda y regularidad de cursada de alumnos en seccion de estudiantes

### A.7 Gestión de asistencia

**Objetivo:** Permite registrar la asistencia de una clase.

**Acceso:** Desde Detalle de curso > Asistencia.

**Elementos principales:** Fecha de la clase (no se puede elegir una fecha futura), totales de estudiantes, presentes y ausentes, acciones masivas (Todos presentes y Todos ausentes), búsqueda, estado por estudiante (Presente, Ausente o Justificado), campo de observación o justificación, y botones Cancelar y Guardar.

**Flujo:** Se elige la fecha. Si esa clase ya tenía asistencia cargada, se muestra para editarla. Se marca el estado de cada estudiante; "Todos ausentes" pide confirmación. No se puede guardar hasta completar a todos los estudiantes. Al guardar se muestra un mensaje de confirmación.

**Datos utilizados:** Estudiantes del curso y registro de asistencia de la fecha elegida, guardado en la base de datos del portal. Cada registro genera el evento `teacher.attendance-recorded.v1` hacia CORE.

**Navegación:** Historial de asistencia y otras pestañas del curso.

**Capturas:**

- Pantalla de detalles de curso con datos precargados en la sección de asistencia
- Aplicacion de filtro de búsqueda y asignación de presentismo para cada alumno en particular
- Mensaje de aviso a la hora de marcar a todos los alumnos de la clase como "Ausente"
- Pantalla posterior a marcar todos los alumnos como "Presente"

### A.8 Historial de asistencia

**Objetivo:** Permite consultar el historial de asistencia del curso.

**Acceso:** Desde Gestión de asistencia > Ver historial de asistencia.

**Elementos principales:** Filtro por período (mes), cantidad de clases registradas, tabla con fecha, presentes y ausentes, paginación de 10 clases, detalle de cada clase y búsqueda de un estudiante.

**Flujo:** Seleccionar una clase abre su detalle con presentes, ausentes, justificados y observaciones. Buscar un estudiante muestra su historial individual con el porcentaje de asistencia y filtros por estado (Todos, Presentes, Ausentes y Justificados).

**Datos utilizados:** Registros de asistencia del curso guardados en el portal y estudiantes del curso.

**Navegación:** Gestión de asistencia.

**Capturas:**

- Pantalla inicial de historial de asistencias de todo el periodo
- Pantalla de historial de asistencia con un periodo específico

### A.9 Calificaciones

**Objetivo:** Gestiona las calificaciones del curso.

**Acceso:** Desde Detalle de curso > Calificaciones.

**Elementos principales:** Cantidad de estudiantes, búsqueda por nombre o legajo, matriz con una columna por cada evaluación creada en el curso (por ejemplo Parcial 1, Parcial 2, Recuperatorio Parcial 1, TP1 o Final) y la nota final, barra de cambios sin guardar y botón "Nueva evaluación".

**Flujo:** Se editan las notas directamente en la matriz: un número de 0 a 10 o "A" si el estudiante estuvo ausente. Las notas inválidas se marcan con un mensaje de error. La nota final se recalcula como promedio; si hay nota de recuperatorio, reemplaza a la del parcial que recupera. Los cambios se guardan o se descartan (con confirmación). Si el curso está finalizado o cancelado, la matriz es de solo lectura.

**Datos utilizados:** Matriz de calificaciones del curso guardada en el portal. Cada nota publicada genera el evento `teacher.grade-published.v1` y una notificación al estudiante.

**Navegación:** Nuevo examen y pestañas del curso.

**Capturas:**

- Pantalla inicial de calificaciones sin notas cargadas
- Pantalla con notas modificadas sin guardar y mensaje de error por carga de nota invalida
- Pantalla calificaciones con filtro por nombre de alumno aplicado

### A.10 Exámenes

**Objetivo:** Lista y filtra los exámenes del curso.

**Acceso:** Desde Detalle de curso > Exámenes.

**Elementos principales:** Totales (exámenes, próximos y realizados), búsqueda, filtro por estado (Próximos, Realizados y Cancelados), filtro por tipo (Parcial, Recuperatorio, TP y Final), tabla con examen, tipo, fecha y horario, y estado.

**Flujo:** Seleccionar un examen abre su detalle. "Nuevo examen" inicia el alta y solo aparece si el curso no está finalizado ni cancelado.

**Datos utilizados:** Exámenes del curso guardados en el portal y catálogo de tipos de examen.

**Navegación:** Nuevo examen y Detalle de examen.

**Capturas:**

- Pantalla inicial con listado de exámenes del curso

### A.11 Nuevo examen

**Objetivo:** Crea o edita un examen.

**Acceso:** Desde Exámenes > Nuevo examen, desde Calificaciones > Nueva evaluación, o desde Detalle de examen > Editar examen.

**Elementos principales:** Tipo, descripción (opcional), fecha, hora de inicio (se toma del horario del curso), duración, modalidad (Presencial o Virtual), datos del curso (curso, comisión y período) y un resumen del examen.

**Flujo:** Se validan los campos obligatorios y se crea o se actualiza el examen. No se permite repetir un tipo de examen que ya esté activo en el mismo curso: se controla en la pantalla y también en el servidor. Si hay cambios sin guardar, cancelar pide confirmación. Al guardar se abre el detalle del examen.

**Datos utilizados:** Examen guardado en el portal. Al crearlo se genera el evento `teacher.exam-created.v1` hacia CORE.

**Navegación:** Exámenes, Detalle de examen y calendario académico (el examen aparece ahí).

**Capturas:**

- Pantalla de inicio de creación de nuevo examen con campos vacíos
- Mensaje de error por tipo de examen repetido para ese curso

### A.12 Detalle de examen

**Objetivo:** Muestra el detalle completo de un examen.

**Acceso:** Desde el listado de Exámenes, desde Detalle de curso, desde Inicio o desde el calendario.

**Elementos principales:** Nombre, estado, fecha, días que faltan, horario de inicio y fin, duración, modalidad, aula y sede (si es presencial), descripción, resumen de calificaciones (cargadas, pendientes, promedio y aprobados) y datos del curso.

**Flujo:** Permite volver al listado, editar el examen (si todavía no se tomó), ir a gestionar calificaciones y cancelarlo con confirmación. Un examen cancelado no se borra: queda visible con un aviso.

**Datos utilizados:** Examen seleccionado y sus calificaciones.

**Navegación:** Exámenes, Nuevo examen (edición), Calificaciones y Detalle de curso.

**Capturas:**

- Pantalla de inicio con detalles de un examen específico (Parte 1/2)
- Pantalla de inicio con detalles de un examen especifico (Parte 2/2)

### A.13 Actas

**Objetivo:** Lista las actas académicas de los cursos del docente.

**Acceso:** Desde la barra lateral > Actas.

**Elementos principales:** Búsqueda, filtro por período, tabla ordenable por número, curso y fecha, con período y estado (Finalizada o Anulada).

**Flujo:** Seleccionar un acta lleva a su detalle. "Nueva acta" inicia la generación.

**Datos utilizados:** Actas generadas por el docente, guardadas en el portal.

**Navegación:** Nueva acta y Detalle de acta.

**Capturas:**

- Pantalla inicial con listado de actas de todos los periodos
- Pantalla de actas existentes filtradas por nombre

### A.14 Nueva acta

**Objetivo:** Permite generar una nueva acta en dos pasos.

**Acceso:** Desde Actas > Nueva acta o desde el acceso rápido de Inicio.

**Elementos principales:** Paso 1, Información general: curso, comisión y período (se completan solos), número de acta (se genera automáticamente), tipo (Final o Cursada), examen final (si el acta es Final) y observaciones. Paso 2, Vista previa: datos del acta, cantidad de aprobados y desaprobados (o regulares y libres), aviso si falta información, lista de estudiantes incluidos y casilla de confirmación.

**Flujo:** El curso determina los estudiantes. Se revisa la vista previa, se confirma y se genera el acta. El servidor calcula los resultados, asigna el número y envía los resultados a Gestión Académica. Al terminar se puede abrir el acta o volver al listado.

**Datos utilizados:** Curso, estudiantes, asistencia y calificaciones. El acta queda guardada en el portal y genera los eventos `teacher.acta-generated.v1` y, si es Final, `teacher.course-result-published.v1` por estudiante.

**Navegación:** Actas, Calificaciones (si falta información) y Detalle de acta.

**Capturas:**

- Crear una nueva acta

### A.15 Detalle de acta

**Objetivo:** Visualiza el documento del acta generada.

**Acceso:** Desde Actas o después de generar un acta.

**Elementos principales:** Documento del acta (encabezado UADE, tipo, comisión, período, docente, tabla de resultados con número, estudiante, legajo, resultado y condición, observaciones y firma), información del acta (número, tipo, curso, comisión, período, fecha, estado de sincronización con Gestión Académica y docente responsable) y acciones.

**Flujo:** Permite ampliar el documento, descargar el PDF, imprimir, reintentar la sincronización con Gestión Académica (si hubo errores) y anular el acta indicando un motivo.

**Datos utilizados:** Acta seleccionada o recién generada. El PDF se arma en el navegador.

**Navegación:** Actas.

**Capturas:**

- Imprimir
- Descargar PDF

### A.16 Calendario académico

**Objetivo:** Permite consultar el calendario académico del docente.

**Acceso:** Desde la barra lateral > Calendario académico o desde Inicio > Ver calendario.

**Elementos principales:** Próximo evento destacado, vistas Mes, Semana, Día y Agenda, botón Hoy, navegación entre períodos, filtro de categorías (Exámenes, Eventos académicos, Feriados y Comedor) y detalle de cada evento.

**Flujo:** Se filtra por categorías y se selecciona un evento para ver su detalle. Un turno de comedor muestra horario, estado de la reserva, importe y ubicación; un evento muestra inscripción y costo; un examen permite ir a su detalle.

**Datos utilizados:** Calendario que arma el portal juntando sus exámenes, los turnos de examen de Gestión Académica, los eventos del módulo de Eventos y las reservas del Comedor (todos simulados en esta entrega).

**Navegación:** Detalle de evento, Detalle de examen y navegación común.

**Capturas:**

- Cambiar de mes
- Filtrar por categoría simple
- Filtrar por categoría doble
- Detalle de evento

### A.17 Notificaciones

**Objetivo:** Centraliza las notificaciones que recibe el docente.

**Acceso:** Desde la barra lateral, desde la campana del encabezado o desde Inicio.

**Elementos principales:** Filtros Todas y No leídas con sus cantidades, búsqueda por título o contenido, orden (Más recientes o Más antiguas), paginación, botón "Marcar todas como leídas" y detalle de cada notificación.

**Flujo:** Seleccionar una notificación la marca como leída y abre su detalle; si la notificación tiene una acción asociada, desde el detalle se puede ir a esa página. "Marcar todas como leídas" pide confirmación.

**Datos utilizados:** Notificaciones de CORE (simuladas localmente). El estado de lectura se guarda en CORE.

**Navegación:** Detalle de notificación y la página relacionada con cada notificación.

**Capturas:**

- Filtro: Todas
- Filtro: No leídas
- Ordenar: Más recientes
- Ordenar: Más antiguas
- Marcar todas como leidas
- Detalle de notificación
- Buscar por título o contenido

### A.18 Mis compras

**Objetivo:** Consulta el historial de compras del docente.

**Acceso:** Desde la barra lateral > Mis compras o desde Cuenta institucional > Ver mis compras.

**Elementos principales:** Cantidad de compras realizadas, búsqueda por producto o número de compra, orden (Más recientes, Más antiguas, Mayor importe y Menor importe), tabla con fecha, compra e importe, y paginación de 8 compras.

**Flujo:** Seleccionar una compra abre su detalle.

**Datos utilizados:** Compras de la Tienda del Campus que el portal consulta (simuladas en esta entrega).

**Navegación:** Detalle de compra.

**Capturas:**

- [06-mis-compras.png] Pantalla de "Mis compras" con el historial de compras del docente

### A.19 Detalle de compra

**Objetivo:** Muestra el detalle de una compra.

**Acceso:** Desde Mis compras.

**Elementos principales:** Productos o servicios, resumen (subtotal, descuento, cargo adicional y total), medio de pago (cuenta institucional), información de la transacción (número de compra, fecha y hora) y datos del comprador (nombre, usuario y correo).

**Flujo:** Permite consultar una compra determinada y volver al historial.

**Datos utilizados:** Compra seleccionada y datos del docente.

**Navegación:** Mis compras.

### A.20 Cuenta institucional

**Objetivo:** Consulta el saldo y los movimientos de la cuenta institucional.

**Acceso:** Desde la barra lateral o desde el chip de saldo del encabezado.

**Elementos principales:** Saldo disponible, botones "Cargar saldo" y "Ver mis compras", ingresos y gastos del mes, búsqueda por concepto o número de operación, orden (Más recientes, Más antiguos, Mayor importe y Menor importe), filtro por tipo (Todos, Ingresos y Egresos), tabla de movimientos y detalle de cada movimiento.

**Flujo:** Seleccionar un movimiento abre su detalle con número de operación, fecha, importe, saldo anterior, saldo resultante y referencia. "Cargar saldo" inicia una nueva operación.

**Datos utilizados:** Billetera institucional de CORE (simulada localmente).

**Navegación:** Cargar saldo y Mis compras.

**Capturas:**

- Ordenar: Menor importe
- Ordenar: Mayor importe
- Ordenar: Más antiguos
- Ordenar: Más recientes
- Filtro: Ingresos
- Filtro: Egresos

### A.21 Cargar saldo

**Objetivo:** Permite cargar saldo a la cuenta institucional.

**Acceso:** Desde Cuenta institucional > Cargar saldo.

**Elementos principales:** Saldo actual, importes rápidos ($5.000, $10.000, $20.000 y $50.000), importe personalizado (mínimo $5.000 y máximo $100.000), medio de pago (tarjeta guardada o nueva tarjeta con número, titular, vencimiento y código de seguridad), resumen con el nuevo saldo, términos y condiciones y confirmación.

**Flujo:** Se validan el importe y, si es una tarjeta nueva, sus datos (por ejemplo, que no esté vencida). Al confirmar se muestra "Procesando carga" y después el resultado: carga exitosa con el nuevo saldo, carga pendiente, pago rechazado o error. Cancelar antes de confirmar pide confirmación porque se pierden los datos.

**Datos utilizados:** Carga de saldo de CORE (simulada). Cada pedido lleva una clave de idempotencia para que no se cobre dos veces.

**Navegación:** Cuenta institucional.

**Capturas:**

- Carga exitosa con tarjeta y monto pre-cargados
- Se supera el importe máximo de carga
- La fecha de vencimiento de la tarjeta está vencida
- Carga exitosa con tarjeta nueva y monto personalizado
- Se cancela la carga antes de que se procese

### A.22 Mi perfil

**Objetivo:** Consulta y administra los datos del docente.

**Acceso:** Desde Perfil en la barra lateral o desde el menú de usuario.

**Elementos principales:** Foto e identidad, estado de cuenta, información personal (solo lectura), datos de contacto (correo institucional, correo personal y teléfono), información institucional (legajo, cargo, ID de usuario y estado) y cursos activos a cargo.

**Flujo:** Permite editar los datos de contacto y cambiar la foto (JPG o PNG de hasta 5 MB). Los cursos a cargo llevan a su detalle.

**Datos utilizados:** Datos del docente que el portal obtiene de Backoffice. Como Backoffice todavía no ofrece un servicio para editar contacto ni foto, esos cambios se guardan por ahora en el navegador.

**Navegación:** Detalle de curso y módulos del portal.

**Capturas:**

- Modificación de datos personales

---

## B. Arquitectura del módulo

El Portal del Docente es el módulo 2 de UADEnet. Tiene dos partes: una aplicación web (frontend) que usa el docente y un servicio propio (backend, llamado `teacher-service`) con su base de datos. En esta entrega el módulo funciona completo pero **sin conexión con los otros módulos**: CORE y los demás servicios se simulan dentro del mismo backend, respetando los contratos reales (mismas rutas y mismos formatos). Pasar a los servicios reales es un cambio de configuración, no de código.

### B.1 Stack tecnológico y por qué lo elegimos

| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | React 19 + Vite | Aplicación de una sola página (SPA): las pantallas cambian sin recargar. Vite compila rápido y simplifica el desarrollo. |
| Navegación | React Router 7 | Cada vista tiene su propia URL y las rutas internas exigen sesión iniciada. |
| Estado y datos en el frontend | Redux Toolkit + RTK Query | Todas las llamadas a la API pasan por un único lugar, con caché y actualización automática de las pantallas cuando cambian los datos. |
| PDF de actas | jsPDF | Genera el PDF del acta en el navegador, sin depender de otro servicio. |
| Backend | Python 3.12 + Flask 3 | Framework liviano para construir una API REST ordenada por capas (rutas, servicios y modelos). |
| Validación y documentación de la API | Pydantic 2 + spectree | Cada endpoint valida lo que recibe y lo que devuelve, y queda documentado automáticamente en Swagger (`/apidocs`). |
| Base de datos | PostgreSQL 16 + SQLAlchemy 2 + Alembic | Permite reglas de negocio en la propia base (por ejemplo, que no existan dos actas vigentes iguales), vistas para cálculos como el porcentaje de asistencia, y migraciones versionadas. |
| Seguridad | JWT RS256 validado con JWKS | Es el esquema que define CORE: el backend valida cada token localmente sin consultar a CORE en cada pedido. |
| Ejecución | Docker Compose (base de datos, API, worker de eventos y web con nginx) | Todo el módulo se levanta con un solo comando y igual en todas las computadoras del equipo. |
| Pruebas | pytest con PostgreSQL real (testcontainers) y Vitest | Las pruebas corren contra la misma base de datos que se usa en producción. |

### B.2 Estructura de carpetas

```
DesarrolloAplicacionesII/
├── frontend/                  Aplicación web (React)
│   └── src/
│       ├── api/               Única capa de acceso a la API (RTK Query) y renovación de sesión
│       ├── app/               Configuración del store de Redux
│       ├── features/          Estado global: sesión (auth) y mensajes (ui)
│       ├── components/        Componentes comunes: layout, navegación del curso, paginación, rutas protegidas
│       ├── pages/             Una página por vista (las 22 vistas de este documento)
│       ├── lib/               Utilidades: formatos, textos de la interfaz, PDF del acta
│       └── styles/            Estilos de cada pantalla, generados a partir de los mockups
├── backend/                   Servicio teacher-service (Flask)
│   ├── app/
│   │   ├── routes/            Endpoints REST (capa fina)
│   │   ├── schemas/           Modelos de entrada y salida de la API (Pydantic)
│   │   ├── services/          Reglas de negocio y transacciones
│   │   ├── models/            Tablas de la base de datos
│   │   ├── integrations/      Conexiones con CORE, Gestión Académica, Backoffice y Campus (reales y simuladas)
│   │   ├── security/          Validación de tokens, roles y acceso a cada curso
│   │   └── mock_core/         Simulador local de CORE (login, billetera, notificaciones)
│   ├── migrations/            Migraciones de la base de datos (Alembic)
│   ├── tests/                 Pruebas unitarias, de integración y de punta a punta
│   └── docker-compose.yml     Levanta base de datos, API, worker y web
├── mockup_pantallas/          Mockups HTML de la primera entrega (referencia visual)
└── docs/                      Documentación de arquitectura y de las entregas
```

### B.3 Manejo de estado y datos

**En el frontend:**

- **Sesión:** el token de acceso se guarda solo en memoria (Redux), nunca en el almacenamiento del navegador. La sesión se renueva con una cookie httpOnly que el código JavaScript no puede leer. Si un pedido devuelve 401, se renueva la sesión una vez y se reintenta; si falla, se vuelve al login.
- **Datos del servidor:** RTK Query guarda en caché las respuestas y, cuando el docente cambia algo (por ejemplo, guarda notas), actualiza automáticamente las pantallas que muestran esos datos. Al cerrar sesión la caché se borra.
- **Sin datos de ejemplo:** todas las pantallas muestran datos que vienen de la API. Lo único que se guarda en el navegador son los datos de contacto y la foto del perfil, porque Backoffice todavía no tiene un servicio para editarlos.

**En el backend, cada dato tiene un dueño:**

| Dato | Dueño | Cómo lo maneja el portal |
|---|---|---|
| Períodos, cursos, inscripciones, turnos de examen | Gestión Académica | Los consulta cuando los necesita; guarda solo los identificadores. |
| Nombre, legajo y email de las personas | Backoffice | Los consulta y, al generar un acta, guarda una copia fija en el acta. |
| Clases, asistencia, exámenes, calificaciones y actas | Portal del Docente | Base de datos propia (PostgreSQL). |
| Usuarios, sesiones, billetera y notificaciones | CORE | Simulados en tablas propias solo mientras CORE no esté conectado. |

Algunas reglas viven en la propia base de datos para que se cumplan aunque haya pedidos simultáneos: no puede haber dos exámenes activos del mismo tipo en un curso, ni dos actas vigentes para el mismo curso, tipo y examen. La numeración de actas es correlativa por año.

### B.4 Integración con CORE y con los otros módulos

| Con quién | Para qué | Cómo |
|---|---|---|
| CORE: autenticación | Login, renovación de sesión, recuperación de contraseña | El frontend llama a `/api/v1/auth/*`. El backend valida cada token JWT con las claves públicas de CORE (JWKS). Roles con acceso: `TEACHER`, `ACADEMIC_ADMIN` y `ADMIN_STAFF`. |
| CORE: gateway | Entrada al portal | Las rutas `/api/v1/teacher/*` se redirigen a la API del portal (`/api/v1/*`). En local lo hacen nginx o Vite. |
| CORE: billetera | Saldo, movimientos y carga de saldo | El frontend llama a `/api/v1/wallets/me/*`. |
| CORE: notificaciones | Bandeja del docente y avisos a estudiantes | El frontend lee `/api/v1/notifications`. El backend envía notificaciones a estudiantes (por ejemplo, cuando se publica una nota) por `/internal/v1/notifications`. |
| CORE: eventos | Avisar al resto del ecosistema lo que pasó en el portal | El backend publica en `/internal/v1/events`, con el formato de evento de CORE y `source = teacher`. |
| Gestión Académica | Cursos, inscripciones, períodos y turnos; recibe los resultados de las actas | API REST. Después de generar un acta, el portal envía el resultado de cada estudiante. |
| Backoffice | Datos personales de docentes y estudiantes | `GET /api/v1/users/{id}`. El identificador de cada persona es el mismo en todos los módulos (UUID). |
| Eventos, Comedor y Tienda del Campus | Calendario y compras | Se consultan para armar el calendario y Mis compras. Por ahora solo existe la versión simulada. |
| Analítica y otros módulos | Consumir resultados académicos | Pueden escuchar los eventos del portal o consultar `/students/{id}/results` y `/courses/{id}/results` con un token de servicio. |

Eventos que publica el portal: `teacher.attendance-recorded.v1`, `teacher.grade-published.v1`, `teacher.exam-created.v1`, `teacher.acta-generated.v1`, `teacher.course-result-published.v1` y `teacher.acta-annulled.v1`.

Para no perder eventos, el portal usa una "bandeja de salida" (outbox): el evento se guarda en la base de datos en la misma operación que el cambio (por ejemplo, la nota) y se envía a CORE después. Si CORE no responde, se reintenta más tarde.

### B.5 Integraciones con terceros

**El módulo no tiene integraciones reales con servicios de terceros.** En particular:

- **Pagos:** no hay pasarela de pago. La carga de saldo la resuelve el simulador de CORE; el resultado (aprobado, pendiente o rechazado) depende de la tarjeta de prueba que se use.
- **Email:** la recuperación de contraseña no envía mails; el simulador de CORE solo responde que recibió el pedido.
- **Almacenamiento de imágenes:** no se usa un servicio externo. La foto de perfil se guarda por ahora en el navegador.
- **PDF:** se genera en el navegador con la librería jsPDF; no se usa un servicio externo.
- **Tipografías:** la única dependencia externa en ejecución es Google Fonts, que sirve las fuentes de la interfaz.

Las integraciones con los otros módulos de UADEnet (CORE, Gestión Académica, Backoffice, Eventos, Comedor y Tienda) están simuladas en esta entrega, como se explica en B.4.

### B.6 Diagrama de arquitectura

```mermaid
graph LR
  D[Docente<br/>navegador] -->|HTTPS| WEB[Web<br/>nginx + React]
  WEB -->|/api/v1/teacher/*| API[teacher-service<br/>Flask]
  WEB -->|/api/v1/auth, wallets,<br/>notifications| CORE[CORE<br/>simulado en la API]
  API -->|valida tokens JWKS| CORE
  API --> DB[(PostgreSQL 16)]
  W[Worker de eventos] --> DB
  W -->|/internal/v1/events<br/>/internal/v1/notifications| CORE
  API -->|cursos, inscripciones,<br/>resultados de actas| GA[Gestión Académica<br/>simulado]
  API -->|datos de personas| BO[Backoffice<br/>simulado]
  API -->|calendario y compras| CAMPUS[Eventos / Comedor / Tienda<br/>simulado]
  OTROS[Analítica y otros módulos] -->|token de servicio: /results| API
  CORE -.eventos teacher.*.-> OTROS
```

---

## C. Puntos que no pudimos verificar

1. **Capturas viejas que se mantienen:** no tuvimos las imágenes de la versión anterior, solo sus pies. Se mantuvieron las que describen funciones que siguen existiendo en el código, pero no pudimos comprobar que cada imagen coincida con la pantalla actual. Conviene revisarlas una por una, en especial las de Cuenta institucional (ahora los datos vienen de la billetera de CORE) y las de Detalle de acta (ahora hay botones nuevos: Anular acta y Reintentar sincronización).
2. **Mi perfil, "Modificación de datos personales":** el mockup de la primera entrega tenía una sección "Seguridad" que ya no existe. Si la captura la muestra, hay que reemplazarla.
3. **Cargar saldo, "Se cancela la carga antes de que se procese":** hoy solo se puede cancelar antes de confirmar; mientras se procesa no hay botón de cancelar. Asumimos que la captura muestra la cancelación previa a confirmar.
4. **Nueva acta:** la versión anterior tenía más pasos y selección individual de estudiantes; la actual tiene dos pasos e incluye a todos los inscriptos. Las capturas de esa sección que no tenían pie no se listaron, y la que sí tenía ("Crear una nueva acta") hay que revisarla.
5. **Sección B anterior ("Flujo de datos del Portal del Docente con el ecosistema UADEnet"):** su texto no estaba en la versión que recibimos. La reemplazamos por la sección de arquitectura que pide la consigna. Si se quiere conservar algo de aquella sección, hay que sumarlo a mano.
6. **Índice:** se quitaron los números de página porque dependen del armado final con imágenes.
7. **Motivos del stack (B.1):** son las razones técnicas que se ven en el código y en el diseño. Conviene que el equipo confirme si hubo otros motivos.
8. **Comportamiento en ejecución:** las vistas se describieron leyendo el código del frontend y del backend; no se ejecutó la aplicación ni las pruebas para este documento.
