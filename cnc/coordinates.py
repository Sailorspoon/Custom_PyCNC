# Aenderung Max 29.11.2019
from __future__ import division
import math


class Coordinates(object):
    """ This object represent machine coordinates.
        Machine supports 3 axis, so there are X, Y and Z.
    """

    def __init__(self, x, y, z, e, q, n, a, b):
        """ Create object.
        :param x: x coordinated.
        :param y: y coordinated.
        :param z: z coordinated.
        """
        self.x = round(x, 10)
        self.y = round(y, 10)
        self.z = round(z, 10)
        self.e = round(e, 10)
        self.q = round(q, 10)  # Einfuegen der anderen FHG
        self.n = round(n, 10)  # Einfuegen der anderen FHG
        self.a = round(a, 10)
        self.b = round(b, 10)

    def is_zero(self):
        """ Check if all coordinates are zero.
        :return: boolean value.
        Ergaenzt um weitere FHGe
        """
        return (self.x == 0.0 and self.y == 0.0 and self.z == 0.0
                and self.e == 0.0 and self.q == 0.0 and self.n == 0.0 and self.a == 0.0 and self.b == 0)

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
        min_n, max_n = sorted((p1.n, p2.n))  # Als Maximal/minimal ueberpruefung des Verdrehwinkels
        min_a, max_a = sorted((p1.a, p2.a))  # Nur Kippmechanismus mit hartem Anschlag erwartet
        if self.x < min_x or self.y < min_y or self.z < min_z or self.n < min_n or self.a < min_a:
            return False
        if self.x > max_x or self.y > max_y or self.z > max_z or self.n > max_n or self.a > max_a:
            return False
        return True
        # Wichtig, dass zu einem spaeteren Zeitpunkt die Werte fuer p1.n und p2.n eingefuehrt werden

    def length(self):
        """ Calculate the length of vector.
        :return: Vector length.
         Vermututng: 4D Raum mit der Bewegung aller Motoren, Hinzufuegen der neuen
        Freiheitsgrade und die Ansteuerung ihrer Motoren
        """
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z
                         + self.e * self.e + self.q * self.q + self.n * self.n + self.a * self.a + self.b * self.b)

    def round(self, base_x, base_y, base_z, base_e, base_q, base_n, base_a, base_b):
        """ Round values to specified base, ie 0.49 with base 0.25 will be 0.5.
        :param base_x: Base for x axis.
        :param base_y: Base for y axis.
        :param base_z: Base for z axis.
        :param base_e: Base for e axis.
        :param base_q: Basis fuer q Freiheitsgrad
        :param base_n: Basis fuer n Freiheitsgrad
        :param base_a: Basis fuer a Freiheitsgrad
        :param base_b: Basis fuer b Freiheitsgrad
        :return: New rounded object.
        Ergaenzt um alle FHGe
        """
        return Coordinates(round(self.x / base_x) * base_x,
                           round(self.y / base_y) * base_y,
                           round(self.z / base_z) * base_z,
                           round(self.e / base_e) * base_e,
                           round(self.q / base_q) * base_q,
                           round(self.n / base_n) * base_n,
                           round(self.a / base_a) * base_a,
                           round(self.b / base_b) * base_b)
        # Runden der neuen Freiheitsgrade auf eine vorher festgelegte Genauigkeit (base_...)

    def find_max(self):
        """ Find a maximum value of all values.
        :return: maximum value.
        """
        return max(self.x, self.y, self.z, self.e, self.q, self.n, self.a, self.b)

    # build in function implementation
    """ Anpassen aller Funktionen an die neuen FHG"""

    def __add__(self, other):
        return Coordinates(self.x + other.x, self.y + other.y,
                           self.z + other.z, self.e + other.e,
                           self.q + other.q, self.n + other.n,
                           self.a + other.a, self.b + other.b)

    def __sub__(self, other):
        return Coordinates(self.x - other.x, self.y - other.y,
                           self.z - other.z, self.e - other.e,
                           self.q - other.q, self.n - other.n,
                           self.a - other.a, self.b - other.b)

    def __mul__(self, v):
        """
        @rtype: Coordinates
        """
        return Coordinates(self.x * v, self.y * v, self.z * v, self.e * v,
                           self.q * v, self.n * v, self.a * v, self.b * v)

    def __div__(self, v):
        """
        @rtype: Coordinates
        """
        return Coordinates(self.x / v, self.y / v, self.z / v, self.e / v,
                           self.q / v, self.n / v, self.a / v, self.b / v)

    def __truediv__(self, v):
        """
        @rtype: Coordinates
        """
        return Coordinates(self.x / v, self.y / v, self.z / v, self.e / v,
                           self.q / v, self.n / v, self.a / v, self.b / v)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z \
               and self.e == other.e and self.q == other.q and self.n == other.n \
               and self.a == other.a and self.b == other.b

    def __str__(self):
        return '(' + str(self.x) + ', ' + str(self.y) + ', ' + str(self.z) \
               + ', ' + str(self.e) + ', ' + str(self.q) + '. ' + str(self.n) \
               + '. ' + str(self.a) + '. ' + str(self.b) + ')'

    def __abs__(self):
        return Coordinates(abs(self.x), abs(self.y), abs(self.z),
                           abs(self.e), abs(self.q), abs(self.n), abs(self.a), abs(self.b))
