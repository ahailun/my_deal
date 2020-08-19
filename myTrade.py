#!/usr/bin/python
# -*- coding: utf8 -*-

from tkinter import *
from futu import *
from tkinter import ttk
from tkinter import messagebox as tkMessageBox
import sys, time
from logger import Logger
import random
import ctypes
from common import is_HK_mkt, is_US_mkt, get_code_list_type, get_last_order_status, get_mkt, \
                    last_order_is_over,myYjNow

lock=threading.Lock()

log_2_file = Logger()

#订阅数量要求，每个订阅类型占用一个额度，我名下额度默认为300
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

last_order_id = None         #根据上一次的订单号查询状态
qty_or_None   = 0            #记录股票数量，撤单用
#交易
is_debug = True
PWD_UNLOCK = '140108'
TRD_ENV = TrdEnv.SIMULATE if is_debug else TrdEnv.REAL


LAST_ORDER_DIREACTION=1                      #:上一次交易方向，0::BUY/1:SELl,str
LAST_ORDER_PRICE=0                           #:上一次交易价格，0.000，float
LAST_ORDER_TIME_IN_PERIOD=time.time()        #:上一次交易时间，time.time
ORDER_COUNT_IN_PERIOD=0                      #:30s周期内交易的次数，int，取值0~15

def unlock(trd_ctx):
    ret, data = trd_ctx.unlock_trade(PWD_UNLOCK)
    if ret==RET_OK:
        return True
    return False

def start_to_deal(trd_ctx, quote_ctx, code,xiayici_mairujia, xiayici_maichujia,qty_or_None, log_2_file):
    '''
    code:HK.00700
    xiayici_mairujia,价格下跌多少百分比后买入，2-->2%
    xiayici_maichujia,价格上升多少百分比后卖出，2-->2%
    qty_or_None:数量
    LAST_ORDER_DIREACTION:上一次交易方向，BUY/SELl,str
    LAST_ORDER_PRICE:上一次交易价格，0.000，float
    LAST_ORDER_TIME_IN_PERIOD:上一次交易时间，time.time
    ORDER_COUNT_IN_PERIOD:30s周期内交易的次数，int，取值0~15
    '''

    global LAST_ORDER_DIREACTION     #:上一次交易方向，0::BUY/1:SELl,str
    global LAST_ORDER_PRICE          #:上一次交易价格，0.000，float
    global LAST_ORDER_TIME_IN_PERIOD #:上一次交易时间，time.time
    global ORDER_COUNT_IN_PERIOD     #:30s周期内交易的次数，int，取值0~15

    if time.time() - LAST_ORDER_TIME_IN_PERIOD <30 and ORDER_COUNT_IN_PERIOD >= 15:
        #超过频率限制
        time.sleep(time.time() - LAST_ORDER_TIME_IN_PERIOD)
        ORDER_COUNT_IN_PERIOD = 0
        LAST_ORDER_TIME_IN_PERIOD = time.time()
    else:
        realTimePrice = real_time_price(quote_ctx, code)
        #realTimePrice=float( "%.2f" % random.uniform(14.15, 14.25))
        log_2_file.info('查询到股票:{}当前价格:{}'.format(code, realTimePrice))
        if LAST_ORDER_DIREACTION==1:
            #空仓状态
            if LAST_ORDER_PRICE==0:
                #当天第一次买入
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.BUY, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret==RET_OK:
                    LAST_ORDER_DIREACTION = 0
                    LAST_ORDER_TIME_IN_PERIOD = time.time()
                    ORDER_COUNT_IN_PERIOD+=1
                    LAST_ORDER_PRICE=realTimePrice
                    last_order_id = data['order_id'][0]
                    log_2_file.info('直接下买单成功，订单号:{}, 买入价格{}，买入数量{}，挂单类型{}.'.format(last_order_id, realTimePrice, qty_or_None, OrderType.NORMAL))
                else:
                    log_2_file.error('直接下买单失败，原因{}。'.format(data))
            elif LAST_ORDER_PRICE!=0:
                #持续交易中，空仓时，等待价格下降后买入
                tmp_price_fudu = 100 * (realTimePrice - LAST_ORDER_PRICE )/realTimePrice
                log_2_file.info('上次卖出价格是{}，已下跌至{},下跌了{}%'.format(LAST_ORDER_PRICE, realTimePrice,tmp_price_fudu))
                if  tmp_price_fudu<0 and abs(tmp_price_fudu)>= xiayici_mairujia:
                    ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.BUY, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                    if ret==RET_OK:
                        LAST_ORDER_DIREACTION = 0
                        LAST_ORDER_TIME_IN_PERIOD = time.time()
                        ORDER_COUNT_IN_PERIOD+=1
                        LAST_ORDER_PRICE=realTimePrice
                        last_order_id = data['order_id'][0]
                        log_2_file.info('下单成功，订单号:{}, 买入价格{}，买入数量{}，挂单类型{}.'.format(last_order_id, realTimePrice, qty_or_None, OrderType.NORMAL))
                else:
                    if tmp_price_fudu>0:
                        log_2_file.info('未持有该股票，前一次卖出价{}，价格{:.4f}已上升,等待下降后再买入。'.format(LAST_ORDER_PRICE,realTimePrice))
                    if tmp_price_fudu<0 and abs(tmp_price_fudu)< xiayici_mairujia:
                        log_2_file.info('未持有该股票，前一次卖出价{}，价格{:.4f}已下降{:.2f}%,须价格下降{}%后买入。'.format(LAST_ORDER_PRICE,realTimePrice,abs(tmp_price_fudu),xiayici_mairujia))
        elif LAST_ORDER_DIREACTION==0:
            #已持仓，等待价格上升后卖出
            log_2_file.info('上一次是购买，现在等待机会卖出')
            tmp_price_fudu_maichu = 100*(realTimePrice - LAST_ORDER_PRICE)/LAST_ORDER_PRICE
            if tmp_price_fudu_maichu >= xiayici_maichujia:
                log_2_file.info('价格已从{}升高至{}，上升幅度超过设定比{}%,准备下单卖出。'.format(LAST_ORDER_PRICE,realTimePrice,xiayici_maichujia))
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret==RET_OK:
                    LAST_ORDER_DIREACTION = 1
                    LAST_ORDER_TIME_IN_PERIOD = time.time()
                    ORDER_COUNT_IN_PERIOD+=1
                    LAST_ORDER_PRICE=realTimePrice
                    last_order_id = data['order_id'][0]
                    log_2_file.info('下单成功，订单号:{}, 卖出价格{}，卖出数量{}，挂单类型{}.'.format(last_order_id, realTimePrice, qty_or_None, OrderType.NORMAL))
                else:
                    log_2_file.info('下单卖出失败，原因：{}。'.format(data))
            else:
                log_2_file.info('买入价{}，当前价格{}，上升幅度[{:.4f}%]未达到预期[{}%]。'.format(LAST_ORDER_PRICE, realTimePrice,tmp_price_fudu_maichu,xiayici_maichujia))

