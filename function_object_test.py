#!/usr/bin/python3
import serial
from collections import deque
from datetime import datetime

# FunctionObjects/CommandPattern.py
# https://python-3-patterns-idioms-test.readthedocs.io/en/latest/FunctionObjects.html
class Command(object):
    """The COMMAND interface"""
    # def __init__(self, obj):
    #     self._obj = obj
    #
    # def execute(self, obj):
    #     raise NotImplementedError
    def execute(self, ser): #  pass
        raise NotImplementedError


class GetCmdShell(Command):
    cmd = 'AT'
    _success_codes = ('$', 'OK')
    _success_index = -1  # 'Where in a response list is the string I want?  Support slicing syn'

    def __init__(self, retry_count=0):
        self._retry_count = retry_count

    def execute(self, ser):
        print('Retry count = {0}'.format(self._retry_count))
        try:
            subshell_response = send_cmd(self, ser)
        except Exception:
            raise
        else:
            count = 0

            while count < self._retry_count:
                if subshell_response:

                    if subshell_response[self._success_index:] in self._success_codes:
                        print('Response from GetCmdShell: \n{0}\n'.format(subshell_response))
                        print('Success code: {0}'.format(subshell_response[self._success_index:]))
                        return subshell_response
                    count += 1



    #def _response_test(self):

class SetEchoOff(Command):
    cmd = 'ATE0'
    success_codes = ('OK')
    response_index = 'Where in a response list is the string I want?'

    def __init__(self, retry_count=0):
        self._retry_count = retry_count

    def execute(self, ser):
        print("Set echo off: {0}\nType{1}\n{2}\n".format(self.cmd, type(ser), id(ser)))
        echo_off_response = send_cmd(self, ser)
        print('Turn off echo: \n{0}\n'.format(echo_off_response))

class GetSigStrength(Command):
    cmd = 'AT+CSQ'
    success_codes = ('OK')
    response_index = -2

    def __init__(self, retry_count=0):
        self._retry_count = retry_count

    def execute(self, ser):
        print("Get signal strength: {0}\nType{1}\n{2}\n".format(self.cmd, type(ser), id(ser)))
        sig_strength_response = send_cmd(self, ser)
        print('Get Signal Strength: \n{0}\n'.format(sig_strength_response))
        print('Signal Strength: {0}'.format(sig_strength_response[self.response_index]))

# An object that holds commands:
#
class Macro:
    """The INVOKER class"""
    def __init__(self):
        self._commands = []
        self._command_results = dict()

    @property
    def results(self):
        return self._command_results

    def add(self, command):
        self._commands.append(command)

    # Run commands on IMS2.
    def run(self, dev='/dev/ttyUSB0'):
        with serial.Serial(
                port=dev,  # '/dev/tty.usbserial-FTAMFK8M',
                baudrate=115200,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1) \
                as ser:
            for c in self._commands:
                # retry_count = c.retry_count
                dt = datetime.now()
                try:
                    cmd_result = c.execute(ser)
                except Exception as ex:
                    raise
                else:
                    self._command_results[c.cmd] = (str(dt), cmd_result)
                # For this to keep the connection open, this (run()) instance method would need to
                # remain active, otherwise the with statement will close and clean up the serial.Serial instance.


def send_cmd(calling_obj, ser):
    """The Receiver (should be a class?)"""
    if ser.isOpen():
        ser.flushInput()
        ser.flushOutput()
        try:
            ser.write('{0}\r'.format(calling_obj.cmd).encode())
        except Exception as e:
            print('Error sending command {0} over serial.\n{1} '.format(calling_obj.cmd, str(e)))
            return None
        else:
            try:
                response = ser.read(64)
                response = [x for x in response.decode('utf-8').split() if x.rstrip('\x00')]
            except Exception as e:
                print('Error reading the serial response from our issued command: {0}\n{1}'.format(calling_obj.cmd, e))
                return None
            else:
                return response
    else:
        print('Serial connection is not open!')
        return None


def main():
    macro = Macro()
    macro.add(GetCmdShell(3))
    # macro.add(SetEchoOff())
    # macro.add(GetSigStrength())
    macro.run()
    print(macro.results['AT'])

    # sleep(3)
    # macro.run()
    #
    # sleep(3)
    # macro.run()

    # with serial.Serial(
    #     port='/dev/ttyUSB0',
    #     baudrate=115200,
    #     bytesize=8,
    #     parity='N',
    #     stopbits=1,
    #     timeout=1) \
    #         as serial_con:
    #
    #     echo_off_cmd = 'ATE0'
    #     subshell_cmd = "AT"
    #     sig_str_cmd = "AT+CSQ"
    #
    #     # The last element of the a stripped returned list should be either 'OK' or a '$' prompt, otherwise fail.
    #     subshell_response = send_cmd(serial_con, subshell_cmd)
    #     print('Get Subshell: \n{0}'.format(subshell_response))
    #
    #     # The last element of the a stripped returned list should be either 'OK' or a '$' prompt, otherwise fail.
    #     echo_off_response = send_cmd(serial_con, echo_off_cmd)
    #     print('Get Subshell: \n{0}'.format(echo_off_response))
    #
    #     # The last element of the list should be an 'OK'.  BUT, we need to be sure there are no empty elements
    #     # in which case we want to assume the first element is '+CSQ: 0-31, 0|99'
    #     sig_str_response = send_cmd(serial_con, sig_str_cmd)
    #     print('Sig strength response: \n{0}'.format(sig_str_response))


if __name__ == '__main__':
    main()
