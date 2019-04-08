#!/usr/bin/python3

import pybleno
import urllib.parse
import json

# constants
HM_10_UART_SERIVCE = '0000FFE0-0000-1000-8000-00805F9B34FB'.replace("-", "")
HM_10_UART_CHARACTERISTIC = '0000FFE1-0000-1000-8000-00805F9B34FB'.replace("-", "")
class UartCharacteristic(pybleno.Characteristic):
    def __init__(self, callback):
        pybleno.Characteristic.__init__(self, {
            'uuid': HM_10_UART_CHARACTERISTIC,
            'properties': ['write', 'write-without-response', 'notify'],
            'value': None,
          })
        self._rawData = bytearray()
        self._blockyList = []
        self._value = bytearray()
        self._updateValueCallback = None
        self._commandReceivedCallback = callback
        
    def onWriteRequest(self, data, offset, withoutResponse, callback):
        #print(repr(data))  # DEBUG
        head = data[0]
        if head == 0xff:
            self._commandReceivedCallback(data)
        elif head == 0xfe:
           self.readSyncedPacket(data[1:])
        else:
            # TODO warning/error
            print("Error: Unknown header")
        callback(pybleno.Characteristic.RESULT_SUCCESS)
      
    def readSyncedPacket(self, data):
        isFinalPacket = bool(data[0])
        self._rawData += data[1:]
        if isFinalPacket:
            decoded = urllib.parse.unquote(self._rawData.decode("utf-8"))  # TODO: Is encoding correct?
            try:
                self._blocklyList = json.loads(decoded)
                self._rawData = bytearray()
                print(repr(self._blocklyList))
            except json.decoder.JSONDecodeError:
                print("Error: Invalid JSON payload")

class UartService(pybleno.BlenoPrimaryService):
    def __init__(self, callback):
        pybleno.BlenoPrimaryService.__init__(self, {
            'uuid': HM_10_UART_SERIVCE,
            'characteristics': [
                UartCharacteristic(callback)
            ]})