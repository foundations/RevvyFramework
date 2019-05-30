import unittest

from revvy.configuration.features import FeatureMap
from revvy.configuration.version import Version


class TestFeatureMap(unittest.TestCase):
    def test_raise_error_when_version_is_too_old(self):
        fm = FeatureMap({'1.0': {}})

        self.assertRaises(ValueError, lambda: fm.get_features(Version('0.1')))

    def test_selects_newest_object_before_given_version(self):
        feature_map = {
            '1.0': '1.0.0',
            '1.0-r1': '1.0.1',
            '1.1-r0': '1.1.0',
        }
        fm = FeatureMap(feature_map)

        features = fm.get_features(Version('1.0-r2'))
        self.assertEqual('1.0.1', features)
