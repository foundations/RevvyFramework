import os, sys, time
from threading import Thread
from threading import Lock
from ctypes import c_uint32, c_uint8, c_uint16, c_char, c_char_p, c_int, POINTER, Structure, Array, Union, create_string_buffer
import array, fcntl, struct
from fcntl import ioctl
from singleton_decorator import singleton

import ctypes
from smbus2 import SMBus, i2c_msg, SMBusWrapper


import pdb
import random
import time

#DEBUG = True
DEBUG = False

RRRC_I2C_TARNSACTION_MIN_DATA_SIZE = 3
RRRC_I2C_TARNSACTION_MAX_DATA_SIZE = 128

#base
RRRC_I2C_CMD_STATUS_UNKNOWN = 0xFF #As ststus
RRRC_I2C_CMD_STATUS_OK      = 0x00 #As ststus
RRRC_I2C_CMD_STATUS_ERROR   = 0x01 #As ststus
RRRC_I2C_CMD_STATUS_BUSY    = 0x02 #As ststus
RRRC_I2C_CMD_STATUS_READY   = 0x03 #As ststus
RRRC_I2C_CMD_DUMMY          = 0x09 #As PING and TEST
RRRC_I2C_CMD_INIT           = 0x0A #No used now

#config
RRRC_I2C_CMD_SENSOR_GET_PORT_AMOUNT = 0x10
RRRC_I2C_CMD_MOTOR_GET_PORT_AMOUNT  = 0x11
RRRC_I2C_CMD_SENSOR_GET_TYPES       = 0x12
RRRC_I2C_CMD_MOTOR_GET_TYPES        = 0x13
#for sensor port
RRRC_I2C_CMD_SENSOR_SET_TYPE        = 0x30
RRRC_I2C_CMD_SENSOR_GET_TYPE        = 0x31
RRRC_I2C_CMD_SENSOR_GET_VALUE       = 0x32 #variable length 
#for motor port
RRRC_I2C_CMD_MOTOR_SET_TYPE         = 0x60
RRRC_I2C_CMD_MOTOR_GET_TYPE         = 0x61
RRRC_I2C_CMD_MOTOR_SET_DIR          = 0x62 #if need
RRRC_I2C_CMD_MOTOR_SET_STATE        = 0x63 #continios run or stop 
RRRC_I2C_CMD_MOTOR_GET_STATE        = 0x64
RRRC_I2C_CMD_MOTOR_SET_STEPS        = 0x65 #accurate steps amount 
RRRC_I2C_CMD_MOTOR_GET_POSITION     = 0x66
#other
RRRC_I2C_CMD_INDICATION_SET_STATUS_LEDS     = 0x92
RRRC_I2C_CMD_INDICATION_SET_RING_SCENARIO   = 0x93

SENSOR_NOTSET = "NOTSET"
MOTOR_NOTSET = "NOTSET"

class rrrc_transaction_cbuffer(Array):
    _length_ = 0
    _type_ = c_char    
rrrc_transaction_cbuffer_pointer_type = POINTER(rrrc_transaction_cbuffer)


class rrrc_port_types(Structure):
    _fields_ = [
        ('type', c_uint8),
        ('size', c_uint8),
        ('name', c_uint8)]    

class rrrc_transaction_buffer(Array):
    _length_ = RRRC_I2C_TARNSACTION_MAX_DATA_SIZE+2
    _type_ = c_uint8    
rrrc_transaction_buffer_pointer_type = POINTER(rrrc_transaction_buffer)

class rrrc_transaction_data(Array):
    _length_ = RRRC_I2C_TARNSACTION_MAX_DATA_SIZE
    _type_ = c_uint8
rrrc_transaction_data_pointer_type = POINTER(rrrc_transaction_data)    

class rrrc_transaction(Structure):
    _fields_ = [
        ('command', c_uint8),
        ('data_size', c_uint8),
        ('data_crc', c_uint8),        
        ('data', rrrc_transaction_data)]
    __slots__ = [name for name, type in _fields_]   