def real_time_price(quote_ctx, stock_num):
    '''
    若持有该股票，则查询该股票实时价格
    返回 406.0 <class 'float'>
    '''
    subscribe_obj = SubsCribe(quote_ctx, stock_num)
    subscribe_obj.query_my_subscription()
    if subscribe_obj.sub_status == NEED_SUBSCRIBE:
        subscribe_obj.subscribe_mystock()
    elif subscribe_obj.sub_status == CAN_NOT_SUBSCRIBE:
        subscribe_obj.unsubscribe_mystock_all()
        subscribe_obj.subscribe_mystock()
    ret, cur_price_df = subscribe_obj.quote_ctx.get_stock_quote(get_code_list_type(stock_num)[0])
    if ret == RET_OK:
        if len(cur_price_df) == 0:
            log_2_file.error('无法查询到股票{}的实时价格。'.format(stock_num))
            raise Exception('无法查询到股票{}的实时价格。'.format(stock_num))
        else:
            return cur_price_df.iloc[0].iat[3].item()
            #return cur_price_df['pl_val'].item()
    else:
        log_2_file.error('查询到股票{code_name}实时价格时发生错误:{errorinfo}。'.format(code_name=stock_num, errorinfo=cur_price_df))
        raise Exception('查询到股票{code_name}实时价格时发生错误:{errorinfo}。'.format(code_name=stock_num, errorinfo=cur_price_df))


