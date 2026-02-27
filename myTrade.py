#!/usr/bin/python
# -*- coding: utf8 -*-
import sys, time, random, ctypes
import pandas as pd
from tkinter import *
from futu import *
from tkinter import ttk
from tkinter import messagebox as tkMessageBox
from logger import Logger
from datetime import datetime, timedelta, date
from subscribe import SubsCribe
from stratergy.stratergy2 import get_largest_volume_resumed_stock
from stratergy.stratergy1 import get_high_turnover_stocks
from common import is_HK_mkt, is_US_mkt, get_code_list_type, get_last_order_status, get_mkt, \
                    last_order_is_over, unlock, myYjNow, is_validation, MAX_STOCKS_PER_REQUEST

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

#根据上一次的订单号查询状态
last_order_id = None

last_order_time  = 0.00000      #记录上一次订单时间
last_sell_price  = 0.00000      #记录上一次卖出价格
first_buy_price  = 0.00000      #记录第一次买入价格
delte_order_time = 0.3          #撤单间隔时间
qty_or_None      = 0            #记录股票数量，撤单用
#交易
is_debug = True
PWD_UNLOCK = '******'
TRD_ENV = TrdEnv.REAL           #默认为模拟环境
DEAL_PAUSE = False              #暂停交易


def start_to_deal(trd_ctx, quote_ctx, meibi_zhuan, code, ZHISUNXIAN, now_qty, jryk, log_2_file):
    '''
    code:HK.00700
    YJ：单程佣金
    ZHISUNXIAN:取整，例如10意为10%
    plVal_or_None:盈亏金额
    qty_or_None:数量
    plRatio：盈亏比例
    Q:盈亏规则挂单后，突然股价跌破止损线的情况： plRatio > ZHISUNXIAN
    jryk:今日盈亏数据，若在前台写入内容并且为数字，则进行对应的检查
    '''
    global last_order_id
    global last_order_time
    global qty_or_None
    global last_sell_price
    global first_buy_price
    global DEAL_PAUSE
    global is_debug
    global TRD_ENV
    realTimePrice = real_time_price(quote_ctx, code)
    log_2_file.info('查询到股票:{}当前价格:{}'.format(code, realTimePrice))
    YJ = myYjNow(trd_ctx, PWD_UNLOCK, code, now_qty, log_2_file, realTimePrice, is_debug)
    last_order_status, last_order_side = get_last_order_status(trd_ctx, code, last_order_id, PWD_UNLOCK, TRD_ENV)
    if last_order_is_over(last_order_status) : 
        #若上一次订单已经结束，则执行卖出操作
        (iHave , plVal_or_None, qty_or_None, plRatio, costPrice) = i_have_the_stock(trd_ctx, code, log_2_file)
        # log_2_file.info('plVal_or_None:%s,%s'%(plVal_or_None,type(plVal_or_None)))
        if iHave:
            if DEAL_PAUSE:
                log_2_file.warn('已持仓股票{}，待挂单后程序会自动暂停，请等待。'.format(code))
            log_2_file.info('已持有股票:{},数量:{},在订单列表中该股票最后一次订单状态[{}]已经结束,准备下单卖出'.format(code, qty_or_None, last_order_status))

            if float(first_buy_price)==0:
                first_buy_price = costPrice
                log_2_file.info('记录软件运行时首次购买价格:{}。'.format(first_buy_price))

            if plVal_or_None - float(meibi_zhuan) - YJ - YJ > 0:
                #达到目标利润则以当前价格卖掉，超过止损线则以当前价格卖掉
                log_2_file.info('该单已盈利{},准备挂单卖出。'.format(plVal_or_None))
                realTimePrice = real_time_price(quote_ctx, code)
                log_2_file.info('准备卖出：股票:{code},当前价格:{realTimePrice},交易数量:{qty_or_None},盈亏金额:{plVal_or_None},盈亏比例:{plRatio}'.format(\
                                code=code, realTimePrice=realTimePrice, qty_or_None=qty_or_None, plVal_or_None=plVal_or_None, plRatio=plRatio
                                ))
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret==RET_OK:
                    last_order_time = time.time()
                    last_order_id = data['order_id'][0]
                    last_sell_price = realTimePrice
                    log_2_file.info('下单成功，订单号:{}, 卖出价格{}，卖出数量{}，挂单类型{}.'.format(last_order_id, realTimePrice, qty_or_None, TrdSide.SELL))
                else:
                    print(data)
                    #lastErrMsg = data['last_err_msg'].item()
                    log_2_file.error('下单失败，原因:{lastErrMsg}.'.format(lastErrMsg=data))
                    #待增加微信通知功能
            elif  0 >=  0-ZHISUNXIAN and 0-ZHISUNXIAN >= plRatio: #两个参数为负数
                log_2_file.warn('当前交易单的亏损比例为：{:.1f}%，超过止损线：{}，以当前价格挂单。'.format(plRatio, ZHISUNXIAN))
                realTimePrice = real_time_price(quote_ctx, code)
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret==RET_OK:
                    last_order_time = time.time()
                    last_order_id = data['order_id'][0]
                    last_sell_price = realTimePrice
                    log_2_file.info('挂单成功，订单号:{}, 卖价{}，数量{}，挂单类型{}'.format(last_order_id, realTimePrice, qty_or_None, TrdSide.SELL))
                else:
                    log_2_file.info('挂单失败,失败原因{}，发送微信通知'.format(data))
            else:
                log_2_file.info('由于没有达到盈利({plVal_or_None}-{meibi_zhuan}-{YJ}-{YJ}={yingli})或止损({plRatio}%)状态，程序未进行下单。'.format(
                                plVal_or_None = plVal_or_None,
                                meibi_zhuan = meibi_zhuan,
                                YJ= YJ,
                                yingli = plVal_or_None - float(meibi_zhuan) - YJ - YJ,
                                plRatio = plRatio
                            ))
        else:
            if DEAL_PAUSE:
                if (ksjy_btn['state'] == DISABLED):
                    ksjy_btn['state'] =NORMAL 
                raise Exception('用户暂停了程序交易.....')
            #检查今日盈亏是否到达预期
            if float(jryk) > 0:
                ret, data=trd_ctx.position_list_query(code=code,refresh_cache=True)
                if ret == RET_OK:
                    try:
                        real_jryk_of_cur_code = data['today_pl_val'][0]
                        if real_jryk_of_cur_code >= float(jryk):
                            raise Exception('当前股票盈利({})超过预期，不再进行程序化交易。'.format(real_jryk_of_cur_code))
                        else:
                            log_2_file.info('该股票:{}今日盈利为:{},暂未达到预期:{},继续购买。'.format(code, real_jryk_of_cur_code, jryk))
                    except IndexError:
                        log_2_file.warn('未查询到该股票{}盈亏信息，可能原因是未持有:{}'.format(code, data))
                else:
                    log_2_file.error('查询今日盈亏失败，原因:{lastErrMsg}.'.format(lastErrMsg=data))
            qty_or_None = now_qty #手工输入的数量
            log_2_file.info('当前没有持仓该股票{}今天最后的订单状态是{}，方向是{},可以下单购买。'.format(code, last_order_status,last_order_side))
            realTimePrice = real_time_price(quote_ctx, code)
            if float(last_sell_price)==0 or float(first_buy_price)>float(realTimePrice):
                log_2_file.info('准备买入股票:{},首次购买价格:{},当前价格:{},交易数量:{}'.format(code, first_buy_price, realTimePrice, qty_or_None))
                ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.BUY, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret == RET_OK:
                    last_order_time = time.time()
                    last_order_id = data['order_id'][0]
                    log_2_file.info('下单成功，订单号:{}, 购买价格{}，购买数量{}，挂单类型{}。'.format(last_order_id, realTimePrice, qty_or_None, TrdSide.BUY))
                else:
                    # print(data,get_code_list_type(code)[0])#想不起来为什么这么写
                    # lastErrMsg = data['last_err_msg'].item()#想不起来为什么这么写
                    log_2_file.error('下单失败，原因:{lastErrMsg}.'.format(lastErrMsg=data))
            else:
                log_2_file.info('等待实时价格[{}]低于首次买入价[{}]后再购买。'.format(realTimePrice, first_buy_price))
    else: 
        #挂单后经过delte_order_time还没有成交，则进行撤单(实盘)/改单(模拟) 模拟交易不支持撤单
        cur_time = time.time()
        if cur_time - last_order_time >= delte_order_time:
            if is_debug:
                log_2_file.info('该股票{}处于挂单中{}超过{}秒，进行改单。'.format(code, last_order_status, delte_order_time))
                realTimePrice = real_time_price(quote_ctx, code)
                ret, data = trd_ctx.change_order(last_order_id, realTimePrice, qty_or_None, trd_env=TRD_ENV)
                if ret == RET_OK:
                    last_order_time = time.time()
                    last_order_id = data['order_id'][0]
                    log_2_file.info('该股票{}改单成功，新订单ID{}，订单价格{}。'.format(code, last_order_id, realTimePrice))
                else:
                    log_2_file.error('该股票{}改单失败，原因是:{}。'.format(code, data))
            else:
                log_2_file.info('该股票{}处于挂单中{}超过{}秒，进行撤单。'.format(code, last_order_status, delte_order_time))
                #ret, data = trd_ctx.change_order(last_order_id, realTimePrice, qty_or_None, trd_env=TRD_ENV)
                ret, data = trd_ctx.modify_order(ModifyOrderOp.CANCEL, last_order_id, qty_or_None, 0, trd_env=TRD_ENV)
                if ret == RET_OK:
                    last_order_time = time.time()
                    last_order_id = data['order_id'][0]
                    log_2_file.info('该股票{}已撤单[{}]，订单价格。'.format(code, last_order_id))
                else:
                    log_2_file.error('该股票{}撤单失败，原因是:{}。'.format(code, data))
        else:
            log_2_file.info('该股票{}仍处于挂单中需继续等待，挂单状态{}。'.format(code, last_order_status))

