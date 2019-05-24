import unittest

from revvy.rrrc_control import *


class TestParseStringList(unittest.TestCase):
    def test_empty_string(self):
        data = parse_string_list(b"")
        self.assertEqual(data, {})

    def test_string_is_returned_as_dict_key(self):
        data = parse_string_list([0, 3, ord('f'), ord('o'), ord('o')])
        self.assertEqual(data, {'foo': 0})
