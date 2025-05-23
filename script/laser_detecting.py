from .LaserSensorCmd import send_modbus_cmd, read_response, calc_crc16, ser
import matplotlib.pyplot as plt
import numpy as np
import struct
import os
import time
import keyboard

DEVICE_ADDR = 0x01
FUNC_READ = 0x04
FUNC_WRITE = 0x06

def read_distance():
    '''
    读取距离值
    返回值: 距离值(单位mm)
    '''
    send_modbus_cmd(DEVICE_ADDR, FUNC_READ, 0x0000, 0x0002)
    resp = read_response(9)
    if len(resp) == 9 and resp[1] == FUNC_READ:
        high = resp[3] << 8 | resp[4]
        low = resp[5] << 8 | resp[6]
        return (high << 16) | low
    return None

def read_mode():
    return _read_single_register(0x0001)

def read_light_intensity():
    return _read_single_register(0x0002)

def read_threshold():
    return _read_single_register(0x0003)

def read_analog_mode():
    return _read_single_register(0x0004)

def read_laser_status():
    return _read_single_register(0x0005)

def _read_single_register(addr):
    send_modbus_cmd(DEVICE_ADDR, FUNC_READ, addr, 0x0001)
    resp = read_response(7)
    if len(resp) == 7 and resp[1] == FUNC_READ:
        return resp[3] << 8 | resp[4]
    return None

# ---------- 写入功能部分 ----------

def write_register(addr, value):
    msg = struct.pack('>B B H H', DEVICE_ADDR, FUNC_WRITE, addr, value)
    crc = calc_crc16(msg)
    msg += struct.pack('<H', crc)
    ser.write(msg)
    time.sleep(0.05)
    resp = ser.read(8)
    if len(resp) == 8 and resp[1] == FUNC_WRITE:
        return True
    return False

def set_mode(value):
    """0: 标准，1: 高速，2: 高精度"""
    return write_register(0x0001, value)

def set_threshold(value):
    """设置阈值（单位mm）"""
    return write_register(0x0003, value)

def set_analog_mode(value):
    """0: 关闭；1: 4~20mA"""
    return write_register(0x0004, value)

def set_laser_status(on=True):
    """打开或关闭激光"""
    return write_register(0x0005, 1 if on else 0)

if __name__ == "__main__":
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = True

    MAX_POINTS = 200
    distances = [None] * MAX_POINTS
    counts = list(range(MAX_POINTS))
    fig, ax = plt.subplots()
    line, = ax.plot(counts, [None]*MAX_POINTS, 'b-')
    ax.set_xlabel('测量次数')
    ax.set_ylabel('距离 (mm)')
    ax.set_title('实时距离-测量次数图')
    plt.ion()

    idx = 0
    while True:
        dist = read_distance()
        # 动态扩展数据
        if idx >= len(distances):
            distances.extend([None] * MAX_POINTS)
            counts.extend(range(len(counts), len(counts) + MAX_POINTS))
            line.set_xdata(counts)
            ax.set_xlim(0, len(counts) - 1)
        distances[idx] = dist
        # 只显示有效数据
        valid_distances = [d if d is not None else np.nan for d in distances]
        line.set_ydata(valid_distances)
        ax.set_xlim(0, len(counts) - 1)
        ax.relim()
        ax.autoscale_view(scaley=True)
        plt.draw()
        plt.pause(0.001)
        idx += 1

        if keyboard.is_pressed('q'):
            print("退出程序")
            break
    
    # 退出后保存图表
    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", "distance_plot.png")
    plt.ioff()
    plt.savefig(save_path)
    print(f"图表已保存到 {save_path}")
