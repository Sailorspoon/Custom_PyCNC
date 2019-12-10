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
