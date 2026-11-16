import unittest

from register.scales import company_probability, decile_points, linear_point, log_point
from register.stats import spearman


class Scales(unittest.TestCase):
    def test_log_limits(self):
        self.assertEqual(log_point(1 / 10), 10)
        self.assertEqual(log_point(1 / 10_000), 4)
        self.assertEqual(log_point(0.99 / 100_000), 1)
        self.assertEqual(log_point(0.0), 1)

    def test_log_is_monotonic(self):
        points = [log_point(10 ** (-e / 4)) for e in range(0, 32)]
        self.assertEqual(points, sorted(points, reverse=True))

    def test_decile_range(self):
        points = decile_points({f"s{i:02d}": i / 1000 for i in range(88)})
        self.assertEqual((min(points.values()), max(points.values())), (1, 10))

    def test_company_probability(self):
        self.assertAlmostEqual(company_probability(7.5e-5, 5000), 0.3127, places=3)
        self.assertEqual(linear_point(7.5e-5, 250), 1)


class Stats(unittest.TestCase):
    def test_spearman(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(spearman([1, 2, 2, 3], [1, 2, 2, 3]), 1.0)


if __name__ == "__main__":
    unittest.main()
