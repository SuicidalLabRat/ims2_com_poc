import os
import errno
import time
import struct

# These message contructing functions could be broken out as a class or its own module
def encode_msg_size(size: int) -> bytes:
    return struct.pack("<I", size)

def decode_msg_size(size_bytes: bytes) -> int:
    return struct.unpack("<I", size_bytes)[0]

def create_msg(content: bytes) -> bytes:
    size = len(content)
    return encode_msg_size(size) + content


# This could be in main or its own writer.py
#import os
#from message import create_msg

if __name__ == "__main__":
    IPC_FIFO_NAME = "/tmp/testpipe"

    fifo = os.open(IPC_FIFO_NAME, os.O_WRONLY)
    try:
        while True:
            #name = input("Enter a name: ")
            #content = f"Hello {name}!".encode("utf8")
            content = "Message {0}\n".format(time.time()).encode("utf8")
            msg = create_msg(content)
            os.write(fifo, msg)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nGoodbye!")
    finally:
        os.close(fifo)