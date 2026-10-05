#!/bin/bash
export SDL_VIDEODRIVER=dummy
python3 -c "
import pygame, time
pygame.init()
pygame.joystick.init()
j = pygame.joystick.Joystick(0)
j.init()
print('Detectado:', j.get_name(), 'ejes:', j.get_numaxes(), 'botones:', j.get_numbuttons())
while True:
    pygame.event.pump()
    axes = [round(j.get_axis(i), 2) for i in range(j.get_numaxes())]
    print(axes, flush=True)
    time.sleep(0.1)
"
