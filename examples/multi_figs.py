import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from animation import FuncAnimation


fig1 = plt.figure()
ax1 = fig1.add_subplot(1, 1, 1)

fig2 = plt.figure()
ax2 = fig2.add_subplot(2, 1, 1)
ax3 = fig2.add_subplot(2, 1, 2)

frameCnt = 400

t = np.linspace(0, 80, frameCnt)
x = np.cos(2 * np.pi * t / 10.)
y = np.sin(2 * np.pi * t / 10.)
z = 10 * t

ax1.set_xlabel('x')
ax1.set_ylabel('y')
line1 = [Line2D([], [], color='black'),
         Line2D([], [], color='red', linewidth=2),
         Line2D([], [], color='red', marker='o', markeredgecolor='r')]

ax1.add_line(line1[0])
ax1.add_line(line1[1])
ax1.add_line(line1[2])
ax1.set_xlim(-1, 1)
ax1.set_ylim(-2, 2)
ax1.set_aspect('equal', 'datalim')

ax2.set_xlabel('y')
ax2.set_ylabel('z')
line2 = [Line2D([], [], color='black'),
         Line2D([], [], color='red', linewidth=2),
         Line2D([], [], color='red', marker='o', markeredgecolor='r')]

ax2.add_line(line2[0])
ax2.add_line(line2[1])
ax2.add_line(line2[2])
ax2.set_xlim(-1, 1)
ax2.set_ylim(0, 800)

ax3.set_xlabel('x')
ax3.set_ylabel('z')
line3 = [Line2D([], [], color='black'),
         Line2D([], [], color='red', linewidth=2),
         Line2D([], [], color='red', marker='o', markeredgecolor='r')]

ax3.add_line(line3[0])
ax3.add_line(line3[1])
ax3.add_line(line3[2])
ax3.set_xlim(-1, 1)
ax3.set_ylim(0, 800)

def draw_left_frame(i, lines, x, y, z, t):
    head = i - 1
    head_len = 10
    head_slice = (t > t[i] - 1.0) & (t < t[i])

    lines[0].set_data(x[:i], y[:i])
    lines[1].set_data(x[head_slice], y[head_slice])
    lines[2].set_data(x[head], y[head])

    return lines

def draw_right_frame(i, lines1, lines2, x, y, z, t) :
    head = i - 1
    head_len = 10
    head_slice = (t > t[i] - 1.0) & (t < t[i])
    lines1[0].set_data(y[:i], z[:i])
    lines1[1].set_data(y[head_slice], z[head_slice])
    lines1[2].set_data(y[head], z[head])

    lines2[0].set_data(x[:i], z[:i])
    lines2[1].set_data(x[head_slice], z[head_slice])
    lines2[2].set_data(x[head], z[head])

    return lines1 + lines2

fig1Anim = FuncAnimation(fig1, draw_left_frame, frameCnt, fargs=(line1, x, y, z, t),
                               interval=250, blit=True)

fig2Anim = FuncAnimation(fig2, draw_right_frame, frameCnt, fargs=(line2, line3, x, y, z, t),
                               event_source=fig1Anim.event_source, blit=True)

#ani.save('test_sub.mp4')
plt.show()
