# Aenderung Max 28.11.2019
from __future__ import division
import time

from cnc.pulses import *
from cnc.config import *

""" This is virtual device class which is very useful for debugging.
    It checks PulseGenerator with some tests.
"""


def init():
    """ Initialize GPIO pins and machine itself.
    """
    logging.info("initialize hal")


def spindle_control(percent):
    """ Spindle control implementation 0..100.
    :param percent: Spindle speed in percent.
    """
    logging.info("spindle control: {}%".format(percent))


def fan_control(on_off):
    """Cooling fan control.
    :param on_off: boolean value if fan is enabled.
    """
    if on_off:
        logging.info("Fan is on")
    else:
        logging.info("Fan is off")


# noinspection PyUnusedLocal
def extruder_heater_control(percent):
    """ Extruder heater control.
    :param percent: heater power in percent 0..100. 0 turns heater off.
    """
    pass


# noinspection PyUnusedLocal
def bed_heater_control(percent):
    """ Hot bed heater control.
    :param percent: heater power in percent 0..100. 0 turns heater off.
    """
    pass


def get_extruder_temperature():
    """ Measure extruder temperature.
    :return: temperature in Celsius.
    """
    return EXTRUDER_MAX_TEMPERATURE * 0.999


def get_bed_temperature():
    """ Measure bed temperature.
    :return: temperature in Celsius.
    """
    return BED_MAX_TEMPERATURE * 0.999


def disable_steppers():
    """ Disable all steppers until any movement occurs.
    """
    logging.info("hal disable steppers")


def calibrate(x, y, z):
    """ Move head to home position till end stop switch will be triggered.
    Do not return till all procedures are completed.
    :param x: boolean, True to calibrate X axis.
    :param y: boolean, True to calibrate Y axis.
    :param z: boolean, True to calibrate Z axis.
    :return: boolean, True if all specified end stops were triggered.
    """
    logging.info("hal calibrate, x={}, y={}, z={}".format(x, y, z))
    return True


