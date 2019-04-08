
import rrrc_transport

BUS_DEV_NAME = "/dev/i2c-1"
RRRC_BOARD_I2CADDR = 0x2D

class rrrc_control(object):
 
    def __init__ (self):
        self.bus = rrrc_transport.rrrc_transport(BUS_DEV_NAME, RRRC_BOARD_I2CADDR)
        self.sensor_ports = 0
        self.motor_ports = 0
        self.sensors = dict()
        self.morots = dict()
        
        self.sensor_ports = self.sensors_get_amount()
        self.motor_ports = self.motors_get_amount()
        
        self.sensors = self.sensor_get_avalible_types()
        self.morots = self.motor_get_avalible_types()

    def sensors_get_amount(self):
        """
        Read sensors amount from device.

        :param none
        :return: byte
        :rtype: int
        """
        val = 0
        data = bytearray(0)
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_SENSOR_GET_PORT_AMOUNT, data)
        if len(data)>0:
            val = data[0];
        return val
    
    def motors_get_amount(self):
        """
        Read motors amount from device.

        :param none
        :return: byte
        :rtype: int
        """
        val = 0
        data = bytearray(0)
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_MOTOR_GET_PORT_AMOUNT, data)
        if len(data)>0:
            val = data[0]          
        return val
    
    def sensor_get_avalible_types(self):
        """
        Read avalible sensor types from device.

        :param none
        :return:  dictionary of types format (Name:ID)
        :rtype: dict
        """
        val = dict()
        data = bytearray(0)
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_SENSOR_GET_TYPES, data)
        if len(data)>0: 
            idx = 0
            while idx<len(data):
                type_id = data[idx]
                idx += 1
                sz = data[idx]
                idx += 1
                name = data[idx:(idx+sz)].decode("utf-8")
                idx += sz
                val[name] = type_id
        
        return val    
    
    def motor_get_avalible_types(self):
        """
        Read avalible motor types from device.

        :param none
        :return:  dictionary of types format (Name:ID)
        :rtype: dict
        """
        val = dict()
        data = bytearray(0)
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_MOTOR_GET_TYPES, data)
        if len(data)>0: 
            idx = 0
            while idx<len(data):
                key = data[idx]
                idx += 1
                sz = data[idx]
                idx += 1
                name = data[idx:(idx+sz)].decode("utf-8")
                idx += sz
                val[name] = key
        
        return val    

    #sensors
    def sensor_set_type(self, port, sens_type):
        """
        Read avalible sensor types from device.

        :param port as int
        :param sens_type as int
        :return:  True or False
        :rtype: Boolean
        """
        #if port >= self.sensor_ports:
        #    raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.sensor_ports-1))
            #return False
        rq = bytearray(2)
        rq[0] = port
        rq[1] = sens_type
        return self.bus.rrrc_write(rrrc_transport.RRRC_I2C_CMD_SENSOR_SET_TYPE, rq)
    
    def sensor_get_type(self, port):
        """
        Read current setted sensor type for port

        :param port as int
        :return:  motor type_id
        :rtype: int
        """
        if port >= self.sensor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.sensor_ports-1))
        rq = bytearray(2)
        rq[0] = port
        rq[1] = 0
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_SENSOR_GET_TYPE, rq)        
        sens_type = 0 #non set
        if len(data)>0:
            sens_type = data[0]        
        return sens_type
    
    def sensor_get_value(self, port):
        """
        Read sensor value for port

        :param port as int
        :return:  list of ints
        :(because some sensors (as accelerometer)
        :  return many values (one val for each axis)))
        :rtype: list()
        """
        if port >= self.sensor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.sensor_ports-1))
        rq = bytearray(1)
        rq[0] = port
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_SENSOR_GET_VALUE, rq)
        sz = int(len(data)/4)
        idx = 0
        sens_val = list()
        #print(hex(sens_val))
        if sz > 0:
            for idx in range(sz):
                val = (data[4*idx]<<24)+(data[4*idx+1]<<16)+(data[4*idx+2]<<8)+data[4*idx+3]
                #print("sensor_get_value p%d [%d] = %s" % (port, idx, hex(val)))
                sens_val.append(val)
        return sens_val
    
    #motors    
    def motor_set_type(self, port, mot_type):
        """
        Read avalible motor types from device.

        :param port as int
        :param mot_type as int
        :return:  True or False
        :rtype: Boolean
        """
        if port >= self.motor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.motor_ports-1))
        ret = True
        rq = bytearray(2)
        rq[0] = port
        rq[1] = mot_type
        val = self.bus.rrrc_write(rrrc_transport.RRRC_I2C_CMD_MOTOR_SET_TYPE, rq)
        return val
    
    def motor_get_type(self, port):
        """
        Read current setted motor type for port

        :param port as int
        :return:  motor type_id
        :rtype: int
        """
        if port >= self.motor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.motor_ports-1))
        rq = bytearray(1)
        rq[0] = port
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_MOTOR_GET_TYPE, rq)       
        mot_type = 0
        if len(data)>0:
            mot_type = data[0]
        return mot_type
    
    def motor_get_counter(self, port):
        """
        Read motor steps amount for port

        :param port as int
        :return:  4 bytes
        :rtype: int
        """
        if port >= self.motor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.motor_ports-1))
        rq = bytearray(1)
        rq[0] = port
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_MOTOR_GET_COUNT, rq)      
        sz = len(data)/4
        idx = 0
        #mot_val = 0
        #if sz != 0:
        #    mot_val = (data[0]<<24)+(data[1]<<16)+(data[2]<<8)+data[3]
            
        sz = len(data)/4
        idx = 0
        mot_val = list()
        #print(hex(sens_val))
        if sz > 0:
            for idx in range(sz):
                val = (data[4*idx]<<24)+(data[4*idx+1]<<16)+(data[4*idx+2]<<8)+data[4*idx+3]
                #print("sensor_get_value p%d [%d] = %s" % (port, idx, hex(val)))
                mot_val.append(val)    
        return mot_val
    
    def motor_set_state(self, port, state):
        """
        Set motor state for port

        :param port as int
        :param state as int  from -127 to 127
        : from -127 to -1 -- speed of reverse  run
        : 0 -- stop
        : from 1 to 127 -- speed of forward run
        :return:  True or False
        :rtype: Boolean
        """
        if port >= self.motor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.motor_ports-1))
        ret = True
        rq = bytearray(5)
        rq[0] = port
       
        if state < 0:
            unsignedState = 1**32-abs(state)
        else:
            unsignedState = state
            
        rq[1] = unsignedState >> 24 & 0xFF
        rq[2] = unsignedState >> 16 & 0xFF
        rq[3] = unsignedState >> 8  & 0xFF
        rq[4] = unsignedState >> 0  & 0xFF
            
        val = self.bus.rrrc_write(rrrc_transport.RRRC_I2C_CMD_MOTOR_SET_STATE, rq)
        return val
    
    def motor_get_position(self, port):
        """
        Read motor current state for port

        :param port as int
        :return:  byte
        :rtype: int
        """
        if port >= self.motor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.motor_ports-1))
        rq = bytearray(1)
        rq[0] = port
        data = self.bus.rrrc_read(rrrc_transport.RRRC_I2C_CMD_MOTOR_GET_POSITION, rq)
        return data
    
    def motor_set_config(self, port, config):
        """
        Set motor amount steps state for port

        :param port as int
        :param state as int  from -127 to 127
        : from -127 to -1 -- speed of reverse  run
        : 0 -- stop
        : from 1 to 127 -- speed of forward run
        :return:  True or False
        :rtype: Boolean
        """
        if port >= self.motor_ports:
            raise ValueError("Wrong port number. Must be from 0 to  %d " % (self.motor_ports-1))
        else:
            ret = True
            rq = bytearray(1)
            rq[0] = port
            for b in config:
                rq.append(b)
            val = self.bus.rrrc_write(rrrc_transport.RRRC_I2C_CMD_MOTOR_SET_STEPS, rq)
            return val
        return 0
        
    def indicator_set_led(self, led, r, g, b):
        rq = bytearray(4)
        rq[0] = led
        rq[1] = r
        rq[2] = g
        rq[3] = b
        val = self.bus.rrrc_write(rrrc_transport.RRRC_I2C_CMD_INDICATION_SET_STATUS_LEDS, rq)
        return val