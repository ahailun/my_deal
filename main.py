#!/usr/bin/python
# -*- coding: utf8 -*-

from tkinter import *
from futu import *
from tkinter import ttk
from tkinter import messagebox as tkMessageBox
from myTrade import callback, deal_thread, stop_thread
from logger import Logger


root = Tk()
root.title('自动化交易助手V2.5')

# 设置窗口尺寸
window_width = 1200
window_height = 600  # 降低整体窗口高度
root.geometry(f"{window_width}x{window_height}")

# 尝试设置窗口图标
try:
    root.iconbitmap(r'.\assassin.ico')
except:
    pass

# 窗口居中显示
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# 设置窗口最小尺寸
root.minsize(900, 500)

# 设置整体背景色
root.configure(bg='#f5f7fa')

# 创建更紧凑的样式
style = ttk.Style()
style.theme_use('clam')

# 按钮样式
style.configure('Compact.TButton',
               font=('Microsoft YaHei', 9, 'bold'),
               padding=3)

style.configure('Compact.TLabel',
               font=('Microsoft YaHei', 9),
               background='#f5f7fa',
               foreground='#2c3e50')

style.configure('Compact.TEntry',
               padding=3,
               borderwidth=1)

style.configure('Compact.TCombobox',
               padding=3)

# ==================== 网格权重配置 ====================
# 配置行权重
for row in range(5):
    if row == 4:  # 日志行需要扩展
        root.rowconfigure(row, weight=1)
    else:
        root.rowconfigure(row, weight=0, minsize=40)  # 减少行最小高度

# 配置列权重
for col in range(12):
    root.columnconfigure(col, weight=1 if col in [0, 2, 4, 6, 8, 10] else 0)

# ==================== 第0行：交易参数设置 ====================
param_label = ttk.Label(root, text='交易参数设置', 
                       font=('Microsoft YaHei', 10, 'bold'),
                       background='#f5f7fa',
                       foreground='#2c3e50')
param_label.grid(row=0, column=0, columnspan=12, pady=(10, 5), sticky=W, padx=20)

# 每笔赚
mbz = ttk.Label(root, text='每笔赚:', style='Compact.TLabel')
mbz.grid(row=0, column=1, padx=(20, 5), pady=8, sticky=E)

mbz_default = StringVar()
mbz_entry = ttk.Entry(root, textvariable=mbz_default, width=10, style='Compact.TEntry')
mbz_entry.grid(row=0, column=2, padx=(5, 5), pady=8, sticky=W)
mbz_default.set("500")

# 止损线
zsx = ttk.Label(root, text='止损线：', style='Compact.TLabel')
zsx.grid(row=0, column=2, padx=(20, 5), pady=8, sticky=E)

defalut_zsx = StringVar()
zsx_entry = ttk.Entry(root, textvariable=defalut_zsx, width=8, style='Compact.TEntry')
zsx_entry.grid(row=0, column=3, padx=(5, 2), pady=8, sticky=W)
defalut_zsx.set("2")

zsx_bfh = ttk.Label(root, text='%', style='Compact.TLabel')
zsx_bfh.grid(row=0, column=3, padx=(50, 0), pady=8, sticky=W)

# 今日盈亏上限
jryk = ttk.Label(root, text='今日盈亏上限：', style='Compact.TLabel')
jryk.grid(row=0, column=4, padx=(5, 2), pady=8, sticky=E)

defalut_jryk = StringVar()
defalut_jryk.set("2")
jryk_entry = ttk.Entry(root, textvariable=defalut_jryk, width=5, style='Compact.TEntry')
jryk_entry.grid(row=0, column=5, padx=(0, 5), pady=8, sticky=W)
jryk_bfh = ttk.Label(root, text='%', style='Compact.TLabel')
jryk_bfh.grid(row=0, column=5, padx=(30, 0), pady=8, sticky=W)

# 添加分隔线
separator1 = ttk.Separator(root, orient='horizontal')
separator1.grid(row=1, column=0, columnspan=12, sticky='ew', padx=20, pady=(0, 5))

# ==================== 第1行：交易控制 ====================
control_label = ttk.Label(root, text='交易控制', 
                        font=('Microsoft YaHei', 10, 'bold'),
                        background='#f5f7fa',
                        foreground='#2c3e50')
control_label.grid(row=1, column=0, columnspan=12, pady=(5, 5), sticky=W, padx=20)

# 交易环境选择
env = StringVar()

env_label = ttk.Label(root, text='交易环境：', style='Compact.TLabel')
env_label.grid(row=1, column=0, padx=(20, 5), pady=8, sticky=E)

cmb_env = ttk.Combobox(root, font=("Microsoft YaHei", 9), 
                      textvariable=env, width=12, style='Compact.TCombobox')
cmb_env['value'] = ('真实交易', '模拟交易')
cmb_env.current(0)
cmb_env.grid(row=1, column=1, padx=(0, 20), pady=8, sticky=W)
cmb_env.bind("<<ComboboxSelected>>", callback)

# 开始交易按钮
ksjy_btn = ttk.Button(root, text="开始交易", 
                     command=deal_thread, width=12, style='Compact.TButton')
ksjy_btn.grid(row=1, column=2, padx=(0, 15), pady=8, ipadx=2)

# 暂停交易按钮
tzjy_btn = ttk.Button(root, text="暂停交易", state='disabled', 
                     command=stop_thread, width=12, style='Compact.TButton')
tzjy_btn.grid(row=1, column=3, padx=(0, 20), pady=8, ipadx=2)

# 添加状态显示
status_frame = ttk.Frame(root, style='Compact.TFrame')
status_frame.grid(row=1, column=4, columnspan=4, padx=(20, 0), pady=8, sticky=W)

