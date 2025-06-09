# main_ui.py
import sys
import time
import os
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from mainwindow import Ui_MainWindow
from script.laser_detecting import read_distance
import serial.tools.list_ports

class LaserApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.serial = None
        self.timer = QTimer(self)
        self.plotting = False
        self.depth_mode = False
        self.distances = []
        self.baseline = None

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
            from script.LaserSensorCmd import ser
            ser.port = port
            ser.baudrate = baudrate
            ser.open()
            QMessageBox.information(self, "串口状态", f"已打开串口 {port} @ {baudrate}bps")
        except Exception as e:
            QMessageBox.warning(self, "串口错误", str(e))

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
            self.plotting = True
            self.depth_mode = True
            self.timer.start(100)
        else:
            self.depth_mode = False
            self.plotting = False
            self.timer.stop()

    def read_and_plot(self):
        dist = read_distance()
        if dist is not None:
            dist /= 100
            self.distances.append(dist)
            if len(self.distances) > 100:
                self.distances.pop(0)
            self.update_plot()

            if self.depth_mode:
                max_val = max(self.distances)
                depth = max_val - self.baseline
                self.ui.textBrowser.setText(f"{depth:.2f} mm")

    def calibrate_baseline(self):
        samples = []
        for _ in range(50):
            dist = read_distance()
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
        self.ui.customPlot.graph(0).clearData()
        self.ui.customPlot.replot()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LaserApp()
    window.show()
    sys.exit(app.exec_())
