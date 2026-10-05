"""
Teleop del Create3 con mando tipo PS4 (clon). Un solo script, sin paquete ROS2.
FASE LOCAL: publica a un topico de prueba, NO al Create3 real todavia.

Mapeo confirmado DENTRO DE WSL/Ubuntu (mando "Sony Interactive Entertainment
Wireless Controller" via evdev) — distinto del mapeo visto en Windows/pygame:
  axis[0] = stick izquierdo X   (reposo 0.0, -1.0 izq / +1.0 der)
  axis[5] = stick derecho Y     (reposo 0.0, -1.0 adelante / +1.0 atras)
  axis[3], axis[4] = gatillos   (reposo -1.0, sin diferenciar cual es cual todavia)

Uso:
  python3 pad_teleop.py
"""
import pygame
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

AXIS_ANGULAR = 0
AXIS_LINEAR = 5

MAX_LINEAR = 0.1
MAX_ANGULAR = 1.0
CMD_VEL_TOPIC = '/cmd_vel_local_test'  # placeholder — NO apuntar al Create3 todavia


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
        twist.linear.x = -linear * MAX_LINEAR   # axis[3] adelante = -1.0 -> linear.x positivo
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
