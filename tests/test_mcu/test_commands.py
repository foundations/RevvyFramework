import unittest

from revvy.mcu.commands import Command
from revvy.mcu.rrrc_transport import Response, ResponseHeader


class MockTransport:
    def __init__(self, responses):
        self._responses = responses
        self._command_count = 0
        self._commands = []

    def send_command(self, command, payload=None) -> Response:
        response = self._responses[self._command_count]
        self._command_count += 1
        self._commands.append((command, payload))
        return response

    @property
    def command_count(self):
        return self._command_count

    @property
    def commands(self):
        return self._commands


# noinspection PyTypeChecker
class TestCommand(unittest.TestCase):
    def test_not_overwritten_command_id_raises_error(self):
        self.assertRaises(NotImplementedError, lambda: Command(None))

    def test_default_call_does_not_accept_arguments(self):
        class TestCommand(Command):
            @property
            def command_id(self):
                return 2

        c = TestCommand(None)
        self.assertRaises(NotImplementedError, lambda: c([1, 2, 3]))

    def test_call_sends_command(self):
        class TestCommand(Command):
            @property
            def command_id(self):
                return 2

        mock_transport = MockTransport([Response(ResponseHeader.Status_Ok, [])])
        c = TestCommand(mock_transport)
        self.assertEqual(0, mock_transport.command_count)
        c()
        self.assertEqual(1, mock_transport.command_count)
        self.assertEqual((2, []), mock_transport.commands[0])
