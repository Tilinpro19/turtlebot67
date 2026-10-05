# TurtleBot4 — Evasión de obstáculos + fusión sensorial tipo dron + QR/señales

Fecha: 2026-07-09
Estado: aprobado para pasar a plan de implementación

## Contexto y objetivo

Proyecto personal/aprendizaje (sin fecha límite de competencia). El robot es un
TurtleBot4 (base Create3 + Raspberry Pi 4 con RPLidar A1M8 y cámara OAK-D).
Ya existe una fase local validada de teleop con mando PS4 (`pad_teleop.py`) y
teleop de teclado corriendo directo en la Pi (`teleop_teclado.py`), además de
visores de lidar (`ver_lidar.py`) y cámara (`ver_camara.py`) por streaming
TCP desde `lidar_server.py` en la Pi.

Objetivo de este documento: diseñar el siguiente salto — un robot que:

1. Evita obstáculos de forma autónoma (prioridad #1, se entrena/implementa primero).
2. Estima su propia pose (posición + orientación) fusionando **odometría de
   ruedas** y **velocidad comandada**, de forma análoga a como un dron vuela
   solo con datos inerciales cuando no tiene GPS — acá no hay GPS, así que el
   "IMU" del dron es sustituido por odometría de encoders + el propio comando
   de velocidad como entrada de control del filtro.
3. Usa esa pose para preferir rumbos hacia zonas no visitadas recientemente
   (exploración libre, no hace falta mapa de ocupación completo — el robot
   debe simplemente evitar lo que detecte con lidar/cámara y tender a no
   repetir sitio).
4. Detecta y decodifica códigos QR y señales de flecha con la cámara (el uso
   final de esos QRs/flechas se define después — por ahora el pipeline debe
   ser genérico: detectar, decodificar, loguear/exponer el resultado).

Este documento cubre las 4 fases como un solo sistema, pero la Fase 1
(evasión con LiDAR) es la que se implementa y valida primero.

**Restricción dura confirmada por el usuario: la Raspberry Pi no se toca.**
Ni un byte de `lidar_server.py` ni de `camera_server.py`/`ver_camara.py`
se modifica. Todo el algoritmo (evasión, fusión, EKF, grid, QR) corre
exclusivamente en la notebook, consumiendo solo lo que la Pi ya transmite
hoy: el scan JSON del lidar por el puerto 5001 y el frame RGB por el puerto
5000. Esto invalida la idea original de pedirle a la Pi que además envíe un
frame de profundidad de la OAK-D — ver Fase 2 revisada más abajo.

## Arquitectura general

```
┌─────────────────────────── Raspberry Pi 4 ───────────────────────────┐
│                                                                        │
│  RPLidar A1M8 --USB--> lidar_server.py  --TCP:5001--> [scan JSON]     │
│                                                                        │
│  OAK-D --USB--> camera_server.py (SIN TOCAR) --TCP:5000--> [solo RGB] │
│                                                                        │
│  Create3 --USB--> ROS2 nativo (rclpy corriendo en la Pi)              │
│         topics nativos: /odom, /cmd_vel, (IMU si existe), etc.        │
│         *** la Pi NO decide nada, solo expone datos/actúa ***         │
└────────────────────────────────────────────────────────────────────┬─┘
                                                                       │
                          WiFi (mismo patrón que pad_teleop.py:       │
                          rclpy directo desde la notebook,            │
                          sin joy_node ni paquete ROS2)               │
                                                                       │
┌───────────────────────────── Notebook (WSL2) ────────────────────────┐
│                                                                        │
│  brain_node.py (un solo nodo rclpy, sin colcon/paquete):              │
│                                                                        │
│   [socket lidar] ─┐                                                   │
│   [socket RGB]  ──┼──> obstacle_fusion.py ──> vector de evasión ─┐    │
│    (mono-depth)    │                                              │    │
│   [/odom ROS2]  ───┼──> pose_estimator.py (EKF liviano) ──> pose ┼──> │
│   [cmd_vel propio] ┘         (odom + control input)               │   │
│                                                                    │   │
│                     visited_grid.py (pose -> celdas visitadas) ───┤   │
│                                                                    ▼   │
│                     motion_planner.py  ──> Twist ──> publica /cmd_vel │
│                                                                        │
│   [socket RGB] ──> qr_sign_detector.py ──> eventos QR/flecha (log)    │
│                                                                        │
└────────────────────────────────────────────────────────────────────┘
```

Regla de oro (heredada del proyecto): la Pi solo abstrae sensores y ejecuta
comandos — toda la decisión (evasión, fusión, planeamiento) vive en la
notebook, igual que ya se hace con el teleop por mando.

## Fase 0 — Descubrimiento (bloquea todo lo demás)

Antes de escribir el EKF hay que confirmar, corriendo en la Pi con el Create3
encendido:

```bash
source /opt/ros/jazzy/setup.bash   # o el setup del Create3 si expone su propio overlay
ros2 topic list
ros2 topic info /odom
ros2 topic echo /odom --once
ros2 topic list | grep -i imu
```

Registrar en este documento (o en un anexo) antes de avanzar a Fase 3:
- Nombre exacto del topic de odometría (se espera `/odom`, tipo
  `nav_msgs/msg/Odometry`) y si trae covarianza usable.
- Si el Create3 expone IMU en algún topic (tiene IMU interno; confirmar si
  Create3 lo publica en Humble o si solo lo usa internamente para su propio
  control). Si existe, es un fusible extra opcional para el EKF (Fase 3b).
- Confirmar si `/odom` ya viene en el frame que se espera (x,y,theta relativo
  al arranque) o si hay que resetear/leer `/tf`.
- Confirmar el FOV horizontal de la OAK-D (dato de fábrica, no requiere tocar
  la Pi) para poder mapear columna de píxel → ángulo en `obstacle_fusion.py`
  (Fase 2).

No adivinar ninguno de estos nombres/tipos en el código — si no está
confirmado, el script debe fallar con un mensaje claro pidiendo correr el
descubrimiento, no asumir un topic por defecto.

## Fase 1 — Evasión de obstáculos (LiDAR únicamente) — PRIMERA A IMPLEMENTAR

### Alcance
Reactivo, sin fusión ni pose todavía. Sirve de base y de red de seguridad
para todas las fases siguientes (cualquier fase posterior puede publicar una
velocidad "deseada" pero esta capa la recorta si hay riesgo de choque).

### Entrada
Reusar el patrón de `ver_lidar.py`: conectar a `lidar_server.py` (puerto
5001), leer líneas JSON `[[angle, distance], ...]` (en mm).

### Algoritmo — evasión tipo VFH simplificado (Vector Field Histogram lite)
1. Descartar puntos con `distance == 0` o fuera de rango (`quality` bajo si
   se decide reincorporar ese campo).
2. Dividir el círculo en N sectores angulares (p.ej. 36 sectores de 10°).
3. Por sector, tomar la distancia mínima detectada. Si no hay lecturas en el
   sector, tratarlo como "libre" (o "desconocido" con precaución, a definir
   en implementación con un valor por defecto conservador).
4. Marcar sector como "bloqueado" si `distancia_min < UMBRAL_SEGURIDAD_MM`
   (parámetro, punto de partida sugerido: 400mm, ajustable en campo).
5. De los sectores frontales (p.ej. ±60° respecto al heading actual) elegir:
   - Si el sector frontal central está libre: avanzar recto.
   - Si está bloqueado: elegir el sector libre más cercano angularmente al
     frente (preferencia por el giro más corto) y girar hacia allí sin
     avanzar (o avanzando a velocidad reducida), tipo "gira y evalúa de
     nuevo" — no hace falta path planning, es puramente reactivo.
   - Si todos los sectores están bloqueados dentro de cierto radio: detener
     y retroceder levemente, luego re-evaluar.
6. Publicar `Twist` resultante a `/cmd_vel` real del Create3 (namespace a
   confirmar en descubrimiento, ver Fase 0) a una tasa fija (sugerido 10Hz).

### Seguridad (obligatorio, mismo criterio que `teleop_teclado.py`)
- Watchdog: si el nodo no logra leer un scan nuevo del lidar en
  `WATCHDOG_TIMEOUT` (sugerido 0.5s), publicar `Twist` cero inmediatamente.
- Límites de velocidad explícitos (`MAX_LINEAR`, `MAX_ANGULAR`) como
  constantes al tope del archivo, igual que en los scripts existentes — no
  subir estos valores sin confirmación del usuario.
- Empezar en modo "solo imprime la decisión, no publica a cmd_vel real" para
  validar en consola antes de mover el robot de verdad (mismo patrón de fase
  local que ya se usó con el mando).

### Archivo sugerido
`obstacle_avoidance.py` — un solo script, standalone, siguiendo el estilo de
los scripts ya existentes (sin paquete ROS2, sin colcon).

## Fase 2 — Sumar la cámara como sensor de obstáculos (revisado: cero cambios en la Pi)

### Motivación
El RPLidar 2D no ve obstáculos bajos (patas de mesa) ni fuera de su plano de
escaneo. La OAK-D calcula profundidad estéreo en su propio chip, pero **no
se puede usar ese depth stream sin tocar `camera_server.py` en la Pi**, y eso
está prohibido. La alternativa: seguir usando exactamente el mismo frame RGB
que ya recibe `ver_camara.py` (puerto 5000, sin cambios), y hacer toda la
estimación de "qué tan cerca hay algo" del lado de la notebook.

### Cambios en la Pi
**Ninguno.** `camera_server.py` sigue enviando únicamente frames RGB por el
puerto 5000, igual que hoy.

### Cambios en la notebook — dos opciones, a elegir en la implementación
1. **Profundidad monocular con un modelo liviano (recomendado):** correr un
   modelo de profundidad monocular pequeño (p.ej. MiDaS small / variantes
   optimizadas para CPU) sobre el frame RGB recibido, para obtener un mapa de
   profundidad relativo. No es tan preciso como el estéreo de la OAK-D, pero
   corre enteramente en la notebook y no requiere nada de la Pi. El costo es
   cómputo en la notebook (evaluar FPS reales antes de comprometerse; si es
   muy lento, cae a la opción 2).
2. **Heurística visual sin profundidad (fallback más barato):** sin modelo de
   profundidad, usar solo indicios 2D — por ejemplo, tamaño/proximidad de
   contornos oscuros/bordes en la mitad inferior del frame (donde suele estar
   el piso/obstáculos cercanos), o flujo óptico entre frames para detectar
   objetos que crecen rápido (indicativo de acercamiento). Menos preciso pero
   trivial en costo de cómputo.

En cualquiera de las dos, `obstacle_fusion.py` proyecta el resultado (columna
de píxel → ángulo relativo al frente del robot, usando el FOV horizontal
conocido de la OAK-D) al mismo sistema de sectores angulares del lidar
(Fase 1), y funde tomando por sector la distancia/riesgo más pesimista entre
lidar y cámara. Esto no reemplaza el VFH de Fase 1, solo enriquece la
histograma de sectores con una segunda fuente. Empezar la implementación con
la opción 2 (heurística, sin dependencias pesadas) y solo subir a la opción 1
si se confirma que hace falta más precisión y que la notebook aguanta el FPS.

## Fase 3 — Estimación de pose (EKF liviano, homólogo al dron)

### Analogía explícita con el dron (para que quede documentado el porqué)
Un dron sin GPS vuela integrando su IMU (aceleración/velocidad angular) sobre
el tiempo, con un filtro que corrige el drift cuando hay otra fuente
disponible. Acá no hay IMU externo confiable ni GPS, pero sí hay dos fuentes
independientes de movimiento:
- **Odometría de encoders** (`/odom` del Create3): mide el desplazamiento
  real de las ruedas, con su propio error acumulado (deslizamiento).
- **Velocidad comandada** (el propio `Twist` que el notebook publica): no es
  una medición, es la entrada de control — cumple el mismo rol que el
  "modelo de movimiento" en un EKF de dron (integrar la acción de control
  como predicción, y corregir con la medición real de odometría).

### Diseño del filtro
Estado: `[x, y, theta]` (pose 2D). Opcionalmente `[v, omega]` si se decide
modelar velocidad como parte del estado en vez de solo como entrada.

- **Predicción**: modelo de movimiento diferencial estándar, usando como
  entrada de control el último `Twist` comandado (v, omega) integrado sobre
  `dt` desde el último ciclo.
- **Corrección**: cuando llega una nueva lectura de `/odom`, usarla como
  medición para corregir el estado predicho (el EKF pesa cuánto confiar en
  cada fuente según sus covarianzas — arrancar con covarianzas fijas
  razonables si `/odom` no trae covarianza real, ver Fase 0).
- Si en la Fase 0 se confirma que el Create3 expone IMU (velocidad angular),
  añadirlo como tercera fuente de corrección para `theta` (igual que un dron
  usa el giroscopio) — esto es opcional, Fase 3b, no bloquea el resto.

### Por qué EKF y no solo integrar `/odom` directo
Fusionar da una pose más estable ante: (a) ruedas patinando (donde `/odom`
solo mentiría), y (b) al menos una segunda fuente para detectar cuándo la
odometría diverge del comando (si llevas rato comandando "avanzar" y `/odom`
no se mueve, es señal de patinaje/atasco — información útil también para la
Fase 1/2 de evasión, como "estoy empujando algo").

### Archivo sugerido
`pose_estimator.py`, con una clase `EKFPoseEstimator` con métodos
`predict(twist_cmd, dt)` y `correct_odom(odom_msg)` — testeable de forma
aislada sin ROS2 (recibe/devuelve tuplas simples), para poder probarlo con
datos grabados antes de conectarlo al robot real.

## Fase 4 — Preferencia de exploración sin repetir sitio (grid ligero)

### Alcance (confirmado: no hace falta mapa de ocupación completo)
Grid de celdas visitadas, no SLAM. Descomponer el plano en celdas (sugerido
30cm x 30cm) y marcar como visitada cada celda por la que pasa la pose
estimada (Fase 3). Estructura de datos: diccionario `{(cell_x, cell_y):
timestamp_ultima_visita}` — no hace falta grilla densa pre-alocada.

### Integración con la evasión (Fase 1/2)
Cuando el VFH de la Fase 1 encuentra **más de un sector libre** entre los
candidatos frontales, en vez de elegir arbitrariamente el más cercano al
heading actual, usar como criterio de desempate: preferir el sector cuya
proyección a corto alcance (p.ej. 1m adelante en esa dirección) caiga en una
celda no visitada o visitada hace más tiempo. Si solo hay un sector libre,
gana igual la seguridad (Fase 1) sobre la exploración — este criterio es
puramente un desempate, nunca fuerza al robot a un sector bloqueado.

### Archivo sugerido
`visited_grid.py` — clase pequeña `VisitedGrid` con `mark(pose)` y
`score_direction(pose, heading_candidato) -> qué tan "nuevo" es`.

## Fase 5 — Detección de QR y señales de flecha

### Alcance actual (genérico, uso final pendiente de definir por el usuario)
Pipeline de detección + decodificación, expuesto como eventos loggeados
(consola + opcionalmente archivo/topic), sin acoplarlo todavía a una acción
específica del robot. Cuando el usuario confirme el uso (checkpoints vs.
comandos codificados en el QR), se añade un dispatcher aparte que consuma
estos eventos — no se debe adelantar esa lógica ahora.

### Entrada
Frames RGB del mismo socket de cámara ya usado por `ver_camara.py`
(puerto 5000).

### Algoritmo sugerido
- QR: `cv2.QRCodeDetector` (ya viene con `opencv-python`, sin dependencias
  nuevas) o `pyzbar` si se necesita mejor tasa de detección en movimiento
  (evaluar ambas, `pyzbar` suele ser más robusto a QRs pequeños/angulados).
- Flechas: al no ser QR, requieren un detector aparte — empezar con visión
  clásica (umbral + contornos + `cv2.matchShapes` o ajuste de un triángulo
  de dirección) antes de considerar un modelo ML; el usuario debe confirmar
  ejemplos de las señales reales antes de afinar el detector.
- Anti-duplicados: un mismo QR/flecha visible en varios frames seguidos debe
  loguearse una sola vez por "aparición" (debounce por contenido decodificado
  + ventana de tiempo, p.ej. no repetir el mismo QR en menos de 3s).

### Archivo sugerido
`qr_sign_detector.py`, standalone, testeable con imágenes sueltas antes de
conectarlo al stream en vivo.

## Estructura de archivos propuesta (todos en la raíz del proyecto, sin paquete ROS2)

```
obstacle_avoidance.py     # Fase 1 — VFH sobre lidar, standalone, PRIMERO
obstacle_fusion.py        # Fase 2 — funde lidar + señal de la cámara (RGB) en sectores
pose_estimator.py         # Fase 3 — EKF liviano (odom + cmd_vel), testeable sin ROS2
visited_grid.py           # Fase 4 — grid de celdas visitadas + desempate
qr_sign_detector.py       # Fase 5 — detección/decodificación QR + flechas
brain_node.py             # integra todo: un solo nodo rclpy que orquesta
                           #   lectura de sockets/topics y publica /cmd_vel final
```

Todo lo anterior corre en la notebook. **En la Pi no se crea, edita, ni
despliega ningún archivo nuevo** — `lidar_server.py` y `camera_server.py`
quedan exactamente como están hoy.

`brain_node.py` es el único que depende de `rclpy`/ROS2 y sockets en vivo —
todos los demás módulos deben poder importarse y probarse de forma aislada
(funciones puras o clases con entrada/salida simple), para poder testear la
lógica de evasión/EKF/grid con datos grabados o sintéticos antes de tocar el
robot real.

## Reglas heredadas del proyecto (aplican a todas las fases)

- No subir `MAX_LINEAR`/`MAX_ANGULAR` sin confirmación explícita del usuario.
- **La Raspberry Pi no se toca, punto.** Ningún script nuevo ni modificación
  a `lidar_server.py`/`camera_server.py`. Todo el algoritmo (evasión, fusión,
  EKF, grid, QR) vive y corre en la notebook, consumiendo los streams TCP
  existentes tal cual están.
- No crear paquete ROS2 (`ros2 pkg create`), ni `colcon build`, ni launch
  files — todo en scripts Python simples, como el resto del proyecto.
- Cada fase nueva empieza en modo "solo imprime/loguea, no publica a
  `/cmd_vel` real" hasta validación explícita del usuario, igual que se hizo
  con `pad_teleop.py`.
- Ante ambigüedad de topic/mensaje/mapeo, preguntar o correr descubrimiento
  — no asumir nombres ni tipos de mensaje.

## Orden de implementación

1. Fase 0 (descubrimiento) — bloqueante, corto.
2. Fase 1 (evasión LiDAR) — la prioridad explícita del usuario, primera en
   entrenarse/probarse end-to-end, incluida en modo local antes de robot real.
3. Fase 3 (EKF) puede desarrollarse en paralelo a la Fase 2 una vez esté
   confirmado `/odom` en la Fase 0, ya que no depende de la cámara.
4. Fase 2 (fusión con profundidad OAK-D).
5. Fase 4 (grid de no repetir sitio) — depende de Fase 3.
6. Fase 5 (QR/flechas) — independiente del resto, puede desarrollarse en
   paralelo en cualquier momento después de la Fase 0.

## Estrategia de ejecución (ahorro de tokens)

Cuando se pase a implementar los scripts de la lista de arriba, conviene
delegar la escritura de cada script standalone (Fase 1, 2, 3, 4, 5 por
separado) a un agente corriendo con el modelo **Fable 5**, que es más barato
que el modelo principal de esta conversación. Cada script cumple el criterio
para delegarse bien: alcance acotado, testeable de forma aislada, y con este
mismo documento como contexto completo (no requiere memoria de esta
conversación). El nodo de integración (`brain_node.py`) sí conviene revisarlo
con el modelo principal, porque ahí es donde se juegan los límites de
seguridad (watchdog, `MAX_LINEAR`/`MAX_ANGULAR`) que no conviene delegar sin
supervisión directa.

## Pendiente de confirmar con el usuario más adelante

- Uso final de los QR y señales de flecha (checkpoints vs. comandos vs. otra
  cosa) — el usuario indicó que lo confirma luego.
- Resultado real de la Fase 0 (nombres de topics, si hay IMU disponible).
