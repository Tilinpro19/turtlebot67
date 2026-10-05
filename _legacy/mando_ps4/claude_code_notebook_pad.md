# Brief para Claude Code — Notebook (script Python, mando tipo PS4)

## Contexto
Voy a teleoperar el Create3 del TurtleBot4 con un mando inalámbrico genérico estilo PS4 (clon de Temu). **Arquitectura:**
- Raspberry Pi 4: solo abstrae cámara OAK-D y lidar, no participa en el control.
- Notebook: se comunica **directo con el Create3 por WiFi**. El Create3 no tiene una API propia por WiFi aparte de ROS2 — así que por debajo seguimos usando `rclpy` (cliente Python de ROS2) para publicar velocidad, pero **sin el flujo típico de paquetes**: nada de `ros2 pkg create`, `colcon build`, `launch files`, ni `joy_node`. Todo en **un solo script Python** que:
  1. Lee el mando directamente (con `pygame` o `evdev`, sin `joy_node` de por medio).
  2. Traduce los valores a velocidad lineal/angular.
  3. Publica con `rclpy` directo al tópico del Create3.

**Fase actual: SOLO TRABAJO LOCAL.** No conectarse al Create3 real todavía. Primero validar que el script lea bien el mando e imprima los valores calculados por consola (o publique a un tópico de prueba local). La conexión real al Create3 queda para cuando yo lo indique explícitamente.

## Tu tarea, en orden

### 1. Conectar el mando (probar por cable USB primero)
Los clones baratos suelen ser más confiables por cable que por Bluetooth al inicio. Si insisto en Bluetooth:
```bash
bluetoothctl
scan on
pair <MAC>
trust <MAC>
connect <MAC>
```

### 2. Elegir librería de lectura del mando
Dos opciones, decidir según lo que ya esté instalado o sea más simple:
- **`pygame`**: más simple para prototipar, `pygame.joystick`.
- **`evdev`**: más bajo nivel, lee directo de `/dev/input/eventX`, no necesita loop de ventana.

Instalar la que se use:
```bash
pip install pygame
# o
pip install evdev
```

### 3. Detectar el mando y listar ejes/botones
Script mínimo de diagnóstico (ejemplo con `pygame`):
```python
import pygame

pygame.init()
pygame.joystick.init()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Detectado: {joystick.get_name()}")
print(f"Ejes: {joystick.get_numaxes()}, Botones: {joystick.get_numbuttons()}")

clock = pygame.time.Clock()
while True:
    pygame.event.pump()
    axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
    print(axes)
    clock.tick(10)
```
Correrlo y ayudame a mapear moviendo stick izq., stick der., y gatillos uno por uno. Construir esta tabla (los clones no siempre respetan el estándar DualShock):

Mando detectado: "PS4 Controller" / "Sony Interactive Entertainment Wireless
Controller" (clon, VID:PID 054c:09cc), 6 ejes.

**IMPORTANTE: el mapeo de ejes NO es el mismo en Windows/pygame que en
Linux/evdev** (mismo mando físico, backends distintos). El mapeo que vale es
el de Linux, porque `rclpy` solo corre ahí (ver sección de entorno más abajo).

| Control | axis[N] en Windows | axis[N] en Linux (WSL) | Reposo | Fondo |
|---|---|---|---|---|
| Stick izq. (X, giro) | axis[0] | axis[0] | 0.0 | -1.0 (izq) / +1.0 (der) |
| Stick der. (Y, avance) | axis[3] | **axis[5]** | 0.0 | -1.0 (adelante) / +1.0 (atrás) |
| Gatillos L2/R2 | axis[4], axis[5] | axis[3], axis[4] | -1.0 | +1.0 (sin diferenciar cuál es cuál en Linux todavía) |

## Entorno de ejecución (resuelto)

