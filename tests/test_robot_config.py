import unittest

from revvy.robot_config import RobotConfig


class TestRobotConfig(unittest.TestCase):
    def test_not_valid_config_is_ignored(self):
        config = RobotConfig.from_string('not valid json')
        self.assertIsNone(config)

    def test_valid_config_needs_robotConfig_and_blocklies_keys(self):
        with self.subTest("Blockly only"):
            config = RobotConfig.from_string('{blocklies: []}')
            self.assertIsNone(config)

        with self.subTest("Robot Config only"):
            config = RobotConfig.from_string('{"robotConfig": {}}')
            self.assertIsNone(config)

        with self.subTest("Both"):
            config = RobotConfig.from_string('{"robotConfig": {}, "blocklies": []}')
            self.assertIsNotNone(config)

    def test_blocklies_are_added_to_scripts(self):
        json = '''
        {
            "robotConfig": {},
            "blocklies": [
                {"pythonCode": "some code", "assignments": {"layoutId": 0, "btnId": 0}},
                {"pythonCode": "other code", "assignments": {"layoutId": 0, "btnId": 1}}
            ]
        }'''
        config = RobotConfig.from_string(json)
        self.assertIn('script_btn_0', config.scripts)
        self.assertIn('script_btn_1', config.scripts)
        self.assertNotIn('script_btn_2', config.scripts)

        self.assertEqual('script_btn_0', config.controller.buttons[0])
        self.assertEqual('script_btn_1', config.controller.buttons[1])
        self.assertIsNone(config.controller.buttons[2])

        self.assertEqual('some code', config.scripts['script_btn_0']['script'])
        self.assertEqual(0, config.scripts['script_btn_0']['priority'])