def real_time_price(quote_ctx, stock_num):
    '''
    若持有该股票，则查询该股票实时价格
    返回 406.0 <class 'float'>
    '''
    subscribe_obj = SubsCribe(quote_ctx, stock_num, writer_handler=log_2_file)
    subscribe_obj.query_my_subscription()
    if subscribe_obj.sub_status == NEED_SUBSCRIBE:
        subscribe_obj.subscribe_mystock()
    if subscribe_obj.sub_status == CAN_NOT_SUBSCRIBE:
        subscribe_obj.unsubscribe_mystock_all()
        subscribe_obj.subscribe_mystock()
    ret, cur_price_df = subscribe_obj.quote_ctx.get_stock_quote(get_code_list_type(stock_num)[0])
    if ret == RET_OK:
        if len(cur_price_df) == 0:
            log_2_file.error('无法查询到股票{}的实时价格。'.format(stock_num))
            raise Exception('无法查询到股票{}的实时价格。'.format(stock_num))
        else: 
            tmp_prc = cur_price_df.iloc[0].iat[3].item()
            findal_price = round(tmp_prc, 2)
            log_2_file.info('查询到实时价格为{},转换后的价格为{}。'.format(tmp_prc, findal_price))
            return findal_price
            #return cur_price_df['pl_val'].item()
    else:
        log_2_file.error('查询到股票{code_name}实时价格时发生错误:{errorinfo}。'.format(code_name=stock_num, errorinfo=cur_price_df))
        raise Exception('查询到股票{code_name}实时价格时发生错误:{errorinfo}。'.format(code_name=stock_num, errorinfo=cur_price_df))

