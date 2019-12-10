# coding=utf-8

from __future__ import division
import logging

from cnc.config import *
from cnc.coordinates import *
from cnc.enums import *
from cnc.gcode import *

SECONDS_IN_MINUTE = 60.0


class PulseGenerator(object):
    """ Stepper motors pulses generator.
        It generates time for each pulses for specified path as accelerated
        movement for specified velocity, then moves linearly and then braking
        with the same acceleration.
        Internally this class treat movement as uniform movement and then
        translate timings to accelerated movements. To do so, it base on
        formulas for distance of uniform movement and accelerated move.
            S = V * Ta = a * Tu^2 / 2
        where Ta - time for accelerated and Tu for uniform movement.
        Velocity will never be more then Vmax - maximum velocity of all axises.
        At the point of maximum velocity we change accelerated movement to
        uniform, so we can translate time for accelerated movement with this
        formula:
            Ta(Tu) = a * Tu^2 / Vmax / 2
        Now we need just to calculate how much time will accelerate and
        brake will take and recalculate time for them. Linear part will be as
        is. Since maximum velocity and acceleration is always the same, there
        is the ACCELERATION_FACTOR_PER_SEC variable.
        In the same way circular or other interpolation can be implemented
        based this class.
    """
    AUTO_VELOCITY_ADJUSTMENT = AUTO_VELOCITY_ADJUSTMENT

    def __init__(self, delta):
        """ Create object. Do not create directly this object, inherit this
            class and implement interpolation function and related methods.
            All child have to call this method ( super().__init__() ).
            :param delta: overall movement delta in mm, uses for debug purpose.
        """
        self._iteration_x = 0
        self._iteration_y = 0
        self._iteration_z = 0
        self._iteration_e = 0
        self._iteration_q = 0
        self._iteration_n = 0
        self._iteration_a = 0
        self._iteration_b = 0
        self._iteration_direction = None
        self._acceleration_time_s = 0.0
        self._linear_time_s = 0.0
        self._2Vmax_per_a = 0.0
        self._delta = delta

    def _adjust_velocity(self, velocity_mm_sec, MAX_INDICATOR):
        """ Automatically decrease velocity to all axises proportionally if
        velocity for one or more axises is more then maximum velocity for axis.
        :param velocity_mm_sec: input velocity.
        :return: adjusted(decreased if needed) velocity.
        """
        if not self.AUTO_VELOCITY_ADJUSTMENT:
            return velocity_mm_sec
        var_const = 1.0
        if velocity_mm_sec * SECONDS_IN_MINUTE > MAX_INDICATOR:
            var_const = min(var_const, MAX_INDICATOR
                            / velocity_mm_sec / SECONDS_IN_MINUTE)
        if var_const != 1.0:
            logging.warning("Out of speed, multiply velocity by {}".format(var_const))
        return velocity_mm_sec * var_const

    def _get_movement_parameters(self):
        """ Get parameters for interpolation. This method have to be
            reimplemented in parent classes and should calculate 3 parameters.
        :return: Tuple of three values:
                acceleration_time_s: time for accelerating and breaking motors
                                     during movement
                linear_time_s: time for uniform movement, it is total movement
                               time minus acceleration and braking time
                max_axis_velocity_mm_per_sec: maximum axis velocity of all
                                              axises during movement. Even if
                                              whole movement is accelerated,
                                              this value should be calculated
                                              as top velocity.
        """
        raise NotImplemented

    def _interpolation_function(self, ix, iy, iz, ie, iq, i_n, ia, ib):
        """ Get function for interpolation path. This function should returned
            values as it is uniform movement. There is only one trick, function
            must be expressed in terms of position, i.e. t = S / V for linear,
            where S - distance would be increment on motor minimum step.
        :param ix: number of pulse for X axis.
        :param iy: number of pulse for Y axis.
        :param iz: number of pulse for Z axis.
        :param ie: number of pulse for E axis.
        :param iq: number of pulses for koFi extruder
        :param i_n: number of pulses for rotatory degree of freedom
        :param ia: number of pulses for tilting bed
        :param ib: number of pulses for rotary degree of freedom
        :return: Two tuples. First is tuple is directions for each axis,
                 positive means forward, negative means reverse. Second is
                 tuple of times for each axis in us or None if movement for
                 axis is finished.
        """
        raise NotImplemented

    def __iter__(self):
        """ Get iterator.
        :return: iterable object.
        """
        (self._acceleration_time_s, self._linear_time_s,
         max_axis_velocity_mm_per_sec) = self._get_movement_parameters()
        # helper variable
        self._2Vmax_per_a = (2.0 * max_axis_velocity_mm_per_sec.find_max()
                             / STEPPER_MAX_ACCELERATION_MM_PER_S2)
        self._iteration_x = 0
        self._iteration_y = 0
        self._iteration_z = 0
        self._iteration_e = 0
        self._iteration_q = 0
        self._iteration_n = 0
        self._iteration_a = 0
        self._iteration_b = 0
        self._iteration_direction = None
        logging.debug(' '.join("%s: %s\n" % i for i in vars(self).items()))
        return self

    def _to_accelerated_time(self, pt_s):
        """ Internal function to translate uniform movement time to time for
            accelerated movement.
        :param pt_s: pseudo time of uniform movement.
        :return: time for each axis or None if movement for axis is finished.
        """
        # calculate acceleration
        # S = Tpseudo * Vmax = a * t^2 / 2

        # logging.debug("pseudo_time: %s, 2Vmax_per_a: %s" % (pt_s, self._2Vmax_per_a))

        t = math.sqrt(pt_s * self._2Vmax_per_a)
        if t <= self._acceleration_time_s:
            return t

        # linear
        # pseudo acceleration time Tpseudo = t^2 / ACCELERATION_FACTOR_PER_SEC
        t = self._acceleration_time_s + pt_s - (self._acceleration_time_s ** 2
                                                / self._2Vmax_per_a)
        # pseudo breaking time
        bt = t - self._acceleration_time_s - self._linear_time_s
        if bt <= 0:
            return t

        # braking
        # Vmax * Tpseudo = Vlinear * t - a * t^2 / 2
        # V on start braking is Vlinear = Taccel * a = Tbreaking * a
        # Vmax * Tpseudo = Tbreaking * a * t - a * t^2 / 2
        d = self._acceleration_time_s ** 2 - self._2Vmax_per_a * bt
        if d > 0:
            d = math.sqrt(d)
        else:
            d = 0
        return 2.0 * self._acceleration_time_s + self._linear_time_s - d

    def __next__(self):
        # for python3
        return self.next()

    def next(self):
        """ Iterate pulses.
        :return: Tuple of nine values:
                    - first is boolean value, if it is True, motors direction
                        should be changed and next pulse should performed in
                        this direction.
                    - values for all machine axises. For direction update,
                        positive values means forward movement, negative value
                        means reverse movement. For normal pulse, values are
                        represent time for the next pulse in microseconds.
                 This iteration strictly guarantees that next pulses time will
                 not be earlier in time then current. If there is no pulses
                 left StopIteration will be raised.
                 Update: Added new axis
        """
        direction, (tx, ty, tz, te, tq, tn, ta, tb) = \
            self._interpolation_function(self._iteration_x, self._iteration_y,
                                         self._iteration_z, self._iteration_e,
                                         self._iteration_q, self._iteration_n,
                                         self._iteration_a, self._iteration_b)
        # check if direction update:
        if direction != self._iteration_direction:
            self._iteration_direction = direction
            dir_x, dir_y, dir_z, dir_e, dir_q, dir_n, dir_a, dir_b = direction
            if STEPPER_INVERTED_X:
                dir_x = -dir_x
            if STEPPER_INVERTED_Y:
                dir_y = -dir_y
            if STEPPER_INVERTED_Z:
                dir_z = -dir_z
            if STEPPER_INVERTED_E:
                dir_e = -dir_e
            if STEPPER_INVERTED_Q:
                dir_q = -dir_q
            if STEPPER_INVERTED_N:
                dir_n = -dir_n
            if STEPPER_INVERTED_A:
                dir_a = -dir_a
            if STEPPER_INVERTED_B:
                dir_b = -dir_b
            return True, dir_x, dir_y, dir_z, dir_e, dir_q, dir_n, dir_a, dir_b
        # check condition to stop
        if tx is None and ty is None and tz is None and te is None and tq is None and tn is None and \
                ta is None and tb is None:
            raise StopIteration

        # convert to real time
        m = None
        for i in (tx, ty, tz, te, tq, tn, ta, tb):  # Adding time for each degree of freedom
            if i is not None and (m is None or i < m):
                m = i
        am = self._to_accelerated_time(m)
        # sort pulses in time
        if tx is not None:
            if tx > m:
                tx = None
            else:
                tx = am
                self._iteration_x += 1
        if ty is not None:
            if ty > m:
                ty = None
            else:
                ty = am
                self._iteration_y += 1
        if tz is not None:
            if tz > m:
                tz = None
            else:
                tz = am
                self._iteration_z += 1
        if te is not None:
            if te > m:
                te = None
            else:
                te = am
                self._iteration_e += 1
        if tq is not None:
            if tq > m:
                tq = None
            else:
                tq = am
                self._iteration_q += 1
        if tn is not None:
            if tn > m:
                tn = None
            else:
                tn = am
                self._iteration_n += 1
        if ta is not None:
            if ta > m:
                ta = None
            else:
                ta = am
                self._iteration_a += 1
        if tb is not None:
            if tb > m:
                tb = None
            else:
                tb = am
                self._iteration_b += 1

        return False, tx, ty, tz, te, tq, tn, ta, tb

    def total_time_s(self):
        """ Get total time for movement.
        :return: time in seconds.
        """
        acceleration_time_s, linear_time_s, _ = self._get_movement_parameters()
        return acceleration_time_s * 2.0 + linear_time_s

    def delta(self):
        """ Get overall movement distance.
        :return: Movement distance for each axis in millimeters.
        """
        return self._delta

    def max_velocity(self):
        """ Get max velocity for each axis.
        :return: Vector with max velocity (in mm per min) for each axis.
        """
        _, _, v = self._get_movement_parameters()
        return v * SECONDS_IN_MINUTE


