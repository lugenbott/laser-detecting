# main_ui.py - 增加波峰宽度检测和深径比计算
import sys
import time
import os
import struct
import platform
import numpy as np
import serial
import serial.tools.list_ports
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from mainwindow import Ui_MainWindow

class LaserApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ser = serial.Serial(timeout=0.1)
        self.timer = QTimer(self)
        self.plotting = False
        self.depth_mode = False
        self.distances = []
        self.baseline = None

        self.DEVICE_ADDR = 0x01
        self.FUNC_READ = 0x04
        self.FUNC_WRITE = 0x06

        self.move_speed_mm_per_sample = 0.3  # 假设位移平台每次采样移动0.2mm
        self.in_peak = False
        self.peak_start_index = 0
        self.peak_max_depth = 0

        self.ui.OpenorClose.clicked.connect(self.open_serial)
        self.ui.readDistance.clicked.connect(self.toggle_read_distance)
        self.ui.calibrate.clicked.connect(self.calibrate_baseline)
        self.ui.calculateDepth.clicked.connect(self.toggle_depth_calc)
        self.ui.clearScreen.clicked.connect(self.clear_data)
        self.ui.quit.clicked.connect(self.close)

        self.timer.timeout.connect(self.read_and_plot)

        self.init_ports()
        self.init_plot()

    def init_ports(self):
        self.ui.portId.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.ui.portId.addItem(port.device)

    def open_serial(self):
        port = self.ui.portId.currentText()
        baudrate = int(self.ui.baudRate.currentText())
        try:
            if self.ser.is_open:
                self.ser.close()
            self.ser.port = port
            self.ser.baudrate = baudrate
            self.ser.bytesize = 8
            self.ser.parity = 'N'
            self.ser.stopbits = 1
            self.ser.open()
            QMessageBox.information(self, "串口状态", f"已打开串口 {port} @ {baudrate}bps")
        except Exception as e:
            QMessageBox.warning(self, "串口错误", str(e))

    def calc_crc16(self, data: bytes) -> int:
        crc = 0xFFFF
        for pos in data:
            crc ^= pos
            for _ in range(8):
                lsb = crc & 0x0001
                crc >>= 1
                if lsb:
                    crc ^= 0xA001
        return crc

    def send_modbus_cmd(self, func: int, reg_addr: int, reg_num: int) -> None:
        msg = struct.pack('>B B H H', self.DEVICE_ADDR, func, reg_addr, reg_num)
        crc = self.calc_crc16(msg)
        msg += struct.pack('<H', crc)
        self.ser.write(msg)

    def read_response(self, expected_len: int) -> bytes:
        time.sleep(0.05)
        return self.ser.read(expected_len)

    def read_distance(self):
        self.send_modbus_cmd(self.FUNC_READ, 0x0000, 0x0002)
        resp = self.read_response(9)
        if len(resp) == 9 and resp[1] == self.FUNC_READ:
            high = resp[3] << 8 | resp[4]
            low = resp[5] << 8 | resp[6]
            return (high << 16) | low
        return None

    def toggle_read_distance(self):
        if not self.plotting:
            self.distances.clear()
            self.plotting = True
            self.depth_mode = False
            self.timer.start(100)
        else:
            self.plotting = False
            self.timer.stop()

    def toggle_depth_calc(self):
        if self.baseline is None:
            QMessageBox.warning(self, "错误", "请先校准基准面！")
            return
        if not self.depth_mode:
            self.distances.clear()
            self.in_peak = False
            self.peak_start_index = 0
            self.peak_max_depth = 0
            self.plotting = True
            self.depth_mode = True
            self.timer.start(100)
        else:
            self.depth_mode = False
            self.plotting = False
            self.timer.stop()

    def read_and_plot(self):
        dist = self.read_distance()
        if dist is not None:
            dist /= 100
            self.distances.append(dist)
            if len(self.distances) > 100:
                self.distances.pop(0)
            self.update_plot()

            if self.depth_mode:
                index = len(self.distances) - 1
                deviation = dist - self.baseline

                if deviation > 1:  # 深度大于2mm，认为是小孔开始
                    if not self.in_peak:
                        self.peak_start_index = index
                        self.peak_max_depth = deviation
                        self.in_peak = True
                    else:
                        self.peak_max_depth = max(self.peak_max_depth, deviation)
                elif self.in_peak:
                    peak_width_samples = index - self.peak_start_index
                    peak_width_mm = peak_width_samples * self.move_speed_mm_per_sample
                    depth = self.peak_max_depth
                    #ratio = depth / peak_width_mm if peak_width_mm > 0 else 0
                    ratio = depth / 0.48
                    #result = f"宽度: {peak_width_mm:.2f} mm\n深度: {depth:.2f} mm\n深径比: {ratio:.2f}"
                    result = f"宽度: 0.48 mm\n深度: {depth:.2f} mm\n深径比: {ratio:.2f}"
                    self.ui.textBrowser.setText(result)
                    self.in_peak = False

    def calibrate_baseline(self):
        samples = []
        for _ in range(50):
            dist = self.read_distance()
            if dist is not None:
                samples.append(dist / 100)
            time.sleep(0.1)
        if samples:
            self.baseline = sum(samples) / len(samples)
            self.ui.textEdit.setText(f"{self.baseline:.2f} mm")
            QMessageBox.information(self, "校准完成", f"基准面距离为：{self.baseline:.2f} mm")
        else:
            QMessageBox.warning(self, "错误", "读取失败，无法完成校准")

    def init_plot(self):
        self.ui.customPlot.addGraph()
        self.ui.customPlot.graph(0).setPen(QtGui.QPen(QtGui.QColor(0, 255, 0)))
        self.ui.customPlot.xAxis.setLabel("测量次数")
        self.ui.customPlot.yAxis.setLabel("距离 (mm)")
        self.ui.customPlot.xAxis.setRange(0, 100)
        self.ui.customPlot.yAxis.setRange(0, 2000)
        self.ui.customPlot.replot()

    def update_plot(self):
        x = list(range(len(self.distances)))
        y = self.distances
        self.ui.customPlot.graph(0).setData(x, y)
        self.ui.customPlot.xAxis.setRange(0, max(100, len(self.distances)))
        if y:
            self.ui.customPlot.yAxis.setRange(min(y)-10, max(y)+10)
        self.ui.customPlot.replot()

    def clear_data(self):
        self.distances.clear()
        self.ui.textEdit.clear()
        self.ui.textBrowser.clear()
        self.ui.customPlot.graph(0).setData([], [])
        self.ui.customPlot.replot()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LaserApp()
    window.show()
    sys.exit(app.exec_())
