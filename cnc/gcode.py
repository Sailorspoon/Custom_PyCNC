# Aenderung Max 28.11.2019
import re

from cnc.coordinates import Coordinates

# extract letter-digit pairs
g_pattern = re.compile('([A-Z])([-+]?[0-9.]+)')
# white spaces and comments start with ';' and in '()'
clean_pattern = re.compile('\s+|\(.*?\)|;.*')


class GCodeException(Exception):
    """ Exceptions while parsing gcode.
    """
    pass


class GCode(object):
    """ This object represent single line of gcode.
        Do not create it manually, use parse_line() instead.
    """
    def __init__(self, params):
        """ Create object.
        :param params: dict with gcode key-values.
        """
        self.params = params

    def has(self, arg_name):
        """
        Check if value is specified.
        :param arg_name: Value name.
        :return: boolean value.
        """
        return arg_name in self.params

    def get(self, arg_name, default=None, multiply=1.0):
        """ Get value from gcode line.
        :param arg_name: Value name.
        :param default: Default value if value doesn't exist.
        :param multiply: if value exist, multiply it by this value.
        :return: Value if exists or default otherwise.
        """
        if arg_name not in self.params:
            return default
        return float(self.params[arg_name]) * multiply

    def coordinates(self, default, multiply):
        """ Get X, Y and Z values as Coord object.
        :param default: Default values, if any of coordinates is not specified.
        :param multiply: If value exist, multiply it by this value.
        :return: Coord object.
        """
        x = self.get('X', default.x, multiply)
        y = self.get('Y', default.y, multiply)
        z = self.get('Z', default.z, multiply)
        e = self.get('E', default.e, multiply)
        q = self.get('Q', default.q, multiply)    # koFi Extruder als neuer Befehl
        n = self.get('N', default.n, multiply)    # Niederhalter als neuer Befehl
        a = self.get('A', default.a, multiply)    # Kippbewegung als neuer Befehl
        b = self.get('B', default.b, multiply)  # Rotationsbewegung als neuer Befehl

        return Coordinates(x, y, z, e, q, n, a, b)    # coordinates muss mit input angepasst werden

    def has_coordinates(self):
        """ Check if at least one of the coordinates is present.
        :return: Boolean value.
        """
        return 'X' in self.params or 'Y' in self.params or 'Z' in self.params \
               or 'E' in self.params or 'Q' in self.params or 'N' in self.params \
            or 'A' in self.params or 'B' in self.params    # neue Freiheitsgrade hinzugefuegt

    def radius(self, default, multiply):
        """ Get radius for circular interpolation(I, J, K or R).
        :param default: Default values, if any of coords is not specified.
        :param multiply: If value exist, multiply it by this value.
        :return: Coord object.
        """
        i = self.get('I', default.x, multiply)
        j = self.get('J', default.y, multiply)
        q = self.get('Q', default.z, multiply)
        return Coordinates(i, j, q, 0, 0, 0, 0, 0)
        # Anpassen der inputs wegen zusaetzlicher Freiheitsgrade (siehe Zeile 59)

    def command(self):
        """ Get value from gcode line.
        :return: String with command or None if no command specified.
        """
        if 'G' in self.params:
            return 'G' + self.params['G']
        if 'M' in self.params:
            return 'M' + self.params['M']
        return None

    @staticmethod
    def parse_line(line):
        """ Parse line.
        :param line: String with gcode line.
        :return: gcode objects.
        """
        line = line.upper()
        line = re.sub(clean_pattern, '', line)
        if len(line) == 0:
            return None
        if line[0] == '%':    # % steht in manchen G-Code flavorn fuer Startbefehl -> nicht notwendig, daher ignorieren
            return None
        m = g_pattern.findall(line)
        if not m:
            raise GCodeException('gcode not found')
        if len(''.join(["%s%s" % i for i in m])) != len(line):
            raise GCodeException('extra characters in line')
        # noinspection PyTypeChecker
        params = dict(m)
        if len(params) != len(m):
            raise GCodeException('duplicated gcode entries')
        if 'G' in params and 'M' in params:
            raise GCodeException('g and m command found')
        if 'N' in params and 'M' in params:
            raise GCodeException('n and m command found')
            # In einer Zeile darf nicht N (Niederhalterkommando) und M (eigener Befehl) stehen
        return GCode(params)
