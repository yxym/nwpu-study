import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

# 你的实验数据 (X: L, Y: T^2)
L = np.array([0.1136667,0.1476667,0.1946667,0.2526667,0.2956667])  # 线长 L (m)
L_error = np.array([0.00073913921,0.00079138788,0.00087812401,0.00100230224,0.00110309328])  # L 的不确定度 (m)

T = np.array([13.32867,14.94733,17.396,19.852,21.41333])  # 振荡周期 T (s)
T_error = np.array([0.116980076,0.151974414,0.439172429,0.314607761,0.364563625])  # T 的不确定度 (s)

# 计算 T² 及其不确定度 Y_error (误差传播公式: ΔY = 2T * ΔT)
Y = T**2
Y_error = 2 * T * T_error  # 计算 Y = T^2 的误差传播

# **计算强制过原点的最佳斜率 k (Y = kX)**
slope_best = np.sum(L * Y) / np.sum(L**2)  # 计算最佳拟合斜率
Y_fit = slope_best * L  # 计算拟合直线上的 Y 值

# 计算最大斜率 (L 最小, Y 最大)
X_max_slope = np.array([L[0] - L_error[0], L[-1] + L_error[-1]])  # L 最小 -> L 最大
Y_max_slope = np.array([Y[0] + Y_error[0], Y[-1] - Y_error[-1]])  # Y 最大 -> Y 最小
slope_max = np.sum(X_max_slope * Y_max_slope) / np.sum(X_max_slope**2)  # 计算最大斜率
Y_max_line = slope_max * L  # 强制过 (0,0)

# 计算最小斜率 (L 最大, Y 最小)
X_min_slope = np.array([L[0] + L_error[0], L[-1] - L_error[-1]])  # L 最大 -> L 最小
Y_min_slope = np.array([Y[0] - Y_error[0], Y[-1] + Y_error[-1]])  # Y 最小 -> Y 最大
slope_min = np.sum(X_min_slope * Y_min_slope) / np.sum(X_min_slope**2)  # 计算最小斜率
Y_min_line = slope_min * L  # 强制过 (0,0)

# 绘图
plt.figure(figsize=(8, 6))

# 画数据点和误差棒 (同时考虑 L 和 Y 的误差)
plt.errorbar(L, Y, xerr=L_error, yerr=Y_error, fmt='o', label='Data with Uncertainty Bars', capsize=5)

# 画强制过 (0,0) 的最佳拟合直线
plt.plot(L, Y_fit, 'r-', label=f'Best Fit (0,0): y={slope_best:.2f}x')

# 画最大和最小斜率线 (都必须过 0,0)
plt.plot(L, Y_max_line, 'g--', label=f'Max Slope: y={slope_min:.2f}x')
plt.plot(L, Y_min_line, 'b--', label=f'Min Slope: y={slope_max:.2f}x')

# 图表设置
plt.xlabel("Length L (m)")
#plt.xlim(0, max(L) * 1.1)  # 设置 x 轴范围，使其从 0 开始
plt.ylabel("Period Squared T² (s²)")
#plt.ylim(0, max(Y) * 1.1)  # 设置 y 轴从 0 开始，确保数据完整可见
plt.title("Polymer")
plt.legend()
plt.grid()
plt.show()

