import os
import time
import keyboard
import matplotlib.pyplot as plt
import numpy as np
from script.laser_detecting import read_distance 

class LaserMenu:
    def __init__(self):
        self.running = True

    def show_menu(self):
        print("\n======= 激光测距传感器主控菜单 =======")
        print("1. 实时读取距离")
        print("2. 计算深度范围（最小-最大差值）并绘图")
        print("3. 初始化")
        print("q. 退出程序")
        print("===================================")

    def start(self):
        while self.running:
            self.show_menu()
            choice = input("请输入你的选择：")
            if choice == '1':
                self.read_realtime_distance()
            elif choice == '2':
                self.calculate_depth_range()
            elif choice == 'q':
                print("退出程序，再见！")
                self.running = False
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
            min_val = min(min_val, dist)
            max_val = max(max_val, dist)
            delta = max_val - min_val
            print(f"最小值：{min_val} mm，最大值：{max_val} mm，深度差值：{delta} mm")

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
        save_path = os.path.join("data", "depth_range_plot.png")
        plt.savefig(save_path)
        print(f"图表已保存至 {save_path}")


if __name__ == "__main__":
    menu = LaserMenu()
    menu.start()
