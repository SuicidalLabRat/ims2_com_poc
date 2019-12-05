#!/usr/bin/python3
import os
import time
import serial
import signal
from glob import glob


class Ims2Macro:
    """Our INVOKER class"""
    def __init__(self):
        self._commands = []
        self._command_results = dict()  # If we end up wanting to do replays, should this be a list, or maybe deque()?

    @property
    def history(self):
        return self._command_results

    def add(self, command):
        self._commands.append(command)

    def run(self):
        for c in self._commands:
            class_name = type(c).__name__
            count = 0
            if hasattr(c, 'retry_count'):
                retry_count = c.retry_count
            else:
                retry_count = count

            while count <= retry_count:
                count += 1
                unix_time = int(time.time())

                try:
                    cmd_result = c.execute()
                except Exception as e:
                    print('{0} command \"{1}\" failed:\n{2}'.format(class_name, c.cmd, e))
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
    """COMMAND interface"""
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
        # print("Subshell serial instance: {0}: ".format(id(self._receiver._serial)))
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
        # print("Echo Off serial instance: {0}: ".format(id(self._receiver._serial)))
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
    cmd = "GetSigStrength"
    sig_keys = ['RSRP', 'RSRQ']

    def __init__(self, receiver, retry_count=0):
        self._receiver = receiver
        self.retry_count = retry_count
        self._getSigStrength = IssueSQNMONI(self._receiver)

    def execute(self):
        # print("Signal Strength serial instance: {0}: ".format(id(self._receiver._serial)))
        try:
            sig_str = self._getSigStrength.execute()
        except Exception as e:
            print('Command \"{0}\" failed:\n{1}'.format(self.cmd, e))
            return None
        else:
            if not sig_str:
                return None
            d = {x: sig_str[x] for x in self.sig_keys}
            return d


class IssueSQNMONI(Command):
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
        # print("IssueSQNMONI serial instance: {0}: ".format(id(self._receiver._serial)))
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


class FileName:
    fn = 0

    def __init__(self, count, ext):
        self._count = count
        self._ext = ext

    @property
    def next_name(self):
        if self.fn == self._count:
            self.fn = 0
        name = '{0:0>2}'.format(self.fn)
        self.fn += 1
        return '{0}.{1}'.format(name, self._ext)


class GracefulKiller:
    """Signal handler.  Lets try to be as graceful as possible in handling systemd's signals."""
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print('Received a kill signal! {}.'.format(signum))
        self.kill_now = True


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


def write_sig_str_file(fname, data):
    delimiter = ','
    if data:
        try:
            filedata = (
                data['GetSigStrength']['timestamp'],
                data['GetSigStrength']['cmd_return']['RSRP'],
                data['GetSigStrength']['cmd_return']['RSRQ']
            )
        except KeyError as e:
            print('Failed to create signal strength log file.  Expected {} key to be available.'.format(e))
            return None
        except Exception as e:
            print('Failed to create signal strength log file.  Unknown exception - {}.'.format(e))
            return None
        else:
            try:
                f = open(fname, 'w')
            except IOError as e:
                print('Error opening signature log file for writing. \n{}'.format(e))
            else:
                with f:
                    f.write(delimiter.join(filedata))
                    f.flush()
                    os.fdatasync(f)
                    # print(delimiter.join(filedata))
                    return True


def garbage_collection(path, ext):
    file_list = glob('{0}*.{1}'.format(path, ext))

    for filePath in file_list:
        try:
            os.remove(filePath)
        except Exception as e:
            print("Garbage collection error deleting file: {0}\n{1}".format(filePath, e))


def main():
    """
    This client code should parameterize the invoker with any commands.
    Maybe move the required commands, i.e. getcmdshell and setecho to the receiver?
    """
    serial_dev = '/dev/ttyUSB0'
    invoker = Ims2Macro()
    killer = GracefulKiller()
    sig_log_file_ext = 'ss'
    sig_file_path = '/tmp/'

    sig_log_file = FileName(10, sig_log_file_ext)
    garbage_collection(sig_file_path, sig_log_file_ext)

    with serial.Serial(
            port=serial_dev,
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

        while not killer.kill_now:
            invoker.run()
            at_response = invoker.history
            if at_response['GetSigStrength']['cmd_return']:
                file = '{0}{1}'.format(sig_file_path, sig_log_file.next_name)
                if file:
                    write_sig_str_file(file, at_response)
            else:
                print("It looks like there was an error running the sigstr at command. "
                      "Maybe there is no carrier or service available.")

            time.sleep(5)
        print('Gracefully stopped.')


if __name__ == '__main__':
    main()
