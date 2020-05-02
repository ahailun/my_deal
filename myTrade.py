#!/usr/bin/python
# -*- coding: utf8 -*-

from tkinter import *
import re
from tkinter import messagebox as tkMessageBox
#import tkMessageBox
import socket
import json
import sys
import threading

COOKIE = 123456

def json_analyze_rsps(rsp_str):
    ret_data_arr = []
    rsp_ar = rsp_str.split("\r\n")
    for rsp in rsp_ar:
        if len(rsp) <= 0 :
            continue
        rsp_after_json_analyze = json.loads(rsp)
        ret_data_arr.append(rsp_after_json_analyze)
    return ret_data_arr

def send_req_and_get_rsp(lstbox, conn, protocol_code, req_param, protocol_version):
    try:
        req = {"Protocol":str(protocol_code), "ReqParam":req_param, "Version":str(protocol_version)}
        req_str = json.dumps(req) + "\r\n"
        conn.send(req_str)
    except socket.timeout:
        print("time out")
        return
    rsp_str = ""
    while True:
        buf = conn.recv(1024)
        rsp_str += buf
        try:
            rsp_str.index('\n')
            break    
        except Exception as e:
            pass
    res_dic = json_analyze_rsps(rsp_str)        #回包josn解析
    
    if int(res_dic[0]["ErrCode"]) == 0:
        if res_dic[0]["RetData"] is not None:
            return res_dic[0]["RetData"]
    else:
        lstbox.insert(END,'交易出现错误，原因是：',res_dic[0]['ErrDesc'])
        return
        #print '交易出现错误，原因是：',res_dic[0]['ErrDesc']

# OrderSide: 0---买入, 1---卖出
# order_type: 增强限价单(普通交易)
# price: 交易价格
# qty:交易数量
# stock_code:股票代码
def place_order(lstbox, conn, order_side, order_type, price, qty, stock_code):
    global COOKIE
    req_param = {"EnvType":"0", "Cookie":str(COOKIE), "OrderSide":str(order_side), "OrderType":str(order_type), "Price":str(price), "Qty":str(qty), "StockCode":stock_code}#EnvType:1,港股仿真交易,0,港股真实交易   
    order_success = True   
    #import time
    #time.sleep(1.5)         #按照要求，30s内不能交易超过20次.
    analyzed_rsps_arr = send_req_and_get_rsp(lstbox, conn, 6003, req_param, 1)
    #analyzed_rsps_arr = send_req_and_get_rsp(conn, 7003, req_param, 1)  # 测试用：Market:美股，StockCode:股票代码
    lstbox.insert(END,"已经下单成功：价格：%s,数量：%s，等待成交..." % (str(float(price)/1000), str(qty)))
    #print "已经下单成功：价格：%s,数量：%s，等待成交..." % (str(float(price)/1000), str(qty))
    if deal_status_ok(lstbox, conn,COOKIE,stock_code):
        COOKIE += 1
        return order_success

#{"Protocol":"7008","ReqParam":{"Cookie":"123123","EnvType":"0"},"Version":"1"}
def deal_status_ok(lstbox, conn,Cookie,stock_code):
    req_param = {"Cookie":str(Cookie),"EnvType":"0"} #EnvType：1,港股仿真交易,0,港股真实交易
    #analyzed_rsps_arr = send_req_and_get_rsp(conn, 7008, req_param, 1) #测试用：Market:美股，StockCode:股票代码
    #order_array = analyzed_rsps_arr["USOrderArr"]#测试用：Market:美股，StockCode:股票代码
    while True:
        analyzed_rsps_arr = send_req_and_get_rsp(lstbox, conn, 6008, req_param, 1)
        order_array = analyzed_rsps_arr["HKOrderArr"]
        if '3' == [cur_deal['Status'] for cur_deal in order_array if cur_deal.get('StockCode')==stock_code][-1]:
            return True
        
