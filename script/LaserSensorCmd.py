import serial
import platform
import struct
import time

if platform.system() == "Windows":
    SERIAL_PORT = "COM4"
elif platform.system() == "Linux":
    SERIAL_PORT = "/dev/ttyUSB0"
else:
    raise EnvironmentError("Unsupported platform")

ser = serial.Serial(SERIAL_PORT, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=0.1)

def calc_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            lsb = crc & 0x0001
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc

def send_modbus_cmd(address: int, func: int, reg_addr: int, reg_num: int) -> None:
    msg = struct.pack('>B B H H', address, func, reg_addr, reg_num)
    crc = calc_crc16(msg)
    msg += struct.pack('<H', crc)  # 小端序CRC
    ser.write(msg)

def read_response(expected_len: int) -> bytes:
    time.sleep(0.05)
    response = ser.read(expected_len)
    return response
