# Software FJ · Gestión de clientes, servicios y reservas

Proyecto académico desarrollado en **Python + Tkinter** para la Fase 4 del curso **Programación (213023)** de la UNAD. Interfaz de escritorio con diseño formal en tonos azul, blanco, verde y amarillo suave. No utiliza bases de datos ni bibliotecas gráficas externas.

## Inicio rápido en Windows

1. Instala **Python 3.10 o posterior** con soporte para Tkinter (versión estándar de python.org).
2. Descomprime la carpeta completa.
3. Haz doble clic en **`INICIAR_SOFTWARE_FJ.pyw`** (ventana sin consola), o **`INICIAR_SOFTWARE_FJ.bat`** si prefieres ver mensajes de diagnóstico. También puedes abrir una terminal dentro de la carpeta y ejecutar:

   ```bash
   python main.py
   ```

4. Se abrirá una **ventana independiente** con barra lateral y formularios. No tienes que operar desde la consola.

> Si se utiliza IDLE, abre `main.py` y presiona **F5**. La interfaz debería abrirse como ventana separada.

## Funciones

| Sección | Funciones |
|---|---|
| Inicio | Indicadores de clientes, servicios activos, reservas y acciones rápidas |
| Clientes | Registro, búsqueda instantánea, edición, eliminación segura y validación de correo/teléfono |
| Servicios | Salas, alquiler de equipos y asesorías; tarifa, capacidad, edición, activar/desactivar |
| Reservas | Crear con fecha/hora/duración/cantidad, descuentos e impuestos; confirmar, cancelar, consultar; control de solapamientos y capacidad |
| Simulaciones | 25 operaciones válidas e inválidas aisladas, con reporte por escenario |
| Registros | Consulta de los últimos eventos y errores en `logs/sistema.log` |

### Recorrido recomendado

1. Abre **Clientes** y registra una persona.
2. En **Servicios**, revisa los tres servicios de ejemplo o añade uno nuevo.
3. Ve a **Reservas** > **Nueva reserva**, selecciona cliente y servicio, fecha y cantidad.
4. Activa **Confirmar inmediatamente** o deja la reserva como pendiente.
5. Revisa el resultado en **Reservas** y **Registros**.
6. Ejecuta **Simulaciones** para validar el manejo de errores.

## Arquitectura

```text
Software_FJ_Tkinter/
├── main.py                   Lanzador de la aplicación y del demo
├── INICIAR_SOFTWARE_FJ.pyw   Doble clic: ventana sin consola en Windows
├── INICIAR_SOFTWARE_FJ.bat   Alternativa con consola de diagnóstico
├── app/
│   ├── interfaz.py           Tkinter: ventanas, tablas, navegación y formularios
│   ├── modelos.py            Entidad, Cliente, Servicio, Sala, Equipo, Asesoria, Reserva
│   ├── gestor.py             Reglas, listas/diccionarios en memoria, confirmación
│   ├── excepciones.py        Excepciones personalizadas
│   ├── registro.py           Rotación y lectura del archivo de logs
│   └── simulaciones.py       25 escenarios esperados, válidos e inválidos
├── tests/
│   └── test_sistema.py       Pruebas automáticas unitarias
├── logs/                      Archivo de registro se crea al ejecutar
├── GUIA_GITHUB.md            Pasos para entregar el repositorio
├── RESULTADOS_DE_PRUEBAS.txt Evidencia de pruebas ejecutadas
├── capturas/                 Vistas previas de la aplicación
└── README.md
```

### Principios de programación orientada a objetos

- **Abstracción:** `Entidad` y `Servicio` son clases abstractas, mediante `ABC` y `@abstractmethod`.
- **Herencia:** `Cliente` y `Servicio` descienden de `Entidad`. `Sala`, `Equipo` y `Asesoria` descienden de `Servicio`.
- **Polimorfismo:** cada servicio implementa `validar_solicitud`, `calcular_subtotal` y `descripcion`.
- **Encapsulación:** `Cliente` mantiene sus campos privados y se edita mediante validaciones.
- **Sobrecarga / argumentos opcionales:** `Servicio.calcular_costo` ofrece variantes documentadas con `@overload` y permite calcular con o sin descuentos/impuestos.
- **Excepciones:** clases propias; `try/except`, `try/except/else`, `try/except/finally`, y encadenamiento `raise ... from`.
- **Logs:** los errores y eventos relevantes se registran mediante `RotatingFileHandler`.

## Pruebas independientes de la interfaz

```bash
python main.py --demo
python -m unittest discover -s tests -v
```

Las simulaciones se ejecutan sobre un **gestor temporal en memoria** y no alteran la sesión de la interfaz. Se generan mensajes válidos, validaciones fallidas y eventos en logs. Es normal que haya errores *controlados* durante las pruebas: precisamente se comprueba que la aplicación no se cierre.

## Reglas de reservas

- Todos los valores monetarios son **COP**. Las tarifas se expresan **por hora**.
- Para una sala el costo es tarifa × horas; la cantidad indica asistentes y no puede superar el aforo. Una misma sala no puede tener reservas confirmadas simultáneas.
- Para equipos y asesorías el costo es tarifa × horas × unidades o participantes. Las reservas confirmadas que se solapan no pueden exceder la capacidad.
- El descuento se aplica antes del impuesto. Ambos deben estar entre 0 y 100%.
- Se deben ingresar fecha y hora actuales o futuras; duración mayor que cero, máximo 24 h (asesorías máximo 8 h).
- Las reservas se crean pendientes y pueden confirmarse o cancelarse. La cancelación conserva un historial; no se permiten transiciones inválidas.

## Alcance y limitaciones

El enunciado **prohíbe usar una base de datos**: por eso los registros de clientes, servicios y reservas permanecen en RAM **mientras la app esté abierta**. Al cerrar se pierden los datos de la sesión, salvo el **registro de eventos y errores** del archivo `logs/sistema.log`, que sí se conserva. Se incluyen tres servicios de ejemplo al iniciar; no se crean clientes ni reservas ficticios.

La interfaz Tkinter es una mejora de usabilidad, **no un requisito explícito** de la guía. El proyecto puede ejecutarse sin conexión a Internet. Se recomienda probarlo en el equipo de entrega.

## Referencia del enunciado

UNAD. (2026). *Guía para el desarrollo del componente práctico – Fase 4 – Prácticas simuladas*, *Anexo 3 – Problema a desarrollar Fase 4* y *Rúbrica de evaluación – Fase 4*. Curso Programación, código 213023.

## Autoría

Este proyecto es una versión individual propuesta para práctica y revisión. Antes de una entrega académica, el estudiante debe revisar el código, comprobar su ejecución e identificar con precisión qué partes realizó y qué herramientas utilizó. No debe presentarse como contribución al repositorio de terceros si no se participó en él.
