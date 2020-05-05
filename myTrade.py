#!/usr/bin/python
# -*- coding: utf8 -*-

from tkinter import * 
from tkinter import messagebox as tkMessageBox
import re, socket, json, sys, threading, time
from logger import Logger
from config import *

log_2_file =  Logger()

#订阅数量要求，每个订阅类型占用一个额度，我名下额度默认为500
#两次订阅/反订阅间隔60s,初始值设置为0s
stard_subscrip_num_level = '500'
time_between_two_subscribe = 60
subscriptime = 0

#下单限制：30s内最多访问15次，且1s内最多5次
cycle_period_count = 0
cycle_period_start = time.time()

#是否持有股票，False为不持有，Ture为持有
#持有股票时需要卖，不持有股票时需要买
hold = False 
trade_side = TrdSide.SELL if hold else TrdSide.BUY




def aaaa(log_2_file, func, t, n):
    '''
    t时间间隔内的最多n次交易
    '''
    global cycle_period_start
    global cycle_period_count
    while need_to_do():
        cycle_period_now = time.time()
        if cycle_period_now - cycle_period_start <= int(t):
            if cycle_period_count < int(n):
                func()
                cycle_period_start = time.time()
                cycle_period_count += 1
            else:
                log_2_file.warn('当前{period_t}s内已执行{period_n}次，无法交易需等待下一次交易机会。'.format(period_t=t, period_n=n))
        else:
            func()
            cycle_period_start = time.time()
            cycle_period_count = 0


class SubsCribe:
    def __init__(self, quote_ctx, stock_code, writer_handler):
        self.quote_ctx = quote_ctx
        self.stock_code = stock_code
        self.writer_handler = writer_handler
        self.sub_status = None
    
    def query_my_subscription(self):
        (ret, data) = self.quote_ctx.query_subscription()
        if ret == RET_OK:
            used_subcrip_count = data.get('total_used')
            remain_subcrip_count  = data.get('remain', stard_subscrip_num_level)
            if int(remain_subcrip_count) <= 0:
                self.writer_handler.info('当前已使用了{used}次订阅额度，剩余{left}次。'\
                    .format(used=str(int(used_subcrip_count) + int(remain_subcrip_count)), left=str(remain_subcrip_count))
                    )
                self.sub_status = CAN_SUBSCRIBE
            else:
                self.writer_handler.warn('当前订阅额度已满{}，等待自动取消原订阅后再订阅{code}。'\
                    .format(used=str(int(used_subcrip_count) + int(remain_subcrip_count)), code=self.stock_code)
                    )
                self.sub_status = CAN_NOT_SUBSCRIBE

    def unsubscribe_mystock_all(self):
        global subscriptime
        while True:
            if time.time() - subscriptime > time_between_two_subscribe:
                subscriptime = time.time()
                self.quote_ctx.unsubscribe_all()
                break

    def subscribe_mystock(self):
        global subscriptime
        try_sub_count = 0
        self.writer_handler.info('开始订阅{code}。'.format(code=self.stock_code))
        while True:
            (ret, err_message) = self.quote_ctx.subscribe(['{US_HK_NAME}'.format(US_HK_NAME=self.stock_code)],\
                                     [SubType.QUOTE])
            subscriptime = time.time()
            if ret == RET_OK:
                self.writer_handler.info('订阅{code}成功。'.format(code=self.stock_code))
                return ret, err_message
            elif try_sub_count == 0:
                self.writer_handler.warn('订阅{code}失败，原因是{fail_reason},等待60s后再次尝试自动订阅。'.format(code=self.stock_code, fail_reason=err_message))
                time.sleep(60)
                try_sub_count += 1
            else:
                self.writer_handler.error('再次尝试自动订阅{code}仍然失败，原因{fail_reason}。'.format(code=self.stock_code, fail_reason=err_message))
                return ret, err_message


if __name__ == "__main__":
    root = Tk()
    root.title('自动化交易助手V2.0')
    root.geometry("1200x500+200+100")
    root.iconbitmap(r'.\assassin.ico')
    root.rowconfigure(1, weight=2)
    root.columnconfigure(9, weight=2)
    gpdm = Label(root, text=' 股票代码:',font=("黑体", 12, "bold"))
    gpdm.grid(row=0, column=0, sticky=E+N+S+W)  
    gpdm_entry = Entry(root)
    gpdm_entry.grid(row=0, column=1, sticky=E+N+S+W)
    gpdm_entry.focus_set()
    gmsl = Label(root, text='  购买数量(手):',font=("黑体", 12, "bold"))
    gmsl.grid(row=0, column=2, sticky=E+N+S+W)
    gmsl_entry = Entry(root)
    gmsl_entry.grid(row=0, column=3)
    mbz = Label(root, text='  每笔赚:',font=("黑体", 12, "bold"))
    mbz.grid(row =0, column=4, sticky=E+N+S+W)
    mbz_entry3= Entry(root)
    mbz_entry3.grid(row=0, column=5, sticky=E+N+S+W)
    zsx = Label(root, text='  止损线：',font=("黑体", 12, "bold"))
    zsx.grid(row =0, column=6, sticky=E+N+S+W)
    defalut_zsx = StringVar()
    zsx_entry = Entry(root, textvariable=defalut_zsx, width=5)
    zsx_entry.grid(row=0, column=7, sticky=E+N+S+W)
    defalut_zsx.set("2")
    zsx_bfh = Label(root, text='%')
    zsx_bfh.grid(row=0, column=8, sticky=E+N+S+W)
    ksjy_btn = Button(root, text="开始交易", font=("黑体", 12, "bold"), command=runThread)
    ksjy_btn.grid(row=0, column=9, sticky=E+N+S+W, ipadx=30)
    tzjy_btn = Button(root, text="停止交易", font=("黑体", 12, "bold"), command=stopThread)
    tzjy_btn.grid(row=0, column=10,sticky=E+N+S+W, ipadx=30)
    scrollbar = Scrollbar(root, orient=VERTICAL)
    listbox = Listbox(root, width=100, height=23, yscrollcommand = scrollbar.set)
    listbox.grid(row=1, column=0, columnspan=11, rowspan=15, sticky=E+N+S+W, padx=10, pady=5)
    listbox.insert(END, '')
    scrollbar.grid(row=1, column=11,  rowspan=15, sticky=E+N+S+W, pady=5)
    scrollbar.config(command=listbox.yview)

    root.mainloop()
