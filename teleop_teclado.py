"""
Teleoperacion del TurtleBot4 con el teclado.
Correr esto EN LA RASPBERRY PI (donde esta ROS2 y el TurtleBot4), no en Windows,
porque usa termios/tty para leer teclas sin necesitar 'Enter'. No requiere IP:
ROS2 se comunica por topics (DDS) dentro de la misma maquina/enlace usb0.

Requiere: ROS2 (rclpy) ya instalado y el TurtleBot4 encendido.

Controles:
  w / s   : adelante / atras
  a / d   : girar izquierda / derecha
  z / c   : diagonal adelante-izquierda / adelante-derecha
  espacio : detener
  u / j   : subir / bajar velocidad lineal
  i / k   : subir / bajar velocidad angular
  q       : salir

Seguridad: si no se presiona ninguna tecla durante WATCHDOG_TIMEOUT segundos,
el robot se detiene automaticamente.

Uso:
  python3 teleop_teclado.py
"""
import os
import sys

# --- Silenciar warnings de bajo nivel de CycloneDDS (inofensivos) ---
# El Create3 usa ROS Humble y la Pi ROS Jazzy: los "type hash" difieren y
# CycloneDDS imprime muchos WARN por stderr. Los mensajes pasan igual, asi que
# redirigimos stderr (fd 2) a /dev/null para no ensuciar la pantalla del teleop.
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 2)
os.environ.setdefault("RCUTILS_LOGGING_SEVERITY", "ERROR")

import time
import termios
import tty
import select

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

LINEAR_SPEED_INICIAL = 0.2   # m/s
ANGULAR_SPEED_INICIAL = 1.0  # rad/s
PASO_LINEAR = 0.05
PASO_ANGULAR = 0.2
LINEAR_MAX = 0.5
ANGULAR_MAX = 2.5
WATCHDOG_TIMEOUT = 0.5  # segundos sin tecla antes de detener el robot

INSTRUCCIONES = """
Controles:
  w = adelante        s = atras
  a = girar izq        d = girar der
  z = diag adel-izq    c = diag adel-der
  espacio = detener
  u/j = +/- velocidad lineal    i/k = +/- velocidad angular
  q = salir

(el robot se detiene solo si no presionas nada por {timeout}s)
""".format(timeout=WATCHDOG_TIMEOUT)


class TeleopTeclado(Node):
    def __init__(self):
        super().__init__("teleop_teclado")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)

    def enviar(self, linear, angular):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)


def leer_tecla(settings):
    tty.setraw(sys.stdin.fileno())
    listo, _, _ = select.select([sys.stdin], [], [], 0.1)
    if listo:
        tecla = sys.stdin.read(1)
    else:
        tecla = ""
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return tecla


def clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def main():
    settings = termios.tcgetattr(sys.stdin)

    rclpy.init()
    nodo = TeleopTeclado()

    print(INSTRUCCIONES)

    velocidad_lineal = LINEAR_SPEED_INICIAL
    velocidad_angular = ANGULAR_SPEED_INICIAL
    ultima_actividad = time.monotonic()
    detenido = True

    try:
        while True:
            tecla = leer_tecla(settings)
            ahora = time.monotonic()

            if tecla:
                ultima_actividad = ahora

            if tecla == "w":
                nodo.enviar(velocidad_lineal, 0.0)
                detenido = False
            elif tecla == "s":
                nodo.enviar(-velocidad_lineal, 0.0)
                detenido = False
            elif tecla == "a":
                nodo.enviar(0.0, velocidad_angular)
                detenido = False
            elif tecla == "d":
                nodo.enviar(0.0, -velocidad_angular)
                detenido = False
            elif tecla == "z":
                nodo.enviar(velocidad_lineal, velocidad_angular)
                detenido = False
            elif tecla == "c":
                nodo.enviar(velocidad_lineal, -velocidad_angular)
                detenido = False
            elif tecla == " ":
                nodo.enviar(0.0, 0.0)
                detenido = True
            elif tecla == "u":
                velocidad_lineal = clamp(velocidad_lineal + PASO_LINEAR, 0.0, LINEAR_MAX)
                print(f"Velocidad lineal: {velocidad_lineal:.2f} m/s")
            elif tecla == "j":
                velocidad_lineal = clamp(velocidad_lineal - PASO_LINEAR, 0.0, LINEAR_MAX)
                print(f"Velocidad lineal: {velocidad_lineal:.2f} m/s")
            elif tecla == "i":
                velocidad_angular = clamp(velocidad_angular + PASO_ANGULAR, 0.0, ANGULAR_MAX)
                print(f"Velocidad angular: {velocidad_angular:.2f} rad/s")
            elif tecla == "k":
                velocidad_angular = clamp(velocidad_angular - PASO_ANGULAR, 0.0, ANGULAR_MAX)
                print(f"Velocidad angular: {velocidad_angular:.2f} rad/s")
            elif tecla == "q":
                break
            elif not tecla and not detenido and (ahora - ultima_actividad) > WATCHDOG_TIMEOUT:
                nodo.enviar(0.0, 0.0)
                detenido = True
    except KeyboardInterrupt:
        pass
    finally:
        nodo.enviar(0.0, 0.0)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        nodo.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