class PulseGeneratorLinear(PulseGenerator):
    def __init__(self, delta_mm, velocity_mm_per_min):
        """ Create pulse generator for linear interpolation.
        :param delta_mm: movement distance of each axis.
        :param velocity_mm_per_min: desired velocity.
        """
        super(PulseGeneratorLinear, self).__init__(delta_mm)

        distance_mm = abs(delta_mm)  # type: Coordinates

        # saving the old carriage_height
        height_carriage_mm_old['a'] = height_carriage_mm['a']
        height_carriage_mm_old['b'] = height_carriage_mm['b']
        height_carriage_mm_old['c'] = height_carriage_mm['c']

        # tu is the position of the Tool, independently of time and completed steps.
        # addition of the position differences (delta)
        tu['x'] += delta_mm.x
        tu['y'] += delta_mm.y
        tu['z'] += delta_mm.z

        # height_carriage_mm is a function of distance_pivot_carriage_mm
        # height carriage_mm calculated with pythagoras of distance_pivot_carriage (calculated wit tx, ty, tz)
        # and the arm lenght. This is added to the height.
        # x-axes and carriage(a) are in alignment.
        # Carriage(b) in 120 degrees to x-axis.
        # carriage(c) in 240 degrees to x-axis.
        # same formular as "start values of the carriage high" in config.py but tx, ty, tz not 0
        # 0 equals the distance of the carriage to the y-axis
        height_carriage_mm['a'] = tu['z'] + height_pivot_tool_mm \
                                  + math.sqrt(length_arm['a'] ** 2
                                              - ((radius_heatbed - (tu['x'] + distance_pivot_tool_mm)) ** 2
                                                 + (0 - tu['y']) ** 2))
        height_carriage_mm['b'] = tu['z'] + height_pivot_tool_mm \
                                  + math.sqrt(length_arm['b'] ** 2 - ((radius_heatbed * math.cos(math.radians(120))
                                                                       - (tu['x'] + distance_pivot_tool_mm *
                                                                          math.cos(math.radians(120)))) ** 2
                                                                      + (radius_heatbed * math.sin(math.radians(120))
                                                                         - (tu['y'] + distance_pivot_tool_mm
                                                                            * math.sin(math.radians(120)))) ** 2))
        height_carriage_mm['c'] = tu['z'] + height_pivot_tool_mm \
                                  + math.sqrt(length_arm['c'] ** 2 - ((radius_heatbed * math.cos(math.radians(240))
                                                                       - (tu['x'] + distance_pivot_tool_mm *
                                                                          math.cos(math.radians(240)))) ** 2
                                                                      + (radius_heatbed * math.sin(math.radians(240))
                                                                         - (tu['y'] + distance_pivot_tool_mm *
                                                                            math.sin(math.radians(240)))) ** 2))

        # driving distance is new position - old position of the carriage
        distance_mm.x = height_carriage_mm['a'] - height_carriage_mm_old['a']
        distance_mm.y = height_carriage_mm['b'] - height_carriage_mm_old['b']
        distance_mm.z = height_carriage_mm['c'] - height_carriage_mm_old['c']

        # velocity of each axis, calculated with pythagoras
        velocity_carriage_mm_per_min = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)
        velocity_mm_per_min_axis = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)

        if delta_mm.x == 0 and delta_mm.y == 0 and delta_mm.z == 0:
            velocity_mm_per_min_axis.x = 0
            velocity_mm_per_min_axis.y = 0
            velocity_mm_per_min_axis.z = 0
        else:
            velocity_mm_per_min_axis.x = velocity_mm_per_min * \
                                         (delta_mm.x / math.sqrt(delta_mm.x ** 2 + delta_mm.y ** 2 + delta_mm.z ** 2))

            velocity_mm_per_min_axis.y = velocity_mm_per_min * \
                                         (delta_mm.y / math.sqrt(delta_mm.x ** 2 + delta_mm.y ** 2 + delta_mm.z ** 2))

            velocity_mm_per_min_axis.z = velocity_mm_per_min * \
                                         (delta_mm.z / math.sqrt(delta_mm.x ** 2 + delta_mm.y ** 2 + delta_mm.z ** 2))

        # coupling of head velocity with koFi extrusion rate
        if delta_mm.x or delta_mm.y or delta_mm.z != 0:
            # check, if absolut velocity of head movement exceeds maximum speed of koFi extrusion rate
            # decrease by factor calculated with function _adjust_velocity
            absolute_vel_head_mm_per_s = math.sqrt(velocity_mm_per_min_axis.x ** 2 + velocity_mm_per_min_axis.y ** 2 +
                                                   velocity_mm_per_min_axis.z ** 2) / SECONDS_IN_MINUTE
            absolute_vel_head_adj_mm_per_s = self._adjust_velocity(absolute_vel_head_mm_per_s, MAX_VELOCITY_MM_PER_MIN_Q)
            # factor may have rounding errors that cause a velocity above the maximum velocity of Q (koFi)
            factor = absolute_vel_head_adj_mm_per_s / absolute_vel_head_mm_per_s

            if factor < 1:
                velocity_mm_per_min_axis.x = velocity_mm_per_min_axis.x * factor  # prevent rounding errors
                velocity_mm_per_min_axis.y = velocity_mm_per_min_axis.y * factor
                velocity_mm_per_min_axis.z = velocity_mm_per_min_axis.z * factor
                logging.debug("Absolute head speed exceeds maximum koFi extrusion rate, "
                              "decrease by factor of {}".format(factor))

        # velocity of the carriages from derivation of Carriage movement ( d/dt height_carriage_mm)
        velocity_carriage_mm_per_min.x = (velocity_mm_per_min_axis.x * (
                radius_heatbed - distance_pivot_tool_mm - tu['x']) -
                                          tu['y'] * velocity_mm_per_min_axis.y) / \
                                         (math.sqrt(- (radius_heatbed - distance_pivot_tool_mm - tu['x']) ** 2 +
                                                    (length_arm['a']) ** 2 - (
                                                        tu['y']) ** 2)) + velocity_mm_per_min_axis.z
        velocity_carriage_mm_per_min.y = velocity_mm_per_min_axis.z + \
                                         (velocity_mm_per_min_axis.x *
                                          (- radius_heatbed / 2 + distance_pivot_tool_mm / 2 - tu['x']) +
                                          velocity_mm_per_min_axis.y * (math.sqrt(3) * radius_heatbed / 2 -
                                                                        (math.sqrt(3) * distance_pivot_tool_mm) / 2
                                                                        - tu['y'])) \
                                         / (math.sqrt(- (- radius_heatbed / 2 + distance_pivot_tool_mm / 2 - tu['x'])
                                                        ** 2 - (math.sqrt(3) * radius_heatbed / 2 - math.sqrt(3)
                                                                * distance_pivot_tool_mm / 2 - tu['y'])
                                                      ** 2 + length_arm['b'] ** 2))
        velocity_carriage_mm_per_min.z = velocity_mm_per_min_axis.z + \
                                         (velocity_mm_per_min_axis.x *
                                          (- radius_heatbed / 2 + distance_pivot_tool_mm / 2 - tu['x']) +
                                          velocity_mm_per_min_axis.y * (-math.sqrt(3) * radius_heatbed / 2 +
                                                                        (math.sqrt(3) * distance_pivot_tool_mm) / 2
                                                                        - tu['y'])) \
                                         / (math.sqrt(- (- radius_heatbed / 2 + distance_pivot_tool_mm / 2 - tu['x'])
                                                        ** 2 - (-math.sqrt(3) * radius_heatbed / 2 + math.sqrt(3)
                                                                * distance_pivot_tool_mm / 2 - tu['y'])
                                                      ** 2 + length_arm['c'] ** 2))

        distance_total_mm = distance_mm.length()

        self.max_velocity_mm_per_sec = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)
        self.max_velocity_mm_per_sec.x = self._adjust_velocity(abs(velocity_carriage_mm_per_min.x) / SECONDS_IN_MINUTE,
                                                               MAX_VELOCITY_MM_PER_MIN_X)
        self.max_velocity_mm_per_sec.y = self._adjust_velocity(abs(velocity_carriage_mm_per_min.y) / SECONDS_IN_MINUTE,
                                                               MAX_VELOCITY_MM_PER_MIN_Y)
        self.max_velocity_mm_per_sec.z = self._adjust_velocity(abs(velocity_carriage_mm_per_min.z) / SECONDS_IN_MINUTE,
                                                               MAX_VELOCITY_MM_PER_MIN_Z)
        # from other script - has to be used for other axis
        self.max_velocity_mm_per_sec.e = self._adjust_velocity(distance_mm.e * (
                velocity_mm_per_min / SECONDS_IN_MINUTE / distance_total_mm), MAX_VELOCITY_MM_PER_MIN_E)
        self.max_velocity_mm_per_sec.q = self._adjust_velocity(distance_mm.q * (
                velocity_mm_per_min / SECONDS_IN_MINUTE / distance_total_mm), MAX_VELOCITY_MM_PER_MIN_Q)

        self.max_velocity_mm_per_sec.n = self._adjust_velocity(distance_mm.n * (
                velocity_mm_per_min / SECONDS_IN_MINUTE / distance_total_mm), MAX_VELOCITY_MM_PER_MIN_N)
        self.max_velocity_mm_per_sec.a = self._adjust_velocity(distance_mm.a * (
                velocity_mm_per_min / SECONDS_IN_MINUTE / distance_total_mm), MAX_VELOCITY_MM_PER_MIN_A)
        self.max_velocity_mm_per_sec.b = self._adjust_velocity(distance_mm.b * (
                velocity_mm_per_min / SECONDS_IN_MINUTE / distance_total_mm), MAX_VELOCITY_MM_PER_MIN_B)

        # acceleration time
        self.acceleration_time_s = (self.max_velocity_mm_per_sec.find_max()
                                    / STEPPER_MAX_ACCELERATION_MM_PER_S2)
        # check if there is enough space to accelerate and brake, adjust time
        # S = a * t^2 / 2
        if STEPPER_MAX_ACCELERATION_MM_PER_S2 * self.acceleration_time_s ** 2 \
                > distance_total_mm:
            self.acceleration_time_s = \
                math.sqrt(distance_total_mm
                          / STEPPER_MAX_ACCELERATION_MM_PER_S2)
            self.linear_time_s = 0.0
            # V = a * t -> V = 2 * S / t, take half of total distance for
            # acceleration and braking
            self.max_velocity_mm_per_sec = (distance_mm
                                            / self.acceleration_time_s)
        else:
            # calculate linear time
            linear_distance_mm = distance_total_mm \
                                 - self.acceleration_time_s ** 2 \
                                 * STEPPER_MAX_ACCELERATION_MM_PER_S2
            self.linear_time_s = (linear_distance_mm
                                  / self.max_velocity_mm_per_sec.length())
        # Abs of total Pulses
        # get direction from distance_mm
        self._total_pulses_x = round(abs(distance_mm.x * STEPPER_PULSES_PER_MM_X))
        self._total_pulses_y = round(abs(distance_mm.y * STEPPER_PULSES_PER_MM_Y))
        self._total_pulses_z = round(abs(distance_mm.z * STEPPER_PULSES_PER_MM_Z))
        self._total_pulses_e = round(abs(distance_mm.e * STEPPER_PULSES_PER_MM_E))
        self._total_pulses_q = round(abs(distance_mm.q * STEPPER_PULSES_PER_MM_Q))
        self._total_pulses_n = round(abs(distance_mm.n * STEPPER_PULSES_PER_MM_N))
        self._total_pulses_a = round(abs(distance_mm.a * STEPPER_PULSES_PER_MM_A))
        self._total_pulses_b = round(abs(distance_mm.b * STEPPER_PULSES_PER_MM_B))
        self._direction = (math.copysign(1, distance_mm.x),
                           math.copysign(1, distance_mm.y),
                           math.copysign(1, distance_mm.z),
                           math.copysign(1, delta_mm.e),
                           math.copysign(1, delta_mm.q),
                           math.copysign(1, delta_mm.n),
                           math.copysign(1, delta_mm.a),
                           math.copysign(1, delta_mm.b))

    def _get_movement_parameters(self):
        """ Return movement parameters, see super class for details.
        """
        return (self.acceleration_time_s,
                self.linear_time_s,
                self.max_velocity_mm_per_sec)

    @staticmethod
    def __linear(i, pulses_per_mm, total_pulses, velocity_mm_per_sec):
        """ Helper function for linear movement.
        """
        # check if need to calculate for this axis
        if total_pulses == 0.0 or i >= total_pulses:
            return None
        # Linear movement, S = V * t -> t = S / V
        return i / pulses_per_mm / velocity_mm_per_sec

    def _interpolation_function(self, ix, iy, iz, ie, iq, i_n, ia, ib):
        """ Calculate interpolation values for linear movement, see super class
            for details.
        """
        # logging.debug("ix: %s, total_pulses_x: %s, max_velocity_mm_per_sec.x: %s" % (ix, self._total_pulses_x,
        #                                                                              self.max_velocity_mm_per_sec.x))
        t_x = self.__linear(ix, STEPPER_PULSES_PER_MM_X, self._total_pulses_x,
                            self.max_velocity_mm_per_sec.x)
        t_y = self.__linear(iy, STEPPER_PULSES_PER_MM_Y, self._total_pulses_y,
                            self.max_velocity_mm_per_sec.y)
        t_z = self.__linear(iz, STEPPER_PULSES_PER_MM_Z, self._total_pulses_z,
                            self.max_velocity_mm_per_sec.z)
        t_e = self.__linear(ie, STEPPER_PULSES_PER_MM_E, self._total_pulses_e,
                            self.max_velocity_mm_per_sec.e)
        t_q = self.__linear(iq, STEPPER_PULSES_PER_MM_Q, self._total_pulses_q,
                            self.max_velocity_mm_per_sec.q)
        t_n = self.__linear(i_n, STEPPER_PULSES_PER_MM_N, self._total_pulses_n,
                            self.max_velocity_mm_per_sec.n)
        t_a = self.__linear(ia, STEPPER_PULSES_PER_MM_A, self._total_pulses_a,
                            self.max_velocity_mm_per_sec.a)
        t_b = self.__linear(ib, STEPPER_PULSES_PER_MM_B, self._total_pulses_b,
                            self.max_velocity_mm_per_sec.b)
        return self._direction, (t_x, t_y, t_z, t_e, t_q, t_n, t_a, t_b)


