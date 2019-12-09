import unittest

from cnc.coordinates import *


class TestCoordinates(unittest.TestCase):
    def setUp(self):
        self.default = Coordinates(96, 102, 150, 228, 228, 96, 102, 42)

    def tearDown(self):
        pass

    def test_constructor(self):
        # constructor rounds values to 10 digits after the point
        self.assertRaises(TypeError, Coordinates)
        c = Coordinates(1.00000000005, 2.00000000004, -3.5000000009, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.assertEqual(c.x, 1.0000000001)
        self.assertEqual(c.y, 2.0)
        self.assertEqual(c.z, -3.5000000009)
        self.assertEqual(c.e, 0.0)
        self.assertEqual(c.q, 0.0)  # see assert in file hal_virtual
        self.assertEqual(c.n, 0.0)
        self.assertEqual(c.a, 0.0)
        self.assertEqual(c.b, 0.0)

    def test_zero(self):
        c = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)
        self.assertTrue(c.is_zero())

    def test_aabb(self):
        # aabb - Axis Aligned Bounded Box.
        # original method checks if point belongs aabb.
        p1 = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)
        p2 = Coordinates(2, 2, 2, 0, 0, 2, 0, 0)
        c = Coordinates(1, 1, 1, 0, 0, 1, 0, 0)
        self.assertTrue(c.is_in_aabb(p1, p2))
        self.assertTrue(c.is_in_aabb(p2, p1))
        c = Coordinates(0, 0, 0, 0, 0, 0, 0, 0)
        self.assertTrue(c.is_in_aabb(p1, p2))
        c = Coordinates(2, 2, 2, 0, 0, 2, 0, 0)
        self.assertTrue(c.is_in_aabb(p1, p2))
        c = Coordinates(2, 3, 2, 0, 0, 2, 0, 0)
        self.assertFalse(c.is_in_aabb(p1, p2))
        c = Coordinates(-1, 1, 1, 0, 0, 1, 0, 0)
        self.assertFalse(c.is_in_aabb(p1, p2))
        c = Coordinates(1, 1, 3, 0, 0, 1, 0, 0)
        self.assertFalse(c.is_in_aabb(p1, p2))

    def test_length(self):
        # adjusted values to fit the test with six inputs
        c = Coordinates(-1, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(c.length(), 1)
        c = Coordinates(0, 3, -2, 0, 2, 0, -2, -2)
        self.assertEqual(c.length(), 5)
        c = Coordinates(3, 2, 0, 2, 0, 12, 2, 2)
        self.assertEqual(c.length(), 13)
        c = Coordinates(1, 1, 0, 0, 1, 1, 2, 1)
        self.assertEqual(c.length(), 3)

    def test_round(self):
        # round works in another way then Python's round.
        # This round() rounds digits with specified step.
        c = Coordinates(1.5, -1.4, 3.05, 3.5, 2.14, 1.5, 2.3, 3.89)
        r = c.round(1, 1, 1, 1, 1, 1, 1, 1)
        self.assertEqual(r.x, 2.0)
        self.assertEqual(r.y, -1.0)
        self.assertEqual(r.z, 3.0)
        self.assertEqual(r.e, 4.0)
        self.assertEqual(r.q, 2.0)
        self.assertEqual(r.n, 2.0)
        self.assertEqual(r.a, 2.0)
        self.assertEqual(r.b, 4.0)
        r = c.round(0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25)
        self.assertEqual(r.x, 1.5)
        self.assertEqual(r.y, -1.5)
        self.assertEqual(r.z, 3.0)
        self.assertEqual(r.e, 3.5)
        self.assertEqual(r.q, 2.25)
        self.assertEqual(r.n, 1.5)
        self.assertEqual(r.a, 2.25)
        self.assertEqual(r.b, 4.0)

    def test_max(self):
        self.assertEqual(self.default.find_max(), max(self.default.x,
                                                      self.default.y,
                                                      self.default.z,
                                                      self.default.e,
                                                      self.default.q,
                                                      self.default.n,
                                                      self.default.a,
                                                      self.default.b))

    # build-in function overriding tests
    def test_add(self):
        r = self.default + Coordinates(1, 2, 3, 4, 5, 6, 7, 8)
        self.assertEqual(r.x, self.default.x + 1)
        self.assertEqual(r.y, self.default.y + 2)
        self.assertEqual(r.z, self.default.z + 3)
        self.assertEqual(r.e, self.default.e + 4)
        self.assertEqual(r.q, self.default.q + 5)
        self.assertEqual(r.n, self.default.n + 6)
        self.assertEqual(r.a, self.default.a + 7)
        self.assertEqual(r.b, self.default.b + 8)

    def test_sub(self):
        r = self.default - Coordinates(1, 2, 3, 4, 5, 6, 7, 8)
        self.assertEqual(r.x, self.default.x - 1)
        self.assertEqual(r.y, self.default.y - 2)
        self.assertEqual(r.z, self.default.z - 3)
        self.assertEqual(r.e, self.default.e - 4)
        self.assertEqual(r.q, self.default.q - 5)
        self.assertEqual(r.n, self.default.n - 6)
        self.assertEqual(r.a, self.default.a - 7)
        self.assertEqual(r.b, self.default.b - 8)

    def test_mul(self):
        r = self.default * 2
        self.assertEqual(r.x, self.default.x * 2)
        self.assertEqual(r.y, self.default.y * 2)
        self.assertEqual(r.z, self.default.z * 2)
        self.assertEqual(r.e, self.default.e * 2)
        self.assertEqual(r.q, self.default.q * 2)
        self.assertEqual(r.n, self.default.n * 2)
        self.assertEqual(r.a, self.default.a * 2)
        self.assertEqual(r.b, self.default.b * 2)

    def test_div(self):
        r = self.default / 2
        self.assertEqual(r.x, self.default.x / 2)
        self.assertEqual(r.y, self.default.y / 2)
        self.assertEqual(r.z, self.default.z / 2)
        self.assertEqual(r.e, self.default.e / 2)
        self.assertEqual(r.q, self.default.q / 2)
        self.assertEqual(r.n, self.default.n / 2)
        self.assertEqual(r.a, self.default.a / 2)
        self.assertEqual(r.b, self.default.b / 2)

    def test_truediv(self):
        r = self.default / 3.0
        self.assertEqual(r.x, self.default.x / 3.0)
        self.assertEqual(r.y, self.default.y / 3.0)
        self.assertEqual(r.z, self.default.z / 3.0)
        self.assertEqual(r.e, self.default.e / 3.0)
        self.assertEqual(r.q, self.default.q / 3.0)
        self.assertEqual(r.n, self.default.n / 3.0)
        self.assertEqual(r.a, self.default.a / 3.0)
        self.assertEqual(r.b, self.default.b / 3.0)

    def test_eq(self):
        a = Coordinates(self.default.x, self.default.y, self.default.z,
                        self.default.e, self.default.q, self.default.n,
                        self.default.a, self.default.b)
        self.assertTrue(a == self.default)
        a = Coordinates(-self.default.x, self.default.y, self.default.z,
                        self.default.e, self.default.q, self.default.n,
                        self.default.a, self.default.b)
        self.assertFalse(a == self.default)
        a = Coordinates(self.default.x, -self.default.y, self.default.z,
                        self.default.e, self.default.q, self.default.n,
                        self.default.a, self.default.b)
        self.assertFalse(a == self.default)
        a = Coordinates(self.default.x, self.default.y, -self.default.z,
                        self.default.e, self.default.q, self.default.n,
                        self.default.a, self.default.b)
        self.assertFalse(a == self.default)
        a = Coordinates(self.default.x, self.default.y, self.default.z,
                        -self.default.e, self.default.q, self.default.n,
                        self.default.a, self.default.b)
        self.assertFalse(a == self.default)
        a = Coordinates(self.default.x, self.default.y, self.default.z,
                        self.default.e, -self.default.q, self.default.n,
                        self.default.a, self.default.b)
        self.assertFalse(a == self.default)
        a = Coordinates(self.default.x, self.default.y, self.default.z,
                        self.default.e, self.default.q, -self.default.n,
                        self.default.a, self.default.b)
        self.assertFalse(a == self.default)

    def test_str(self):
        self.assertTrue(isinstance(str(self.default), str))

    def test_abs(self):
        c = Coordinates(-1, -2.5, -99, -23, -2, -4, -6, -8.5)
        # noinspection PyTypeChecker
        r = abs(c)
        self.assertEqual(r.x, 1.0)
        self.assertEqual(r.y, 2.5)
        self.assertEqual(r.z, 99.0)
        self.assertEqual(r.e, 23.0)
        self.assertEqual(r.q, 2.0)
        self.assertEqual(r.n, 4.0)
        self.assertEqual(r.a, 6.0)
        self.assertEqual(r.b, 8.5)


if __name__ == '__main__':
    unittest.main()
