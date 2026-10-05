# TurtleBot 4 · ROS 2 Jazzy · Computer Vision

Guía de puesta a punto para **cualquier TurtleBot 4** (Lite o Standard) con
**ROS 2 Jazzy / Ubuntu 24.04 Noble**, orientada al ciclo de Computer Vision.

- **Flujo base:** guía del curso de Luis Cortijo,
  [requeerimientos_turtlebot4](https://github.com/LuisEnriqueCortijoGonzales/requeerimientos_turtlebot4).
  Es el procedimiento probado; los pasos numerados lo siguen en el mismo orden.
- **💡 Hallazgos:** notas añadidas a partir de la experiencia en laboratorio
  (casos donde el flujo base no bastaba). Son complementarias: aplícalas cuando el
  síntoma coincida.
- Manual oficial: [TurtleBot 4 User Manual](https://turtlebot.github.io/turtlebot4-user-manual/).

> Si algo falla → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

Valores que debes sustituir:

| Marcador | Significado |
|---|---|
| `<IP_ROBOT>` | IP del robot en la red del laboratorio |
| `<DOMAIN_ID>` | `ROS_DOMAIN_ID` asignado a **tu** robot (único por robot) |
| `<WIFI_SSID>` / `<WIFI_PASSWORD>` | Red del laboratorio (p. ej. `Lab_Computech_5G`); la contraseña la da el docente |

---

## Índice

0. [Estructura del repositorio](#0-estructura-del-repositorio)
1. [Entorno de desarrollo (WSL2 / nativo / VirtualBox)](#1-entorno-de-desarrollo-ubuntu-2404)
2. [Preparar Ubuntu e instalar ROS 2 Jazzy](#2-preparar-ubuntu-e-instalar-ros-2-jazzy)
3. [Paquetes del TurtleBot 4 en la VM](#3-paquetes-del-turtlebot-4-en-la-vm)
4. [Configurar y conectar el TurtleBot 4](#4-configurar-y-conectar-el-turtlebot-4)
   — incluye la **conexión diaria con `tb4_connect.sh`** ([§4.5](#45-conexión-diaria-tb4_connectsh-y-tb4_checksh))
5. [Sincronizar `ROS_DOMAIN_ID` y probar talker/listener](#5-sincronizar-ros_domain_id-y-probar-talkerlistener)
6. [Sensores y bringup](#6-sensores-y-bringup)
7. [Movimiento y teleoperación (`TwistStamped`)](#7-movimiento-y-teleoperación-twiststamped)
8. [Cámara y visión](#8-cámara-y-visión)
9. [Herramientas de este repositorio](#9-herramientas-de-este-repositorio)

---

## 0. Estructura del repositorio

```
turtleclaude4/
├── README.md               ← este documento
├── TROUBLESHOOTING.md      ← fallos frecuentes y checklist de diagnóstico
├── tb4_connect.sh          ← conecta la terminal al robot (multicast → peers automático)
├── tb4_check.sh            ← checklist de diagnóstico automático (PC y, opcional, robot)
├── teleop_wasd.py          ← teleop por teclado (Twist/TwistStamped automático)
├── ver_camara_tb4.py       ← visor OAK-D (/oakd/rgb/preview/image_raw)
├── ver_lidar_tb4.py        ← visor 2D del LiDAR (/scan)
├── docs/                   ← caso práctico: bitácora de conexión de un robot concreto
│   ├── guia_conexion_turtlebot4.md     (Wi-Fi de respaldo, cable directo, hotspot)
│   └── tarjeta_offline_lab.md          (WSL2 + ROS_STATIC_PEERS)
└── _legacy/                ← mando PS4 y planes antiguos (solo referencia)
```

Los valores de `docs/` (IPs, `ROS_DOMAIN_ID`, MAC) son de **un** robot; úsalos como
ejemplo, no como configuración.

---

## 1. Entorno de desarrollo (Ubuntu 24.04)

Lo único imprescindible es **Ubuntu 24.04 con ROS 2 Jazzy**, en la misma red que el
robot. Dónde corra ese Ubuntu es elección tuya:

| Opción | GPU para visión (CUDA, YOLO…) | Red con el robot | Ventanas (rviz, rqt, `cv2.imshow`) | Recomendado para |
|---|---|---|---|---|
| **A. WSL2** (Windows) | ✅ CUDA con el driver NVIDIA de Windows | ⚠️ `mirrored` + `ROS_STATIC_PEERS` (lo automatiza `tb4_connect.sh`) | ✅ WSLg | **Uso diario en Windows** |
| **B. Ubuntu nativo** (dual boot) | ✅ Completa | ✅ Sin ajustes | ✅ | Máximo rendimiento y menos problemas DDS |
| **C. VirtualBox** (guía del curso) | ❌ Sin CUDA, 3D lento | ⚠️ Adaptador puente | ⚠️ rviz/rqt lentos | Seguir el curso al pie de la letra |

Para Computer Vision, el procesamiento de imagen ocurre en tu PC: con modelos de
detección conviene tener GPU, y VirtualBox no puede usarla. Elige **A** o **B** si
puedes.

### 1.A WSL2 (Windows 10/11)

1. PowerShell **como administrador**:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
2. Red espejo, imprescindible para DDS. Crea `C:\Users\<usuario>\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   y aplica con `wsl --shutdown`.
3. Firewall de Hyper-V: permite tráfico entrante a WSL (PowerShell **administrador**):
   ```powershell
   Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
   ```
4. Marca la red Wi-Fi del laboratorio como **Privada** en Windows
   (Configuración → Red → Wi-Fi → la red → Tipo de perfil).
5. Abre Ubuntu (`wsl -d Ubuntu-24.04`) y sigue desde la [sección 2](#2-preparar-ubuntu-e-instalar-ros-2-jazzy).

> 💡 **Ventanas gráficas.** WSLg ya viene con Windows 11: `rqt_image_view`, `rviz2` y
> `cv2.imshow` abren ventanas sin configurar nada.
> **GPU.** Con una NVIDIA, instala solo el driver de Windows y comprueba `nvidia-smi`
> dentro de WSL; **no** instales drivers NVIDIA dentro de Ubuntu.

> 💡 **Multicast en WSL.** Aun en modo `mirrored`, el descubrimiento por multicast es
> poco fiable (verificado: 0 tópicos en 30 s sin peers, descubrimiento en ~1 s con
> `ROS_STATIC_PEERS`). `tb4_connect.sh` (§4.5) lo detecta y lo corrige solo.

### 1.B Ubuntu nativo

Instala Ubuntu 24.04 desde la [ISO oficial](https://releases.ubuntu.com/24.04) (dual
boot o equipo dedicado) y sigue en la [sección 2](#2-preparar-ubuntu-e-instalar-ros-2-jazzy).

### 1.C VirtualBox (flujo del curso)

1. Instala [VirtualBox](https://www.virtualbox.org).
2. Crea una VM: Linux → Ubuntu (64-bit), **RAM ≥ 4 GB** (recomendado 8 GB),
   **disco ≥ 20 GB**, ISO de [Ubuntu 24.04](https://releases.ubuntu.com/24.04).
3. Instala Ubuntu y las **Guest Additions**.
4. Actualiza:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo reboot
   ```

> 💡 **Red de la VM en modo puente.** En VirtualBox → Configuración → Red, pon el
> adaptador en **Adaptador puente** sobre la interfaz Wi-Fi real. Con **NAT** (por
> defecto) el ping al robot puede funcionar, pero DDS no descubre los tópicos.

En el resto de la guía, **"VM"** significa tu entorno de desarrollo, sea cual sea.

---

## 2. Preparar Ubuntu e instalar ROS 2 Jazzy

```bash
# Entorno UTF-8
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Repositorios
sudo apt install -y software-properties-common
sudo add-apt-repository -y universe

# Repositorio de ROS 2
sudo apt install -y curl gnupg2 lsb-release
sudo mkdir -p /usr/share/keyrings
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update

# ROS 2 Jazzy
sudo apt install -y ros-jazzy-desktop
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

Verifica:

```bash
ros2 run demo_nodes_cpp talker     # Ctrl+C para salir
```

> 💡 Si `apt update` falla con `EXPKEYSIG`/`NO_PUBKEY`, la llave de ROS rotó:
> [TROUBLESHOOTING § 4.1](TROUBLESHOOTING.md#41-error-de-firma-gpg-en-apt-update).

---

## 3. Paquetes del TurtleBot 4 en la VM

```bash
sudo apt update
sudo apt install -y ros-jazzy-turtlebot4-desktop
ros2 pkg list | grep turtlebot4
```

> 💡 Útiles para visión y teleop (si no vinieron con `desktop`):
> ```bash
> sudo apt install -y ros-jazzy-teleop-twist-keyboard ros-jazzy-rqt-image-view \
>   ros-jazzy-image-transport-plugins ros-jazzy-cv-bridge python3-opencv
> ```

---

## 4. Configurar y conectar el TurtleBot 4

### 4.1 Primer acceso (modo punto de acceso)

1. **Enciende el robot** y espera ~1 min.
2. Conecta la PC a la Wi-Fi **`turtlebot4`** (contraseña: `turtlebot4`).
3. SSH:
   ```bash
   ssh ubuntu@10.42.0.1
   # contraseña por defecto: turtlebot4
   ```

### 4.2 Wi-Fi del laboratorio

```bash
turtlebot4-setup
```

En **Wi-Fi Setup** introduce los parámetros de red y luego **Apply Settings**:

| Campo | Valor |
|---|---|
| Wi-Fi Mode | `Client` |
| SSID | `<WIFI_SSID>` (p. ej. `Lab_Computech_5G`) |
| Password | `<WIFI_PASSWORD>` |
| Band | `5GHz` (o `2.4GHz` según la red) |

El robot deja el modo AP y se pierde el SSH: conecta la PC a la **misma red**.

> 💡 **Encontrar la IP del robot.**
> - **Standard**: la muestra la pantalla del robot.
> - **Lite** (sin pantalla): panel del router, `ssh ubuntu@turtlebot4.local`, o
>   `arp -a` buscando una MAC de Raspberry Pi (`d8:3a:dd`, `dc:a6:32`, `e4:5f:01`).

> 💡 **No borres la red del laboratorio** de un robot ya configurado; para otras redes
> *agrega* conexiones (ejemplo en `docs/guia_conexion_turtlebot4.md`).

### 4.3 Red del Create 3 (puerto 8080)

Abre en el navegador:

```
http://<IP_ROBOT>:8080
```

En la interfaz web del **Create 3** configura la red/ROS
(**Application → Configuration**): mismo `ROS_DOMAIN_ID` que el robot, RMW
`rmw_fastrtps_cpp`, namespace vacío. Guarda y reinicia el robot:

```bash
sudo reboot
```

> 💡 En **Update** revisa que el firmware del Create 3 corresponda a **Jazzy**; un
> firmware de otra distro produce tópicos que aparecen pero no funcionan bien.

### 4.4 Vías de conexión física

El flujo del curso usa la Wi-Fi del laboratorio. Hay dos vías más para cuando no está
disponible:

| Vía | Cuándo | Cómo |
|---|---|---|
| **Wi-Fi del laboratorio** (por defecto) | Siempre que se pueda | PC y robot en `<WIFI_SSID>` |
| **Cable Ethernet directo** | Wi-Fi caída, sin multicast o robot "perdido" | Cable PC ↔ Raspberry Pi. La imagen del TB4 trae `eth0` fija en `192.168.185.3/24`. En la PC: IP `192.168.185.10`, máscara `255.255.255.0`, sin puerta de enlace. `ssh ubuntu@192.168.185.3` |
| **Hotspot del celular** | Fuera del laboratorio | Añade la red al robot como conexión *extra* (no reemplaces la del lab); PC y robot al hotspot |

Para agregar una red sin perder la del laboratorio (en el robot):

```bash
sudo nmcli connection add type wifi ifname wlan0 con-name respaldo \
  ssid "<SSID>" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<CLAVE>" \
  connection.autoconnect yes connection.autoconnect-priority 5 \
  802-11-wireless.powersave 2
```

> 💡 Evita redes con **aislamiento de clientes** (invitados, Wi-Fi universitaria
> abierta, algunos hotspots): el ping puede funcionar a medias y DDS no.

### 4.5 Conexión diaria: `tb4_connect.sh` y `tb4_check.sh`

Hecha la configuración inicial (§4.1–4.3 y §5), la forma recomendada de conectar
cada día es:

```bash
cd ~/turtleclaude4        # o la ruta del repo (en WSL: /mnt/c/Users/<usuario>/turtleclaude4)
source tb4_connect.sh <IP_ROBOT> <DOMAIN_ID>
```

`tb4_connect.sh` hace en un paso lo que antes era manual:

1. Carga ROS 2 Jazzy y exporta `ROS_DOMAIN_ID` y `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`.
2. Hace ping al robot.
3. Prueba el descubrimiento por **multicast**. Si no ve los 4 tópicos clave
   (`/scan`, `/odom`, `/cmd_vel`, `/oakd/rgb/preview/image_raw`), prueba con
   **`ROS_STATIC_PEERS`** y se queda con el modo que funcione mejor.
4. Guarda la configuración que funcionó en `~/.tb4_robot`.

```bash
source tb4_connect.sh                    # reconectar al último robot guardado
source tb4_connect.sh <IP> <ID> peers    # forzar modo (auto | multicast | peers)
source tb4_connect.sh --off              # limpiar (dominio 0, sin peers)
```

Para que **cada terminal nueva** quede configurada al instante (sin repetir pruebas):

```bash
echo '[ -f ~/.tb4_robot ] && source ~/.tb4_robot' >> ~/.bashrc
```

Si algo no va, `tb4_check.sh` ejecuta el checklist de
[TROUBLESHOOTING § 3](TROUBLESHOOTING.md#3-checklist-rápido-de-diagnóstico) y te
indica la sección a consultar:

```bash
./tb4_check.sh                 # desde la PC: entorno, red, puertos, tópicos, datos, tipo de /cmd_vel
./tb4_check.sh --robot         # además entra por SSH: dominio, servicio, Create 3, OAK-D, LiDAR
```

Ninguno de los dos mueve ni reconfigura el robot.

### 4.6 Modos de descubrimiento DDS

| Modo | Cómo se activa | Cuándo usarlo |
|---|---|---|
| **Multicast** (por defecto) | Nada que hacer | Ubuntu nativo o VirtualBox en puente, en una red que deja pasar multicast |
| **Peers estáticos** (Jazzy) | `export ROS_STATIC_PEERS=<IP_ROBOT>` (o `tb4_connect.sh`) | WSL, redes que bloquean multicast. Solo hace falta en la PC |
| **Discovery Server** | `turtlebot4-setup` → *ROS Setup* → *Discovery Server*, más la configuración de la PC según el [manual oficial](https://turtlebot.github.io/turtlebot4-user-manual/setup/discovery_server.html) | Muchos robots en una misma red o redes muy restrictivas. Cambia la configuración del robot: acuérdalo con el docente |

### 4.7 SSH cómodo

En `~/.ssh/config` de la PC (en Windows: `C:\Users\<usuario>\.ssh\config`):

```
Host tb4
  HostName <IP_ROBOT>
  User ubuntu
  ServerAliveInterval 15
  ServerAliveCountMax 4
```

Con eso basta `ssh tb4`. Para entrar sin contraseña: `ssh-keygen -t ed25519` y luego
`ssh-copy-id tb4`.

> 💡 Portal del Create 3 sin acceso directo al 8080: `ssh -L 8080:192.168.186.2:80 tb4`
> y abre `http://localhost:8080`.

### 4.8 Varios robots en el laboratorio

- **Un `ROS_DOMAIN_ID` distinto por robot o grupo.** Si no, todos ven todos los
  tópicos y un `/cmd_vel` puede mover el robot de otro grupo.
- Lleva un registro (IP, ID, grupo). `~/.tb4_robot` guarda el último robot; si cambias
  de robot, vuelve a ejecutar `source tb4_connect.sh <IP> <ID>`.
- Con muchos robots en la misma Wi-Fi, el tráfico de cámara satura la red: usa
  `/compressed` (§8).

---

## 5. Sincronizar `ROS_DOMAIN_ID` y probar talker/listener

### 5.1 `ROS_DOMAIN_ID`

Usa **el mismo valor** en la VM y en el robot:

```bash
echo $ROS_DOMAIN_ID                 # ver el actual
export ROS_DOMAIN_ID=<DOMAIN_ID>    # cambiarlo (sesión actual)
source /opt/ros/jazzy/setup.bash    # actualizar variables de entorno
```

> 💡 **Hazlo persistente.** `export` solo dura en esa terminal. En la VM:
> ```bash
> echo "export ROS_DOMAIN_ID=<DOMAIN_ID>" >> ~/.bashrc
> ```
> En el **robot**, el bringup corre como servicio y **no** lee tu `export`: cámbialo con
> `turtlebot4-setup` → *ROS Setup* → *Bash Setup* → `ROS_DOMAIN_ID` → *Save* → *Apply Settings*.
> Debe coincidir en tres sitios: VM, Raspberry Pi y Create 3 (portal 8080).

> 💡 **Rango.** Aunque se suele decir 0–255, usa **0–101** (los valores altos pueden
> chocar con puertos efímeros de Linux). Cada robot del laboratorio necesita un ID
> distinto para no mezclar tópicos entre grupos.

### 5.2 Prueba de comunicación

En el **robot**, instala los nodos demo:

```bash
sudo apt update
sudo mkdir -p /usr/share/keyrings
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu noble main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py
```

| Dónde | Comando |
|---|---|
| **Robot** | `ros2 run demo_nodes_cpp listener` |
| **VM** | `ros2 run demo_nodes_cpp talker` |

✅ Si el listener recibe los mensajes, la comunicación ROS funciona.
❌ Si no, revisa el `ROS_DOMAIN_ID` → [TROUBLESHOOTING § 1](TROUBLESHOOTING.md#1-red-y-dds).

Luego entra a `turtlebot4-setup`, **reinicia el Create 3** y aplica todo. Espera la
melodía alegre de arranque del robot (“pu puru pupu”).

> 💡 **Redes que bloquean multicast** (WSL, Wi-Fi universitaria o de invitados): el ping
> funciona pero no se ven tópicos. En la VM:
> ```bash
> export ROS_STATIC_PEERS=<IP_ROBOT>
> ros2 daemon stop
> ```
> Resolvió el caso WSL documentado en `docs/`. `source tb4_connect.sh` (§4.5) lo
> detecta y lo aplica solo.

---

## 6. Sensores y bringup

En el **robot**:

```bash
sudo apt install -y \
  ros-jazzy-rplidar-ros \
  ros-jazzy-depthai-ros \
  ros-jazzy-irobot-create-nodes \
  ros-jazzy-turtlebot4-msgs \
  ros-jazzy-turtlebot4-description \
  ros-jazzy-turtlebot4-bringup
```

Apaga y vuelve a encender el robot. Al reconectarte por SSH:

```bash
ros2 launch turtlebot4_bringup lite.launch.py        # TurtleBot 4 Lite
ros2 launch turtlebot4_bringup standard.launch.py    # TurtleBot 4 Standard
```

> 💡 **Bringup automático.** La imagen oficial trae `turtlebot4.service`, que ya lanza el
> bringup al arrancar. Compruébalo antes de lanzarlo a mano para no duplicar nodos:
> ```bash
> systemctl is-active turtlebot4.service    # "active" → ya está corriendo
> ```

### 6.1 Sensores individuales

```bash
ros2 launch turtlebot4_bringup rplidar.launch.py    # LiDAR → /scan
ros2 launch turtlebot4_bringup oakd.launch.py       # Cámara OAK-D → /oakd/...
```

El bringup general ya los incluye; lánzalos aparte para activarlos si no publican o
para depurar uno aislado.

### 6.2 Checklist de tópicos

En otra terminal: `ros2 topic list`. Para visión y navegación deben estar:

| Tópico | Tipo | Uso | Verificar |
|---|---|---|---|
| `/oakd/rgb/preview/image_raw` | `sensor_msgs/Image` | **Visión** (RGB) | `ros2 topic hz /oakd/rgb/preview/image_raw` |
| `/oakd/rgb/preview/image_raw/compressed` | `sensor_msgs/CompressedImage` | Visión por Wi-Fi | `ros2 topic hz …/compressed` |
| `/oakd/rgb/preview/camera_info` | `sensor_msgs/CameraInfo` | Calibración | `ros2 topic echo --once …` |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR / navegación | `ros2 topic hz /scan` |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | Control de velocidad | `ros2 topic info /cmd_vel` |
| `/odom` | `nav_msgs/Odometry` | Odometría | `ros2 topic echo /odom --once` |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | Transformadas | `ros2 run tf2_tools view_frames` |
| `/imu`, `/oakd/imu/data` | `sensor_msgs/Imu` | IMU | `ros2 topic hz /imu` |
| `/battery_state` | `sensor_msgs/BatteryState` | Batería | `ros2 topic echo /battery_state --once` |

Lista completa esperada (TurtleBot 4 Lite):

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

El Standard añade tópicos de pantalla y botones (`/hmi/...`). Si faltan tópicos →
[TROUBLESHOOTING § 2](TROUBLESHOOTING.md#2-cámara-y-sensores).

> 💡 Si aparecen `/scan` y `/oakd/...` pero **faltan** `/odom` y `/battery_state`, la Pi
> está bien y el problema es el Create 3 (dominio o firmware): [TROUBLESHOOTING § 1.2](TROUBLESHOOTING.md#12-discrepancias-de-ros_domain_id).

---

## 7. Movimiento y teleoperación (`TwistStamped`)

En el **robot**:

```bash
ros2 topic echo /cmd_vel
```

En la **VM**:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
```

> 💡 **Por qué `stamped:=true`.** En Jazzy, `/cmd_vel` del TurtleBot 4 es
> `geometry_msgs/msg/TwistStamped`. Un `Twist` simple en `/cmd_vel` **no mueve el
> robot**. Para `Twist` sin cabecera existe `/cmd_vel_unstamped`. Desde la CLI:
> ```bash
> ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
>   "{header: {frame_id: base_link}, twist: {linear: {x: 0.1}}}"
> ```
> En código propio (rclpy), rellena `msg.header.stamp` con el reloj del nodo y
> `msg.header.frame_id = "base_link"`, y escribe la velocidad en `msg.twist`.

> 💡 **Seguridad.** Empieza con velocidades bajas (0.1 m/s, 1.0 rad/s). El Create 3 no
> tiene sensores traseros. Evita que dos nodos publiquen en `/cmd_vel` a la vez (un mando
> conectado al robot también publica).

---

## 8. Cámara y visión

```bash
ros2 run rqt_image_view rqt_image_view
```

Selecciona `/oakd/rgb/preview/image_raw`.

> 💡 **Ancho de banda.** Por Wi-Fi, la imagen cruda puede verse entrecortada o no
> llegar. Usa `/oakd/rgb/preview/image_raw/compressed` (requiere
> `ros-jazzy-image-transport-plugins`). Para procesar en la VM, suscríbete con QoS
> *sensor data* (best effort).

> 💡 **Reloj.** La Raspberry Pi no tiene RTC y el Create 3 lleva su propio reloj: si los
> *timestamps* no cuadran (tf, sincronización cámara-LiDAR), ver
> [TROUBLESHOOTING § 2.4](TROUBLESHOOTING.md#24-reloj-desfasado-tf--fusión-de-sensores).

---

## 9. Herramientas de este repositorio

Scripts independientes (sin paquete colcon) para ejecutar en la VM con ROS 2 cargado:

| Script | Qué hace | Uso |
|---|---|---|
| `tb4_connect.sh` | Configura la terminal para un robot; multicast → peers automático; guarda en `~/.tb4_robot` | `source tb4_connect.sh <IP> <ID>` |
| `tb4_check.sh` | Checklist automático con ✅/❌ y referencia a TROUBLESHOOTING | `./tb4_check.sh [IP] [--robot]` |
| `teleop_wasd.py` | Teleop WASD; detecta si `/cmd_vel` es `Twist` o `TwistStamped`; se detiene solo si sueltas las teclas | `python3 teleop_wasd.py` · `--dry` (no publica) |
| `ver_camara_tb4.py` | Visor OpenCV de la OAK-D con FPS | `python3 ver_camara_tb4.py --scale 3` |
| `ver_lidar_tb4.py` | Vista cenital de `/scan`; marca en rojo obstáculos frontales < 0.5 m | `python3 ver_lidar_tb4.py --range 6 --rot 90` |

Si no ven datos, el problema es de red/DDS, no del script → [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
