from utils import *
from ble_revvy import *
from longmessage import LongMessageStorage, LongMessageHandler

def main():
    dnp = DeviceNameProvider(FileStorage('device_name.txt'))
    device_name = Observable(dnp.get_device_name())

    def on_device_name_changed(new_name):
        print('Device name changed to {}'.format(new_name))
        dnp.update_device_name(new_name)

    device_name.subscribe(on_device_name_changed)

    ble = RevvyBLE(device_name, getserial(), LongMessageHandler(LongMessageStorage("/home/pi/longmsg/")))

    try:
        ble.start()
        while True:
            time.sleep(1)
    finally:
        ble.stop()

    print('terminated.')

if __name__ == "__main__":
    main()