La notebook Windows no tiene `rclpy` (no hay ROS2 nativo para Windows).
Se instaló **Ubuntu 24.04 en WSL2** con ROS2 Jazzy (`ros-jazzy-ros-base`) +
`pygame`, y el mando se pasa por USB a WSL2 con `usbipd-win`
(`usbipd bind`/`attach --wsl`, requiere un PowerShell como administrador).
Todo el trabajo de `rclpy` corre DENTRO de esa distro WSL, no en Windows nativo.
La VM VirtualBox `Ubuntu_ROS2_Jazzy` quedó descartada (contraseña perdida, sin
snapshot) — no se usa.

### 4. Script único de teleop — FASE LOCAL (sin Create3 real)
`pad_teleop.py`, todo en un archivo, sin paquete ROS2:

```python
import pygame
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

AXIS_ANGULAR = 0
AXIS_LINEAR = 5     # axis[5] en Linux/WSL — NO 3 (eso vale solo en Windows)

MAX_LINEAR = 0.1
MAX_ANGULAR = 1.0
CMD_VEL_TOPIC = '/cmd_vel_local_test'  # placeholder — NO apuntar al Create3 todavía

class PadTeleop(Node):
    def __init__(self, joystick):
        super().__init__('pad_teleop')
        self.joystick = joystick
        self.pub = self.create_publisher(Twist, CMD_VEL_TOPIC, 10)
        self.timer = self.create_timer(0.05, self.loop)  # 20 Hz

    def loop(self):
        pygame.event.pump()
        angular = self.joystick.get_axis(AXIS_ANGULAR)
        linear = self.joystick.get_axis(AXIS_LINEAR)

        twist = Twist()
        twist.linear.x = linear * MAX_LINEAR
        twist.angular.z = -angular * MAX_ANGULAR
        self.pub.publish(twist)
        print(f"linear={twist.linear.x:.2f} angular={twist.angular.z:.2f}")

def main():
    pygame.init()
    pygame.joystick.init()
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    rclpy.init()
    node = PadTeleop(joystick)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

Correr directo, sin `colcon build`, DENTRO de WSL (Ubuntu-24.04):
```bash
source /opt/ros/jazzy/setup.bash
python3 pad_teleop.py
```

### 5. Verificación local — HECHO ✅
En otra terminal (WSL), confirmar que publique:
```bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /cmd_vel_local_test
```
Mover el mando y confirmar signos correctos: adelante = positivo, giro esperado según lado.

**Validado:** `linear` positivo con stick derecho adelante, `angular` responde
al stick izquierdo, tópico publicando correctamente vía `ros2 topic echo`.
Fase local completa.

Esta fase termina acá. Cuando esté validado, avisame y pasamos a fase 2: apuntar `CMD_VEL_TOPIC` al namespace real del Create3 (`ros2 topic list | grep cmd_vel` para confirmarlo primero) — eso no está en el alcance de este documento todavía.

## Reglas
- No subir `MAX_LINEAR`/`MAX_ANGULAR` sin confirmación explícita mía.
- No tocar nada del Raspberry Pi — ese Pi solo maneja cámara y lidar, lo lleva otra sesión.
- No conectar ni publicar hacia el Create3 real bajo ningún motivo en esta fase.
- No crear paquete ROS2 (`ros2 pkg create`), ni `colcon build`, ni launch files — todo queda en un script Python simple.
- Ante ambigüedad de mapeo de ejes, preguntar o pedirme que mueva el control de nuevo — no asumir.

## Troubleshooting de referencia

| Síntoma | Causa probable | Fix |
|---|---|---|
| Mando no detectado por `pygame` | Driver/permiso de `/dev/input` | Probar `evdev` en su lugar, o revisar permisos de usuario en input group |
| Ejes con mapeo raro/invertido | Clon no respeta estándar DualShock | Verificar todo de nuevo con el script de diagnóstico, no asumir |
| Bluetooth se desconecta solo | Común en clones baratos | Preferir cable USB para pruebas serias |
| `rclpy` no encontrado | Entorno ROS2 no sourceado | `source /opt/ros/<distro>/setup.bash` antes de correr el script |
