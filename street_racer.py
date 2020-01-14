#!/usr/bin/python3
import json
import os
import scipy.interpolate
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


def load_image(file):
    """ loads an image, prepares it for play """
    file = os.path.join(assets_dir, file)
    try:
        surface = pg.image.load(file)
    except pg.error:
        raise SystemExit('Could not load image "%s" %s' % (file, pg.get_error()))
    return surface.convert_alpha()


def rot_center(image, rect, angle):
    """Rotate an image while keeping its center"""
    rot_image = pg.transform.rotate(image, angle)
    rot_rect = rot_image.get_rect(center=rect.center)
    return rot_image, rot_rect

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

def interpolate_spline(x: list, y: list, newx: list) -> list:
    """Since scipy's spline is deprecated this is a function with a similar interface"""
    f = scipy.interpolate.interp1d(x, y, kind='cubic', fill_value='extrapolate')
    newy = f(newx)
    # plt.plot(x, y, 'o', newx, newy, '-')
    # plt.show()
    return newy


class Player(pg.sprite.Sprite):
    """
    Represents the player controlled car
    """

    images = []

    def __init__(self, configuration: dict):
        """
        Args:
            configuration: dictionary with vehicle data such as name and stats
        """
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image           = self.images[0]
        self.image_original  = self.images[0]
        self.rect            = self.image.get_rect(midbottom=SCREENRECT.midbottom)
        self.angle           = 0  # current sprite rotation in degrees
        self.posX, self.posY = self.rect.center
        self.origtop         = self.rect.top
        self.acceleration    = 0 # Way which car accelerates +1 = foreward, -1 = backward, 0 = no acceleration
        self.velocity        = 0
        self.engine_RPM      = 5000 # For now use constant RPM of the engine
        self.mass            = configuration["stats"]["mass"]

        # Below lists represent the interpolated values of engine power and torque every 1 RPM
        self.power_interpolation = []
        self.torque_interpolation = []
        self._interpolate_power_and_torque(configuration)

    def _interpolate_power_and_torque(self, configuration: dict):
        torque_data = configuration["stats"]["torque_samples"]
        power_data  = configuration["stats"]["power_samples"]
        if len(torque_data) != len(power_data):
            raise Exception(f"{configuration['full_name']} has incosistent amount of torque and power samples")
        # Define range at which we will interpolate the data
        start               = 0
        end                 = configuration["stats"]["max_rpm"] + 1
        sampling_start      = configuration["stats"]["sampling_start"]
        sampling_precision  = configuration["stats"]["sampling_precision"]
        # calculate the position of data on x axis (RPM axis)
        samples_x = [sampling_precision*i + sampling_start for i in range(len(torque_data))]
        self.torque_interpolation = interpolate_spline(samples_x, torque_data, range(start, end))
        self.power_interpolation  = interpolate_spline(samples_x, power_data, range(start, end))


    def accelerate(self, direction):
        self.acceleration = direction

    def rotate(self, direction):
        """
        Rotate the sprite
        Args:
            direction: +1 turn counter-clockwise, -1 turn clockwise
        """
        self.angle += direction
        self.image, self.rect = rot_center(self.image_original, self.rect, self.angle)
    
    def get_power(self):
        """ Returns the current power output from the engine """
        return self.power_interpolation[int(self.engine_RPM)]
    
    def get_torque(self):
        """ Returns the current power output from the engine """
        return self.torque_interpolation[int(self.engine_RPM)]

    def update(self, deltaTime):
        # F = ma, F*s = P, W = P*t, M = r*F

        # calculate the position delta
        currX, currY = self.rect.center
        deltaX = int(self.posX - currX)
        deltaY = int(self.posY - currY)
        self.rect.move_ip(deltaX, deltaY)
        pass


def main(winstyle=0, framerate=60):
    """
    Street drifter's entry point
    Args:
        winstyle: 0 = windowed, 1 = fullscreen
        framerate: screen refresh rate, also tickrate
    """
    # Initialize pygame
    if pg.get_sdl_version()[0] == 2:
        # needed for audio later on
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

    # Create the background, tile the background image
    bgdtile = load_image("background.png")
    background = pg.Surface(SCREENRECT.size)
    for x in range(0, SCREENRECT.width, bgdtile.get_width()):
        background.blit(bgdtile, (x, 0))
    screen.blit(background, (0, 0))
    pg.display.flip()

    # Load images, assign to sprite classes
    img = pg.transform.smoothscale(load_image("McLarenF1.png"), (80, 160))
    Player.images = [img]

    # Initialize Game Groups
    all_groups = pg.sprite.RenderUpdates()

    # Assign default groups to each sprite class
    Player.containers = all_groups

    # Initialize the starting sprites
    mclaren_cfg = load_config("McLarenF1.json")
    player = Player(mclaren_cfg)

    ## Create Some Starting Values
    clock = pg.time.Clock()
    # set ticksLastFrame to -10ms to make sure math is not broken
    ticksLastFrame = pg.time.get_ticks() - 10

    while True:
        t = pg.time.get_ticks()
        # deltaTime from last tick in seconds.
        deltaTime = (t - ticksLastFrame) / 1000.0  #type: float
        ticksLastFrame = t

        # get input
        for event in pg.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                return

        keystate = pg.key.get_pressed()

        # clear/erase the last drawn sprites
        all_groups.clear(screen, background)

        # update all the sprites
        all_groups.update(deltaTime)

        # inform the car about current
        direction = keystate[K_UP] - keystate[K_DOWN]
        player.accelerate(direction)
        rotation = keystate[K_LEFT] - keystate[K_RIGHT]
        player.rotate(rotation)

        # draw the scene
        dirty = all_groups.draw(screen)
        pg.display.update(dirty)

        # wait for next tick
        clock.tick(framerate)

if __name__ == "__main__":
    main()
