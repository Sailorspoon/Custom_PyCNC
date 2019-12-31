from __future__ import division

import cnc.logging_config as logging_config
from cnc import hal
from cnc.pulses import *
from cnc.coordinates import *
from cnc.heater import *
from cnc.enums import *
from cnc.watchdog import *
from cnc.hal_raspberry.hal import gpio
import math

coord = None


class GMachineException(Exception):
    """ Exceptions while processing gcode line.
    """
    pass


class GMachine(object):
    """ Main object which control and keep state of whole machine: steppers,
        spindle, extruder etc
        Since there are now eight axis after adding kofi Nozzle, rotatory degree
        of freedom, tilting heating bed and spinning heating bed all functions,
        classes and methods have been extended to support these. Since an indicator
        for every change would have been to many unnecessary comments only logically
        different sections will be marked.
    """
    AUTO_FAN_ON = AUTO_FAN_ON

    def __init__(self):
        """ Initialization.
            Starting postion is at the top of the printer
        """
        # self._position = Coordinates(0.0, 0.0, TABLE_SIZE_Z_MM, 0.0, 0.0, 0.0, 0.0, 0.0)
        self._position = Coordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0) # Da Druckkopf runter wandert wenn die Motoren abgeschaltet sind
        # init variables
        self._velocity = 0
        self._local = None
        self._convertCoordinates = 0
        self._absoluteCoordinates = 0
        self._plane = None
        self._fan_state = False
        self._heaters = dict()
        self.reset()
        hal.init()
        self.watchdog = HardwareWatchdog()

    def release(self):
        """ Free all resources.
        """
        for h in self._heaters:
            self._heaters[h].stop()
        self._fan(False)
        hal.deinit()

    def reset(self):
        """ Reinitialize all program configurable things.
        """
        self._velocity = min(MAX_VELOCITY_MM_PER_MIN_X,
                             MAX_VELOCITY_MM_PER_MIN_Y,
                             MAX_VELOCITY_MM_PER_MIN_Z,
                             MAX_VELOCITY_MM_PER_MIN_E,
                             MAX_VELOCITY_MM_PER_MIN_Q,
                             MAX_VELOCITY_MM_PER_MIN_N,
                             MAX_VELOCITY_MM_PER_MIN_A,
                             MAX_VELOCITY_MM_PER_MIN_B)
        self._local = Coordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self._convertCoordinates = 1.0
        self._absoluteCoordinates = True
        self._plane = PLANE_XY

    def _fan(self, state):
        hal.fan_control(state)
        self._fan_state = state

    def _heat(self, heater, temperature, wait):
        # check if sensor is ok
        if heater == HEATER_EXTRUDER:
            measure = hal.get_extruder_temperature
            control = hal.extruder_heater_control
            coefficients = EXTRUDER_PID
        elif heater == HEATER_BED:
            measure = hal.get_bed_temperature
            control = hal.bed_heater_control
            coefficients = BED_PID
        else:
            raise GMachineException("unknown heater")
        try:
            measure()
        except (IOError, OSError):
            raise GMachineException("can not measure temperature")
        if heater in self._heaters:
            self._heaters[heater].stop()
            del self._heaters[heater]
        if temperature != 0:
            if heater == HEATER_EXTRUDER and self.AUTO_FAN_ON:
                self._fan(True)
            self._heaters[heater] = Heater(temperature, coefficients, measure,
                                           control)
            if wait:
                self._heaters[heater].wait()

    def __check_delta(self, delta):
        pos = self._position + delta
        if not pos.is_in_aabb(Coordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                              Coordinates(TABLE_SIZE_RADIUS_MM, TABLE_SIZE_RADIUS_MM,  # only calibrated axis relevant
                                          TABLE_SIZE_Z_MM, 0, 0, MAX_ROTATION_N_MM, MAX_TILT_ANGLE, 0)):
            raise GMachineException("out of effective area")

    # noinspection PyMethodMayBeStatic
    @staticmethod
    def __check_velocity(max_velocity):
        if max_velocity.x > MAX_VELOCITY_MM_PER_MIN_X \
                or max_velocity.y > MAX_VELOCITY_MM_PER_MIN_Y \
                or max_velocity.z > MAX_VELOCITY_MM_PER_MIN_Z \
                or max_velocity.e > MAX_VELOCITY_MM_PER_MIN_E \
                or max_velocity.q > MAX_VELOCITY_MM_PER_MIN_Q \
                or max_velocity.n > MAX_VELOCITY_MM_PER_MIN_N \
                or max_velocity.a > MAX_VELOCITY_MM_PER_MIN_A \
                or max_velocity.b > MAX_VELOCITY_MM_PER_MIN_B:
            raise GMachineException("out of maximum speed")

    def _move_linear(self, delta, velocity):
        delta = delta.round(1.0 / STEPPER_PULSES_PER_MM_X,
                            1.0 / STEPPER_PULSES_PER_MM_Y,
                            1.0 / STEPPER_PULSES_PER_MM_Z,
                            1.0 / STEPPER_PULSES_PER_MM_E,
                            1.0 / STEPPER_PULSES_PER_MM_Q,
                            1.0 / STEPPER_PULSES_PER_MM_N,
                            1.0 / STEPPER_PULSES_PER_MM_A,
                            1.0 / STEPPER_PULSES_PER_MM_B)
        if delta.is_zero():
            return
        self.__check_delta(delta)

        logging.info("Moving linearly {}".format(delta))
        gen = PulseGeneratorLinear(delta, velocity)
        self.__check_velocity(gen.max_velocity())
        hal.move(gen)
        # save position
        self._position = self._position + delta

    def safe_zero(self, x=True, y=True, z=True, n=True, a=True):
        """ Move head to zero position safely.
        :param x: boolean, move X axis to zero
        :param y: boolean, move Y axis to zero
        :param n: boolean, move N axis to zero position (rotatory degree of freedom)
        :param a: boolean, move A axis to zero position (tilt)
        the logic of this function has been changed - the savest position is at the top
        of the printer. So the printer will move this position no matter what the inputs of the other
        axis are. The amount of koFi, that has to be extruded corresponds with the total distance.
        As inputs there are consequently no values for z or q needed. e as FFF print head needs no
        home position anyway, hence only five parameters are needed.
        IMPORTANT
        Note that if you call G28 there is no need to add an instruction for the koFi
        nozzle in G-Code preprocessing
        """
        # In order to prevent the "out of effective area" error message (rounding errors)
        TOP_Z_LOCATION = TABLE_SIZE_Z_MM - self._position.z
        MIN_VEL = min(800, MAX_VELOCITY_MM_PER_MIN_X, MAX_VELOCITY_MM_PER_MIN_Y, MAX_VELOCITY_MM_PER_MIN_Z,
                      MAX_VELOCITY_MM_PER_MIN_Q)
        logging.debug("self_position (x): %s, self_position (y): %s, self_position (z): %s, self_position (dest):%s"
                      % (self._position.x, self._position.y, self._position.z, TOP_Z_LOCATION))
        if not x and not y:
            extrusion_amount = TOP_Z_LOCATION
            logging.debug("kofi extrusion amount (only z): %s" % extrusion_amount)
            d = Coordinates(0, 0, TOP_Z_LOCATION, 0, extrusion_amount, 0, 0, 0)
            self._move_linear(d, MIN_VEL)
        if x and not y:
            extrusion_amount = math.sqrt(self._position.x * self._position.x + TOP_Z_LOCATION * TOP_Z_LOCATION)
            logging.debug("kofi extrusion amount (x, z): %s" % extrusion_amount)
            d = Coordinates(-self._position.x, 0, TOP_Z_LOCATION, 0, extrusion_amount, 0, 0, 0)
            self._move_linear(d, MIN_VEL)
        elif y and not x:
            extrusion_amount = math.sqrt(self._position.y * self._position.y + TOP_Z_LOCATION * TOP_Z_LOCATION)
            logging.debug("kofi extrusion amount (y, z): %s" % extrusion_amount)
            d = Coordinates(0, -self._position.y, TOP_Z_LOCATION, 0, extrusion_amount, 0, 0, 0)
            self._move_linear(d, MIN_VEL)

        elif x and y:
            extrusion_amount = math.sqrt(self._position.x * self._position.x + self._position.y * self._position.y +
                                         TOP_Z_LOCATION * TOP_Z_LOCATION)
            logging.debug("kofi extrusion amount (x, y and z): %s" % extrusion_amount)
            d = Coordinates(-self._position.x, -self._position.y, TOP_Z_LOCATION, 0, extrusion_amount, 0, 0, 0)
            self._move_linear(d, min(MAX_VELOCITY_MM_PER_MIN_X,
                                     MAX_VELOCITY_MM_PER_MIN_Y, MAX_VELOCITY_MM_PER_MIN_Z, MAX_VELOCITY_MM_PER_MIN_Q))

        if n:
            d = Coordinates(0, 0, 0, 0, 0, -self._position.n, 0, 0)
            logging.debug("self_position (n): %s" % self._position.n)
            self._move_linear(d, MAX_VELOCITY_MM_PER_MIN_N)
        if a:
            d = Coordinates(0, 0, 0, 0, 0, 0, -self._position.a, 0)
            logging.debug("self_position (a): %s" % self._position.a)
            self._move_linear(d, MAX_VELOCITY_MM_PER_MIN_A)

    def position(self):
        """ Return current machine position (after the latest command)
            Note that hal might still be moving motors and in this case
            function will block until motors stops.
            This function for tests only.
            :return current position.
        """
        hal.join()
        return self._position

    def fan_state(self):
        """ Check if fan is on.
            :return True if fan is on, False otherwise.
        """
        return self._fan_state

    def __get_target_temperature(self, heater):
        if heater not in self._heaters:
            return 0
        return self._heaters[heater].target_temperature()

    def extruder_target_temperature(self):
        """ Return desired extruder temperature.
            :return Temperature in Celsius, 0 if disabled.
        """
        return self.__get_target_temperature(HEATER_EXTRUDER)

    def bed_target_temperature(self):
        """ Return desired bed temperature.
            :return Temperature in Celsius, 0 if disabled.
        """
        return self.__get_target_temperature(HEATER_BED)

    @staticmethod
    def _maximum_compatible_vel(x, y, z, e, q, n, a, b):
        """ Support function for G0 command"""
        vl = 9999999    # initialization as dummy variable
        if not (x or y or z or e or q or n or a or b):
            vl = MIN_VELOCITY_MM_PER_MIN
        if x or y or z:
            vl = min(MAX_VELOCITY_MM_PER_MIN_X, MAX_VELOCITY_MM_PER_MIN_Y, MAX_VELOCITY_MM_PER_MIN_Z,
                     MAX_VELOCITY_MM_PER_MIN_Q)
        if e and vl > MAX_VELOCITY_MM_PER_MIN_E:
            vl = MAX_VELOCITY_MM_PER_MIN_E
        if q and vl > MAX_VELOCITY_MM_PER_MIN_Q:
            vl = MAX_VELOCITY_MM_PER_MIN_Q
        if n and vl > MAX_VELOCITY_MM_PER_MIN_N:
            vl = MAX_VELOCITY_MM_PER_MIN_N
        if a and vl > MAX_VELOCITY_MM_PER_MIN_A:
            vl = MAX_VELOCITY_MM_PER_MIN_A
        if b and vl > MAX_VELOCITY_MM_PER_MIN_B:
            vl = MAX_VELOCITY_MM_PER_MIN_B
        return vl

    def do_command(self, gcode):
        """ Perform action.
        :param gcode: GCode object which represent one gcode line
        :return String if any answer require, None otherwise.
        """
        if gcode is None:
            return None
        answer = None
        logging.debug("got command " + str(gcode.params))
        # read command
        c = gcode.command()
        if c is None and gcode.has_coordinates():
            c = 'G1'
        # read parameters
        if self._absoluteCoordinates:
            global coord
            coord = gcode.coordinates(self._position - self._local,
                                      self._convertCoordinates)
            coord = coord + self._local
            delta = coord - self._position
        else:
            delta = gcode.coordinates(Coordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                                      self._convertCoordinates)
        velocity = gcode.get('F', self._velocity)
        # check parameters
        if velocity < MIN_VELOCITY_MM_PER_MIN:
            raise GMachineException("feed speed too low")
        # select command and run it
        if c == 'G0':  # rapid move
            vl = min(MAX_VELOCITY_MM_PER_MIN_X,
                     MAX_VELOCITY_MM_PER_MIN_Y,
                     MAX_VELOCITY_MM_PER_MIN_Z,
                     MAX_VELOCITY_MM_PER_MIN_E,
                     MAX_VELOCITY_MM_PER_MIN_Q,
                     MAX_VELOCITY_MM_PER_MIN_N,
                     MAX_VELOCITY_MM_PER_MIN_A,
                     MAX_VELOCITY_MM_PER_MIN_B)
            # has been changed to minimum of the maximum speed for all axis
            custom_vel = gcode.has('X'), gcode.has('Y'), gcode.has('Z'), gcode.has('E'), \
                         gcode.has('Q'), gcode.has('N'), gcode.has('A'), gcode.has('B')
            vl = self._maximum_compatible_vel(*custom_vel)
            self._move_linear(delta, vl)
        elif c == 'G1':  # linear interpolation
            self._move_linear(delta, velocity)
        elif c == 'G2':  # circular interpolation, clockwise
            raise GMachineException("G2 not implemented")
        elif c == 'G3':  # circular interpolation, counterclockwise
            raise GMachineException("G3 not implemented")
        elif c == 'G4':  # delay in s
            if not gcode.has('P'):
                raise GMachineException("P is not specified")
            pause = gcode.get('P', 0)
            if pause < 0:
                raise GMachineException("bad delay")
            hal.join()
            time.sleep(pause)
        elif c == 'G17':  # XY plane select
            self._plane = PLANE_XY
        elif c == 'G18':  # ZX plane select
            self._plane = PLANE_ZX
        elif c == 'G19':  # YZ plane select
            self._plane = PLANE_YZ
        elif c == 'G20':  # switch to inches
            self._convertCoordinates = 25.4
        elif c == 'G21':  # switch to mm
            self._convertCoordinates = 1.0
        elif c == 'G28':  # home
            # see safe_zero function in this file for explanation
            axises = gcode.has('X'), gcode.has('Y'), True, gcode.has('N'), gcode.has('A')
            if axises == (False, False, False, False, False):
                axises = True, True, True, True, True
            self.safe_zero(*axises)
            hal.join()
            if not hal.calibrate(gcode.has('X'), gcode.has('Y'), True):
            	print("calibrate failed")
                raise GMachineException("failed to calibrate")
        elif c == 'G53':  # switch to machine coords
            self._local = Coordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        elif c == 'G90':  # switch to absolute coords
            self._absoluteCoordinates = True
        elif c == 'G91':  # switch to relative coords
            self._absoluteCoordinates = False
        elif c == 'G92':  # switch to local coords
            # local coords are applicable for all axis
            # important for G-Code preprocessing
            if gcode.has_coordinates():
                self._local = self._position - gcode.coordinates(
                    Coordinates(self._position.x - self._local.x,
                                self._position.y - self._local.y,
                                self._position.z - self._local.z,
                                self._position.e - self._local.e,
                                self._position.q - self._local.q,
                                self._position.n - self._local.n,
                                self._position.a - self._local.a,
                                self._position.b - self._local.b),
                    self._convertCoordinates)
            else:
                self._local = self._position
        elif c == 'M3':  # spindle on
            raise GMachineException("M3 not implemented")
        elif c == 'M5':  # spindle off
            raise GMachineException("M5 not implemented")
        elif c == 'M2' or c == 'M30':  # program finish, reset everything.
            self.reset()
        elif c == 'M84':  # disable motors
            hal.disable_steppers()
        # extruder and bed heaters control
        elif c == 'M104' or c == 'M109' or c == 'M140' or c == 'M190':
            if c == 'M104' or c == 'M109':
                heater = HEATER_EXTRUDER
            elif c == 'M140' or c == 'M190':
                heater = HEATER_BED
            else:
                raise Exception("Unexpected heater command")
            wait = c == 'M109' or c == 'M190'
            if not gcode.has("S"):
                raise GMachineException("temperature is not specified")
            t = gcode.get('S', 0)
            if (not (not (heater == HEATER_EXTRUDER and t > EXTRUDER_MAX_TEMPERATURE) and not (
                    heater == HEATER_BED and t > BED_MAX_TEMPERATURE)) or t < MIN_TEMPERATURE) and t != 0:
                raise GMachineException("bad temperature")
            self._heat(heater, t, wait)
        elif c == 'M105':  # get temperature
            try:
                et = hal.get_extruder_temperature()
            except (IOError, OSError):
                et = None
            try:
                bt = hal.get_bed_temperature()
            except (IOError, OSError):
                bt = None
            if et is None and bt is None:
                raise GMachineException("can not measure temperature")
            answer = "E:{} B:{}".format(et, bt)
        elif c == 'M106':  # fan control
            if gcode.get('S', 1) != 0:
                self._fan(True)
            else:
                self._fan(False)
        elif c == 'M107':  # turn off fan
            self._fan(False)
        elif c == 'M111':  # enable debug
            logging_config.debug_enable()
        elif c == 'M114':  # get current position
            hal.join()
            p = self.position()
            answer = "X:{} Y:{} Z:{} E:{} Q:{} N:{} A:{} B:{}".format(p.x, p.y, p.z, p.e, p.q, p.n, p.a, p.b)
        elif c is None:  # command not specified(ie just F was passed)
            pass
        # commands below are added just for compatibility
        elif c == 'M82':  # absolute mode for extruder
            if not self._absoluteCoordinates:
                raise GMachineException("Not supported, use G90/G91")
        elif c == 'M83':  # relative mode for extruder
            if self._absoluteCoordinates:
                raise GMachineException("Not supported, use G90/G91")
        elif c == 'G93':  # in 0.01 grad Schritten richtung Endstopp, wenn Endstopp erreicht 
            print("Homing A Axis") 
            self._absoluteCoordinates = False
            self._position.a = 90.0
            while gpio.read(ENDSTOP_PIN_A) == 0:
		logging.debug("enter loop")
            	d = Coordinates(0, 0, 0, 0, 0, 0, -0.01, 0)
            	logging.debug("self_position (a): %s" % self._position.a)
            	self._move_linear(d, MAX_VELOCITY_MM_PER_MIN_A)
            print("self_position (a): %s" % self._position.a)
            self._position.a = 0.0
            print("self_position (a): %s" % self._position.a)
            self._absoluteCoordinates = True
            print("absoluteCorrdinates")
            d = Coordinates(0, 0, 0, 0, 0, 0, 45, 0)
            self._move_linear(d, MAX_VELOCITY_MM_PER_MIN_A)
	    print("ende")

        else:
            raise GMachineException("unknown command")
        # save parameters on success
        self._velocity = velocity
        logging.debug("position {}".format(self._position))
        return answer