class PulseGeneratorCircular(PulseGenerator):
    def __init__(self, delta, radius, plane, direction, velocity):
        """ Create pulse generator for circular interpolation.
            Position calculates based on formulas:
            R^2 = x^2 + y^2
            x = R * sin(phi)
            y = R * cos(phi)
            phi = omega * t,   2 * pi / omega = 2 * pi * R / V
            phi = V * t / R
            omega is angular_velocity.
            so t = V / R * phi
            phi can be calculated based on steps position.
            Each axis can calculate circle phi base on iteration number, the
            only one difference, that there is four quarters of circle and
            signs for movement and solving expressions are different. So
            we use additional variables to control it.
            :param delta: finish position delta from the beginning, must be on
                          circle on specified plane. Zero means full circle.
            :param radius: vector to center of circle.
            :param plane: plane to interpolate.
            :param direction: clockwise or counterclockwise.
            :param velocity: velocity in mm per min.
            IMPORTANT: Since the circular PulseGenerator is not used when working
            with 3D printers  (no G2 or G3 instructions from any existing slicer as of today)
            this whole section has not been checked for applicability and needs to be overhauled!
        """
        super(PulseGeneratorCircular, self).__init__(delta)
        self._plane = plane
        self._direction = direction
        velocity = velocity / SECONDS_IN_MINUTE
        # Get circle start point and end point.
        if self._plane == PLANE_XY:
            sa = -radius.x
            sb = -radius.y
            ea = sa + delta.x
            eb = sb + delta.y
            apm = STEPPER_PULSES_PER_MM_X
            bpm = STEPPER_PULSES_PER_MM_Y
        elif self._plane == PLANE_YZ:
            sa = -radius.y
            sb = -radius.z
            ea = sa + delta.y
            eb = sb + delta.z
            apm = STEPPER_PULSES_PER_MM_Y
            bpm = STEPPER_PULSES_PER_MM_Z
        elif self._plane == PLANE_ZX:
            sa = -radius.z
            sb = -radius.x
            ea = sa + delta.z
            eb = sb + delta.x
            apm = STEPPER_PULSES_PER_MM_Z
            bpm = STEPPER_PULSES_PER_MM_X
        else:
            raise ValueError("Unknown plane")
        # adjust radius to fit into axises step.
        radius = (round(math.sqrt(sa * sa + sb * sb) * min(apm, bpm))
                  / min(apm, bpm))
        radius_ac = (round(math.sqrt(sa * sa + sb * sb) * apm) / apm)
        radius_bc = (round(math.sqrt(sa * sa + sb * sb) * bpm) / bpm)
        self._radius_a2 = radius_ac * radius_ac
        self._radius_b2 = radius_bc * radius_bc
        self._radius_ac_pulses = int(radius * apm)
        self._radius_bc_pulses = int(radius * bpm)
        self._start_ac_pulses = int(sa * apm)
        self._start_bc_pulses = int(sb * bpm)
        assert (round(math.sqrt(ea * ea + eb * eb) * min(apm, bpm))
                / min(apm, bpm) == radius), "Wrong end point"

        # Calculate angles and directions.
        start_angle = self.__angle(sa, sb)
        end_angle = self.__angle(ea, eb)
        delta_angle = end_angle - start_angle
        if delta_angle < 0 or (delta_angle == 0 and direction == CW):
            delta_angle += 2 * math.pi
        if direction == CCW:
            delta_angle -= 2 * math.pi
        if direction == CW:
            if start_angle >= math.pi:
                self._dir_bc = 1
            else:
                self._dir_bc = -1
            if math.pi / 2 <= start_angle < 3 * math.pi / 2:
                self._dir_ac = -1
            else:
                self._dir_ac = 1
        elif direction == CCW:
            if 0.0 < start_angle <= math.pi:
                self._dir_bc = 1
            else:
                self._dir_bc = -1
            if start_angle <= math.pi / 2 or start_angle > 3 * math.pi / 2:
                self._dir_ac = -1
            else:
                self._dir_ac = 1
        self._side_ac = (self._start_bc_pulses < 0
                         or (self._start_bc_pulses == 0 and self._dir_bc < 0))
        self._side_bc = (self._start_ac_pulses < 0
                         or (self._start_ac_pulses == 0 and self._dir_ac < 0))
        self._start_angle = start_angle
        logging.debug("start angle {}, end angle {}, delta {}".format(
            start_angle * 180.0 / math.pi,
            end_angle * 180.0 / math.pi,
            delta_angle * 180.0 / math.pi))
        delta_angle = abs(delta_angle)
        self._delta_angle = delta_angle

        # calculate values for interpolation.

        # calculate travel distance for axis in circular move.
        self._iterations_ac = 0
        self._iterations_bc = 0
        end_angle_m = end_angle
        if start_angle >= end_angle:
            end_angle_m += 2 * math.pi
        quarter_start = int(start_angle / (math.pi / 2.0))
        quarter_end = int(end_angle_m / (math.pi / 2.0))
        if quarter_end - quarter_start >= 4:
            self._iterations_ac = 4 * round(radius * apm)
            self._iterations_bc = 4 * round(radius * bpm)
        else:
            if quarter_start == quarter_end:
                self._iterations_ac = round(abs(sa - ea) * apm)
                self._iterations_bc = round(abs(sb - eb) * bpm)
            else:
                for r in range(quarter_start, quarter_end + 1):
                    i = r
                    if i >= 4:
                        i -= 4
                    if r == quarter_start:
                        if i == 0 or i == 2:
                            self._iterations_ac += round(radius * apm) \
                                                   - round(abs(sa) * apm)
                        else:
                            self._iterations_ac += round(abs(sa) * apm)
                        if i == 1 or i == 3:
                            self._iterations_bc += round(radius * bpm) \
                                                   - round(abs(sb) * bpm)
                        else:
                            self._iterations_bc += round(abs(sb) * bpm)
                    elif r == quarter_end:
                        if i == 0 or i == 2:
                            self._iterations_ac += round(abs(ea) * apm)
                        else:
                            self._iterations_ac += round(radius * apm) \
                                                   - round(abs(ea) * apm)
                        if i == 1 or i == 3:
                            self._iterations_bc += round(abs(eb) * bpm)
                        else:
                            self._iterations_bc += round(radius * bpm) \
                                                   - round(abs(eb) * bpm)
                    else:
                        self._iterations_ac += round(radius * apm)
                        self._iterations_bc += round(radius * bpm)
            if direction == CCW:
                self._iterations_ac = (4 * round(radius * apm)
                                       - self._iterations_ac)
                self._iterations_bc = (4 * round(radius * bpm)
                                       - self._iterations_bc)

        arc = delta_angle * radius
        e2 = delta.e * delta.e
        if self._plane == PLANE_XY:
            self._iterations_3rd = abs(delta.z) * STEPPER_PULSES_PER_MM_Z
            full_length = math.sqrt(arc * arc + delta.z * delta.z + e2)
            if full_length == 0:
                self._velocity_3rd = velocity
            else:
                self._velocity_3rd = abs(delta.z) / full_length * velocity
            self._third_dir = math.copysign(1, delta.z)
        elif self._plane == PLANE_YZ:
            self._iterations_3rd = abs(delta.x) * STEPPER_PULSES_PER_MM_X
            full_length = math.sqrt(arc * arc + delta.x * delta.x + e2)
            if full_length == 0:
                self._velocity_3rd = velocity
            else:
                self._velocity_3rd = abs(delta.x) / full_length * velocity
            self._third_dir = math.copysign(1, delta.x)
        elif self._plane == PLANE_ZX:
            self._iterations_3rd = abs(delta.y) * STEPPER_PULSES_PER_MM_Y
            full_length = math.sqrt(arc * arc + delta.y * delta.y + e2)
            if full_length == 0:
                self._velocity_3rd = velocity
            else:
                self._velocity_3rd = abs(delta.y) / full_length * velocity
            self._third_dir = math.copysign(1, delta.y)
        else:
            raise ValueError("Unknown plane")
        self._iterations_e = abs(delta.e) * STEPPER_PULSES_PER_MM_E
        # Velocity splits with corresponding distance.
        if full_length == 0:
            circular_velocity = velocity
            self._e_velocity = velocity
        else:
            circular_velocity = arc / full_length * velocity
            self._e_velocity = abs(delta.e) / full_length * velocity
        if self._plane == PLANE_XY:
            self.max_velocity_mm_per_sec = self._adjust_velocity(
                Coordinates(circular_velocity, circular_velocity,
                            self._velocity_3rd, self._e_velocity, 0, 0, 0, 0), MAX_VELOCITY_MM_PER_MIN_X)
            circular_velocity = min(self.max_velocity_mm_per_sec.x,
                                    self.max_velocity_mm_per_sec.y)
            self._velocity_3rd = self.max_velocity_mm_per_sec.z
        elif self._plane == PLANE_YZ:
            self.max_velocity_mm_per_sec = self._adjust_velocity(
                Coordinates(self._velocity_3rd, circular_velocity,
                            circular_velocity, self._e_velocity, 0, 0, 0, 0), MAX_VELOCITY_MM_PER_MIN_X)
            circular_velocity = min(self.max_velocity_mm_per_sec.y,
                                    self.max_velocity_mm_per_sec.z)
            self._velocity_3rd = self.max_velocity_mm_per_sec.x
        elif self._plane == PLANE_ZX:
            self.max_velocity_mm_per_sec = self._adjust_velocity(
                Coordinates(circular_velocity, self._velocity_3rd,
                            circular_velocity, self._e_velocity, 0, 0, 0, 0), MAX_VELOCITY_MM_PER_MIN_X)
            circular_velocity = min(self.max_velocity_mm_per_sec.z,
                                    self.max_velocity_mm_per_sec.x)
            self._velocity_3rd = self.max_velocity_mm_per_sec.y
        self._e_velocity = self.max_velocity_mm_per_sec.e
        self._r_div_v = radius / circular_velocity
        self._e_dir = math.copysign(1, delta.e)
        self.acceleration_time_s = (self.max_velocity_mm_per_sec.find_max()
                                    / STEPPER_MAX_ACCELERATION_MM_PER_S2)
        if full_length == 0:
            self.linear_time_s = 0.0
            self.max_velocity_mm_per_sec = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)
        elif STEPPER_MAX_ACCELERATION_MM_PER_S2 * self.acceleration_time_s \
                ** 2 > full_length:
            self.acceleration_time_s = \
                math.sqrt(full_length / STEPPER_MAX_ACCELERATION_MM_PER_S2)
            self.linear_time_s = 0.0
            v = full_length / self.acceleration_time_s
            if self.max_velocity_mm_per_sec.x > 0.0:
                self.max_velocity_mm_per_sec.x = v
            if self.max_velocity_mm_per_sec.y > 0.0:
                self.max_velocity_mm_per_sec.y = v
            if self.max_velocity_mm_per_sec.z > 0.0:
                self.max_velocity_mm_per_sec.z = v
            if self.max_velocity_mm_per_sec.e > 0.0:
                self.max_velocity_mm_per_sec.e = v
        else:
            linear_distance_mm = full_length - self.acceleration_time_s ** 2 \
                                 * STEPPER_MAX_ACCELERATION_MM_PER_S2
            self.linear_time_s = linear_distance_mm / math.sqrt(
                circular_velocity ** 2 + self._velocity_3rd ** 2
                + self._e_velocity ** 2)

    @staticmethod
    def __angle(ac, bc):
        # Calculate angle of entry point (a, b) of circle with center in (0,0)
        angle = math.acos(bc / math.sqrt(ac * ac + bc * bc))
        if ac < 0:
            return 2 * math.pi - angle
        return angle

    def _get_movement_parameters(self):
        """ Return movement parameters, see super class for details.
        """
        return (self.acceleration_time_s,
                self.linear_time_s,
                self.max_velocity_mm_per_sec)

    @staticmethod
    def __circular_helper(start, i, radius, side, direction):
        np = start + direction * i
        if np > radius:
            np -= 2 * (np - radius)
            direction = -direction
            side = not side
        if np < -radius:
            np -= 2 * (np + radius)
            direction = -direction
            side = not side
        if np > radius:
            np -= 2 * (np - radius)
            direction = -direction
            side = not side
        return np, direction, side

    def __circular_find_time(self, ac, bc):
        angle = self.__angle(ac, bc)
        if self._direction == CW:
            delta_angle = angle - self._start_angle
        else:
            delta_angle = self._start_angle - angle
        if delta_angle <= 0:
            delta_angle += 2 * math.pi
        return self._r_div_v * delta_angle

    def __circular_ac(self, i, pulses_per_mm):
        if i >= self._iterations_ac:
            return self._dir_ac, None
        ac, direction, side = \
            self.__circular_helper(self._start_ac_pulses, i + 1,
                                   self._radius_ac_pulses,
                                   self._side_ac, self._dir_ac)
        ac /= pulses_per_mm
        # first and last item can be slightly out of bound due float precision
        if i + 1 == self._iterations_ac:
            return direction, self._r_div_v * self._delta_angle
        bc = math.sqrt(self._radius_a2 - ac * ac)
        if side:
            bc = -bc
        return direction, self.__circular_find_time(ac, bc)

    def __circular_bc(self, i, pulses_per_mm):
        if i >= self._iterations_bc:
            return self._dir_bc, None
        bc, direction, side = \
            self.__circular_helper(self._start_bc_pulses, i + 1,
                                   self._radius_bc_pulses,
                                   self._side_bc, self._dir_bc)
        bc /= pulses_per_mm
        # first and last item can be slightly out of bound due float precision
        if i + 1 == self._iterations_bc:
            return direction, self._r_div_v * self._delta_angle
        ac = math.sqrt(self._radius_b2 - bc * bc)
        if side:
            ac = -ac
        return direction, self.__circular_find_time(ac, bc)

    @staticmethod
    def __linear(i, total_i, pulses_per_mm, velocity):
        if i >= total_i:
            return None
        return i / pulses_per_mm / velocity

    def _interpolation_function(self, ix, iy, iz, ie, iq, i_n, ia, ib):
        """ Calculate interpolation values for linear movement, see super class
            for details.
        """
        if self._plane == PLANE_XY:
            dx, tx = self.__circular_ac(ix, STEPPER_PULSES_PER_MM_X)
            dy, ty = self.__circular_bc(iy, STEPPER_PULSES_PER_MM_Y)
            tz = self.__linear(iz, self._iterations_3rd,
                               STEPPER_PULSES_PER_MM_Z, self._velocity_3rd)
            dz = self._third_dir
        elif self._plane == PLANE_YZ:
            dy, ty = self.__circular_ac(iy, STEPPER_PULSES_PER_MM_Y)
            dz, tz = self.__circular_bc(iz, STEPPER_PULSES_PER_MM_Z)
            tx = self.__linear(ix, self._iterations_3rd,
                               STEPPER_PULSES_PER_MM_X, self._velocity_3rd)
            dx = self._third_dir
        else:  # self._plane == PLANE_ZX:
            dz, tz = self.__circular_ac(iz, STEPPER_PULSES_PER_MM_Z)
            dx, tx = self.__circular_bc(ix, STEPPER_PULSES_PER_MM_X)
            ty = self.__linear(iy, self._iterations_3rd,
                               STEPPER_PULSES_PER_MM_Y, self._velocity_3rd)
            dy = self._third_dir
        te = self.__linear(ie, self._iterations_e, STEPPER_PULSES_PER_MM_E,
                           self._e_velocity)
        return (dx, dy, dz, self._e_dir), (tx, ty, tz, te)
