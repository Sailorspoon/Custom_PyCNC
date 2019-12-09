import unittest

from cnc.gcode import *


class TestGCode(unittest.TestCase):
    def setUp(self):
        self.default = Coordinates(-7, 8, 9, -10, 11, -12, 13, -14)

    def tearDown(self):
        pass

    def test_constructor(self):
        # GCode shouldn't be created with constructor, but since it uses
        # internally, let's checq it.
        self.assertRaises(TypeError, GCode)
        gc = GCode({"X": "1", "Y": "-2", "Z": "0", "E": 99, "Q": 43, "N": "2", "A": "5", "B": "7", "G": "1"})
        self.assertEqual(gc.coordinates(self.default, 1).x, 1.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, -2.0)
        self.assertEqual(gc.coordinates(self.default, 1).z, 0.0)
        self.assertEqual(gc.coordinates(self.default, 1).e, 99.0)
        self.assertEqual(gc.coordinates(self.default, 1).q, 43.0)
        self.assertEqual(gc.coordinates(self.default, 1).n, 2.0)
        self.assertEqual(gc.coordinates(self.default, 1).a, 5.0)
        self.assertEqual(gc.coordinates(self.default, 1).b, 7.0)

    def test_has(self):
        gc = GCode.parse_line("g1X2Y3z4E5F50Q2N1A3B9")
        self.assertTrue(gc.has("G"))
        self.assertTrue(gc.has("X"))
        self.assertTrue(gc.has("Y"))
        self.assertTrue(gc.has("Z"))
        self.assertTrue(gc.has("E"))
        self.assertTrue(gc.has("F"))
        self.assertTrue(gc.has("Q"))
        self.assertTrue(gc.has("N"))
        self.assertTrue(gc.has("A"))
        self.assertTrue(gc.has("B"))

    def test_parser(self):
        gc = GCode.parse_line("G1X2Y-3Z4E1.5Q2.1N1.1A9.2B4.4")
        self.assertEqual(gc.command(), "G1")
        self.assertEqual(gc.coordinates(self.default, 1).x, 2.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, -3.0)
        self.assertEqual(gc.coordinates(self.default, 1).z, 4.0)
        self.assertEqual(gc.coordinates(self.default, 1).e, 1.5)
        self.assertEqual(gc.coordinates(self.default, 1).q, 2.1)
        self.assertEqual(gc.coordinates(self.default, 1).n, 1.1)
        self.assertEqual(gc.coordinates(self.default, 1).a, 9.2)
        self.assertEqual(gc.coordinates(self.default, 1).b, 4.4)
        gc = GCode.parse_line("")
        self.assertIsNone(gc)

    def test_defaults(self):
        # defaults are values which should be returned if corresponding
        # value doesn't exist in gcode.
        default = Coordinates(11, -12, 14, -10, 10, 2, 2, 2)
        gc = GCode.parse_line("G1")
        self.assertEqual(gc.coordinates(default, 1).x, 11.0)
        self.assertEqual(gc.coordinates(default, 1).y, -12.0)
        self.assertEqual(gc.coordinates(default, 1).z, 14.0)
        self.assertEqual(gc.coordinates(default, 1).e, -10.0)
        self.assertEqual(gc.coordinates(default, 1).q, 10)
        self.assertEqual(gc.coordinates(default, 1).n, 2)
        self.assertEqual(gc.coordinates(default, 1).a, 2)
        self.assertEqual(gc.coordinates(default, 1).b, 2)

    def test_commands(self):
        gc = GCode({"G": "1"})
        self.assertEqual(gc.command(), "G1")
        gc = GCode.parse_line("M99")
        self.assertEqual(gc.command(), "M99")

    def test_case_sensitivity(self):
        gc = GCode.parse_line("m111")
        self.assertEqual(gc.command(), "M111")
        gc = GCode.parse_line("g2X3y-4Z5e6q2n5a6b7")
        self.assertEqual(gc.command(), "G2")
        self.assertEqual(gc.coordinates(self.default, 1).x, 3.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, -4.0)
        self.assertEqual(gc.coordinates(self.default, 1).z, 5.0)
        self.assertEqual(gc.coordinates(self.default, 1).e, 6.0)
        self.assertEqual(gc.coordinates(self.default, 1).q, 2.0)
        self.assertEqual(gc.coordinates(self.default, 1).n, 5.0)
        self.assertEqual(gc.coordinates(self.default, 1).a, 6.0)
        self.assertEqual(gc.coordinates(self.default, 1).b, 7.0)

    def test_has_coordinates(self):
        gc = GCode.parse_line("X2Y-3Z4")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("G1")
        self.assertFalse(gc.has_coordinates())
        gc = GCode.parse_line("X1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("Y1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("Z1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("E1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("Q1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("N1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("A1")
        self.assertTrue(gc.has_coordinates())
        gc = GCode.parse_line("B1")
        self.assertTrue(gc.has_coordinates())

    def test_radius(self):
        gc = GCode.parse_line("G2I1J2Q3")
        self.assertEqual(gc.radius(self.default, 1).x, 1)
        self.assertEqual(gc.radius(self.default, 1).y, 2)
        self.assertEqual(gc.radius(self.default, 1).z, 3)
        gc = GCode.parse_line("G3")
        self.assertEqual(gc.radius(self.default, 1).x, self.default.x)
        self.assertEqual(gc.radius(self.default, 1).y, self.default.y)
        self.assertEqual(gc.radius(self.default, 1).z, self.default.z)

    def test_multiply(self):
        # getting coordinates could modify value be specified multiplier.
        gc = GCode.parse_line("X2 Y-3 Z4 E5 Q3 N2 A3 B4")
        self.assertEqual(gc.coordinates(self.default, 25.4).x, 50.8)
        self.assertEqual(gc.coordinates(self.default, 2).y, -6)
        self.assertEqual(gc.coordinates(self.default, 0).z, 0)
        self.assertEqual(gc.coordinates(self.default, 5).e, 25)
        self.assertEqual(gc.coordinates(self.default, 2).q, 6)
        self.assertEqual(gc.coordinates(self.default, 4).n, 8)
        self.assertEqual(gc.coordinates(self.default, 4).a, 12)
        self.assertEqual(gc.coordinates(self.default, 4).b, 16)

    def test_whitespaces(self):
        gc = GCode.parse_line("X1 Y2")
        self.assertEqual(gc.coordinates(self.default, 1).x, 1.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, 2.0)
        gc = GCode.parse_line("X 3 Y4")
        self.assertEqual(gc.coordinates(self.default, 1).x, 3.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, 4.0)
        gc = GCode.parse_line("X 5 Y\t 6")
        self.assertEqual(gc.coordinates(self.default, 1).x, 5.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, 6.0)
        gc = GCode.parse_line(" \tX\t\t  \t\t7\t ")
        self.assertEqual(gc.coordinates(self.default, 1).x, 7.0)

    def test_errors(self):
        self.assertRaises(GCodeException, GCode.parse_line, "X1X1")
        self.assertRaises(GCodeException, GCode.parse_line, "X1+Y1")
        self.assertRaises(GCodeException, GCode.parse_line, "X1-Y1")
        self.assertRaises(GCodeException, GCode.parse_line, "~Y1")
        self.assertRaises(GCodeException, GCode.parse_line, "Y")
        self.assertRaises(GCodeException, GCode.parse_line, "abracadabra")
        self.assertRaises(GCodeException, GCode.parse_line, "G1M1")
        self.assertRaises(GCodeException, GCode.parse_line, "x 1 y 1 z 1 X 1")
        self.assertRaises(GCodeException, GCode.parse_line, "M3N5")

    def test_comments(self):
        self.assertIsNone(GCode.parse_line("; some text"))
        self.assertIsNone(GCode.parse_line("    \t   \t ; some text"))
        self.assertIsNone(GCode.parse_line("(another comment)"))
        gc = GCode.parse_line("X2.5 ; end of line comment")
        self.assertEqual(gc.coordinates(self.default, 1).x, 2.5)
        gc = GCode.parse_line("X2 Y(inline comment)7")
        self.assertEqual(gc.coordinates(self.default, 1).x, 2.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, 7.0)
        gc = GCode.parse_line("X2 Y(inline comment)3 \t(one more comment) "
                              "\tz4 ; multi comment test")
        self.assertEqual(gc.coordinates(self.default, 1).x, 2.0)
        self.assertEqual(gc.coordinates(self.default, 1).y, 3.0)
        self.assertEqual(gc.coordinates(self.default, 1).z, 4.0)


if __name__ == '__main__':
    unittest.main()