class FT:
    def __init__(self, code, lstbox):
        self._code = code
        self.lstbox = lstbox
        self._conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #try:
        self._conn.connect(("localhost", 11111))
        #except Exception as e:
            #print "连接FTNN错误，退出程序！!", e
        
    def __del__(self):
        self._conn.close()
        self.lstbox.insert(END, "连接FTNN结束.")
        #print "连接FTNN结束."

    def get_cur_price(self):
        req_param = {'Market':'1','StockCode':'%s' % str(self._code)}  #Market:港股，StockCode:股票代码
        # req_param = {'Market':'2','StockCode':'%s' % str(self._code)}    # 测试用：Market:美股，StockCode:股票代码
        data = send_req_and_get_rsp(self.lstbox, self._conn, 1001, req_param, 1)    #获取当前股票基础信息
        real_price,Time = int(data["Cur"]),data["Time"]
        return real_price,Time

    def get_stock_gear(self, get_gear_num):
        req_param = {"Market":"1",'StockCode':'%s' % str(self._code),"GetGearNum":str(get_gear_num)}
        #req_param = {"Market":"2",'StockCode':'%s' % str(self._code),"GetGearNum":str(get_gear_num)} # 测试用：Market:美股，StockCode:股票代码
        analyzed_rsps = send_req_and_get_rsp(self.lstbox, self._conn,1002,req_param,1)
        try:
            dic_gear_info_lst = analyzed_rsps["GearArr"]
            if dic_gear_info_lst is None:
                #print "获取买卖档口错误."
                self.lstbox.insert(END, "获取买卖档口错误.")
                return
        except TypeError as e:
            #print "股票输入错误：",e
            self.lstbox.insert(END, "股票输入错误：%s" % e)
            sys.exit()
        return dic_gear_info_lst

    def get_account_info(self):
        req_param = {"Cookie":"123456","EnvType":"0"} #EnvType：1,港股仿真交易 0：港股真实交易
        account_info_rsp = send_req_and_get_rsp(self.lstbox, self._conn, 6007, req_param, 1)
        # account_info_rsp = send_req_and_get_rsp(self._conn, 7007, req_param, 1)  # 测试用：Market:美股，StockCode:股票代码
        return account_info_rsp["Power"], account_info_rsp["ZCJZ"]

    def check_on_hold(self):
        req_param = {"Cookie":"123457","EnvType":"0"} #EnvType：1,港股仿真交易 0：港股真实交易
        on_hold_dict = send_req_and_get_rsp(self.lstbox, self._conn, 6009, req_param, 1)
        #on_hold_dict = send_req_and_get_rsp(self._conn, 7009, req_param, 1)        # 测试用：Market:美股，StockCode:股票代码
        on_holded_stock_lst = on_hold_dict["HKPositionArr"]
        #on_holded_stock_lst = on_hold_dict["USPositionArr"]                        # 测试用：Market:美股，StockCode:股票代码
        return on_holded_stock_lst