# noinspection PyUnusedLocal
def move(generator):
    """ Move head to specified position.
    :param generator: PulseGenerator object.
    """
    delta = generator.delta()
    ix = iy = iz = ie = iq = i_n = ia = ib = 0
    lx, ly, lz, le, lq, ln, la, lb = None, None, None, None, None, None, None, None
    dx, dy, dz, de, dq, dn, da, db = 0, 0, 0, 0, 0, 0, 0, 0
    mx, my, mz, me, mq, mn, ma, mb = 0, 0, 0, 0, 0, 0, 0, 0
    cx, cy, cz, ce, cq, cn, ca, cb = 0, 0, 0, 0, 0, 0, 0, 0
    direction_x, direction_y, direction_z, direction_e, direction_q, direction_n, direction_a, direction_b = \
        1, 1, 1, 1, 1, 1, 1, 1
    st = time.time()
    direction_found = False
    for direction, tx, ty, tz, te, tq, tn, ta, tb in generator:
        if direction:
            direction_found = True
            direction_x, direction_y, direction_z, direction_e, direction_q, direction_n = tx, ty, tz, te, tq, tn
            if STEPPER_INVERTED_X:
                direction_x = -direction_x
            if STEPPER_INVERTED_Y:
                direction_y = -direction_y
            if STEPPER_INVERTED_Z:
                direction_z = -direction_z
            if STEPPER_INVERTED_E:
                direction_e = -direction_e
            if STEPPER_INVERTED_Q:
                direction_q = -direction_q
            if STEPPER_INVERTED_N:
                direction_n = -direction_n
            if STEPPER_INVERTED_A:
                direction_a = -direction_a
            if STEPPER_INVERTED_B:
                direction_b = -direction_b
            if isinstance(generator, PulseGeneratorLinear):
                assert ((direction_x < 0 and delta.x < 0)
                        or (direction_x > 0 and delta.x > 0) or delta.x == 0)
                assert ((direction_y < 0 and delta.y < 0)
                        or (direction_y > 0 and delta.y > 0) or delta.y == 0)
                assert ((direction_z < 0 and delta.z < 0)
                        or (direction_z > 0 and delta.z > 0) or delta.z == 0)
                assert ((direction_e < 0 and delta.e < 0)
                        or (direction_e > 0 and delta.e > 0) or delta.e == 0)
                assert ((direction_q < 0 and delta.q < 0)
                        or (direction_q > 0 and delta.q > 0) or delta.q == 0)
                assert ((direction_e < 0 and delta.n < 0)
                        or (direction_n > 0 and delta.n > 0) or delta.n == 0)
                assert ((direction_a < 0 and delta.a < 0)
                        or (direction_a > 0 and delta.a > 0) or delta.a == 0)
                assert ((direction_b < 0 and delta.b < 0)
                        or (direction_b > 0 and delta.b > 0) or delta.b == 0)
            continue
        if tx is not None:
            if tx > mx:
                mx = tx
            tx = int(round(tx * 1000000))
            ix += direction_x
            cx += 1
            if lx is not None:
                dx = tx - lx
                assert dx > 0, "negative or zero time delta detected for x"
            lx = tx
        else:
            dx = None
        if ty is not None:
            if ty > my:
                my = ty
            ty = int(round(ty * 1000000))
            iy += direction_y
            cy += 1
            if ly is not None:
                dy = ty - ly
                assert dy > 0, "negative or zero time delta detected for y"
            ly = ty
        else:
            dy = None
        if tz is not None:
            if tz > mz:
                mz = tz
            tz = int(round(tz * 1000000))
            iz += direction_z
            cz += 1
            if lz is not None:
                dz = tz - lz
                assert dz > 0, "negative or zero time delta detected for z"
            lz = tz
        else:
            dz = None
        if te is not None:
            if te > me:
                me = te
            te = int(round(te * 1000000))
            ie += direction_e
            ce += 1
            if le is not None:
                de = te - le
                assert de > 0, "negative or zero time delta detected for e"
            le = te
        else:
            de = None
        if tq is not None:
            if tq > mq:
                mq = tq
            tq = int(round(tq * 1000000))
            iq += direction_q
            cq += 1
            if lq is not None:
                dq = tq - lq
                assert dq > 0, "negative or zero time delta detected for q"
            lq = tq
        else:
            dq = None
        if tn is not None:
            if tn > mn:
                mn = tn
            tn = int(round(tn * 1000000))
            i_n += direction_n
            cn += 1
            if ln is not None:
                dn = tn - ln
                assert dn > 0, "negative or zero time delta detected for n"
            ln = tn
        else:
            dn = None
        if ta is not None:
            if ta > ma:
                ma = ta
            ta = int(round(ta * 1000000))
            ia += direction_a
            ca += 1
            if la is not None:
                da = ta - la
                assert da > 0, "negative or zero time delta detected for a"
            la = ta
        else:
            da = None
        if tb is not None:
            if tb > mb:
                mb = tb
            tb = int(round(tb * 1000000))
            ib += direction_b
            cb += 1
            if lb is not None:
                db = tb - lb
                assert db > 0, "negative or zero time delta detected for b"
            lb = tb
        else:
            db = None
        # very verbose, uncomment on demand
        # logging.debug("Iteration {} is {} {} {} {}".
        #               format(max(ix, iy, iz, ie), tx, ty, tz, te))
        f = list(x for x in (tx, ty, tz, te, tq, tn, ta, tb) if x is not None)
        assert f.count(f[0]) == len(f), "fast forwarded pulse detected"
    pt = time.time()
    assert direction_found, "direction not found"
    assert round(ix / STEPPER_PULSES_PER_MM_X, 10) == delta.x,\
        "x wrong number of pulses"
    assert round(iy / STEPPER_PULSES_PER_MM_Y, 10) == delta.y,\
        "y wrong number of pulses"
    assert round(iz / STEPPER_PULSES_PER_MM_Z, 10) == delta.z, \
        "z wrong number of pulses"
    assert round(ie / STEPPER_PULSES_PER_MM_E, 10) == delta.e, \
        "e wrong number of pulses"
    assert round(iq / STEPPER_PULSES_PER_MM_Q, 10) == delta.q, \
        "q wrong number of pulses"
    assert round(i_n / STEPPER_PULSES_PER_MM_N, 10) == delta.n, \
        "n wrong number of pulses"
    assert round(ia / STEPPER_PULSES_PER_MM_A, 10) == delta.a, \
        "a wrong number of pulses"
    assert round(ib / STEPPER_PULSES_PER_MM_B, 10) == delta.b, \
        "b wrong number of pulses"
    assert max(mx, my, mz, me, mq, mn, ma, mb) <= generator.total_time_s(), \
        "interpolation time or pulses wrong"
    logging.debug("Moved {}, {}, {}, {}, {}, {}, {}, {} iterations".format(ix, iy, iz, ie, iq, i_n, ia, ib))
    logging.info("prepared in " + str(round(pt - st, 2)) + "s, estimated "
                 + str(round(generator.total_time_s(), 2)) + "s")


def join():
    """ Wait till motors work.
    """
    logging.info("hal join()")


def deinit():
    """ De-initialise.
    """
    logging.info("hal deinit()")


def watchdog_feed():
    """ Feed hardware watchdog.
    """
    pass
