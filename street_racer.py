#!/usr/bin/python3
import json
import os

from lib import Player
from lib import Speedmeter, Tachometer

try:
    # Only used to show the power and torque interpolation
    import matplotlib.pyplot as plt
except ImportError:
    pass

import pygame as pg
from pygame.locals import *

# Game constants
SCREENRECT = Rect(0, 0, 1280, 720)

# constant to convert Pferdestarke (PS) to kW
PS_TO_KW = 0.73549875

# see if we can load more than standard BMP
if not pg.image.get_extended():
    raise SystemExit("Sorry, extended image module required")

main_dir = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir))
assets_dir = os.path.join(main_dir, "assets")
config_dir = os.path.join(main_dir, "config")


def load_image(file) -> pg.Surface:
    """ loads an image, prepares it for play """
    file = os.path.join(assets_dir, file)
    try:
        surface = pg.image.load(file)
    except pg.error:
        raise SystemExit('Could not load image "%s" %s' % (file, pg.get_error()))
    return surface.convert_alpha()


def load_config(name: str) -> dict:
    """
    Loads specified configuration file in JSON format, and converts it to a Python dict.
    Args:
        name: file name to be loaded (file must be in directory described by global config_dir)
    """
    path = os.path.join(config_dir, name)
    with open(path, "r") as r:
        data = json.load(r)
    return data


  

def main(winstyle=0, framerate=60):
    """
    Street drifter's entry point
    Args:
        winstyle: 0 = windowed, 1 = fullscreen
        framerate: screen refresh rate, also tickrate
    """
    global SCREENRECT
    # Initialize pygame
    if pg.get_sdl_version()[0] == 2:
        # needed for audio later
        pg.mixer.pre_init(44100, 32, 2, 4096)
    pg.init()

    fullscreen = bool(winstyle)
    # Set the display mode
    bestdepth = pg.display.mode_ok(SCREENRECT.size, winstyle, 32)
    screen = pg.display.set_mode(SCREENRECT.size, winstyle, bestdepth)

    # Decorate the game window
    icon = pg.transform.scale(load_image("icon.png"), (32, 32))
    pg.display.set_icon(icon)
    pg.display.set_caption("Street Racer")
    pg.mouse.set_visible(0)

    # Create the background
    # leave it like this, in the future the background can be scrollable
    bgdtile = pg.transform.smoothscale(load_image("background.png"), SCREENRECT.size)
    background = pg.Surface(SCREENRECT.size)
    for x in range(0, SCREENRECT.width, bgdtile.get_width()):
        background.blit(bgdtile, (x, 0))
    screen.blit(bgdtile, (0, 0))
    pg.display.flip()
    bg_moved = False

    # Load images, assign to sprite classes
    img = pg.transform.smoothscale(load_image("McLarenF1.png"), (32, 71))
    Player.images = [img]

    # Initialize Game Groups
    all_groups = pg.sprite.RenderUpdates()

    # Assign default groups to each sprite class
    Player.containers = all_groups
    Speedmeter.containers = all_groups

    # Initialize the starting sprites
    mclaren_cfg = load_config("McLarenF1.json")
    player = Player(mclaren_cfg, SCREENRECT)
    speed = Speedmeter(position=(1080, 640))
    all_groups.add(speed)
    tachometer = Tachometer(padding=4, position=(800, 640), color="blue")
    all_groups.add(tachometer)

    ## Create Some Starting Values
    clock = pg.time.Clock()
    # set ticksLastFrame to -10ms to make sure math is not broken
    ticksLastFrame = pg.time.get_ticks() - 10
    # cameraOffset = (0,0)

    while True:
        t = pg.time.get_ticks()
        # deltaTime from last tick in seconds.
        deltaTime = (t - ticksLastFrame) / 1000.0  # type: float
        ticksLastFrame = t

        # get input
        for event in pg.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                pg.quit()
                return

        keystate = pg.key.get_pressed()

        # clear/erase the last drawn sprites
        all_groups.clear(screen, background)

        # update all the sprites
        all_groups.update(deltaTime)
        speed.set(int(player.velocity*3.6))
        tachometer.set(int(player.engine_RPM))

        # inform the car about current
        direction = keystate[K_UP] - keystate[K_DOWN]
        player.accelerate(direction)
        rotation = keystate[K_LEFT] - keystate[K_RIGHT]
        player.rotate(rotation)

        # draw the scene
        # bg_moved = True
        # if bg_moved:
        #     cameraOffset = cameraOffset[0] + 1, cameraOffset[1] + 1
        #     screen.blit(bgdtile, cameraOffset)     
        #     pg.display.flip()
        dirty = all_groups.draw(screen)
        pg.display.update(dirty)

        # wait for next tick
        clock.tick(framerate)


if __name__ == "__main__":
    main()
