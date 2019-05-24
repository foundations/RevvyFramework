import unittest

from revvy.rrrc_control import *


class TestParseStringList(unittest.TestCase):
    def test_empty_string_gives_empty_dict(self):
        data = parse_string_list(b"")
        self.assertEqual(data, {})

    def test_string_is_returned_as_dict_key(self):
        data = parse_string_list([0, 3, ord('f'), ord('o'), ord('o')])
        self.assertEqual(data, {'foo': 0})

    def test_multiple_strings_result_in_multiple_pairs_of_data(self):
        data = parse_string_list([0, 3, ord('f'), ord('o'), ord('o'), 1, 3, ord('b'), ord('a'), ord('r')])
        self.assertEqual(data, {'foo': 0, 'bar': 1})
