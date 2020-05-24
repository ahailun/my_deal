#!/usr/bin/python
# -*- coding: utf8 -*-

from tkinter import * 
from futu import *
from tkinter import messagebox as tkMessageBox
import sys, time
from logger import Logger
from common import is_HK_mkt, is_US_mkt, get_code_list_type, get_last_order_status

log_2_file =  Logger()

#订阅数量要求，每个订阅类型占用一个额度，我名下额度默认为500
#两次订阅/反订阅间隔60s,初始值设置为0s
stard_subscrip_num_level = '500'
time_between_two_subscribe = 60
subscriptime = 0

#下单限制：30s内最多访问15次，且1s内最多5次
cycle_period_count = 0
cycle_period_start = time.time()

 #0, 订阅额度还有空余
 #1，订阅额度已无空余
 #2，已订阅过，无须再次订阅
NEED_SUBSCRIBE = 0        
CAN_NOT_SUBSCRIBE = 1   
NEED_NOT_SUBSCRIBE = 2

#交易
is_debug = True
PWD_UNLOCK = '140108'
TRD_ENV = TrdEnv.REAL if is_debug else TrdEnv.SIMULATE

def unlock(trd_ctx):
    ret, date = trd_ctx.unlock_trade(pwd_unlock)
    if ret:
        return True
    return False