def i_have_the_stock(quote_ctx, stock_num, log_2_file):
    '''
    获取账户的持仓列表 检查是否持有该股票stock_num
    返回：(param1, param2, param3， param4) -> (str, float, float, int)
    '''
    ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
    tmp_stock_dict = {}
    try:
        for index, row in data.iterrows():
            tmp_stock_dict.update({row['code']:[row['pl_val'],row['qty'],row['pl_ratio']]})
    except TypeError as e:
        if '频率限制' in str(e): #此协议请求太频繁，触发了频率限制，请稍后再试
            time.sleep(1)
            tmp_stock_dict = {}
            ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
            for index, row in data.iterrows():
                tmp_stock_dict.update({row['code']:[row['pl_val'],row['qty'],row['pl_ratio']]})
    # print('*'*50)
    # print(time.strftime('%H:%M:%S',time.localtime(time.time()))+' 本账户已持有{n}个股票{tmp_stock_dict}'.format(n=len(data), tmp_stock_dict=str(tmp_stock_dict.keys())))
    # print('*'*50)
    log_2_file.warn('本账户已持有{n}个股票{tmp_stock_dict}'.format(n=len(tmp_stock_dict), tmp_stock_dict=str(list(tmp_stock_dict.keys()))))
    
    dst_stock_num = get_code_list_type(stock_num)[0]
    log_2_file.info('目标股票是{dst_stock_num}'.format(dst_stock_num=dst_stock_num))
    if dst_stock_num in tmp_stock_dict:
        tempinfo = tmp_stock_dict[dst_stock_num]
        log_2_file.info('已持有该股票{dst_stock_num}'.format(dst_stock_num=dst_stock_num))
        #return (True, data['pl_val'].item(),  data['qty'].item(), data['pl_ratio'].item())
        return (True, float(tempinfo[0]),int(tempinfo[1]),float(tempinfo[2]))
    log_2_file.info('未持有该股票:{dst_stock_num}'.format(dst_stock_num=dst_stock_num))
    return (False, None, None, None)

def main_deal(deal_function, t, n, trd_ctx, quote_ctx, mbz, code_str, zsx, gmsl, log_2_file):
    '''
    t时间间隔内的最多执行n次func函数
    '''
    global cycle_period_start
    global cycle_period_count
    while True:
        cycle_period_now = time.time()
        if cycle_period_now - cycle_period_start <= int(t):
            if cycle_period_count < int(n):
                #deal_function()
                deal_function(trd_ctx, quote_ctx, mbz, code_str, zsx, gmsl, log_2_file)
                #cycle_period_start = time.time()
                cycle_period_count += 1
            else:
                log_2_file.warn('当前{}s内已执行{}次，无法交易需等待下一次交易机会。'.format(t, int(n)+1))
                time.sleep(30)
        else:
            #deal_function()
            deal_function(trd_ctx, quote_ctx, mbz, code_str, zsx, gmsl, log_2_file)
            cycle_period_start = time.time()
            cycle_period_count = 0


def test():
    time.sleep(1)
    log_2_file.info('in test func....')

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
                    .format(used=str(int(used_subcrip_count)), left=str(remain_subcrip_count))
                    )
                my_subscribe_list = data.get('sub_list').get('QUOTE')
                self.writer_handler.info('已订阅列表为{}'.format(my_subscribe_list))
                if my_subscribe_list and self.stock_code in my_subscribe_list:
                    self.writer_handler.info('已订阅该股票{}'.format(self.stock_code))
                    self.sub_status = NEED_NOT_SUBSCRIBE
                else:
                    self.sub_status = NEED_SUBSCRIBE
            else:
                self.writer_handler.warn('当前订阅额度已满{used}，等待自动取消原订阅后再订阅{code}。'\
                    .format(used=str(int(used_subcrip_count) + int(remain_subcrip_count)), code=self.stock_code)
                    )
                self.sub_status = CAN_NOT_SUBSCRIBE
        else:
             self.writer_handler.info('查询订阅失败，{}'.format(data))

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
            (ret, err_message) = self.quote_ctx.subscribe(get_code_list_type(self.stock_code), [SubType.QUOTE])
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
    

def deal(gpdm, gmsl, xiayici_mairujia, xiayici_maichujia, log_2_file):
    mktInfo = get_mkt(gpdm)
    trd_ctx = mktInfo.get('trd_ctx')(host='127.0.0.1', port=11111)
    quote_ctx = mktInfo.get('quote_ctx')(host='127.0.0.1', port=11111)
    code_str = gpdm
    unlock(trd_ctx)
    try:
        while True:
            start_to_deal(trd_ctx, quote_ctx, code_str, xiayici_mairujia, xiayici_maichujia, gmsl, log_2_file)
    except Exception as e:
        log_2_file.error('遇到异常[%s]需要关闭客户端连接' % str(e))
        if trd_ctx:
            trd_ctx.close()
            log_2_file.info('关闭当前交易连接')
        if quote_ctx:
            quote_ctx.close()
            log_2_file.info('关闭当前查询连接')
        