def i_have_the_stock(quote_ctx, stock_num, log_2_file):
    '''
    获取账户的持仓列表 检查是否持有该股票stock_num
    返回：(param1, param2, param3， param4) -> (str, float, float, int)
    '''
    global TRD_ENV
    ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
    tmp_stock_dict = {}
    try:
        if ret == RET_OK:
            for index, row in data.iterrows():
                if float(row['qty']) >= 1:
                    tmp_stock_dict.update({row['code']:[row['pl_val'],row['qty'],row['pl_ratio'],row['cost_price']]})
                else:
                    log_2_file.info('股票{}的持仓为{}，认为没有持有该股票'.format(row['code'], row['qty']))
        else:
            raise Exception('查询持仓失败:{}，{}'.format(ret, str(data)))
    except Exception as e:
        if '频率限制' in str(e): #此协议请求太频繁，触发了频率限制，请稍后再试
            log_2_file.warn('查询股票持仓时遇到频率限制：{},尝试重新查询.'.format(str(e)))
            time.sleep(2)
            tmp_stock_dict = {}
            ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
            for index, row in data.iterrows():
                if float(row['qty']) >= 1:
                    tmp_stock_dict.update({row['code']:[row['pl_val'],row['qty'],row['pl_ratio'],row['cost_price']]})
                else:
                    log_2_file.info('股票{}的持仓为{}，认为没有持有该股票'.format(row['code'], row['qty']))
        else:
            log_2_file.error('查询股票持仓接口失败，返回数据：\n{}\n尝试重新查询。'.format(str(e)))
            time.sleep(1)
            tmp_stock_dict = {}
            ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
            for index, row in data.iterrows():
                if float(row['qty']) >= 1:
                    tmp_stock_dict.update({row['code']:[row['pl_val'],row['qty'],row['pl_ratio'],row['cost_price']]})
                else:
                    log_2_file.info('股票{}的持仓为{}，认为没有持有该股票'.format(row['code'], row['qty']))
    # print('*'*50)
    # print(time.strftime('%H:%M:%S',time.localtime(time.time()))+' 本账户已持有{n}个股票{tmp_stock_dict}'.format(n=len(data), tmp_stock_dict=str(tmp_stock_dict.keys())))
    # print('*'*50)
    log_2_file.warn('本账户已持有{n}个股票{tmp_stock_dict}'.format(n=len(tmp_stock_dict), tmp_stock_dict=str(list(tmp_stock_dict.keys()))))
    
    dst_stock_num = get_code_list_type(stock_num)[0]
    log_2_file.info('目标股票是{dst_stock_num}'.format(dst_stock_num=dst_stock_num))
    if dst_stock_num in tmp_stock_dict:
        tempinfo = tmp_stock_dict[dst_stock_num]
        log_2_file.info('已持有该股票{dst_stock_num}'.format(dst_stock_num=dst_stock_num))
        log_2_file.info('成本价是{}'.format(float(tempinfo[3])))
        #return (True, data['pl_val'].item(),  data['qty'].item(), data['pl_ratio'].item())
        return (True, float(tempinfo[0]),int(tempinfo[1]),float(tempinfo[2]),float(tempinfo[3]))
    log_2_file.info('未持有该股票:{dst_stock_num}'.format(dst_stock_num=dst_stock_num))
    return (False, None, None, None, None)

