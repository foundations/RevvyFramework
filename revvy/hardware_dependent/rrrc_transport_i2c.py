from smbus2 import i2c_msg, SMBus
from revvy.rrrc_transport import RevvyTransportInterface, RevvyTransport


class RevvyTransportI2CImpl:
    def __init__(self, bus):
        self._bus = bus

    def bind(self, address):
        return RevvyTransport(RevvyTransportI2CDevice(address, self._bus))


class RevvyTransportI2CDevice(RevvyTransportInterface):
    def __init__(self, address, bus):
        self._address = address
        self._bus = bus

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


class RevvyTransportI2C:
    def __enter__(self):
        self._bus = SMBus(1)
        return RevvyTransportI2CImpl(self._bus)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._bus.close()