def start_to_deal(trd_ctx, meibi_zhuan, code, YJ, ZHISUNXIAN, pwd_unlock):
    '''
    code:HK.00700
    YJ：单程佣金
    ZHISUNXIAN:取整，例如10意为10%
    plVal_or_None:盈亏金额
    qty_or_None:数量
    plRatio：盈亏比例
    Q:盈亏规则挂单后，突然股价跌破止损线的情况： plRatio > ZHISUNXIAN
    '''
    (iHave , plVal_or_None, qty_or_None, plRatio) = i_have_the_stock(log_2_file, trd_ctx, code)
    last_order_status = get_last_order_status(trd_ctx, code, pwd_unlock, TRD_ENV)
    if iHave:
        log_2_file.info('已持有股票:{code},数量:{qty_or_None}'.format(code=code, qty_or_None=qty_or_None))
        log_2_file.info('在我的订单列表中，该股票{}最后一次订单状态是{}'.format(code, last_order_status))
        if last_order_is_over(last_order_status) : #若上一次订单已经结束，则执行卖出操作
            if plVal_or_None - float(meibi_zhuan) - YJ - YJ - 1.000 > 0:
                #达到目标利润则以当前价格卖掉
                #超过止损线则以当前价格卖掉
                realTimePrice = real_time_price(trd_ctx, code)
                log_2_file.info('准备卖出：股票:{code},当前价格:{realTimePrice},交易数量:{qty_or_None},盈亏金额:{plVal_or_None},盈亏比例:{}'.format(\
                                code=code, realTimePrice=realTimePrice, qty_or_None=qty_or_None, plVal_or_None=plVal_or_None, plRatiov=plRatiov
                                ))
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, code, TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret:
                    orderId = data['order_id'].item()
                    log_2_file.info('下单成功，订单号:{}, 卖出价格{}，卖出数量{}，挂单类型{}.'.format(orderId, realTimePrice, qty_or_None, TrdSide.SELL))
                else:
                    lastErrMsg = data['last_err_msg'].item()
                    log_2_file.error('下单失败，原因:{lastErrMsg}.'.format(lastErrMsg=lastErrMsg))
                    #待增加微信通知功能
            if  plRatio > ZHISUNXIAN:
                log_2_file.warn('当前交易单的盈亏比例为：{}，超过止损线：{}，以止损价挂单。'.format(plRatio, ZHISUNXIAN))
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, code, TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret:
                    orderId = data['order_id'].item()
                    log_2_file.info('挂单成功，订单号:{}, 卖价{}，数量{}，挂单类型{}'.format(orderId, realTimePrice, qty_or_None, TrdSide.SELL))
                else:
                    log_2_file.info('挂单失败,失败原因{}，发送微信通知'.format(data))
                sys.exit(1)
        else: #若上一次订单没有结束，则继续等待
            log_2_file.info('该股票{}最后一次订单状态仍处于挂单中，无法挂单卖出，继续等待。')

    else:
        log_2_file.info('没有持仓该股票:{code}'.format(code=code))
        log_2_file.info('在我的订单列表中，该股票{}最后一次订单状态是{}'.format(code, last_order_status))
        if last_order_is_over(last_order_status) : #若上一次订单已经结束，则执行买入操作
            log_2_file.info('准备买入股票:{},当前价格:{},交易数量:{}'.format(code, realTimePrice, qty_or_None))
            ret, data = quote_ctx.place_order(realTimePrice, qty_or_None, code, TrdSide.BUY, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
            if ret:
                orderId = data['order_id'].item()
                log_2_file.info('下单成功，订单号:{}, 购买价格{}，购买数量{}，挂单类型{}.'.format(orderId, realTimePrice, qty_or_None, TrdSide.SELL))
            else:
                lastErrMsg = data['last_err_msg'].item()
                log_2_file.error('下单失败，原因:{lastErrMsg}.'.format(lastErrMsg=lastErrMsg))
        else: #若上一次订单没有结束，则继续等待
            log_2_file.info('该股票{}最后一次订单状态仍处于挂单中，无法挂单买入，继续等待。')


def real_time_price(quote_ctx, stock_num):
    '''
    若持有该股票，则查询该股票实时价格
    返回 406.0 <class 'float'>
    '''
    subscribe_obj = SubsCribe(quote_ctx, stock_num)
    subscribe_obj.query_my_subscription()
    if subscribe_obj.sub_status == NEED_SUBSCRIBE:
        subscribe_obj.subscribe_mystock()
    if subscribe_obj.sub_status == CAN_NOT_SUBSCRIBE:
        subscribe_obj.unsubscribe_mystock_all()
        subscribe_obj.subscribe_mystock()
    cur_price_df = quote_ctx.get_stock_quote(code_list)[1]
    return cur_price_df.iloc[0].iat[3].item()
    #return cur_price_df['pl_val'].item()

def i_have_the_stock(quote_ctx, stock_num):
    '''
    获取账户的持仓列表 检查是否持有该股票stock_num
    返回：(param1, param2, param3， param4) -> (str, float, float, int)
    '''
    ret, data = quote_ctx.position_list_query()
    tmp_stock_list = []
    for i in range(0, len(data)):
        #tmp_stock_list.append(data.iloc[i].iat[0])
        tmp_stock_list.append(data['code'].item())
    log_2_file.warn('账户下持有{n}个股票tmp_stock_list'.format(n=len(data), tmp_stock_list=str(tmp_stock_list)))
    dst_stock_num = get_code_list_type(stock_num)
    log_2_file.info('目标股票是dst_stock_num'.format(dst_stock_num=dst_stock_num))
    if dst_stock_num in tmp_stock_list:
        log_2_file.info('已持有该股票dst_stock_num'.format(dst_stock_num=dst_stock_num))
        return (True, data['pl_val'].item(),  data['qty'].item(), data['pl_ratio'].item())
    log_2_file.info('未持有该股票dst_stock_num'.format(dst_stock_num=dst_stock_num))
    return (False, None, None, None)

def main(deal_function, t, n, trd_ctx):
    '''
    t时间间隔内的最多执行n次func函数
    '''
    global cycle_period_start
    global cycle_period_count
    while True:
        try:
            cycle_period_now = time.time()
            if cycle_period_now - cycle_period_start <= int(t):
                if cycle_period_count < int(n):
                    deal_function()
                    #cycle_period_start = time.time()
                    cycle_period_count += 1
                else:
                    log_2_file.warn('当前{}s内已执行{}次，无法交易需等待下一次交易机会。'.format(t, n))
            else:
                deal_function()
                cycle_period_start = time.time()
                cycle_period_count = 0
        except Exception as e:
            log_2_file.info('程序遇到异常:{}, 退出主程序'.format(str(e)))
            trd_ctx.close()
            sys.exit(1)

class SubsCribe(object):
    def __init__(self, quote_ctx, stock_code, writer_handler=log_2_file):
        self.quote_ctx = quote_ctx
        self.stock_code = stock_code.strip()
        self.writer_handler = writer_handler
        self.sub_status = None
    
    def query_my_subscription(self):
        (ret, data) = self.quote_ctx.query_subscription()
        if ret == RET_OK:
            used_subcrip_count = data.get('total_used')
            remain_subcrip_count  = data.get('remain', stard_subscrip_num_level)
            if int(remain_subcrip_count) > 0:
                self.writer_handler.info('当前已使用了{used}次订阅额度，剩余{left}次。'\
                    .format(used=str(int(used_subcrip_count) + int(remain_subcrip_count)), left=str(remain_subcrip_count))
                    )
                my_subscribe_list = data.get('sub_list').get('QUOTE'))
                self.writer_handler.info('已订阅列表为sub_list_QUOTE'.format(sub_list_QUOTE=my_subscribe_list))
                if self.stock_code in my_subscribe_list:
                    self.sub_status = NEED_NOT_SUBSCRIBE
                else:
                    self.sub_status = NEED_SUBSCRIBE
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
            (ret, err_message) = self.quote_ctx.subscribe(['{US_HK_NAME}'.format(US_HK_NAME=get_code_list_type(self.stock_code))],\
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