def pre_deal(gmsl, mbz, zsx, jryk, log_2_file):
    global lock
    lock.acquire()
    ksjy_btn['state'] = DISABLED
    if (tzjy_btn['state'] == DISABLED):
        tzjy_btn['state'] =NORMAL 
    global DEAL_PAUSE
    DEAL_PAUSE = False

    # 方案二：查询当天复牌股票中交易量最大的一支
    the_code_for_2nd_stratergy = get_largest_volume_resumed_stock() 
    if the_code_for_2nd_stratergy:
        code_str =  the_code_for_2nd_stratergy
    else:
        log_2_file.warn(f"未找到符合【复牌】定义的股票,将按照涨幅选股。")
        while True:
            #方案一：涨幅百分比前五名且成交额大于指定数值
            the_code_for_1st_stratergy = get_high_turnover_stocks(quote_ctx, log_2_file)   
            if the_code_for_1st_stratergy:
                code_str = the_code_for_1st_stratergy[0]
                break
    mktInfo = get_mkt(code_str)
    trd_ctx = mktInfo.get('trd_ctx')(host='127.0.0.1', port=11111)
    quote_ctx = mktInfo.get('quote_ctx')(host='127.0.0.1', port=11111)
    
    unlock(trd_ctx)
    try:
        if not is_validation(jryk):
            raise Exception('今日盈亏上限只能填写整数或小数！')
        while True:
            start_to_deal(trd_ctx, quote_ctx, mbz, code_str, zsx, gmsl, jryk, log_2_file)
            time.sleep(3)
        #main(test, 30, 15, trd_ctx, quote_ctx, int(mbz), code_str, int(zsx), int(gmsl))
        
    except Exception as e:
        log_2_file.error('遇到异常[%s]需要关闭客户端连接' % str(e))
        if trd_ctx:
            trd_ctx.close()
            log_2_file.info('关闭当前交易连接')
        if quote_ctx:
            quote_ctx.close()
            log_2_file.info('关闭当前查询连接')
        ksjy_btn['state'] = NORMAL
    finally:
        lock.release()
        
