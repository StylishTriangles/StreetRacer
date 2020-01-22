import pygame as pg
from typing import Tuple


class Meter(pg.sprite.Sprite):
    """General purpose meter"""

    def __init__(
        self, padding: int = 3, position: Tuple[int, int] = (1180, 640), color: str = "red"
    ):
        """
        Args:
            padding: padding of the displayed number, uses 0's for padding
            position: onscreen position
            color: color of the displayed text
        """
        pg.sprite.Sprite.__init__(self)
        self.font = pg.font.Font(None, 72)
        # self.font.set_italic(1)
        self.color = pg.Color(color)
        self.lastdata = -1
        self.data = 0
        self.format = "%0" + str(padding) + "d"
        self.padding = padding
        self.update()
        self.rect = self.image.get_rect().move(position[0], position[1])

    def set(self, val: int):
        """Set the displayed value"""
        self.data = val

    def update(self, *args):
        """
        Update the sprite image with current value
        """
        if self.data != self.lastdata:
            self.lastdata = self.data
            msg = self.format % self.data
            self.image = self.font.render(msg, 0, self.color)


class Speedmeter(Meter):
    """ 
    To keep track of speed
    """

    def __init__(self, padding=3, position=(1180, 640), color="red"):
        Meter.__init__(self, padding, position, color)
        self.format = "%0" + str(padding) + "dKPH"

    def set(self, speed: int):
        """Set the displayed speed"""
        self.data = speed

    def update(self, *args):
        """
        Update the sprite image with current speed
        """
        Meter.update(self, *args)


class Tachometer(Meter):
    """
    To keep track of RPM
    """

    def __init__(self, padding=4, position=(1180, 640), color="red"):
        Meter.__init__(self, padding, position, color)
        self.format = "%0" + str(padding) + "dRPM"

    def set(self, rpm: int):
        """Set the displayed RPM"""
        self.data = rpm

    def update(self, *args):
        """
        Update the sprite image with current RPM
        """
        Meter.update(self, *args)
