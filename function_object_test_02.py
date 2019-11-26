#!/usr/bin/python3
import serial
import time
from json import dumps
# from time import sleep


class Ims2Macro:
    """Our INVOKER class"""
    def __init__(self):
        self._commands = []
        self._command_results = dict()  # Should this be a deque?

    @property
    def results(self):
        return self._command_results

    def add(self, command):
        self._commands.append(command)

    # Run commands on IMS2.
    def run(self, ser):
        for c in self._commands:
            # class_name = type(c).__name__
            count = 0
            if hasattr(c, 'retry_count'):
                retry_count = c.retry_count
            else:
                retry_count = count

            while count <= retry_count:
                count += 1
                unix_time = int(time.time())

                try:
                    cmd_result = c.execute(ser)
                except Exception as e:
                    print('AT command \"{0}\" failed:\n{1}'.format(c.cmd, e))
                    time.sleep(.5)
                else:
                    if cmd_result:
                        self._command_results[c.cmd] = {
                            'timestamp': str(unix_time),
                            'cmd_return': cmd_result
                        }
                        break
                    else:
                        self._command_results[c.cmd] = {
                            'timestamp': str(unix_time),
                            'cmd_return': None
                        }
                        time.sleep(.5)


class Command(object):
    """Base COMMAND interface"""
    def execute(self):
        raise NotImplementedError


class GetCmdShell(Command):
    """ Get the IMS2 command shell.
    The IMS2 UART2 connects to the debug shell, however, to run AT commands we need to drop to the command shell.
    This command will always need to be run on the IMS2 before issuing AT commands.  Note, if no input is detected
    on the command shell for some period of time, it exits back to the debug shell.
    """
    cmd = 'AT'
    _success_codes = ('$', 'OK')
    _success_index = -1

    def __init__(self, receiver, retry_count=0):
        self.retry_count = retry_count
        self._receiver = receiver

    def execute(self):
        # print("Subshell serial instance: {0}: ".format(id(ser)))
        try:
            subshell_response = self._receiver.issue_at_cmd(self)
        except Exception as e:
            print('AT command \"{0}\" failed:\n{1}'.format(self.cmd, e))
            return None
        else:
            if subshell_response and subshell_response[self._success_index] in self._success_codes:
                return subshell_response
            else:
                return None


class SetEchoOff(Command):
    """Turns off the command shells echo feature.
    This is required before we can issue AT commands for which we expect to process the output,
    otherwise all kinds of extraneous data will be in the output stream.
    """
    cmd = 'ATE0'
    _success_codes = 'OK'
    _success_index = -1

    def __init__(self, receiver, retry_count=0):
        self._receiver = receiver
        self.retry_count = retry_count

    def execute(self):
        # print("Echo Off serial instance: {0}: ".format(id(ser)))
        try:
            echo_off_response = self._receiver.issue_at_cmd(self)
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
    cmd = "AT+SQNMONI=9"    # NOTE: Unlike the CSQ command, SQNMONI will fail if there is no carrier.
    _success_codes = 'OK'
    _success_index = -1
    _response_index = -2
    _unmapped_response_fields = {
        'AT&T': 'carrier',
        'VZN': 'carrier',
        'OK': 'status'
    }

    def __init__(self, receiver, retry_count=0):
        self._receiver = receiver
        self.retry_count = retry_count

    def execute(self):
        # print("Signal Strength serial instance: {0}: ".format(id(ser)))
        try:
            sig_strength_response = self._receiver.issue_at_cmd(self)
        except Exception as e:
            print('Command \"{0}\" failed:\n{1}'.format(self.cmd, e))
            return None
        else:
            if sig_strength_response and sig_strength_response[self._success_index] in self._success_codes:

                sig_strength_response = [s.split(':') for s in sig_strength_response]

                return list_of_lists2dict(sig_strength_response, self._unmapped_response_fields)
            else:
                return None


class Ims2CmdShellReceiver:
    """This Receiver is the IMS2 AT command shell"""
    def __init__(self, ser):
        self._serial = ser

    def issue_at_cmd(self, calling_obj):
        if self._serial.isOpen():
            self._serial.flushInput()
            self._serial.flushOutput()
            try:
                self._serial.write('{0}\r'.format(calling_obj.cmd).encode())
            except Exception as e:
                print('Error sending command {0} over serial.\n{1} '.format(calling_obj.cmd, str(e)))
                return None
            else:
                try:
                    response = self._serial.read(1024)  # 64)
                    response = [x for x in response.decode('utf-8').split() if x.rstrip('\x00')]
                except Exception as e:
                    print('Error reading the serial response from AT command: {0}\n{1}'.format(calling_obj.cmd, e))
                    return None
                else:
                    return response
        else:
            # !!! We need to do something that will recover the connection is we detect its gone !!
            # So, will returning None enable us to decide if we want to reopen the connection?
            # or maybe the serial connection needs to be managed here?
            print('Serial connection is not open!')
            return None


# class Ims2Status(object):
#     """CLIENT class"""
#     def __init__(self):
#         self._receiver = Ims2CmdShell()  # <-- our case requires arguments :/
#         self._invoker = Ims2Macro()


def list_of_lists2dict(cmd_response_list, keymap=None):
    """The keymap is a dict of potentially orphan values we might find in the cmd_response_list, and the keys that
    they should end up associated with in the returned dictionary."""
    d = dict()
    for l in cmd_response_list:
        if isinstance(l, list) and len(l) < 2:
            if keymap:
                key = keymap.get(l[0], '')
                if key:
                    d[key] = l[0]
                    continue
                else:
                    l.append(None)
        d[l[0]] = l[1]
    return d


def main():
    # ! Do we need a clean, signal based, way to proactively shut this down,
    # ! or is the serial connection being managed by 'with' enough to insure
    # ! we gracefully close the serial connection when this service gets killed?
    """
    This client code should parameterize the invoker with any commands.
    Maybe move the required commands, i.e. getcmdshell and setecho to the receiver?"""
    serial_dev = '/dev/ttyUSB0'
    invoker = Ims2Macro()

    with serial.Serial(
            port=serial_dev,  # '/dev/tty.usbserial-FTAMFK8M',
            baudrate=115200,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1) \
            as serial_comm:

        receiver = Ims2CmdShellReceiver(serial_comm)
        invoker.add(GetCmdShell(receiver, 2))
        invoker.add(SetEchoOff(receiver))
        invoker.add(GetSigStrength(receiver, 2))
        # ! If the command list persists, we may return stale data!?
        invoker.run(serial_comm)
        at_response = invoker.results

        print(invoker.results)
        print(dumps(at_response['AT+SQNMONI=9']))
        print(at_response['AT+SQNMONI=9']['timestamp'])
        print(at_response['AT+SQNMONI=9']['cmd_return'])
        if at_response['AT+SQNMONI=9']['cmd_return']:
            print(at_response['AT+SQNMONI=9']['cmd_return']['RSRQ'])
        else:
            print("It looks like there was an error running the sigstr at command. "
                  "Maybe there is not service available.")
        print('json version:\n{}'.format(dumps(at_response['AT+SQNMONI=9'])))


if __name__ == '__main__':
    main()
