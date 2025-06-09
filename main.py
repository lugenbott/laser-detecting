from datetime import datetime
import os
import time
import keyboard
import matplotlib.pyplot as plt
import numpy as np
from script.laser_detecting import read_distance 

class LaserMenu:
    def __init__(self):
        self.__running = True
        self.__baseline = None

    def show_menu(self):
        print("\n======= 激光测距传感器主控菜单 =======")
        print("1. 实时读取距离")
        print("2. 计算深度范围（最小-最大差值）并绘图")
        print("3. 校准基准面")
        print("4. 读取当前基准面距离")
        print("q. 退出程序")
        print("===================================")

    def start(self):
        while self.__running:
            self.show_menu()
            choice = input("请输入你的选择：")
            if choice == '1':
                self.read_realtime_distance()
            elif choice == '2':
                self.calculate_depth_range()
            elif choice == '3':
                self.calibrate_baseline()
            elif choice == '4':
                self.get_baseline()
            elif choice == 'q':
                print("退出程序，再见！")
                self.__running = False
            else:
                print("无效输入，请重新选择。")

    def read_realtime_distance(self):
        print("按下 Ctrl+C 停止实时读取")
        try:
            while True:
                dist = read_distance()
                dist=dist/100
                print(f"当前距离：{dist} mm")
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("\n已停止实时读取")

    def calculate_depth_range(self):
        print("正在记录距离变化，按下 q 键退出...")

        failure_count = 0
        while self.__baseline is None:
            self.calibrate_baseline()
            failure_count += 1
            if failure_count > 3:
                print("⚠ 初始化失败，请检查传感器连接或位置。")
                return

        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
        MAX_POINTS = 200
        distances = [np.nan] * MAX_POINTS
        counts = list(range(MAX_POINTS))
        fig, ax = plt.subplots()
        line, = ax.plot(counts, distances, 'g-')
        ax.set_xlabel('测量次数')
        ax.set_ylabel('距离 (mm)')
        ax.set_title('实时最大-最小距离差')
        plt.ion()

        idx = 0
        min_val = float('inf')
        max_val = float('-inf')

        while True:
            dist = read_distance()
            dist=dist/100
            if dist is None:
                continue
            max_val = max(max_val, dist)
            delta = max_val - self.__baseline
            print(f"最大值：{max_val} mm，深度差值：{delta:.2f} mm")

            if idx >= len(distances):
                distances.extend([np.nan] * MAX_POINTS)
                counts.extend(range(len(counts), len(counts) + MAX_POINTS))
                line.set_xdata(counts)
                ax.set_xlim(0, len(counts) - 1)
            distances[idx] = dist
            valid_distances = [d if d is not None else np.nan for d in distances]
            line.set_ydata(valid_distances)
            ax.relim()
            ax.autoscale_view(scaley=True)
            plt.draw()
            plt.pause(0.01)
            idx += 1

            if keyboard.is_pressed('q'):
                break

        plt.ioff()
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join("data", f"depth_range_plot_{timestamp}.png")
        plt.savefig(save_path)
        print(f"图表已保存至 {save_path}")
    
    def calibrate_baseline(self):
        print("\n正在进行基准距离初始化，请保持传感器对准参考平面...")
        duration = 5  # 秒
        interval = 0.1  # 每 0.1 秒读取一次
        samples = []

        for i in range(int(duration / interval)):
            dist = read_distance()
            if dist is not None:
                samples.append(dist)
            time.sleep(interval)

        if samples:
            self.__baseline = sum(samples) / len(samples)
            self.__baseline = self.__baseline / 100
            print(f"✅ 基准距离初始化完成，平均值为：{self.__baseline:.2f} mm")
        else:
            print("⚠ 初始化失败，未能读取到有效数据")

    def get_baseline(self):
        if self.__baseline is None:
            print("⚠ 请先进行基准距离初始化")
            return None
        return self.__baseline

if __name__ == "__main__":
    menu = LaserMenu()
    menu.start()