class rrrc_union_transaction(Union):
    _fields_ = [
        ("rrrc_transaction", rrrc_transaction),
        ("buffer", rrrc_transaction_buffer)
    ]
    def toByteArray(self):
        arr = bytearray()
        arr.append(self.rrrc_transaction.command)
        arr.append(self.rrrc_transaction.data_size)
        arr.append(self.rrrc_transaction.data_crc)
        for i in range(self.rrrc_transaction.data_size):
            arr.append(self.rrrc_transaction.data[i])
        return arr
    def fromByteArray(self, barr):
        if type(barr) != bytearray:
            raise ValueError("Wrong data size. Must be from %d to  %d " %RRRC_I2C_TARNSACTION_MIN_DATA_SIZE %RRRC_I2C_TARNSACTION_MIN_DATA_SIZE)
        sz = len(barr)
        if (sz<RRRC_I2C_TARNSACTION_MIN_DATA_SIZE) or (sz>RRRC_I2C_TARNSACTION_MIN_DATA_SIZE):
            raise ValueError("Wrong data size. Must be from %d to  %d " %RRRC_I2C_TARNSACTION_MIN_DATA_SIZE %RRRC_I2C_TARNSACTION_MIN_DATA_SIZE)
        self.rrrc_transaction.command = barr[0]
        self.rrrc_transaction.data_size = barr[0]
        self.rrrc_transaction.data_crc = barr[0]
        for i in range(self.rrrc_transaction.data_size):
            self.rrrc_transaction.data[i] = barr[i+3]

rrrc_union_transaction_pointer_type = POINTER(rrrc_union_transaction)   

def rrrc_trasaction_make(cmd, length, buf_in):
    buff = rrrc_union_transaction()
    buff.rrrc_transaction.command = cmd
    buff.rrrc_transaction.data_size = length
    buff.rrrc_transaction.data_crc = 0
    if len(buf_in) >= length:
        for i in range(length):
            buff.rrrc_transaction.data[i] = buf_in[i]

    return buff

def rrrc_trasaction_read_from(buff_in):
    if type(buff_in) != rrrc_union_transaction:
        sz = len(buff_in)
        ls = list(buff_in)
        buff = rrrc_union_transaction()
        for x in range(sz):
            buff.buffer[x] = ls[x]
            if x >= sz:
                break       
    #elif type(buff_in) == bytearray:
    else:
        buff = buff_in
        
    return rrrc_trasaction_make(buff.rrrc_transaction.command, buff.rrrc_transaction.data_size, buff.rrrc_transaction.data)

def rrrc_trasaction_write_to(cmd, length, buf_in):
    return rrrc_trasaction_make(cmd, length, buf_in)
        
    