status_label = ttk.Label(status_frame, text='状态:', style='Compact.TLabel')
status_label.pack(side=LEFT, padx=(0, 5))

status_value = ttk.Label(status_frame, text='就绪', 
                        font=('Microsoft YaHei', 9, 'bold'),
                        foreground='#27ae60',
                        background='#f5f7fa')
status_value.pack(side=LEFT)

# 添加分隔线
separator2 = ttk.Separator(root, orient='horizontal')
separator2.grid(row=2, column=0, columnspan=12, sticky='ew', padx=20, pady=(5, 5))

# ==================== 第2行：系统信息 ====================
info_label = ttk.Label(root, text='系统信息', 
                      font=('Microsoft YaHei', 10, 'bold'),
                      background='#f5f7fa',
                      foreground='#2c3e50')
info_label.grid(row=2, column=0, columnspan=12, pady=(5, 5), sticky=W, padx=20)

# 系统信息显示区域
info_frame = ttk.Frame(root, style='Compact.TFrame')
info_frame.grid(row=2, column=0, columnspan=12, pady=(5, 10), sticky=W+E, padx=20)

# 今日交易次数
trades_today = ttk.Label(info_frame, text='今日交易: 0 笔', style='Compact.TLabel')
trades_today.grid(row=0, column=0, padx=(0, 20), pady=3, sticky=W)

# 累计盈利
total_profit = ttk.Label(info_frame, text='累计盈利: ¥0.00', style='Compact.TLabel')
total_profit.grid(row=0, column=1, padx=(0, 20), pady=3, sticky=W)

# 成功率
success_rate = ttk.Label(info_frame, text='成功率: 0.00%', style='Compact.TLabel')
success_rate.grid(row=0, column=2, padx=(0, 20), pady=3, sticky=W)

# 运行时间
uptime = ttk.Label(info_frame, text='运行: 0h 0m', style='Compact.TLabel')
uptime.grid(row=0, column=3, padx=(0, 20), pady=3, sticky=W)

# 添加分隔线
separator3 = ttk.Separator(root, orient='horizontal')
separator3.grid(row=3, column=0, columnspan=12, sticky='ew', padx=20, pady=(5, 10))

# ==================== 第3行：日志显示区 ====================
log_label = ttk.Label(root, text='系统日志', 
                     font=('Microsoft YaHei', 10, 'bold'),
                     background='#f5f7fa',
                     foreground='#2c3e50')
log_label.grid(row=3, column=0, columnspan=12, pady=(0, 5), sticky=W, padx=20)

# 创建滚动条和列表框的容器框架
log_frame = ttk.Frame(root, relief=GROOVE, borderwidth=1)
log_frame.grid(row=4, column=0, columnspan=12, sticky=N+S+E+W, padx=20, pady=(0, 20))
log_frame.columnconfigure(0, weight=1)
log_frame.rowconfigure(0, weight=1)

# 日志工具栏
toolbar_frame = ttk.Frame(log_frame)
toolbar_frame.grid(row=0, column=0, columnspan=2, sticky=E+W, padx=5, pady=(5, 5))
toolbar_frame.columnconfigure(0, weight=1)

# 清空日志按钮
clear_btn = ttk.Button(toolbar_frame, text="清空", 
                      command=lambda: listbox.delete(0, END), 
                      width=8, style='Compact.TButton')
clear_btn.grid(row=0, column=0, sticky=W, padx=5)

# 自动滚动复选框
scroll_var = IntVar(value=1)
scroll_cb = ttk.Checkbutton(toolbar_frame, text="自动滚动", 
                           variable=scroll_var, style='Compact.TCheckbutton')
scroll_cb.grid(row=0, column=1, sticky=W, padx=(20, 0))

# 滚动条
scrollbar = Scrollbar(log_frame, orient=VERTICAL)
scrollbar.grid(row=1, column=1, sticky=N+S, pady=2)

# 列表框
listbox = Listbox(log_frame, width=100, height=20, 
                 font=("Consolas", 9), bg="#2c3e50", fg="#ecf0f1",
                 yscrollcommand=scrollbar.set,
                 selectbackground="#3498db", selectforeground="white",
                 relief=FLAT, borderwidth=0, highlightthickness=0)
listbox.grid(row=1, column=0, sticky=E+W+N+S, padx=(5, 0), pady=5)
listbox.insert(END, '[ 2024-01-01 00:00:00.000 ] [ INFO ] 系统启动完成，等待用户操作...')

# 滚动条配置
scrollbar.config(command=listbox.yview)

# 创建日志记录器
log_2_file = Logger(listbox=listbox)

# 创建底部状态栏
statusbar_frame = ttk.Frame(root, style='Compact.TFrame')
statusbar_frame.grid(row=5, column=0, columnspan=12, sticky=E+W, padx=20, pady=(0, 5))

# 状态信息
status_info = ttk.Label(statusbar_frame, text='就绪', 
                       font=('Microsoft YaHei', 8),
                       foreground='#7f8c8d',
                       background='#f5f7fa')
status_info.pack(side=LEFT, padx=5)

# 时间显示
time_label = ttk.Label(statusbar_frame, 
                      text=time.strftime('%Y-%m-%d %H:%M:%S'),
                      font=('Consolas', 8),
                      foreground='#7f8c8d',
                      background='#f5f7fa')
time_label.pack(side=RIGHT, padx=5)

# 更新时间函数
def update_time():
    time_label.config(text=time.strftime('%Y-%m-%d %H:%M:%S'))
    time_label.after(1000, update_time)

update_time()

root.mainloop()