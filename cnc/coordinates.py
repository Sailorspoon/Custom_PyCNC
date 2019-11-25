from __future__ import division
import math


class Coordinates(object):
    """ This object represent machine coordinates.
        Machine supports 3 axis, so there are X, Y and Z.
    """
    def __init__(self, x, y, z, e, k, n):
        """ Create object.
        :param x: x coordinated.
        :param y: y coordinated.
        :param z: z coordinated.
        """
        self.x = round(x, 10)
        self.y = round(y, 10)
        self.z = round(z, 10)
        self.e = round(e, 10)
        self.k = round(k, 10)    # Einfügen der anderen FHG
        self.n = round(n, 10)    # Einfügen der anderen FHG

    def is_zero(self):
        """ Check if all coordinates are zero.
        :return: boolean value.
        """
        return (self.x == 0.0 and self.y == 0.0 and self.z == 0.0
                and self.e == 0.0 and self.k == 0.0 and self.n == 0.0)    # Einfügen der anderen FHG

    def is_in_aabb(self, p1, p2):
        """ Check coordinates are in aabb(Axis-Aligned Bounding Box).
            aabb is specified with two points. E is ignored.
        :param p1: First point in Coord object.
        :param p2: Second point in Coord object.
        :return: boolean value.
        """
        min_x, max_x = sorted((p1.x, p2.x))
        min_y, max_y = sorted((p1.y, p2.y))
        min_z, max_z = sorted((p1.z, p2.z))
        min_n, max_n = sorted((p1.n, p2.n))    # Als Maximal/minimal Überprüfung des Verdrehwinkels
        if self.x < min_x or self.y < min_y or self.z < min_z or self.n < min_n:
            return False
        if self.x > max_x or self.y > max_y or self.z > max_z or self.n > max_n:
            return False
        return True
        # Wichtig, dass zu einem späteren Zeitpunkt die Werte für p1.n und p2.n eingeführt werden

    def length(self):
        """ Calculate the length of vector.
        :return: Vector length.
        """
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z
                         + self.e * self.e + self.k * self.k + self.n * self.n)
        # Vermututng: 4D Raum mit der Bewegung aller Motoren, Hinzufügen der neuen Freiheitsgrade und die Ansteuerung ihrer Motoren

    def round(self, base_x, base_y, base_z, base_e):
        """ Round values to specified base, ie 0.49 with base 0.25 will be 0.5.
        :param base_x: Base for x axis.
        :param base_y: Base for y axis.
        :param base_z: Base for z axis.
        :param base_e: Base for e axis.
        :return: New rounded object.
        """
        return Coordinates(round(self.x / base_x) * base_x,
                           round(self.y / base_y) * base_y,
                           round(self.z / base_z) * base_z,
                           round(self.e / base_e) * base_e,
                           round(self.k / base_k) * base_k,
                           round(self.n / base_n) * base_n)
        # Runden der neuen Freiheitsgrade auf eine vorher festgelegte Genauigkeit (base_...)

    def find_max(self):
        """ Find a maximum value of all values.
        :return: maximum value.
        """
        return max(self.x, self.y, self.z, self.e, self.k, self.n)

    # build in function implementation
    """ Anpassen aller Funktionen an die neuen FHG"""
    def __add__(self, other):
        return Coordinates(self.x + other.x, self.y + other.y,
                           self.z + other.z, self.e + other.e,
                           self.k + other.k, self.n + other.n)

    def __sub__(self, other):
        return Coordinates(self.x - other.x, self.y - other.y,
                           self.z - other.z, self.e - other.e,
                           self.k - other.k, self.n - other.n)

    def __mul__(self, v):
        """
        @rtype: Coordinates
        """
        return Coordinates(self.x * v, self.y * v, self.z * v, self.e * v,
                           self.k * v, self.n * v)

    def __div__(self, v):
        """
        @rtype: Coordinates
        """
        return Coordinates(self.x / v, self.y / v, self.z / v, self.e / v,
                           self.k / v, self.n / v)

    def __truediv__(self, v):
        """
        @rtype: Coordinates
        """
        return Coordinates(self.x / v, self.y / v, self.z / v, self.e / v,
                           self.k / v, self.n / v)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z \
               and self.e == other.e and self.k == other.k and self.n == other.n

    def __str__(self):
        return '(' + str(self.x) + ', ' + str(self.y) + ', ' + str(self.z) \
               + ', ' + str(self.e) + ', ' + str(self.k) + '. ' + str(self.n) + ')'

    def __abs__(self):
        return Coordinates(abs(self.x), abs(self.y), abs(self.z),  abs(self.e), abs(self.k), abs(self,n))