class debug_bus(object):
    def __init__ (self, bus_name):
        self.bus_name = bus_name
        self.fd = 1
        self.request = rrrc_union_transaction()
        self.sensor_amount = 6
        self.motor_amount = 4
        self.sensors = {'non_set': 0, 'rrrc_sens_t1': 1, 'rrrc_sens_t2':2, 'rrrc_sens_t3':3}
        self.motors = {'non_set': 0, 'dc_motor': 1, 'step_motor':2}
    def read_block_data(self, addr, reg, size):
        cmd = self.request.rrrc_transaction.command
        resp = rrrc_union_transaction()
        err = random.randint(0, 1000)//990
        if err>0:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_ERROR
            resp.rrrc_transaction.data_size = 0        
        elif cmd == RRRC_I2C_CMD_DUMMY:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_OK
            resp.rrrc_transaction.data_size = 0
        elif cmd == RRRC_I2C_CMD_SENSOR_GET_PORT_AMOUNT:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_SENSOR_GET_PORT_AMOUNT
            resp.rrrc_transaction.data_size = 1
            resp.rrrc_transaction.data[0] = self.sensor_amount
        elif cmd == RRRC_I2C_CMD_MOTOR_GET_PORT_AMOUNT:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_MOTOR_GET_PORT_AMOUNT
            resp.rrrc_transaction.data_size = 1
            resp.rrrc_transaction.data[0] = self.motor_amount
        elif cmd == RRRC_I2C_CMD_SENSOR_GET_TYPES:
            idx = 0
            resp.rrrc_transaction.command = RRRC_I2C_CMD_SENSOR_GET_TYPES
            for name, key in self.sensors.items():
                sz = len(name)
                bytename = bytearray(name)
                resp.rrrc_transaction.data[idx] = key
                idx+=1
                resp.rrrc_transaction.data[idx] = sz
                idx+=1
                for x in bytename:
                    resp.rrrc_transaction.data[idx] = x
                    idx+=1
            resp.rrrc_transaction.data_size = idx         
        elif cmd == RRRC_I2C_CMD_MOTOR_GET_TYPES:
            idx = 0
            resp.rrrc_transaction.command = RRRC_I2C_CMD_MOTOR_GET_TYPES
            for name, key in self.motors.items():
                sz = len(name)
                bytename = bytearray(name)
                resp.rrrc_transaction.data[idx] = key
                idx+=1
                resp.rrrc_transaction.data[idx] = sz
                idx+=1
                for x in bytename:
                    resp.rrrc_transaction.data[idx] = x
                    idx+=1
            resp.rrrc_transaction.data_size = idx
        elif cmd == RRRC_I2C_CMD_SENSOR_SET_TYPE:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_OK
            resp.rrrc_transaction.data_size = 0             
        elif cmd == RRRC_I2C_CMD_SENSOR_GET_TYPE:
            val = random.randint(0, len(self.sensors))
            resp.rrrc_transaction.command = RRRC_I2C_CMD_SENSOR_GET_TYPE
            resp.rrrc_transaction.data_size = 1
            resp.rrrc_transaction.data[0] = val    
        elif cmd == RRRC_I2C_CMD_MOTOR_SET_TYPE:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_OK
            resp.rrrc_transaction.data_size = 0             
        elif cmd == RRRC_I2C_CMD_MOTOR_GET_TYPE:
            val = random.randint(0, len(self.motors))
            resp.rrrc_transaction.command = RRRC_I2C_CMD_MOTOR_GET_TYPE
            resp.rrrc_transaction.data_size = 1
            resp.rrrc_transaction.data[0] = val     
        elif cmd == RRRC_I2C_CMD_SENSOR_GET_VALUE:
            cnt = random.randint(1,6)
            resp.rrrc_transaction.command = RRRC_I2C_CMD_SENSOR_GET_VALUE
            resp.rrrc_transaction.data_size = 4*cnt
            for x in range(cnt):
                resp.rrrc_transaction.data[4*x+3] = random.randint(0, 255)
                resp.rrrc_transaction.data[4*x+2] = random.randint(0, 255)
                resp.rrrc_transaction.data[4*x+1] = random.randint(0, 255)
                resp.rrrc_transaction.data[4*x+0] = random.randint(0, 255)
        elif cmd == RRRC_I2C_CMD_MOTOR_GET_COUNT:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_MOTOR_GET_COUNT
            resp.rrrc_transaction.data_size = 4
            resp.rrrc_transaction.data[4*x+3] = random.randint(0, 255)
            resp.rrrc_transaction.data[4*x+2] = random.randint(0, 255)
            resp.rrrc_transaction.data[4*x+1] = random.randint(0, 255)
            resp.rrrc_transaction.data[4*x+0] = random.randint(0, 255)            
        elif cmd == RRRC_I2C_CMD_MOTOR_SET_STATE:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_OK
            resp.rrrc_transaction.data_size = 0        
        elif cmd == RRRC_I2C_CMD_MOTOR_GET_STATE:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_MOTOR_GET_STATE
            resp.rrrc_transaction.data_size = 1
            resp.rrrc_transaction.data[0] = random.randint(-127, 127)        
        elif cmd == RRRC_I2C_CMD_MOTOR_SET_STEPS:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_OK
            resp.rrrc_transaction.data_size = 0        
        else:
            resp.rrrc_transaction.command = RRRC_I2C_CMD_STATUS_UNKNOWN
            resp.rrrc_transaction.data_size = 0            
        return resp
    def write_block_data(self, addr, reg, data):
        self.request.buffer = data #rrrc_transaction.read_from(data)
        return    
    def write_quick(self, addr):
        return    




