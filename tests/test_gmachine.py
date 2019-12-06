# 28.11.2019 Christian A und B Achsen eingefuegt
import unittest

from cnc.gcode import *
from cnc.gmachine import *
from cnc.coordinates import *
from cnc.heater import *
from cnc.pid import *
from cnc.config import *


class TestGMachine(unittest.TestCase):
    def setUp(self):
        Pid.FIX_TIME_S = 0.01
        Heater.LOOP_INTERVAL_S = 0.001

    def tearDown(self):
        pass

    def test_reset(self):
        # reset() resets all configurable from gcode things.
        m = GMachine()
        m.do_command(GCode.parse_line("G20"))
        m.do_command(GCode.parse_line("G91"))
        m.do_command(GCode.parse_line("X1Y1Z1"))
        m.reset()
        m.do_command(GCode.parse_line("X3Y4Z5E6Q7N8A9B10"))
        self.assertEqual(m.position(), Coordinates(3, 4, 5, 6, 7, 8, 9, 10))

    def test_safe_zero(self):
        m = GMachine()
        m.do_command(GCode.parse_line("X1Y2Z3E4Q4N5A6B7"))
        m.safe_zero()    # In safe_zero (in gmachine.py) die anderen safe daten eingeben
        self.assertEqual(m.position(), Coordinates(0, 0, 0, 4, 4, 0, 0, 0))

    def test_none(self):
        # GMachine must ignore None commands, since GCode.parse_line()
        # returns None if no gcode found in line.
        m = GMachine()
        m.do_command(None)
        self.assertEqual(m.position(), Coordinates(0, 0, 0, 0, 0, 0, 0, 0))

    def test_unknown(self):
        # Test commands which doesn't exists
        m = GMachine()
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G99699X1Y2Z3"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("M99699"))

    # Test gcode commands.
    def test_g0_g1(self):
        m = GMachine()
        m.do_command(GCode.parse_line("G0X10Y10Z11"))
        self.assertEqual(m.position(), Coordinates(10, 10, 11, 0, 0, 0, 0, 0))
        m.do_command(GCode.parse_line("G0X3Y2Z1E-2Q-2N0A3B3"))
        self.assertEqual(m.position(), Coordinates(3, 2, 1, -2, -2, 0, 3, 3))
        m.do_command(GCode.parse_line("G1X1Y2Z3E4Q4N1A2B5"))
        self.assertEqual(m.position(), Coordinates(1, 2, 3, 4, 4, 1, 2, 5))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G1F-1"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G1X-1Y0Z0"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G1X0Y-1Z0"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G1X0Y0Z-1"))

    #     commented out - should be rechecked later
    # def test_feed_rate(self):
    #     PulseGenerator.AUTO_VELOCITY_ADJUSTMENT = False
    #     m = GMachine()
    #     self.assertRaises(GMachineException,
    #                       m.do_command, GCode.parse_line("G1X1F-1"))
    #     cl = "G1X1F" + str(MIN_VELOCITY_MM_PER_MIN - 0.0000001)
    #     self.assertRaises(GMachineException, m.do_command,
    #                       GCode.parse_line(cl))
    #     m.do_command(GCode.parse_line("G1X100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_X)))
    #     m.do_command(GCode.parse_line("G1Y100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_Y)))
    #     m.do_command(GCode.parse_line("G1Z100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_Z)))
    #     m.do_command(GCode.parse_line("G1E100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_E)))
    #     m.do_command(GCode.parse_line("G1Q100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_Q)))
    #     m.do_command(GCode.parse_line("G1N100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_N)))
    #     m.do_command(GCode.parse_line("G1A100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_A)))
    #     m.do_command(GCode.parse_line("G1B100F"
    #                                   + str(MAX_VELOCITY_MM_PER_MIN_B)))
    #     self.assertRaises(GMachineException,
    #                       m.do_command, GCode.parse_line("G1X0F999999"))
    #     s = "G1X0F" + str(MAX_VELOCITY_MM_PER_MIN_X + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1Y0F" + str(MAX_VELOCITY_MM_PER_MIN_Y + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1Z0F" + str(MAX_VELOCITY_MM_PER_MIN_Z + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1E0F" + str(MAX_VELOCITY_MM_PER_MIN_E + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1Q0F" + str(MAX_VELOCITY_MM_PER_MIN_Q + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1N0F" + str(MAX_VELOCITY_MM_PER_MIN_N + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1A0F" + str(MAX_VELOCITY_MM_PER_MIN_A + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     s = "G1B0F" + str(MAX_VELOCITY_MM_PER_MIN_B + 1)
    #     self.assertRaises(GMachineException, m.do_command, GCode.parse_line(s))
    #     PulseGenerator.AUTO_VELOCITY_ADJUSTMENT = True
    #     m.do_command(GCode.parse_line("G1X10Y10Z10F9999999999999999999"))
    #     # m.do_command(GCode.parse_line("G2I0.1F9999999999999999999"))
    #     # m.do_command(GCode.parse_line("G2I10F9999999999999999999"))
    #     # Spaeter checken ob es hier einen Error gibt, ggf ergaenzen
    #     PulseGenerator.AUTO_VELOCITY_ADJUSTMENT = AUTO_VELOCITY_ADJUSTMENT

    def test_g2_g3(self):
        m = GMachine()
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G3I1J1F-1"))
        m.do_command(GCode.parse_line("G19"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G3I1J0K0"))
        m.do_command(GCode.parse_line("G18"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G3I0J1K0"))
        m.do_command(GCode.parse_line("G17"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G3I0J0K1"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G2X99999999Y99999999"
                                                         "I1J1"))
        self.assertRaises(GMachineException,
                          m.do_command,
                          GCode.parse_line("G2X2Y2Z99999999I1J1"))
        self.assertEqual(m.position(), Coordinates(0, 0, 0, 0, 0, 0, 0, 0))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G2X4Y4I2J2"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G3X4Y4I2J2"))
        m.do_command(GCode.parse_line("G17"))
        m.do_command(GCode.parse_line("G1X1"))
        m.do_command(GCode.parse_line("G2J1"))
        m.do_command(GCode.parse_line("G3J1"))
        self.assertEqual(m.position(), Coordinates(1, 0, 0, 0, 0, 0, 0, 0))
        m.do_command(GCode.parse_line("G1X10Y10B2"))
        m.do_command(GCode.parse_line("G2X9I1Q2A3"))
        self.assertEqual(m.position(), Coordinates(9, 10, 0, 0, 2, 0, 3, 2))
        m.do_command(GCode.parse_line("G19"))
        m.do_command(GCode.parse_line("G1X10Y10Z10N5"))
        m.do_command(GCode.parse_line("G3Y8K1Q1A3B2"))
        self.assertEqual(m.position(), Coordinates(0, 10, 8, 10, 0, 1, 3, 2))
        m.do_command(GCode.parse_line("G17"))
        m.do_command(GCode.parse_line("G1X5Y5Z0Q2A5"))
        m.do_command(GCode.parse_line("G2X0Y0Z5I-2J-2Q5A2B2"))
        self.assertEqual(m.position(), Coordinates(0, 0, 5, 0, 5, 5, 2, 2))
        m.do_command(GCode.parse_line("G17"))
        m.do_command(GCode.parse_line("G1X90Y90N1A3"))
        m.do_command(GCode.parse_line("G2X90Y70I-5J-5"))
        self.assertEqual(m.position(), Coordinates(90, 70, 5, 0, 5, 1, 3, 0))
        m.do_command(GCode.parse_line("G18"))
        m.do_command(GCode.parse_line("G1X90Y90Z20E0A0B0"))
        m.do_command(GCode.parse_line("G2Z20X70I-5K-5E22Q0N0"))
        self.assertEqual(m.position(), Coordinates(70, 90, 20, 22, 0, 0, 0, 0))
        m.do_command(GCode.parse_line("G19"))
        m.do_command(GCode.parse_line("G1X90Y90Z20Q1N1A1B1"))
        m.do_command(GCode.parse_line("G2Y90Z0J-5K-5E27Q2N3A2B2"))
        self.assertEqual(m.position(), Coordinates(90, 90, 0, 27, 2, 3, 2, 2))

    def test_g4(self):
        m = GMachine()
        st = time.time()
        m.do_command(GCode.parse_line("G4P0.5"))
        self.assertLess(0.5, time.time() - st)
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("G4P-0.5"))

    def test_g17_g18_g19(self):
        # Einstellen der Ebene moeglich (verwendung fuer schwernkbares bett)
        m = GMachine()
        m.do_command(GCode.parse_line("G19"))
        self.assertEqual(m.plane(), PLANE_YZ)
        m.do_command(GCode.parse_line("G18"))
        self.assertEqual(m.plane(), PLANE_ZX)
        m.do_command(GCode.parse_line("G17"))
        self.assertEqual(m.plane(), PLANE_XY)

    def test_g20_g21(self):
        # Wechsel zwischen inches und millimeter
        m = GMachine()
        m.do_command(GCode.parse_line("G20"))    # Ab hier ist der G-Code in inches
        m.do_command(GCode.parse_line("X3Y2Z1E0.5Q2N1A5B7"))
        self.assertEqual(m.position(), Coordinates(76.2, 50.8, 25.4, 12.7, 50.8, 25.4, 127, 177.8))
        # Rechnet den angegebenen G-Code von inches zu millimeter
        m.do_command(GCode.parse_line("G21"))   # Ab hier ist der G-Code in millimeter
        m.do_command(GCode.parse_line("X3Y2Z1E0.5Q2N1A2B3"))
        self.assertEqual(m.position(), Coordinates(3, 2, 1, 0.5, 2, 1, 2, 3))

    def test_g90_g91(self):
        m = GMachine()
        m.do_command(GCode.parse_line("G91"))    # relative coords
        m.do_command(GCode.parse_line("X1Y1Z1E1Q1N1A1B1"))
        m.do_command(GCode.parse_line("X1Y1Z1Q1N1A1B1"))
        m.do_command(GCode.parse_line("X1Y1N-1B1"))
        m.do_command(GCode.parse_line("X1"))
        self.assertEqual(m.position(), Coordinates(4, 3, 2, 1, 2, 1, 2, 3))
        m.do_command(GCode.parse_line("X-1Y-1Z-1E-1Q-1N-1A-1B-1"))
        m.do_command(GCode.parse_line("G90"))   # absolute coords
        m.do_command(GCode.parse_line("X1Y1Z1E1Q1N1A1B1"))
        self.assertEqual(m.position(), Coordinates(1, 1, 1, 1, 1, 1, 1, 1))

    def test_g53_g92(self):
        m = GMachine()
        m.do_command(GCode.parse_line("G92X100Y100Z100E100Q100N100A100B100"))
        m.do_command(GCode.parse_line("X101Y102Z103E104Q105N106A107B108"))
        self.assertEqual(m.position(), Coordinates(1, 2, 3, 4, 5, 6, 7, 8))
        m.do_command(GCode.parse_line("G92X-1Y-1Z-1E-1Q-1N-1A-1B-1"))
        m.do_command(GCode.parse_line("X1Y1Z1E1Q1N1A1B1"))
        self.assertEqual(m.position(), Coordinates(3, 4, 5, 6, 7, 8, 9, 10))
        m.do_command(GCode.parse_line("G92X3Y4Z5E6Q7N8A9B10"))
        m.do_command(GCode.parse_line("X0Y0Z0E0Q0N0A0B0"))
        self.assertEqual(m.position(), Coordinates(0, 0, 0, 0, 0, 0, 0, 0))
        m.do_command(GCode.parse_line("X1Y2Z3E4Q5N6A7B8"))
        self.assertEqual(m.position(), Coordinates(1, 2, 3, 4, 5, 6, 7, 8))
        m.do_command(GCode.parse_line("G53"))
        m.do_command(GCode.parse_line("X6Y7Z8E9Q10N11A12B13"))
        self.assertEqual(m.position(), Coordinates(6, 7, 8, 9, 10, 11, 12, 13))
        m.do_command(GCode.parse_line("G92E0"))
        m.do_command(GCode.parse_line("X6Y7Z8E1Q10N11A12B13"))
        self.assertEqual(m.position(), Coordinates(6, 7, 8, 10, 10, 11, 12, 13))
        m.do_command(GCode.parse_line("G92"))
        m.do_command(GCode.parse_line("X1Y1Z1E1Q1N1A1B1"))
        self.assertEqual(m.position(), Coordinates(7, 8, 9, 11, 11, 12, 13, 14))
        # Unsicher bei dieser Zeile aber why not koennte ja amazing werden

    def test_g53_g91_g92(self):
        m = GMachine()
        m.do_command(GCode.parse_line("G92X-50Y-60Z-70E-80Q-90N-100A-110B-120"))    # Wechsel zu local coords
        m.do_command(GCode.parse_line("X-45Y-55Z-65E-75Q-85N-95A-105B-115"))
        self.assertEqual(m.position(), Coordinates(5, 5, 5, 5, 5, 5, 5, 5))
        m.do_command(GCode.parse_line("G91"))    # Wechsel zu relativ coords
        m.do_command(GCode.parse_line("X-1Y-2Z-3E-4Q-3N-2A-2B-1"))
        self.assertEqual(m.position(), Coordinates(4, 3, 2, 1, 2, 3, 3, 2))

    def test_m3_m5(self):
        # Ist fuer spindel gedacht, never touch a running system
        m = GMachine()
        m.do_command(GCode.parse_line("M3S" + str(SPINDLE_MAX_RPM)))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("M3S-10"))
        self.assertRaises(GMachineException,
                          m.do_command, GCode.parse_line("M3S999999999"))
        m.do_command(GCode.parse_line("M5"))

    def test_m104_m109(self):
        # Test von extruder und heater
        m = GMachine()
        m.do_command(GCode.parse_line("M104S"+str(MIN_TEMPERATURE)))
        self.assertEqual(m.extruder_target_temperature(), MIN_TEMPERATURE)
        m.do_command(GCode.parse_line("M104S0"))
        self.assertEqual(m.extruder_target_temperature(), 0)
        # blocking heating should be called with max temperature since virtual
        # hal always return this temperature.
        m.do_command(GCode.parse_line("M109S" + str(EXTRUDER_MAX_TEMPERATURE)))
        self.assertEqual(m.extruder_target_temperature(),
                         EXTRUDER_MAX_TEMPERATURE)
        m.do_command(GCode.parse_line("M104S0"))
        self.assertEqual(m.extruder_target_temperature(), 0)
        self.assertRaises(GMachineException, m.do_command,
                          GCode.parse_line("M104S"+str(MIN_TEMPERATURE - 1)))
        et = EXTRUDER_MAX_TEMPERATURE + 1
        self.assertRaises(GMachineException, m.do_command,
                          GCode.parse_line("M109S" + str(et)))
        self.assertRaises(GMachineException, m.do_command,
                          GCode.parse_line("M109"))

    def test_m106_m107(self):
        # An und aus stellen des ventilators
        m = GMachine()
        m.do_command(GCode.parse_line("M106"))
        self.assertTrue(m.fan_state())
        m.do_command(GCode.parse_line("M106S0"))
        self.assertFalse(m.fan_state())
        m.do_command(GCode.parse_line("M106S123"))
        self.assertTrue(m.fan_state())
        m.do_command(GCode.parse_line("M107"))
        self.assertFalse(m.fan_state())
        # check auto fan feature
        m.AUTO_FAN_ON = True
        m.do_command(GCode.parse_line("M104S" + str(MIN_TEMPERATURE)))
        self.assertTrue(m.fan_state())
        m.do_command(GCode.parse_line("M104S0"))
        self.assertTrue(m.fan_state())
        m.do_command(GCode.parse_line("M107"))
        self.assertFalse(m.fan_state())
        m.AUTO_FAN_ON = False

    def test_m140_m190(self):
        # Abfrage von heater bed und heater temperature, aber unsicher
        m = GMachine()
        m.do_command(GCode.parse_line("M140S"+str(MIN_TEMPERATURE)))
        self.assertEqual(m.bed_target_temperature(), MIN_TEMPERATURE)
        m.do_command(GCode.parse_line("M140S0"))
        self.assertEqual(m.bed_target_temperature(), 0)
        # blocking heating should be called with max temperature since virtual
        # hal always return this temperature.
        m.do_command(GCode.parse_line("M190S" + str(BED_MAX_TEMPERATURE)))
        self.assertEqual(m.bed_target_temperature(), BED_MAX_TEMPERATURE)
        m.do_command(GCode.parse_line("M190S0"))
        self.assertEqual(m.bed_target_temperature(), 0)
        self.assertRaises(GMachineException, m.do_command,
                          GCode.parse_line("M140S"+str(MIN_TEMPERATURE - 1)))
        self.assertRaises(GMachineException, m.do_command,
                          GCode.parse_line("M190S"
                                           + str(BED_MAX_TEMPERATURE + 1)))
        self.assertRaises(GMachineException, m.do_command,
                          GCode.parse_line("M190"))


if __name__ == '__main__':
    unittest.main()
