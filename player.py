import scipy.interpolate
from math import cos, sin, degrees, radians, asin, pi
import pygame as pg
from pygame.locals import *

# air density in kg/m^3
AIR_DENSITY = 1.225
PIXELS_PER_METRE = 142 / 4.29
EARTH_ACCELERATION = 9.81

def rot_center(image, rect, angle):
    """Rotate an image while keeping its center"""
    rot_image = pg.transform.rotate(image, angle)
    rot_rect = rot_image.get_rect(center=rect.center)
    return rot_image, rot_rect

def interpolate_spline(x: list, y: list, newx: list) -> list:
    """Since scipy's spline is deprecated this is a function with a similar interface"""
    f = scipy.interpolate.interp1d(x, y, kind="cubic", fill_value="extrapolate")
    newy = f(newx)
    # plt.plot(x, y, 'o', newx, newy, '-')
    # plt.show()
    return newy

class Player(pg.sprite.Sprite):
    """
    Represents the player controlled car
    """

    images = []

    def __init__(self, configuration: dict, screenrect: Rect):
        """
        Args:
            configuration: dictionary with vehicle data such as name and stats
            screenrect: Screen rectangle, used to place the car
        """
        # sprite configuration
        pg.sprite.Sprite.__init__(self, self.containers)
        self.image = self.images[0]
        self.image_original = self.images[0]
        self.rect = self.image.get_rect(midbottom=screenrect.midbottom)
        # player configuration
        self.configuration = configuration
        self.angle = 0  # current sprite rotation in degrees
        self.posX, self.posY = self.rect.center
        self.origtop = self.rect.top
        # Way in which car accelerates +1 = forward, -1 = backward, 0 = no acceleration
        self.acceleration = 0
        # Way which driver wants to turn +1 = left, -1 = right, 0 = no steering
        self.steering = 0
        self.velocity = 0  # current velocity of the vehicle
        self.min_RPM = configuration["stats"]["min_rpm"]
        self.max_RPM = configuration["stats"]["max_rpm"]
        self.engine_RPM = 5000  # For now use constant RPM of the engine
        self.mass = configuration["stats"]["mass"]
        self.gear = 1 # current gear
        self.gears = configuration["transmission"]

        # Below lists represent the interpolated values of engine power and torque every 1 RPM
        self.power_interpolation = []
        self.torque_interpolation = []
        self._interpolate_power_and_torque(configuration)

    def _interpolate_power_and_torque(self, configuration: dict):
        torque_data = configuration["stats"]["torque_samples"]
        power_data = configuration["stats"]["power_samples"]
        if len(torque_data) != len(power_data):
            raise Exception(
                f"{configuration['full_name']} has incosistent amount of torque and power samples"
            )
        # Define range at which we will interpolate the data
        start = 0
        end = configuration["stats"]["max_rpm"] + 1
        sampling_start = configuration["stats"]["sampling_start"]
        sampling_precision = configuration["stats"]["sampling_precision"]
        # calculate the position of data on x axis (RPM axis)
        samples_x = [sampling_precision * i + sampling_start for i in range(len(torque_data))]
        self.torque_interpolation = interpolate_spline(samples_x, torque_data, range(start, end))
        self.power_interpolation = interpolate_spline(samples_x, power_data, range(start, end))

    def accelerate(self, direction):
        self.acceleration = direction

    def rotate(self, direction):
        """
        Rotate the sprite
        Args:
            direction: +1 turn counter-clockwise, -1 turn clockwise
        """
        self.steering = direction
        # self.angle += direction
        # self.image, self.rect = rot_center(self.image_original, self.rect, self.angle)

    def get_power(self):
        """ Returns the current power output from the engine """
        return self.power_interpolation[int(self.engine_RPM)]

    def get_torque(self):
        """ 
        Returns the current torque output from the engine 
        (probably not the most scientific way to say this)
        """
        return self.torque_interpolation[int(self.engine_RPM)]

    def update_rpm(self):
        # wheel revolutions per second
        revolutions = self.velocity / (2 * self.configuration["wheels"]["radius"] * pi)
        engine_revolutions = revolutions * trans

    def update(self, deltaTime):
        # F = ma, F*s = P, W = P*t, M = r*F
        fs = self.configuration["wheels"]["static_friction"]
        if self.acceleration > 0 or self.velocity < 0:
            r = self.configuration["wheels"]["radius"]
            F = self.get_torque() / r  # force that pushes the car forward
        else:
            F = fs * self.mass * EARTH_ACCELERATION

        F *= self.acceleration

        # calculate aerodynamic drag
        SCd = (
            self.configuration["stats"]["front_area"]
            * self.configuration["stats"]["drag_coefficient"]
        )
        Fd = 0.5 * AIR_DENSITY * self.velocity ** 2 * SCd
        F -= Fd  # F is now the net force exerted on vehicle
        a = F / self.mass

        self.velocity += a * deltaTime

        self.posX += -sin(radians(self.angle)) * self.velocity * deltaTime * PIXELS_PER_METRE
        self.posY += -cos(radians(self.angle)) * self.velocity * deltaTime * PIXELS_PER_METRE

        if self.steering != 0:
            # Calculate the maximum angle at which the car can turn without losing grip
            wheelbase = self.configuration["geometry"]["wheelbase"]
            max_friction = fs * self.mass * EARTH_ACCELERATION

            # wheelbase/ R = sin(turningAngle)
            # centrifugal force: Fc = mv^2/r
            R = self.mass * self.velocity ** 2 / max_friction
            max_turning_angle = self.configuration["wheels"]["max_turning_angle"]
            turning_angle = 90  # no car can turn at 90 degrees
            if R > wheelbase:
                turning_angle = degrees(asin(wheelbase / R))
                actualR = R
            if turning_angle > max_turning_angle:
                turning_angle = max_turning_angle
                actualR = sin(radians(turning_angle)) * wheelbase
            # omega = v / r
            angular_velocity = self.velocity / actualR  # in radians
            # print(self.velocity*3.6, turning_angle, max_friction)

            self.angle += self.steering * degrees(angular_velocity) * deltaTime

        # calculate the position delta in relation to players rectangle
        currX, currY = self.rect.center
        deltaX = int(self.posX - currX)
        deltaY = int(self.posY - currY)
        self.rect.move_ip(deltaX, deltaY)
        # rotate the rectangle to correct position
        self.image, self.rect = rot_center(self.image_original, self.rect, self.angle)