@singleton   
class rrrc_transport(object):
    #__metaclass__ = Singleton
    
    def __init__ (self, bus_name, addr):
        self.bus_name = bus_name
        self.bus_num = 1
        self.rrrc_addr = addr
        self.bus_mutex = Lock()
        if DEBUG == True:
            self.bus = debug_bus(self.bus_name)
        else:
            #self.bus = rrrc_i2c(self.bus_name, False)
            #self.bus = SMBus(self.bus_num, False)
            self.bus = SMBusWrapper(1)
            


    def rrrc_write(self, cmd, snd_data = None):
        self.bus_mutex.acquire(1)
        ret = True
        try:
            snd_size = 0
            if snd_data != None :
                snd_size = len(snd_data)
            request =  rrrc_trasaction_write_to(cmd, snd_size, snd_data)
                
            write = i2c_msg.write(self.rrrc_addr, request.toByteArray())
            read = i2c_msg.read(self.rrrc_addr, RRRC_I2C_TARNSACTION_MAX_DATA_SIZE)
        
            with SMBusWrapper(1) as bus:
                bus.i2c_rdwr(write)   
                #time.sleep(0.01)
                bus.i2c_rdwr(read)  
        except:
            ret = False
        finally:
            lst_wr = list(write)
            #print("request: ")
            #print(lst_wr)
            lst_rd = list(read)
            #print("response: ")
            #print(lst_rd)
            response = rrrc_trasaction_read_from(lst_rd)
            
            msg = response.rrrc_transaction
            if msg.command != RRRC_I2C_CMD_STATUS_OK:
                ret = False
        
        self.bus_mutex.release()
        return ret
    
    def rrrc_read(self, cmd, snd_data):
        self.bus_mutex.acquire(1)
        #request
        try:
            request =  rrrc_trasaction_write_to(cmd, len(snd_data), snd_data)
                
            write = i2c_msg.write(self.rrrc_addr, request.toByteArray())
            read = i2c_msg.read(self.rrrc_addr, RRRC_I2C_TARNSACTION_MAX_DATA_SIZE)
            
            with SMBusWrapper(1) as bus:
                bus.i2c_rdwr(write)   
                #time.sleep(0.01)
                bus.i2c_rdwr(read)  
        except:
            ret = False
        finally:            
            lst_wr = list(write)
            #print("request: ")
            #print(lst_wr)
            lst_rd = list(read)
            #print("response: ")
            #print(lst_rd)
            response = rrrc_trasaction_read_from(lst_rd)
            
            msg = response.rrrc_transaction
            
            rcv_data = bytearray(0)
            if msg.command == cmd:
                if msg.data_size > RRRC_I2C_TARNSACTION_MAX_DATA_SIZE:
                    msg.data_size = RRRC_I2C_TARNSACTION_MAX_DATA_SIZE
                rcv_data = bytearray(msg.data[0:(msg.data_size)])

        self.bus_mutex.release()
        return  rcv_data  
    
    def connected(self):
        val = (self.bus.fd>0)
            
        if val == True:
            try:
                self.bus.write_quick(self.rrrc_addr)
            except Exception as e:
                val = False                   
        
        return val
            
            

