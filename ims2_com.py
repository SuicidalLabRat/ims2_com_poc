from pyftdi.serialext import serial_for_url
import time


def pyftdi_readline_fix(ser):
    original_read = ser.read

    def new_read(*args, **kwargs):
        ret_val = original_read(*args, **kwargs)
        if isinstance(ret_val, bytearray):
            return bytes(ret_val)
        else:
            return ret_val
    ser.read = new_read


my_ftdi_url = 'ftdi:///1'
baud_rate = 115200
timeout = 5

ser = serial_for_url(my_ftdi_url, baud_rate)
pyftdi_readline_fix(ser)


ser.write(b'at\r\n')
time.sleep(.3)
line1 = ser.readline()
print(line1.decode("utf-8"))

ser.write(b'AT+CSQ\r\n')
time.sleep(.3)
line2 = ser.readline()
print(line2.decode("utf-8"))

print('finished')
