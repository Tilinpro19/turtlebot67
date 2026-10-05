# TurtleBot 4 · ROS 2 Jazzy · Guía de trabajo diario

Guía para trabajar con **cualquier TurtleBot 4** (Lite o Standard) en el laboratorio de
Computer Vision, con **ROS 2 Jazzy sobre Ubuntu 24.04 Noble**. Supone el escenario
normal: el robot **ya está configurado y conectado a la red del laboratorio**.

<table>
<tr>
<td>🛠️ <b><a href="CONFIGURACION_INICIAL.md">CONFIGURACION_INICIAL.md</a></b><br>
El robot viene de fábrica, se reseteó o está desconfigurado (red, Create 3,
paquetes, udev, servicio).</td>
<td>🩺 <b><a href="TROUBLESHOOTING.md">TROUBLESHOOTING.md</a></b><br>
Algo no funciona: diagnóstico por síntomas y checklist rápido.</td>
</tr>
</table>

**Base:** guía del curso de Luis Cortijo,
[requeerimientos_turtlebot4](https://github.com/LuisEnriqueCortijoGonzales/requeerimientos_turtlebot4),
integrada en el mismo orden. Los bloques **➕ Extra** son adaptaciones probadas en el
laboratorio (WSL 2, detalles de Jazzy, scripts de este repositorio).
Manual oficial: [TurtleBot 4 User Manual](https://turtlebot.github.io/turtlebot4-user-manual/).

| Marcador | Significado |
|---|---|
| `<IP_ROBOT>` | IP del robot en la red del laboratorio |
| `<DOMAIN_ID>` | `ROS_DOMAIN_ID` de **tu** robot (uno distinto por robot) |
| `<WIFI_PASSWORD>` | Contraseña de la Wi-Fi del laboratorio (la da el docente; no se versiona) |

---

## Índice

**Parte I: preparar la PC (una sola vez)**
1. [Máquina virtual con Ubuntu 24.04](#1-máquina-virtual-con-ubuntu-2404)
2. [Preparar Ubuntu para ROS 2 Jazzy](#2-preparar-ubuntu-para-ros-2-jazzy)
3. [Instalar ROS 2 Jazzy](#3-instalar-ros-2-jazzy)
4. [Instalar paquetes del TurtleBot 4](#4-instalar-paquetes-del-turtlebot-4)
5. [➕ Entorno WSL 2](#5--entorno-wsl-2)
6. [➕ Variables de entorno en ROS 2 Jazzy](#6--variables-de-entorno-en-ros-2-jazzy)

**Parte II: flujo de laboratorio (cada sesión)**

7. [Conectar con el robot](#7-conectar-con-el-robot)
8. [Verificar `ROS_DOMAIN_ID`](#8-verificar-ros_domain_id)
9. [Verificación de comunicación (talker/listener)](#9-verificación-de-comunicación-talkerlistener)
10. [Bringup y sensores](#10-bringup-y-sensores)
11. [➕ Validar tópicos de cámara OAK-D y LiDAR](#11--validar-tópicos-de-cámara-oak-d-y-lidar)
12. [Pruebas de movimiento (`TwistStamped`)](#12-pruebas-de-movimiento-twiststamped)
13. [Cámara, visión y scripts del repositorio](#13-cámara-visión-y-scripts-del-repositorio)
14. [Notas y solución de errores](#14-notas-y-solución-de-errores)

**Anexos**
[A. Comparativa de entornos](#anexo-a-comparativa-de-entornos) ·
[B. Descubrimiento DDS y varios robots](#anexo-b-descubrimiento-dds-y-varios-robots) ·
[C. Estructura del repositorio](#anexo-c-estructura-del-repositorio)

---

# Parte I: preparar la PC (una sola vez)

## 1. Máquina virtual con Ubuntu 24.04

1. Instala **[VirtualBox](https://www.virtualbox.org)**.
2. Crea una nueva VM:
   - **Tipo:** Linux → Ubuntu (64-bit)
   - **RAM:** mínimo 4 GB (recomendado 8 GB)
   - **Disco:** 20 GB o más
   - **ISO:** [Ubuntu 24.04](https://releases.ubuntu.com/24.04)
3. Instala Ubuntu normalmente.
4. Instala las **Guest Additions** (mejor resolución y portapapeles).
5. Actualiza el sistema:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   sudo reboot
   ```

> ➕ **Extra: red en modo puente.** En VirtualBox → Configuración → Red, usa
> **Adaptador puente** sobre la interfaz Wi-Fi real. Con NAT (el valor por defecto) el
> ping al robot puede funcionar, pero ROS 2 no descubre los tópicos.

> ➕ **Extra: otros entornos.** Funciona igual con **Ubuntu 24.04 nativo**, o con
> **WSL 2** en Windows 11 (configúralo según la [sección 5](#5--entorno-wsl-2)). En el resto
> de la guía, "VM" significa tu entorno, sea cual sea.

---

## 2. Preparar Ubuntu para ROS 2 Jazzy

```bash
# Asegurar entorno UTF-8
sudo apt install locales -y
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Habilitar repositorios
sudo apt install software-properties-common -y
sudo add-apt-repository universe

# Añadir repositorio de ROS
sudo apt install curl gnupg2 lsb-release -y
sudo mkdir -p /usr/share/keyrings
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
```

> ➕ Si `apt update` falla con `EXPKEYSIG` o `NO_PUBKEY`:
> [TROUBLESHOOTING § 4.1](TROUBLESHOOTING.md#41-error-de-firma-gpg-en-apt-update).

---

## 3. Instalar ROS 2 Jazzy

```bash
sudo apt install ros-jazzy-desktop -y
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

Verifica que ROS 2 funciona:

```bash
ros2 run demo_nodes_cpp talker
```

---

## 4. Instalar paquetes del TurtleBot 4

```bash
sudo apt update
sudo apt install ros-jazzy-turtlebot4-desktop -y
```

Verifica que está instalado:

```bash
ros2 pkg list | grep turtlebot4
```

> ➕ **Extra: herramientas para teleop y visión.**
> ```bash
> sudo apt install -y ros-jazzy-teleop-twist-keyboard ros-jazzy-rqt-image-view \
>   ros-jazzy-image-transport-plugins ros-jazzy-cv-bridge python3-opencv python3-numpy
> ```

---

## 5. ➕ Entorno WSL 2

Solo si trabajas desde **Windows 11 con WSL 2** en lugar de la VM. Sin estos pasos,
ROS 2 no ve el robot.

### 5.1 Instalación y red

1. PowerShell **como administrador**:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
2. **Red espejo.** WSL usa NAT por defecto, y por NAT no pasa el descubrimiento de ROS 2.
   Crea `C:\Users\<usuario>\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   Aplícalo con `wsl --shutdown` y vuelve a abrir Ubuntu.
3. **Firewall de Hyper-V.** Permite el tráfico entrante (PowerShell **administrador**):
   ```powershell
   Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
   ```
4. **Perfil de red Privado.** En Windows: Configuración → Red → Wi-Fi → la red del
   laboratorio → *Tipo de perfil de red*: **Privada**.
5. Dentro de Ubuntu, sigue las secciones [2](#2-preparar-ubuntu-para-ros-2-jazzy) a
   [4](#4-instalar-paquetes-del-turtlebot-4) igual que en la VM.

### 5.2 Multicast y `ROS_STATIC_PEERS` (FastDDS)

Aun con `mirrored`, el **multicast** de descubrimiento es poco fiable en WSL. Resultado
de las pruebas: sin peers, **0 tópicos en 30 s**; con peers, descubrimiento en **~1 s**.

La solución en Jazzy es el descubrimiento **unicast** con `ROS_STATIC_PEERS`, que
FastDDS (`rmw_fastrtps_cpp`, el RMW por defecto) soporta de forma nativa:

```bash
export ROS_STATIC_PEERS=<IP_ROBOT>    # una o varias IPs separadas por ';'
ros2 daemon stop                      # el daemon guarda el descubrimiento anterior
ros2 topic list
```

- Basta con configurarlo **en la PC**; el robot no necesita cambios.
- Si cambia la IP del robot, actualiza la variable.
- `source tb4_connect.sh` ([§7.2](#72--conexión-con-tb4_connectsh)) lo detecta y lo
  aplica solo.

### 5.3 Ventanas, GPU y archivos

- **Ventanas gráficas:** WSLg (incluido en Windows 11) abre `rqt_image_view`, `rviz2` y
  `cv2.imshow` sin configuración adicional.
- **GPU NVIDIA:** instala solo el driver de **Windows**; dentro de WSL comprueba con
  `nvidia-smi`. No instales drivers NVIDIA dentro de Ubuntu.
- **Archivos del repositorio:** desde WSL están en `/mnt/c/Users/<usuario>/turtleclaude4`.
  Los scripts usan finales de línea LF (lo fuerza `.gitattributes`).

---

## 6. ➕ Variables de entorno en ROS 2 Jazzy

`source` carga ROS en la terminal; las variables definen con quién hablas. Añade al
final de `~/.bashrc` en la VM/WSL:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=<DOMAIN_ID>          # el MISMO que tu robot
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
# Solo WSL o redes sin multicast:
# export ROS_STATIC_PEERS=<IP_ROBOT>
```

```bash
source ~/.bashrc
printenv | grep -E 'ROS_|RMW_'     # ROS_DISTRO=jazzy, ROS_DOMAIN_ID, RMW_IMPLEMENTATION
```

| Variable | Valor | Nota |
|---|---|---|
| `ROS_DISTRO` | `jazzy` | La define el `source`. Vacía significa ROS no cargado |
| `ROS_DOMAIN_ID` | `<DOMAIN_ID>` | Usa **0–101** (los valores altos chocan con puertos de Linux). Distinto por robot |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | El mismo que el robot y el Create 3 |
| `ROS_STATIC_PEERS` | `<IP_ROBOT>` | Solo si el multicast no funciona (§5.2) |

> `export` en una terminal solo dura en esa terminal. Tras cambiar variables, ejecuta
> `ros2 daemon stop` para que el daemon no use datos de descubrimiento viejos.

---

# Parte II: flujo de laboratorio (cada sesión)

## 7. Conectar con el robot

El robot ya está en la red del laboratorio. Conecta tu PC a la **misma red Wi-Fi**.

### 7.1 SSH directo

```bash
ssh ubuntu@<IP_ROBOT>
```

**Encontrar `<IP_ROBOT>`:**
- **Standard:** la muestra la pantalla del robot.
- **Lite:** panel del router, `ssh ubuntu@turtlebot4.local`, o `arp -a` buscando una MAC
  de Raspberry Pi (`d8:3a:dd`, `dc:a6:32`, `e4:5f:01`).
- Ya dentro del robot: `hostname -I`.

> ➕ **Extra: alias SSH.** En `~/.ssh/config` (en Windows, `C:\Users\<usuario>\.ssh\config`):
> ```
> Host tb4
>   HostName <IP_ROBOT>
>   User ubuntu
>   ServerAliveInterval 15
>   ServerAliveCountMax 4
> ```
> Después basta `ssh tb4`. Para entrar sin contraseña: `ssh-keygen -t ed25519` y
> `ssh-copy-id tb4`.

### 7.2 ➕ Conexión con `tb4_connect.sh`

Configura la terminal de la VM para tu robot en un solo paso:

```bash
cd ~/turtleclaude4      # en WSL: cd /mnt/c/Users/<usuario>/turtleclaude4
source tb4_connect.sh <IP_ROBOT> <DOMAIN_ID>
```

Qué hace:
1. Carga Jazzy y exporta `ROS_DOMAIN_ID` y `RMW_IMPLEMENTATION`.
2. Hace ping al robot.
3. Prueba el descubrimiento por multicast. Si no ve los 4 tópicos clave (`/scan`,
   `/odom`, `/cmd_vel`, `/oakd/rgb/preview/image_raw`), prueba con `ROS_STATIC_PEERS` y
   se queda con el modo que funcione.
4. Guarda la configuración que funcionó en `~/.tb4_robot`.

```bash
source tb4_connect.sh                    # reconectar al último robot guardado
source tb4_connect.sh <IP> <ID> peers    # forzar modo: auto | multicast | peers
source tb4_connect.sh --off              # limpiar (dominio 0, sin peers)
```

Para que cada terminal nueva arranque ya configurada:

```bash
echo '[ -f ~/.tb4_robot ] && source ~/.tb4_robot' >> ~/.bashrc
```

---

## 8. Verificar `ROS_DOMAIN_ID`

Usa el **mismo valor** en la VM y en el TurtleBot:

```bash
echo $ROS_DOMAIN_ID
export ROS_DOMAIN_ID=<DOMAIN_ID>   # valor entre 0 y 101
source /opt/ros/jazzy/setup.bash   # actualizar variables de entorno
```

Compruébalo en los dos lados:

| Dónde | Comando |
|---|---|
| VM | `echo $ROS_DOMAIN_ID` |
| Robot (SSH) | `echo $ROS_DOMAIN_ID` |

> ➕ **Extra: tres lugares deben coincidir.** La VM, la Raspberry Pi y el Create 3.
> En el robot, el bringup corre como servicio y **no** lee un `export` hecho en tu sesión
> SSH. Si el valor del robot no es el correcto, cámbialo con `turtlebot4-setup`
> ([CONFIGURACION_INICIAL § 3](CONFIGURACION_INICIAL.md#3-ros_domain_id-del-robot)).

---

## 9. Verificación de comunicación (talker/listener)

En el **robot (terminal 1)**:
```bash
ros2 run demo_nodes_cpp listener
```

En la **VM (terminal 2)**:
```bash
ros2 run demo_nodes_cpp talker
```

✅ Si se ven los mensajes, la comunicación ROS funciona.
❌ Si no, revisa el `ROS_DOMAIN_ID` ([§8](#8-verificar-ros_domain_id)),
[TROUBLESHOOTING § 1](TROUBLESHOOTING.md#1-red-y-dds), o llama a **Cortijo** 😎

> Si el robot no tiene los nodos demo (`Package 'demo_nodes_cpp' not found`), instálalos
> según [CONFIGURACION_INICIAL § 4](CONFIGURACION_INICIAL.md#4-instalación-base-en-el-robot).

---

## 10. Bringup y sensores

Luego de conectarte por SSH:

```bash
ros2 launch turtlebot4_bringup lite.launch.py        # TurtleBot 4 Lite
ros2 launch turtlebot4_bringup standard.launch.py    # TurtleBot 4 Standard
```

> ➕ **Extra: el bringup suele estar ya en marcha.** `turtlebot4.service` lo lanza al
> encender el robot. Antes de lanzarlo a mano, compruébalo para no duplicar nodos:
> ```bash
> systemctl is-active turtlebot4.service    # "active": ya corre, no lances otro
> ```

Al ejecutar `ros2 topic list` deberías ver una lista extensa que incluya:

```
/battery_state
/cmd_vel
/odom
/scan
/oakd/rgb/preview/image_raw
/tf
...
```

<details>
<summary>Lista completa esperada (TurtleBot 4 Lite)</summary>

```
/battery_state  /cmd_audio  /cmd_lightring  /cmd_vel  /cmd_vel_unstamped
/diagnostics  /diagnostics_agg  /diagnostics_toplevel_state  /dock_status
/function_calls  /hazard_detection  /imu  /interface_buttons  /ip
/joint_states  /joy  /joy/set_feedback  /mouse  /oakd/imu/data
/oakd/rgb/preview/camera_info  /oakd/rgb/preview/image_raw
/oakd/rgb/preview/image_raw/{compressed,compressedDepth,theora,zstd}
/odom  /parameter_events  /robot_description  /rosout  /scan
/tf  /tf_static  /wheel_status
```
El Standard añade tópicos de pantalla y botones (`/hmi/...`).
</details>

Si no aparecen, llama a Cortijo o revisa [TROUBLESHOOTING § 2](TROUBLESHOOTING.md#2-cámara-y-sensores).

### Activar sensores individualmente

```bash
ros2 launch turtlebot4_bringup rplidar.launch.py    # LiDAR
ros2 launch turtlebot4_bringup oakd.launch.py       # Cámara OAK-D
```

✅ Si escuchas el sonido alegre del robot ("pu puru pupu 🎵"), el bringup se cargó correctamente.

---

## 11. ➕ Validar tópicos de cámara OAK-D y LiDAR

Desde la **VM**, antes de trabajar en visión:

| Tópico | Tipo | Comando de validación | Esperado |
|---|---|---|---|
| `/oakd/rgb/preview/image_raw` | `sensor_msgs/Image` | `ros2 topic hz /oakd/rgb/preview/image_raw` | Frecuencia > 0 |
| `/oakd/rgb/preview/image_raw/compressed` | `sensor_msgs/CompressedImage` | `ros2 topic hz /oakd/rgb/preview/image_raw/compressed` | Frecuencia > 0 (mejor por Wi-Fi) |
| `/oakd/rgb/preview/camera_info` | `sensor_msgs/CameraInfo` | `ros2 topic echo --once /oakd/rgb/preview/camera_info` | Matriz `k` con valores |
| `/scan` | `sensor_msgs/LaserScan` | `ros2 topic hz /scan` | ~7–8 Hz (RPLIDAR A1) |
| `/scan` | | `ros2 topic echo --once --no-arr /scan` | `range_min`/`range_max` coherentes |
| `/odom` | `nav_msgs/Odometry` | `ros2 topic echo --once /odom` | Datos del Create 3 |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | `ros2 topic info /cmd_vel` | `Type: geometry_msgs/msg/TwistStamped` |

**Versión automática** de toda la tabla, con referencia a TROUBLESHOOTING en cada fallo:

```bash
./tb4_check.sh <IP_ROBOT>            # desde la VM
./tb4_check.sh <IP_ROBOT> --robot    # además revisa el robot por SSH (dominio, servicio, USB)
```

> Si aparecen `/scan` y `/oakd/...` pero **faltan** `/odom` y `/battery_state`, la Raspberry
> Pi funciona y el problema está en el Create 3:
> [TROUBLESHOOTING § 1.2](TROUBLESHOOTING.md#12-discrepancias-de-ros_domain_id).

---

## 12. Pruebas de movimiento (`TwistStamped`)

En el **TurtleBot**:
```bash
ros2 topic echo /cmd_vel
```

En la **VM**:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
```

> ➕ **Extra: por qué `stamped:=true`.** En Jazzy, `/cmd_vel` del TurtleBot 4 es
> **`geometry_msgs/msg/TwistStamped`** (cabecera con `stamp` y `frame_id`). Un `Twist`
> simple publicado en `/cmd_vel` **no mueve el robot**. Hay dos opciones:
>
> | Opción | Tópico | Mensaje |
> |---|---|---|
> | Recomendada | `/cmd_vel` | `TwistStamped` (`-p stamped:=true`) |
> | Compatibilidad | `/cmd_vel_unstamped` | `Twist` (código antiguo) |
>
> Desde la CLI:
> ```bash
> ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
>   "{header: {frame_id: base_link}, twist: {linear: {x: 0.1}}}"
> ```
> En rclpy: rellena `msg.header.stamp = node.get_clock().now().to_msg()` y
> `msg.header.frame_id = "base_link"`, y escribe la velocidad en `msg.twist`.

> ➕ **Seguridad.** Empieza lento (0.1 m/s, 1.0 rad/s). El Create 3 no tiene sensores
> traseros. Evita que dos nodos publiquen en `/cmd_vel` a la vez (un mando emparejado con
> el robot también publica).

---

## 13. Cámara, visión y scripts del repositorio

### Ver la cámara

```bash
ros2 run rqt_image_view rqt_image_view
```

Selecciona `/oakd/rgb/preview/image_raw`, o `/oakd/rgb/preview/image_raw/compressed`
si la Wi-Fi va justa.

### ➕ Scripts de este repositorio

Se ejecutan en la VM/WSL con ROS cargado (§6 o `tb4_connect.sh`):

| Script | Para qué | Uso |
|---|---|---|
| `ver_camara_tb4.py` | Visor OpenCV de la OAK-D con FPS. Base para tus nodos de visión | `python3 ver_camara_tb4.py` · `--scale 3` · `--topic <tópico>` |
| `ver_lidar_tb4.py` | Vista cenital de `/scan`; marca en rojo los obstáculos frontales a menos de 0.5 m | `python3 ver_lidar_tb4.py` · `--range 6` · `--rot 90` |
| `teleop_wasd.py` | Teleop WASD; detecta solo si `/cmd_vel` es `Twist` o `TwistStamped`; se detiene al soltar las teclas | `python3 teleop_wasd.py` · `--dry` (no publica) |

Controles de `teleop_wasd.py`: `w`/`s` adelante/atrás · `a`/`d` girar · `q`/`e` avanzar
girando · `u`/`j` velocidad lineal ± · `i`/`k` velocidad angular ± · espacio/`x` parar ·
`Ctrl+C` salir.

> Los scripts usan QoS *sensor data* (best effort) para la cámara y el LiDAR. Si no
> reciben nada en 8 s, avisan por consola: el problema es de red o de DDS (§7 y §8), no
> del script.

---

## 14. Notas y solución de errores

- **Cambiar o revisar el dominio ROS:**
  ```bash
  echo $ROS_DOMAIN_ID
  export ROS_DOMAIN_ID=4   # ejemplo; usa el de tu robot
  ```
  Usa el mismo valor en la VM y en el TurtleBot.
- **Actualizar variables de entorno:**
  ```bash
  source /opt/ros/jazzy/setup.bash
  ```
- **Verificar comunicación:**
  ```bash
  ros2 topic list
  ```
- **Si algo falla:**
  - Reinicia el Create 3 (`turtlebot4-setup`, aplicar red, reboot).
  - Revisa la conexión Wi-Fi y el ping entre VM ↔ TurtleBot.
  - Ejecuta `./tb4_check.sh <IP_ROBOT> --robot` y consulta [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
  - Si el robot está desconfigurado: [CONFIGURACION_INICIAL.md](CONFIGURACION_INICIAL.md).
  - Si nada resulta: **llamar a Cortijo** 😄

---

## Anexo A. Comparativa de entornos

| Entorno | Descubrimiento DDS con el robot | GPU (CUDA) para visión | Ventanas (rviz, rqt, `cv2.imshow`) |
|---|---|---|---|
| **VirtualBox** | Requiere adaptador puente; con NAT no se ven tópicos. El puente sobre Wi-Fi puede fallar | No disponible | Aceleración 3D limitada: rviz y rqt van lentos |
| **WSL 2** | Requiere `mirrored`, firewall y `ROS_STATIC_PEERS` (§5) | Sí, con el driver NVIDIA de Windows | WSLg (Windows 11) |
| **Ubuntu nativo** | Funciona sin ajustes | Completa | Nativas |

- **Windows 10** no admite `networkingMode=mirrored`: usa VirtualBox o Ubuntu nativo.
- **Mac con Apple Silicon:** VirtualBox no es práctico; usa UTM o Parallels con Ubuntu
  24.04 ARM64 en modo puente.
- **Visión pesada** (redes neuronales): requiere GPU, disponible en nativo y en WSL 2.

## Anexo B. Descubrimiento DDS y varios robots

| Modo | Cómo se activa | Cuándo |
|---|---|---|
| **Multicast** (por defecto) | Nada que hacer | VM en puente o Ubuntu nativo, en una red que deja pasar multicast |
| **Peers estáticos** | `export ROS_STATIC_PEERS=<IP_ROBOT>` o `tb4_connect.sh` | WSL 2, redes con aislamiento de clientes |
| **Discovery Server** | `turtlebot4-setup`, más la configuración de la PC según el [manual](https://turtlebot.github.io/turtlebot4-user-manual/setup/discovery_server.html) | Muchos robots o redes muy restrictivas. Cambia la configuración del robot: acuérdalo con el docente |

**Varios robots en el laboratorio:**
- Un `ROS_DOMAIN_ID` **distinto por robot**. Si no, todos ven todos los tópicos y un
  `/cmd_vel` puede mover el robot de otro grupo.
- Lleva un registro de IP, ID y grupo. `~/.tb4_robot` guarda el último robot usado.
- Con muchos robots en la misma Wi-Fi, usa `/compressed` para la cámara.

## Anexo C. Estructura del repositorio

```
turtleclaude4/
├── README.md                  ← guía de trabajo diario (este documento)
├── CONFIGURACION_INICIAL.md   ← aprovisionamiento del robot desde cero
├── TROUBLESHOOTING.md         ← diagnóstico por síntomas y checklist
├── tb4_connect.sh             ← configura la terminal para un robot (multicast → peers)
├── tb4_check.sh               ← checklist automático (PC y, opcionalmente, robot)
├── ver_camara_tb4.py          ← visor OAK-D
├── ver_lidar_tb4.py           ← visor LiDAR
├── teleop_wasd.py             ← teleop por teclado
├── docs/                      ← bitácora de un robot concreto (valores de ejemplo)
└── _legacy/                   ← mando PS4 y planes antiguos (solo referencia)
```