def stopp():
    tzjy_btn['state'] = DISABLED
    tkMessageBox.showwarning('警告','待空仓后程序自动会停止，请跟进！')
    global DEAL_PAUSE
    DEAL_PAUSE = True

def deal_thread():
    # gmsl, mbz, zsx
    print(gmsl_entry.get(), mbz_entry3.get(),zsx_entry.get(), log_2_file)
    th=threading.Thread(target=pre_deal, args=(int(gmsl_entry.get()), float(mbz_entry3.get()),float(zsx_entry.get()), jryk_entry.get().strip(), log_2_file))        
    th.setDaemon(True)    
    th.start()    

def stop_thread():
    ts=threading.Thread(target=stopp, args=())        
    ts.setDaemon(True)    
    ts.start() 

def callback(eventObject): 
    global is_debug
    global TRD_ENV
    if '模拟交易' in env.get():
        is_debug = True
        print('开始模拟交易......')
    if '真实交易' in env.get():
        is_debug = False
        print('开始真实交易......')
    TRD_ENV = TrdEnv.SIMULATE if is_debug else TrdEnv.REAL



if __name__ == "__main__":    
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myappid") 
    # import sys
    # gmsl = '100'  #股票数量
    # mbz = '1'     #每笔赚
    # zsx = 8       #止损线
    root = Tk()
    root.title('自动化交易助手V2.5')
    root.geometry("1200x500+200+100")
    root.iconbitmap(r'.\assassin.ico')
    root.rowconfigure(1, weight=2)
    root.columnconfigure(10, weight=2)
    gmsl = Label(root, text='  购买数量(股):',font=("黑体", 12, "bold"))
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
    env = StringVar()
    cmb_env = ttk.Combobox(root, font=("黑体", 12, "bold"), textvariable=env)
    cmb_env['value'] = ('真实交易','模拟交易')
    cmb_env.current(0)
    cmb_env.grid(row=1, column=1,)  
    cmb_env.bind("<<ComboboxSelected>>", callback) 
    ksjy_btn = Button(root, text="开始交易", font=("黑体", 12, "bold"), command=deal_thread)
    ksjy_btn.grid(row=1, column=2, ipadx=30)
    tzjy_btn = Button(root, text="暂停交易", state='disable',font=("黑体", 12, "bold"), command=stop_thread)
    tzjy_btn.grid(row=1, column=3, ipadx=30)
    jryk = Label(root, text='  今日盈亏上限：',font=("黑体", 12, "bold"))
    jryk.grid(row =1, column=4)
    defalut_jryk = StringVar()
    defalut_jryk.set("0")
    jryk_entry = Entry(root, textvariable=defalut_jryk)
    jryk_entry.grid(row=1, column=5)
    scrollbar = Scrollbar(root, orient=VERTICAL)
    listbox = Listbox(root, width=100, height=23, yscrollcommand = scrollbar.set)
    listbox.grid(row=2, column=0, columnspan=11, rowspan=15, sticky=E+N+S+W, padx=10, pady=5)
    listbox.insert(END, '')
    scrollbar.grid(row=2, column=11,  rowspan=15, sticky=E+N+S+W, pady=5)
    scrollbar.config(command=listbox.yview)
    log_2_file = Logger(listbox=listbox)
    

    root.mainloop()