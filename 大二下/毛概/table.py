import matplotlib.pyplot as plt

# 数据统计
names = ["杨伟", "唐长红", "赵霞", "韩克岑", "赵春玲", "陈迎春", "其他"]
counts = [38, 24, 15, 9, 12, 8, 3]

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Songti SC', 'Arial Unicode MS']  # macOS 系统字体
plt.rcParams['axes.unicode_minus'] = False

# 生成柱状图
plt.figure(figsize=(10, 6))
bars = plt.barh(names, counts, color='#2c7fb8')

# 添加数据标签
for bar in bars:
    width = bar.get_width()
    plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
             f'{width}', 
             ha='left', va='center')

plt.xlabel("提及次数")
plt.title("西工大总师知名度排名")
plt.gca().invert_yaxis()  # 从高到低排序
plt.tight_layout()
plt.show()


# 数据统计
channels = ["学校官网/公众号", "媒体报道", "同学讨论", "校内讲座/展览", "书籍文献", "其他"]
counts = [32, 25, 18, 20, 12, 5]

# 生成条形图
plt.figure(figsize=(10, 6))
bars = plt.bar(channels, counts, color='#7fcdbb')

# 添加数据标签
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + 0.5, 
             f'{height}', 
             ha='center', va='bottom')

plt.xticks(rotation=45)
plt.ylabel("选择人数")
plt.title("了解西工大总师的主要渠道")
plt.tight_layout()
plt.show()

# 数据统计
traits = ["家国情怀", "科技创新", "团队协作", "艰苦奋斗", "追求卓越"]
counts = [35, 28, 22, 15, 10]

# 生成横向柱状图
plt.figure(figsize=(10, 6))
bars = plt.barh(traits, counts, color='#edf8b1')

# 添加数据标签
for bar in bars:
    width = bar.get_width()
    plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
             f'{width}', 
             ha='left', va='center')

plt.xlabel("提及次数")
plt.title("西工大总师精神核心内涵")
plt.tight_layout()
plt.show()


# 数据统计
labels = ["事迹报告会", "影视纪录片", "主题展览", "校友沙龙", "实践调研"]
sizes = [45, 40, 30, 25, 15]
colors = ['#ff7f0e', '#1f77b4', '#2ca02c', '#d62728', '#9467bd']

# 生成饼图
plt.figure(figsize=(8, 8))
plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)

# 添加标题
plt.title("受欢迎的总师精神活动形式")
plt.tight_layout()
plt.show()

import numpy as np

# 数据统计
labels = ["爱国主义", "工匠精神", "开拓创新", "集体主义", "淡泊名利"]
stats = [38, 34, 28, 25, 20]

# 雷达图闭合处理
angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
stats += stats[:1]
angles += angles[:1]

# 生成雷达图
fig = plt.figure(figsize=(6, 6))
ax = fig.add_subplot(111, polar=True)
ax.plot(angles, stats, linewidth=2, linestyle='solid', color='#e41a1c')
ax.fill(angles, stats, color='#e41a1c', alpha=0.25)

# 添加数据标签
for angle, value in zip(angles[:-1], stats[:-1]):
    ax.text(angle, value + 1, str(value), ha='center', va='bottom')

ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
plt.xticks(angles[:-1], labels)
plt.title("总师精神与价值观关联雷达图")
plt.tight_layout()
plt.show()