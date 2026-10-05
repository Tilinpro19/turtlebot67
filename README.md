# TurtleBot 4 Lite · ROS 2 Jazzy · Computer Vision

Espacio de trabajo para el ciclo de **Computer Vision** con TurtleBot 4 Lite
(Create 3 + Raspberry Pi 4 + RPLIDAR A1 + OAK-D) sobre **ROS 2 Jazzy / Ubuntu 24.04 Noble**.

Fuentes: repositorio de requerimientos
[LuisEnriqueCortijoGonzales/requeerimientos_turtlebot4](https://github.com/LuisEnriqueCortijoGonzales/requeerimientos_turtlebot4),
notas de laboratorio 2025 y datos verificados en `docs/` (2026-09-30).
Manual oficial: [TurtleBot 4 User Manual](https://turtlebot.github.io/turtlebot4-user-manual/).

> Problemas → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## Índice

1. [Estructura del repositorio](#1-estructura-del-repositorio)
2. [Distribución base y variables de entorno](#2-distribución-base-y-variables-de-entorno)
3. [Configuración de red y hardware](#3-configuración-de-red-y-hardware)
4. [Instalación de paquetes y sensores](#4-instalación-de-paquetes-y-sensores)
5. [Flujo de ejecución y teleoperación](#5-flujo-de-ejecución-y-teleoperación)
6. [Herramientas de este repositorio](#6-herramientas-de-este-repositorio)

---

## 1. Estructura del repositorio

```
turtleclaude4/
├── README.md               ← este documento
├── TROUBLESHOOTING.md      ← fallos frecuentes y checklist de diagnóstico
├── teleop_wasd.py          ← teleop por teclado (Twist/TwistStamped automático)
├── ver_camara_tb4.py       ← visor OAK-D (/oakd/rgb/preview/image_raw)
├── ver_lidar_tb4.py        ← visor 2D del LiDAR (/scan)
├── docs/
│   ├── guia_conexion_turtlebot4.md   ← vías de conexión (Wi-Fi, cable, hotspot)
│   └── tarjeta_offline_lab.md        ← datos verificados del robot del lab
└── _legacy/                ← mando PS4 y planes de julio (solo referencia)
```

---

## 2. Distribución base y variables de entorno

| Componente | Versión |
|---|---|
| SO (PC/VM y robot) | Ubuntu 24.04 LTS **Noble** |
| ROS 2 | **Jazzy Jalisco** |
| RMW (por defecto en TB4 Jazzy) | `rmw_fastrtps_cpp` |
| Robot | TurtleBot 4 **Lite** |

### 2.1 Instalar ROS 2 Jazzy en la PC/VM

```bash
# Locale UTF-8
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Repositorio de ROS 2
sudo apt install -y software-properties-common curl gnupg2 lsb-release
sudo add-apt-repository -y universe
sudo mkdir -p /usr/share/keyrings
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-turtlebot4-desktop ros-jazzy-teleop-twist-keyboard
```

> Si `apt update` da error de firma GPG, ver [TROUBLESHOOTING § 4.1](TROUBLESHOOTING.md#41-error-de-firma-gpg-en-apt-update).

### 2.2 Variables de entorno (persistentes)

`export` solo vale para la terminal actual. Añádelas al final de `~/.bashrc` **en la PC/VM**:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=<DOMAIN_ID>          # el MISMO que el robot (lab verificado: 67)
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
# Solo si la red bloquea multicast (WSL, redes universitarias):
# export ROS_STATIC_PEERS=<IP_ROBOT>
```

```bash
source ~/.bashrc
printenv | grep -E 'ROS_|RMW_'
```

> **`ROS_DOMAIN_ID`**: aunque se suele decir "0–255", usa **0–101** para evitar choques
> de puertos UDP en Linux. Cada robot del laboratorio debe tener un ID distinto.

### 2.3 Tipo de máquina de desarrollo

| Opción | Requisito de red para DDS |
|---|---|
| **VirtualBox** (referencia del curso) | Adaptador en **Bridged / Puente**, no NAT. Con NAT los tópicos no se ven |
| **WSL2** (Windows) | `C:\Users\<usuario>\.wslconfig` con `[wsl2]` + `networkingMode=mirrored`, luego `wsl --shutdown`. Si el multicast no pasa, usa `ROS_STATIC_PEERS` |
| Ubuntu nativo | Sin requisitos extra |

---

## 3. Configuración de red y hardware

### 3.1 Primer acceso: punto de acceso `turtlebot4`

Un TurtleBot 4 recién flasheado levanta su propia red Wi-Fi.

1. Enciende el robot y espera ~1 min.
2. Conecta la PC a la red **`turtlebot4`** (contraseña por defecto: `turtlebot4`).
3. Entra por SSH:
   ```bash
   ssh ubuntu@10.42.0.1
   # contraseña por defecto: turtlebot4
   ```

### 3.2 Wi-Fi del laboratorio con `turtlebot4-setup`

```bash
turtlebot4-setup
```

En **Wi-Fi Setup** configura:

| Campo | Valor |
|---|---|
| Wi-Fi Mode | `Client` |
| SSID | `Lab_Computech_5G` *(otra variante en el lab: `Lab_Computech_3_5G`)* |
| Password | `<WIFI_PASSWORD>` *(la da el docente; no la subas al repo)* |
| Band | `5GHz` |

Guarda, luego **Apply Settings**. El robot se reinicia y sale del modo AP: la conexión
SSH se pierde. Conecta la PC a la **misma red** y busca la nueva IP del robot
(router, `arp -a` con MAC `d8:3a:dd…`, o `ssh ubuntu@turtlebot4.local`).

> No borres la red del laboratorio del robot; para otras redes **agrega** conexiones
> (ver `docs/guia_conexion_turtlebot4.md`).

### 3.3 Red del iRobot Create 3 (portal web, puerto 8080)

La Raspberry Pi reenvía el portal del Create 3 (que vive en `192.168.186.2`, por `usb0`):

```
http://<IP_ROBOT>:8080
```

En **Application → Configuration** verifica/ajusta:

| Parámetro | Valor |
|---|---|
| `ROS_DOMAIN_ID` | igual al de la Pi y la PC |
| RMW | `rmw_fastrtps_cpp` |
| Namespace | vacío (salvo multi-robot) |

Guarda y **Application → Restart Application**. Revisa también en **Update** que el
firmware del Create 3 sea el de Jazzy.

### 3.4 Sincronizar `ROS_DOMAIN_ID` en robot y PC/VM

En el **robot**, el bringup corre como servicio (`turtlebot4.service`) y **no** lee tu
`export` de la sesión SSH. Cámbialo con el asistente:

```bash
turtlebot4-setup
# ROS Setup → Bash Setup → ROS_DOMAIN_ID = <DOMAIN_ID> → Save → Apply Settings
```

Comprueba en el robot (sesión SSH nueva) y en la PC:

```bash
echo $ROS_DOMAIN_ID
source /opt/ros/jazzy/setup.bash
```

Ambos valores, más el del portal 8080 del Create 3, deben coincidir.

### 3.5 Prueba de comunicación nodo a nodo

Instala los nodos demo en el **robot**:

```bash
sudo apt update
sudo apt install -y ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py
```

| Dónde | Comando |
|---|---|
| **Robot** (SSH) | `ros2 run demo_nodes_cpp listener` |
| **PC/VM** | `ros2 run demo_nodes_cpp talker` |

✅ El listener imprime `I heard: [Hello World: N]` → DDS funciona entre PC y robot.
❌ Si no: [TROUBLESHOOTING § 1](TROUBLESHOOTING.md#1-red-y-dds).

Después: `turtlebot4-setup` → reiniciar Create 3 / aplicar todo, y esperar la
melodía de arranque del robot.

---

## 4. Instalación de paquetes y sensores

En el **robot** (la imagen oficial ya trae la mayoría; esto repara/completa):

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-rplidar-ros \
  ros-jazzy-depthai-ros \
  ros-jazzy-irobot-create-nodes \
  ros-jazzy-irobot-create-msgs \
  ros-jazzy-turtlebot4-msgs \
  ros-jazzy-turtlebot4-description \
  ros-jazzy-turtlebot4-bringup
```

Apaga y vuelve a encender el robot.

En la **PC/VM** (visión y herramientas):

```bash
sudo apt install -y \
  ros-jazzy-turtlebot4-desktop \
  ros-jazzy-rqt-image-view \
  ros-jazzy-image-transport-plugins \
  ros-jazzy-cv-bridge \
  python3-opencv python3-numpy
```

---

## 5. Flujo de ejecución y teleoperación

### 5.1 Bringup general

En el TurtleBot 4 Lite, `turtlebot4.service` lanza el bringup **automáticamente** al
arrancar. Antes de lanzarlo a mano:

```bash
systemctl status turtlebot4.service --no-pager | head -5
```

- **`active (running)`** → ya está corriendo; **no** lances otro (duplicarías nodos).
- **inactivo** → lánzalo manualmente:
  ```bash
  ros2 launch turtlebot4_bringup lite.launch.py
  ```

### 5.2 Sensores individuales

`lite.launch.py` ya incluye ambos. Úsalos solo para depurar un sensor aislado
(con el bringup general detenido):

```bash
ros2 launch turtlebot4_bringup rplidar.launch.py   # LiDAR RPLIDAR A1 → /scan
ros2 launch turtlebot4_bringup oakd.launch.py      # Cámara OAK-D → /oakd/...
```

### 5.3 Checklist de tópicos

Desde la **PC/VM**: `ros2 topic list`

| Tópico | Tipo | Uso | Verificar |
|---|---|---|---|
| `/oakd/rgb/preview/image_raw` | `sensor_msgs/Image` | **Visión** (RGB preview) | `ros2 topic hz /oakd/rgb/preview/image_raw` |
| `/oakd/rgb/preview/image_raw/compressed` | `sensor_msgs/CompressedImage` | Visión por Wi-Fi (menos ancho de banda) | `ros2 topic hz …/compressed` |
| `/oakd/rgb/preview/camera_info` | `sensor_msgs/CameraInfo` | Calibración intrínseca | `ros2 topic echo --once …` |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR / navegación (~7.5 Hz) | `ros2 topic hz /scan` |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | **Control de velocidad** | `ros2 topic info /cmd_vel` |
| `/odom` | `nav_msgs/Odometry` | Odometría | `ros2 topic echo /odom --once` |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | Transformadas | `ros2 run tf2_tools view_frames` |
| `/imu`, `/oakd/imu/data` | `sensor_msgs/Imu` | IMU Create 3 / OAK-D | `ros2 topic hz /imu` |
| `/battery_state` | `sensor_msgs/BatteryState` | Batería | `ros2 topic echo /battery_state --once` |

Lista completa esperada tras el bringup (notas de laboratorio):
`/battery_state /cmd_audio /cmd_lightring /cmd_vel /cmd_vel_unstamped /diagnostics
/diagnostics_agg /diagnostics_toplevel_state /dock_status /function_calls
/hazard_detection /imu /interface_buttons /ip /joint_states /joy /joy/set_feedback
/mouse /oakd/imu/data /oakd/rgb/preview/{camera_info,image_raw,image_raw/compressed,…}
/odom /parameter_events /robot_description /rosout /scan /tf /tf_static /wheel_status`

### 5.4 Control de velocidad: `TwistStamped`

En Jazzy, `/cmd_vel` del TurtleBot 4 es **`geometry_msgs/msg/TwistStamped`**
(cabecera con `stamp` + `frame_id`). Publicar un `Twist` simple en `/cmd_vel` **no mueve
el robot**. Para `Twist` sin cabecera existe `/cmd_vel_unstamped`.

```bash
ros2 topic info /cmd_vel   # Type: geometry_msgs/msg/TwistStamped
```

Ejemplo mínimo desde CLI (avanza 0.1 m/s):

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.1}, angular: {z: 0.0}}}"
```

### 5.5 Teleoperación por teclado

| Dónde | Comando |
|---|---|
| **Robot** (verificación) | `ros2 topic echo /cmd_vel` |
| **PC/VM** | `ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true` |

Sin `-p stamped:=true` el teleop publica `Twist` y el robot lo ignora.

> Seguridad: el Create 3 no tiene sensores traseros. Empieza a velocidad baja
> (0.1 m/s, 1.0 rad/s) y evita que dos nodos publiquen en `/cmd_vel` a la vez
> (en el robot corre `teleop_twist_joy_node`).

### 5.6 Ver la cámara

```bash
ros2 run rqt_image_view rqt_image_view
# Elegir /oakd/rgb/preview/image_raw/compressed si la Wi-Fi va justa
```

---

## 6. Herramientas de este repositorio

Scripts independientes (sin paquete colcon); requieren el entorno de §2.2.

| Script | Qué hace | Uso |
|---|---|---|
| `teleop_wasd.py` | Teleop WASD; detecta si `/cmd_vel` es `Twist` o `TwistStamped`; watchdog de parada | `python3 teleop_wasd.py` · `--dry` (no publica) |
| `ver_camara_tb4.py` | Visor OpenCV de la OAK-D con FPS | `python3 ver_camara_tb4.py --scale 3` |
| `ver_lidar_tb4.py` | Vista cenital de `/scan`, marca obstáculos frontales < 0.5 m | `python3 ver_lidar_tb4.py --range 6 --rot 90` |

Las tres leen o publican por ROS 2: si no ven datos, el problema es de red/DDS
→ [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
