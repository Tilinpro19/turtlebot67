#!/bin/bash
export SDL_VIDEODRIVER=dummy
python3 -c "
import pygame
pygame.init()
pygame.joystick.init()
print('count:', pygame.joystick.get_count())
if pygame.joystick.get_count() > 0:
    j = pygame.joystick.Joystick(0)
    j.init()
    print('Detectado:', j.get_name())
"
