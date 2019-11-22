#!/usr/bin/python3
import serial


def send_cmd(ser, cmd):
    if ser.isOpen():
        ser.flushInput()
        ser.flushOutput()
        try:
            ser.write('{0}\r'.format(cmd).encode())
        except Exception as e:
            print('Error sending command {0} over serial.\n{1} '.format(cmd, str(e)))
            return None
        else:
            try:
                response = ser.read(64)
                response = [x for x in response.decode('utf-8').split() if x.rstrip('\x00')]
            except Exception as e:
                print('Error reading the serial response from our issued command: {0}\n{1}'.format(cmd, e))
                return None
            else:
                return response  # .decode('utf-8')
    else:
        print('Serial connection is not open!')
        return None


def main():
    with serial.Serial(
        port='/dev/ttyUSB0',
        baudrate=115200,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=1) \
            as serial_con:

        echo_off_cmd = 'ATE0'
        subshell_cmd = "AT"
        sig_str_cmd = "AT+CSQ"

        # The last element of the a stripped returned list should be either 'OK' or a '$' prompt, otherwise fail.
        subshell_response = send_cmd(serial_con, subshell_cmd)
        print('Get Subshell: \n{0}'.format(subshell_response))

        # The last element of the a stripped returned list should be either 'OK' or a '$' prompt, otherwise fail.
        echo_off_response = send_cmd(serial_con, echo_off_cmd)
        print('Get Subshell: \n{0}'.format(echo_off_response))

        # The last element of the list should be an 'OK'.  BUT, we need to be sure there are no empty elements
        # in which case we want to assume the first element is '+CSQ: 0-31, 0|99'
        sig_str_response = send_cmd(serial_con, sig_str_cmd)
        print('Sig strength response: \n{0}'.format(sig_str_response))


if __name__ == '__main__':
    main()
