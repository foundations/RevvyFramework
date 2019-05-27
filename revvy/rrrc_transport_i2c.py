from smbus2 import SMBus, i2c_msg
from revvy.rrrc_transport import RevvyTransportInterface


class RevvyTransportI2CImpl(RevvyTransportInterface):
    def __init__(self, address):
        self._address = address
        self._bus = SMBus(1)

    def read(self, length):
        read_msg = i2c_msg.read(self._address, length)
        self._bus.i2c_rdwr(read_msg)
        return list(read_msg)

    def write(self, data):
        write_msg = i2c_msg.write(self._address, data)
        self._bus.i2c_rdwr(write_msg)

    def write_and_read(self, data, read_length):
        """
        Don't use this function as it generates a repeated start
        """
        write_msg = i2c_msg.write(self._address, data)
        read_msg = i2c_msg.read(self._address, read_length)
        self._bus.i2c_rdwr(write_msg, read_msg)
        return list(read_msg)

    def close(self):
        self._bus.close()


class RevvyTransportI2C:
    def __init__(self, address):
        self._address = address

    def __enter__(self):
        self._transport = RevvyTransportI2CImpl(self._address)
        return self._transport

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._transport.close()