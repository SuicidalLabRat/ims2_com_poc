#!/usr/bin/python3
import serial
import time
from json import dumps
#from time import sleep
# from datetime import datetime
from collections import deque

# https://python-3-patterns-idioms-test.readthedocs.io/en/latest/FunctionObjects.html


class Ims2Macro:
    """The INVOKER class"""
    def __init__(self):
        self._commands = []
        self._command_results = dict()  # Should this be a deque?

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
                class_name = type(c).__name__
                count = 0
                if hasattr(c, 'retry_count'):
                    retry_count = c.retry_count
                    print('{0} has attribute retry_count and its set to {1}'.format(class_name, retry_count))
                else:
                    print('{0} has no attribute retry_count.'.format(class_name))
                    retry_count = count

                while count <= retry_count:
                    count += 1
                    unix_time = time.time()

                    try:
                        cmd_result = c.execute(ser)
                    except Exception as e:
                        print('Command \"{0}\" failed:\n{1}'.format(c.cmd, e))
                        time.sleep(.5)
                    else:
                        if cmd_result:
                            print('{0} response: {1}'.format(class_name, cmd_result[c._success_index]))
                            self._command_results[c.cmd] = (str(unix_time), cmd_result)
                            break
                        else:
                            self._command_results[c.cmd] = (str(unix_time), None)
                            time.sleep(.5)


class Command(object):
    """The COMMAND interface"""
    def execute(self, ser):
        raise NotImplementedError


class GetCmdShell(Command):
    """ Get the IMS2 command shell.
    The IMS2 UART2 starts at the debug shell, however, to run AT commands we need to drop to the command shell.
    This command will always need to be run on the IMS2 before issuing AT commands.  Note, if no input is detected
    on the command shell for some period of time, it exits back to the debug shell.
    """
    cmd = 'AT'
    _success_codes = ('$', 'OK')
    _success_index = -1

    def __init__(self, retry_count=0):
        self.retry_count = retry_count

    def execute(self, ser):
        print("Subshell serial instance: {0}: ".format(id(ser)))
        try:
            subshell_response = Ims2CmdShell(self, ser)
        except Exception as e:
            print('Command \"{0}\" failed:\n{1}'.format(self.cmd, e))
            return None
        else:
            if subshell_response and subshell_response[self._success_index] in self._success_codes:
                return subshell_response
            else: return None


class SetEchoOff(Command):
    """Turns off the command shells echo feature.
    This is required before we can issue AT commands for which we expect to process the output,
    otherwise all kinds of extraneous data will be in the output stream.
    """
    cmd = 'ATE0'
    _success_codes = 'OK'
    _success_index = -1

    def __init__(self, retry_count=0):
        self.retry_count = retry_count

    def execute(self, ser):
        print("Echo Off serial instance: {0}: ".format(id(ser)))
        try:
            echo_off_response = Ims2CmdShell(self, ser)
        except Exception as e:
            print('Command \"{0}\" failed:\n{1}'.format(self.cmd, e))
            return None
        else:
            if echo_off_response and echo_off_response[self._success_index] in self._success_codes:
                return echo_off_response
            else:
                return None


class GetSigStrength(Command):
    """Gets the IMS2's current signal strength, in dBm."""
    cmd = "AT+SQNMONI=9"  # 'AT+CSQ'  ## NOTE: Unlike the short command, CSQ, the longform command, SQNMONI, fails
                          # if there isnt a carrier.
    _success_codes = 'OK'
    _success_index = -1
    _response_index = -2

    def __init__(self, retry_count=0):
        self.retry_count = retry_count

    def execute(self, ser):
        print("Signal Strength serial instance: {0}: ".format(id(ser)))
        try:
            sig_strength_response = Ims2CmdShell(self, ser)
        except Exception as e:
            print('Command \"{0}\" failed:\n{1}'.format(self.cmd, e))
            return None
        else:
            print(sig_strength_response)
            print(type(sig_strength_response))
            if sig_strength_response and sig_strength_response[self._success_index] in self._success_codes:
                return sig_strength_response
            else:
                return None


def Ims2CmdShell(calling_obj, ser):
    """This Receiver is the IMS2 command interface (should be a class?)"""
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
                response = ser.read(1024)  # 64)
                response = [x for x in response.decode('utf-8').split() if x.rstrip('\x00')]
            except Exception as e:
                print('Error reading the serial response from our issued command: {0}\n{1}'.format(calling_obj.cmd, e))
                return None
            else:
                return response
    else:
        print('Serial connection is not open!')
        return None


class Ims2Status(object):
    """CLIENT class"""
    def __init__(self):
        self._receiver = Ims2CmdShell()  # <-- our case requires arguments :/
        self._invoker = Ims2Macro()


def main():
    """Maybe move the required commands, i.e. getcmdshell and setecho to the receiver?"""
    macro = Ims2Macro()
    macro.add(GetCmdShell(3))
    macro.add(SetEchoOff())
    macro.add(GetSigStrength(3))
    macro.run()
    #print(macro.results)
    at_response = macro.results
    print(type(at_response))
    #dumps(at_response[1])
    #print('Sig Str: {0}'.format(macro.results['AT+SQNMONI=9'][1][4]))


if __name__ == '__main__':
    main()