def stopp():
    tzjy_btn['state'] = DISABLED
    tkMessageBox.showwarning('警告','待空仓后程序自动会停止，请跟进！')
    global DEAL_PAUSE
    DEAL_PAUSE = True

def deal_thread():
    # #gpdm, gmsl, mbz, zsx
    log_2_file.info('股票代码[{}],交易数量[{}]，降幅比[{}%]，升幅比[{}%]'.format(gpdm_entry.get(), gmsl_entry.get(), mbz_entry3.get(),zsx_entry.get()))
    th=threading.Thread(target=deal, args=(gpdm_entry.get(), int(gmsl_entry.get()), float(mbz_entry3.get()),float(zsx_entry.get()), log_2_file))        
    th.setDaemon(True)    
    th.start()    
    

def stop_thread():
    ts=threading.Thread(target=stopp, args=())        
    ts.setDaemon(True)    
    ts.start() 

def callback(eventObject): 
    global is_debug
    if '模拟交易' in env.get():
        is_debug = True
        print('开始模拟交易......')
    if '真实交易' in env.get():
        is_debug = False
        print('开始真实交易......')



if __name__ == "__main__":    
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid") 
    # import sys
    # gpdm = 'AAPL' #股票代码
    # gmsl = '100'  #股票数量
    # mbz = '1'     #每笔赚
    # zsx = 8       #止损线
    root = Tk()
    root.title('自动化交易助手V2.0')
    root.geometry("1200x500+200+100")
    root.iconbitmap(r'.\assassin.ico')
    root.rowconfigure(1, weight=2)
    root.columnconfigure(10, weight=2)
    gpdm = Label(root, text=' 股票代码:',font=("黑体", 12, "bold"))
    gpdm.grid(row=0, column=0, sticky=E+N+S+W)  
    gpdm_entry = Entry(root)
    gpdm_entry.grid(row=0, column=1, sticky=E+N+S+W)
    gpdm_entry.focus_set()
    gmsl = Label(root, text='  购买数量(股):',font=("黑体", 12, "bold"))
    gmsl.grid(row=0, column=2, sticky=E+N+S+W)
    gmsl_entry = Entry(root)
    gmsl_entry.grid(row=0, column=3)
    mbz = Label(root, text='  降幅比:',font=("黑体", 12, "bold"))
    mbz.grid(row =0, column=4, sticky=E+N+S+W)
    mbz_entry3= Entry(root)
    mbz_entry3.grid(row=0, column=5, sticky=E+N+S+W)
    zsx_bfh1 = Label(root, text='%')
    zsx_bfh1.grid(row=0, column=6, sticky=E+N+S+W)
    zsx = Label(root, text='  升高比：',font=("黑体", 12, "bold"))
    zsx.grid(row =0, column=7, sticky=E+N+S+W)
    zsx_entry = Entry(root, width=5)
    zsx_entry.grid(row=0, column=8, sticky=E+N+S+W)
    zsx_bfh = Label(root, text='%')
    zsx_bfh.grid(row=0, column=9, sticky=E+N+S+W)
    env = StringVar()
    cmb_env = ttk.Combobox(root, font=("黑体", 12, "bold"), textvariable=env)
    cmb_env['value'] = ('模拟交易','真实交易')
    cmb_env.current(0)
    cmb_env.grid(row=1, column=1,)  
    cmb_env.bind("<<ComboboxSelected>>", callback) 
    ksjy_btn = Button(root, text="开始交易", font=("黑体", 12, "bold"), command=deal_thread)
    ksjy_btn.grid(row=1, column=2, ipadx=30)
    # tzjy_btn = Button(root, text="暂停交易", state='disable',font=("黑体", 12, "bold"), command=stop_thread)
    # tzjy_btn.grid(row=1, column=3, ipadx=30)
    scrollbar = Scrollbar(root, orient=VERTICAL)
    listbox = Listbox(root, width=100, height=23, yscrollcommand = scrollbar.set)
    listbox.grid(row=2, column=0, columnspan=11, rowspan=15, sticky=E+N+S+W, padx=10, pady=5)
    listbox.insert(END, '')
    scrollbar.grid(row=2, column=11,  rowspan=15, sticky=E+N+S+W, pady=5)
    scrollbar.config(command=listbox.yview)
    log_2_file = Logger(listbox=listbox)
    

    root.mainloop()