import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# 数据
L_values = [10, 15, 20, 25, 30]
data = {
    10: [0.117783036, 0.3254224, 0.492476485, 0.693147181, 0.944461609],
    15: [0, 0.182321557, 0.405465108, 0.587786665, 0.810930216],
    20: [0.057158414, 0.251314428, 0.364643114, 0.538996501, 0.875468737],
    25: [0.117783036,0.251314428,0.405465108,0.587786665,0.944461609],
    30: [0.149531734, 0.287682072, 0.492476485, 0.693147181, 0.944461609]
}

x = np.array([0, 1, 2, 3, 4, 5])  # 横坐标从0开始

# 定义过原点的线性函数
def linear_func(x, k):
    return k * x

plt.figure(figsize=(8, 6))

# 进行拟合并绘图
for L in L_values:
    y = np.array([0] + data[L])  # 在y数据前添加0，使其与x对齐
    k_opt, _ = curve_fit(linear_func, x, y)
    y_fit = linear_func(x, k_opt[0])
    plt.plot(x, y_fit, label=f'L={L}, y={k_opt[0]:.4f}x')
    plt.scatter(x, y)  # 原始数据点

# 图例与标签
plt.xlabel("n")
plt.ylabel("ln(A0/An)")
plt.legend()
plt.grid()
plt.show()