# stcokcode: 股票代码
# lowline: 止损线
# upline: 止盈线
# controlline: 交易触发线
class DEAL(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stockcode = entry1.get()
        self.meishou = entry2.get()
        self.fst_price = entry3.get()
        self.upline = float(entry4.get())
        self.lowline = float(entry5.get())
        self.controlline = float(entry6.get())
        
        #print '###','+',self.stockcode,'+',self.meishou,'+',self.fst_price,'+',self.upline,'+',self.lowline,'+',self.controlline,'+','###'
        #print '###',type(self.stockcode), type(self.meishou), type(self.fst_price), type(self.upline), type(self.lowline), type(self.controlline),'###'
        #listbox.insert(END, '###','+',self.stockcode,'+',self.meishou,'+',self.fst_price,'+',self.upline,'+',self.lowline,'+',self.controlline,'+','###')
        try:
            self.ft = FT(self.stockcode,listbox)
        except Exception as e:
            #print "连接服务器错误, 检查牛牛是否开启 %s" % e
            #listbox.delete(0, END)
            listbox.insert(END, "连接服务器错误, 检查牛牛是否开启 %s" % e)
            return
    def input_valid(self):
        return  self.upline> self.lowline>  self.controlline
    
    # 检查持仓列表
    def i_have_hold(self):
        hold_lsts = self.ft.check_on_hold()
        return hold_lsts

    def run(self):
        i_have = self.i_have_hold()
        listbox.delete(0, END)
        listbox.insert(END, "***************************天下武功，唯快不破***************************")
        listbox.insert(END, "当前输入内容为："+'#'.join((self.stockcode,self.meishou,self.fst_price,str(self.upline),str(self.lowline),str(self.controlline))))
        hold_stock_lst = []
        if i_have:
            hold_stock_lst = [hold_lst["StockCode"] for hold_lst in i_have]  # 已经持有的股票代码，列表
            if str(self.stockcode) in hold_stock_lst:# and int(hold_stock_num) != 0:
                hold_stock_num = [hold_lst["CanSellQty"] for hold_lst in i_have if hold_lst["StockCode"]==str(self.stockcode)]
                if int(hold_stock_num[0])!=0:
                    listbox.insert(END, '该股票已在持仓列表中，开始高频交易...')
                    #print "该股票已在持仓列表中，开始高频交易..."
                    for hold_lst in i_have:
                        if hold_lst.get("StockCode") == str(self.stockcode) and hold_lst.get("CostPriceValid") == "1":
                            buy_stock_at_price = float(hold_lst.get("CostPrice"))
                            buy_stock_at_qty = int(hold_lst.get("Qty"))
                            self.run_multy_deal(buy_stock_at_price, 0, buy_stock_at_qty)                 # 开始自动交易
        # 没有持有任何股票,或者此股票不在已持股票行列
        #print "我还没持有该股票(%s)，开始购买..." % self.stockcode
        listbox.insert(END, "我还没持有该股票(%s)，开始购买..." % self.stockcode)
        (mairujia, mairushuliang) = self.fst_time_auto_buy()                                  # 购买股票
        if mairujia==False or mairushuliang==False:
            del self.ft
            return
        self.run_multy_deal(mairujia, 0, mairushuliang)                                                  # 开始自动交易

    # buy_num:购买数量，单位：股，
    # buy_price_one, sell_price_one，摆盘中的数据
    def fst_time_auto_buy(self):
        fst_buy_fail = True
        sell_price_one = 0
        buy_price_one = 0
        buy_num = 0

        power_str, zcjz_str = self.ft.get_account_info()
        gear_info_lst = self.ft.get_stock_gear(1)           #真实环境
        while fst_buy_fail:
            for gear_info in gear_info_lst:
                sell_price_one = gear_info["SellPrice"]
                buy_price_one  = gear_info["BuyPrice"]

                buy_num = int(float(power_str)/(int(self.meishou) * int(sell_price_one)))
                buy_num = buy_num * int(self.meishou) #购买的数量，美股self.meishou=1
                if buy_num < 1:
                    listbox.insert(END, "资产净值(%.3f)，但购买力(%.3f)不够买一手！" % (float(zcjz_str) / 1000, float(power_str) / 1000))
                    #print "资产净值(%.3f)，但购买力(%.3f)不够买一手！" % (float(zcjz_str) / 1000, float(power_str) / 1000)
                    return (False,False)

                '''第1次购买时，以现价/卖一价/设定价的最低值为交易价格，待商榷'''
                #fst_bu_prc = min(float(sell_price_one), float(self.ft.get_cur_price()), float(self.fst_price)*1000)
                fst_bu_prc = float(self.fst_price)*1000
                # 美股中，参数三：2为普通下单；港股中，0为普通单
                #if place_order(self.ft._conn, 0, 2, fst_bu_prc, buy_num, self.stockcode):
                if place_order(listbox, self.ft._conn, 0, 0, fst_bu_prc, buy_num, self.stockcode):
                    listbox.insert(END,"第1次交易%s成功，以价格%0.3f买入%d手." % (self.stockcode, (float(fst_bu_prc))/1000, int(buy_num)))
                    #print "第1次交易%s成功，以价格%0.3f买入%d手." % (self.stockcode, (float(fst_bu_prc))/1000, int(buy_num))
                else:
                    listbox.insert(END,"第1次购买失败，退出程序.")
                    #print "第1次购买失败，退出程序."
                                  
                fst_buy_fail=False
        return float(fst_bu_prc), buy_num   # 买入成功、买入价、买入数量

    def run_multy_deal(self, lst_time_exchange_price, lst_time_exchange_side, lst_time_exchange_num, i=2):
        listbox.insert(END,"等待下一次交易中...")
        #print "等待下一次交易中..."
        while True:
            cur_p,tm = self.ft.get_cur_price()[0:]
            Label9_display.set(tm)
            # 买入后涨幅在2%-8%的时候，卖出，并记录本次交易价格
            if self.controlline <= (float(cur_p) - float(lst_time_exchange_price))/float(lst_time_exchange_price) *100 < self.lowline \
                    and lst_time_exchange_side == 0:

#                gear_info_lst_1 = self.ft.get_stock_gear(1)
#                 for gear_info in gear_info_lst_1:
#                     buy_price_one_in_if = gear_info["BuyPrice"]
                lst_time_exchange_side = lst_time_exchange_side^1
#                     # 0 --买入， 1--卖出
#                     print "查看摆盘数据1..."
#                     if float(buy_price_one_in_if) >= float(self.ft.get_cur_price()):
                listbox.insert(END,"价格上升，大于控制线，卖出股票...")
                #print "价格上升，大于控制线，卖出股票..."
                place_order(listbox,self.ft._conn, lst_time_exchange_side, 0, cur_p, lst_time_exchange_num, self.stockcode)
                listbox.insert(END,"第%s次交易成功，以价格%.3f 卖出%d手." % (i, (float(cur_p)/1000), lst_time_exchange_num))
                #print "第%s次交易成功，以价格%.3f 卖出%d手." % (i, (float(cur_p)/1000), lst_time_exchange_num)
                lst_time_exchange_price = cur_p
                i += 1
                continue

            # 卖出后跌幅在2%-8%之间的时候，买入，并记录本次交易价格
            if self.controlline <= (float(lst_time_exchange_price) - float(cur_p)) / float(lst_time_exchange_price)*100 < self.lowline\
                    and lst_time_exchange_side == 1:
#                 gear_info_lst_2 = self.ft.get_stock_gear(1)
#                 for gear_info in gear_info_lst_2:
# 
#                     sell_price_in_if = gear_info["SellPrice"]
                lst_time_exchange_side = lst_time_exchange_side^1                   
#                     # 0 --买入， 1--卖出
#                     print "查看摆盘数据2..."
#                     if float(sell_price_in_if) <= float(self.ft.get_cur_price()):
                listbox.insert(END,"价格下降，大于控制线，准备买入股票...")
                #print "价格下降，大于控制线，准备买入股票..."
                place_order(listbox, self.ft._conn, lst_time_exchange_side, 0, cur_p, lst_time_exchange_num, self.stockcode)
                listbox.insert(END,"第%s次交易%s成功，以买一价格%0.3f买入%d手." % (i, self.stockcode, (float(cur_p))/1000, lst_time_exchange_num))
                #print "第%s次交易%s成功，以买一价格%0.3f买入%d手." % (i, self.stockcode, (float(cur_p))/1000, lst_time_exchange_num)
                lst_time_exchange_price = cur_p
                i += 1
                continue

            # 买入后跌幅大于8%或涨幅大于15%，全仓释放，不再交易
            if lst_time_exchange_side == 0 and \
                    ((float(lst_time_exchange_price) - float(cur_p)) / float(lst_time_exchange_price) *100  >= self.lowline or
                        (float(cur_p) - float(lst_time_exchange_price)) / float(lst_time_exchange_price) *100 > self.upline):

#                 gear_info_lst_3 = self.ft.get_stock_gear(1)
#                 for gear_info in gear_info_lst_3:
#                     buy_price_one_in_8_15 = gear_info["BuyPrice"]
                lst_time_exchange_side = lst_time_exchange_side^1
                listbox.insert(END,"价格波动过大，准备清仓走人...")
                #print  "价格波动过大，准备清仓走人..."
                place_order(listbox, self.ft._conn, lst_time_exchange_side, 0, cur_p, lst_time_exchange_num, self.stockcode)
                listbox.insert(END,"第%s次交易成功，以买一价格%0.3f卖出%d手,退出程序！" % (i, (float(cur_p))/1000, lst_time_exchange_num))
                #print "第%s次交易成功，以买一价格%0.3f卖出%d手,退出程序！" % (i, (float(cur_p))/1000, lst_time_exchange_num)
                
                return

def runThread():
    th = DEAL()
    th.start()


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
