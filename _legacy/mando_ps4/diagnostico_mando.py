"""
Diagnostico del mando tipo PS4 (clon). Detecta el mando conectado y muestra
en vivo los valores de todos los ejes para poder mapearlos (paso 3 del brief).

Uso:
  python diagnostico_mando.py
"""
import pygame

pygame.init()
pygame.joystick.init()

count = pygame.joystick.get_count()
if count == 0:
    print("No se detecto ningun mando. Verificar conexion USB y volver a intentar.")
    raise SystemExit(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Detectado: {joystick.get_name()}")
print(f"Ejes: {joystick.get_numaxes()}, Botones: {joystick.get_numbuttons()}, Hats: {joystick.get_numhats()}")
print("Mover stick izq., stick der., y gatillos uno por uno. Ctrl+C para salir.\n")

clock = pygame.time.Clock()
try:
    while True:
        pygame.event.pump()
        axes = [round(joystick.get_axis(i), 2) for i in range(joystick.get_numaxes())]
        print(axes)
        clock.tick(10)
except KeyboardInterrupt:
    pass
