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
                    last_order_finished, unlock, myYjNow, is_validation, MAX_STOCKS_PER_REQUEST, \
                    PWD_UNLOCK, NEED_SUBSCRIBE, CAN_NOT_SUBSCRIBE, NEED_NOT_SUBSCRIBE, get_dynamic_qty, \
                    avalible_cash, sell_done, buy_done

lock=threading.Lock()

log_2_file = Logger()

#下单限制：30s内最多访问15次，且1s内最多5次
cycle_period_count = 0
cycle_period_start = time.time()

#根据上一次的订单号查询状态
last_order_id = None

last_order_time  = 0.00000      #记录上一次订单时间
last_sell_price  = 0.00000      #记录上一次卖出价格
first_buy_price  = 0.00000      #记录第一次买入价格
delte_order_time = 0.3          #撤单间隔时间
qty_or_None      = 0            #记录股票数量，撤单用

#交易
is_debug = True
TRD_ENV = TrdEnv.REAL           #默认为模拟环境
DEAL_PAUSE = False              #暂停交易

program_st = time.strftime("%Y-%m-%d %X",time.localtime())

def start_to_deal(trd_ctx, quote_ctx, meibi_zhuan, code, zhi_sun_xian, log_2_file):
    '''
    code:HK.00700
    YJ：单程佣金
    zhi_sun_xian:取整，例如10意为10%
    plVal_or_None:盈亏金额
    qty_or_None:数量
    plRatio：盈亏比例
    Q:盈亏规则挂单后，突然股价跌破止损线的情况： plRatio > zhi_sun_xian
    '''
    global last_order_id
    global last_order_time
    global qty_or_None
    global last_sell_price
    global first_buy_price
    global DEAL_PAUSE
    global is_debug
    global TRD_ENV

    last_order_status, last_order_side, last_order_id = get_last_order_status(trd_ctx, code, last_order_id, program_st, PWD_UNLOCK, TRD_ENV)
    log_2_file.info('目前股票[{}]数量[{}],最后一次动作[{}-{}].'.format(code, qty_or_None, last_order_status, last_order_side))

    # 交易之前已经持仓了股票需要考虑吗?
    # pass

    # 程序进行第一次购买, 当前策略下，只够买一次即可。
    if not last_order_id:
        log_2_file.info('准备购买[{}].'.format(code))
        if DEAL_PAUSE:
            if (ksjy_btn['state'] == DISABLED):
                ksjy_btn['state'] =NORMAL 
            raise Exception('用户暂停了程序交易.....')
        
        realTimePrice = real_time_price(quote_ctx, code)
        now_qty = get_dynamic_qty(trd_ctx, code, realTimePrice, TRD_ENV)
        if now_qty == 0:
            free_cash = avalible_cash(trd_ctx, TRD_ENV, log_2_file)
            log_2_file.info('{}可用资金[{}]太少,无法交易该股票[{}].'.format(TRD_ENV, free_cash, code))
            raise Exception('{}可用资金[{}]太少,无法交易该股票[{}].'.format(TRD_ENV, free_cash, code))
        qty_or_None = now_qty #自动计算可以购买的数量
        log_2_file.info('准备以价格[{}]买入[{}]股票[{}]支,'.format(realTimePrice, code, qty_or_None))
        ret, data = trd_ctx.place_order(realTimePrice, qty_or_None, get_code_list_type(code)[0], TrdSide.BUY, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
        if ret == RET_OK:
            last_order_time = time.time()
            last_order_id = data['order_id'][0]
            log_2_file.info('已下单购买，订单号:{}, 购买价格{}，购买数量{}。'.format(last_order_id, realTimePrice, qty_or_None))
        else:
            # lastErrMsg = data['last_err_msg'].item()#想不起来为什么这么写
            log_2_file.error('下单失败，原因:{lastErrMsg}.'.format(lastErrMsg=data))
    
    # 第一次购买后，全部撮合完成 或者 没有全部撮合完成
    else:
        # true/false, 盈亏金额str, 可用数量float, 盈亏比例float, 摊薄成本价int
        (ihavethestock , plVal_or_None, can_sell_qty, plRatio, costPrice) = i_have_the_stock(trd_ctx, code, log_2_file)

        # 当卖单全部撮合成功的时候，程序结束。
        if sell_done(last_order_status, last_order_side):
            log_2_file.info('已成功卖出股票，程序结束')
            raise Exception('已成功卖出股票，程序结束')
        
        # 当‘买单全部撮合成功的时候’ 或 ‘成功买入的时候’ 就准备卖掉
        elif ihavethestock and buy_done(last_order_status, last_order_side):
            if DEAL_PAUSE:
                log_2_file.warn('已持仓股票{}，待挂单后程序会自动暂停，请等待。'.format(code))
            
            log_2_file.info('股票买单结束，准备卖出')
            YJ = myYjNow(trd_ctx, PWD_UNLOCK, code, can_sell_qty, log_2_file, costPrice, is_debug)
            
            # 若达到每笔赚目标则以当前价格卖掉
            if plVal_or_None - float(meibi_zhuan) - YJ - YJ > 0:
                realTimePrice = real_time_price(quote_ctx, code)
                log_2_file.info('到达每笔赚的目标，准备以价格[{}]卖出[{}]数量[{}],盈亏金额:{}'.format(\
                                realTimePrice, code, can_sell_qty, plVal_or_None))
                ret, data = trd_ctx.place_order(realTimePrice, can_sell_qty, get_code_list_type(code)[0], TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret == RET_OK:
                    last_order_time = time.time()
                    last_order_id = data['order_id'][0]
                    last_sell_price = realTimePrice
                    log_2_file.info('下单成功，订单号:{}, 卖出价格{}，卖出数量{}，挂单类型{}.'.format(last_order_id, realTimePrice, can_sell_qty, TrdSide.SELL))
                else:
                    #lastErrMsg = data['last_err_msg'].item()
                    log_2_file.error('下单失败，原因:{lastErrMsg}.'.format(lastErrMsg=data))
                    #待增加微信通知功能
            
            # 若超过止损线则以当前价格卖掉
            elif  0 >=  0-zhi_sun_xian and 0-zhi_sun_xian >= plRatio: #两个参数为负数
                log_2_file.warn('当前交易单的亏损比例为：{:.1f}%，超过止损线：{}，准备挂单卖出。'.format(plRatio, zhi_sun_xian))
                realTimePrice = real_time_price(quote_ctx, code)
                ret, data = trd_ctx.place_order(realTimePrice, can_sell_qty, get_code_list_type(code)[0], TrdSide.SELL, order_type=OrderType.NORMAL, trd_env=TRD_ENV)
                if ret==RET_OK:
                    last_order_id = data['order_id'][0]
                    last_sell_price = realTimePrice
                    log_2_file.info('挂单成功，订单号:{}, 卖价{}，数量{}，挂单类型{}'.format(last_order_id, realTimePrice, can_sell_qty, TrdSide.SELL))
                else:
                    log_2_file.info('挂单失败,失败原因{}，发送微信通知'.format(data))
            
            else:
                log_2_file.info('由于没有达到盈利目标({:.1f}-{:.1f}-{:.1f}-{:.1f}={:.1f})或止损目标({:.1f}%)，继续等待。'.format(
                                plVal_or_None,
                                meibi_zhuan,
                                YJ,
                                YJ,
                                plVal_or_None - float(meibi_zhuan) - YJ - YJ,
                                plRatio
                            ))
        

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
            firstCodeInfo = cur_price_df.iloc[0]
            tmp_prc =float(firstCodeInfo.iat[4])
            finnal_price = round(tmp_prc, 3) # 小数点后面取三位
            log_2_file.info('查询到实时价格为{},转换后的价格为{}。'.format(tmp_prc, finnal_price))
            return finnal_price
            #return cur_price_df['pl_val'].item()
    else:
        log_2_file.error('查询到股票{code_name}实时价格时发生错误:{errorinfo}。'.format(code_name=stock_num, errorinfo=cur_price_df))
        raise Exception('查询到股票{code_name}实时价格时发生错误:{errorinfo}。'.format(code_name=stock_num, errorinfo=cur_price_df))

def i_have_the_stock(quote_ctx, stock_num, log_2_file):
    '''
    获取账户的持仓列表 检查是否持有该股票stock_num
    返回：(param1, param2, param3， param4) -> (盈亏金额str, 可用数量float, 盈亏比例float, 摊薄成本价int)
    可用数量=持有数量(qty)-冻结数量
    '''
    global TRD_ENV
    ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
    tmp_stock_dict = {}
    try:
        if ret == RET_OK:
            for index, row in data.iterrows():
                if float(row['qty']) >= 1:
                    tmp_stock_dict.update({row['code']:[row['pl_val'],row['can_sell_qty'],row['pl_ratio'],row['cost_price']]})
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
                    tmp_stock_dict.update({row['code']:[row['pl_val'],row['can_sell_qty'],row['pl_ratio'],row['cost_price']]})
        else:
            log_2_file.error('查询股票持仓接口失败，返回数据：\n{}\n尝试重新查询。'.format(str(e)))
            time.sleep(1)
            tmp_stock_dict = {}
            ret, data = quote_ctx.position_list_query(trd_env=TRD_ENV, refresh_cache=True)
            for index, row in data.iterrows():
                if float(row['qty']) >= 1:
                    tmp_stock_dict.update({row['code']:[row['pl_val'],row['can_sell_qty'],row['pl_ratio'],row['cost_price']]})

    if len(tmp_stock_dict) == 0:
        log_2_file.warn('本账户当前还没有持仓股票')
        return (False, None, None, None, None) # 未持有
    
    log_2_file.warn('本账户当前已持仓{n}个股票{tmp_stock_dict}'.format(n=len(tmp_stock_dict), tmp_stock_dict=str(list(tmp_stock_dict.keys()))))
    dst_stock_num = get_code_list_type(stock_num)[0]
    if dst_stock_num in tmp_stock_dict:
        tempinfo = tmp_stock_dict[dst_stock_num]
        #return (True, data['pl_val'].item(),  data['qty'].item(), data['pl_ratio'].item())
        return (True, float(tempinfo[0]),int(tempinfo[1]),float(tempinfo[2]),float(tempinfo[3])) # 持有
    

def pre_deal(mbz, zsx, log_2_file):
    global lock
    lock.acquire()
    ksjy_btn['state'] = DISABLED
    if (tzjy_btn['state'] == DISABLED):
        tzjy_btn['state'] =NORMAL 
    global DEAL_PAUSE
    DEAL_PAUSE = False

    from futu import OpenQuoteContext 
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

    # 方案二：查询当天复牌股票中交易量最大的一支
    the_code_for_2nd_stratergy = get_largest_volume_resumed_stock(quote_ctx, log_2_file) 
    if the_code_for_2nd_stratergy:
        code_str =  the_code_for_2nd_stratergy
    else:
        log_2_file.warn(f"未找到符合【复牌】定义的股票,将按照涨幅选股。")
        while True:
            #方案一：涨幅百分比前五名且成交额大于指定数值
            the_code_for_1st_stratergy = get_high_turnover_stocks(quote_ctx, log_2_file)   
            if the_code_for_1st_stratergy:
                sorted_data = sorted(the_code_for_1st_stratergy, key=lambda x: x[1], reverse=True)
                code_str = sorted_data[0][0] # HK.00042
                code_str = code_str[3:]
                break
            else:
                time.sleep(3) # 防止频率限制
                log_2_file.warn(f"持续寻找涨幅前五的股票数据...")
    mktInfo = get_mkt(code_str)
    trd_ctx = mktInfo.get('trd_ctx')(host='127.0.0.1', port=11111)
    
    unlock(trd_ctx)
    try:
        while True:
            start_to_deal(trd_ctx, quote_ctx, mbz, code_str, zsx, log_2_file)
            time.sleep(3)
        #main(test, 30, 15, trd_ctx, quote_ctx, int(mbz), code_str, int(zsx), int(gmsl))
    except Exception as e:
        log_2_file.error('遇到异常[%s].' % str(e))
        if trd_ctx:
            trd_ctx.close()
            log_2_file.info('关闭交易连接和查询连接')
        if quote_ctx:
            quote_ctx.close()
        ksjy_btn['state'] = NORMAL
    finally:
        lock.release()
        
def stopp():
    tzjy_btn['state'] = DISABLED
    tkMessageBox.showwarning('警告','待空仓后程序自动会停止，请跟进！')
    global DEAL_PAUSE
    DEAL_PAUSE = True

def deal_thread():
    th=threading.Thread(target=pre_deal, args=(float(mbz_entry.get()),float(zsx_entry.get()), log_2_file))        
    th.daemon = True  
    th.start()    

def stop_thread():
    ts=threading.Thread(target=stopp, args=())        
    ts.daemon = True   
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
    
    root = Tk()
    root.title('自动化交易助手V2.5')
    
    # 设置窗口尺寸
    window_width = 1200
    window_height = 500
    root.geometry(f"{window_width}x{window_height}")
    
    # 尝试设置窗口图标
    try:
        root.iconbitmap(r'.\assassin.ico')
    except:
        pass  # 图标文件不存在时静默处理
    
    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 计算窗口位置使其居中
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # 设置窗口位置
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # 设置窗口最小尺寸
    root.minsize(800, 400)
    
    # ==================== 网格权重配置 ====================
    # 配置行权重
    for row in range(3):
        if row == 2:  # 日志行需要扩展
            root.rowconfigure(row, weight=1)
        else:
            root.rowconfigure(row, weight=0, minsize=50)
    
    # 配置列权重
    for col in range(12):
        root.columnconfigure(col, weight=1 if col in [0, 2, 4, 6, 8, 10] else 0)
    
    # ==================== 第0行：交易参数设置 ====================
    # 每笔赚
    mbz = Label(root, text='每笔赚:', font=("黑体", 12, "bold"))
    mbz.grid(row=0, column=1, padx=(10, 5), pady=15, sticky=E)
    
    mbz_default = StringVar()
    mbz_entry = Entry(root, textvariable=mbz_default, width=10)  # 重命名以保持一致性
    mbz_entry.grid(row=0, column=2, padx=(5, 5), pady=15, sticky=W)
    mbz_default.set("500")
    
    # 止损线
    zsx = Label(root, text='止损线：', font=("黑体", 12, "bold"))
    zsx.grid(row=0, column=2, padx=(20, 5), pady=15, sticky=E)
    
    defalut_zsx = StringVar()
    zsx_entry = Entry(root, textvariable=defalut_zsx, width=8)
    zsx_entry.grid(row=0, column=3, padx=(5, 2), pady=10, sticky=W)
    defalut_zsx.set("2")
    
    zsx_bfh = Label(root, text='%')
    zsx_bfh.grid(row=0, column=3, padx=(50, 0), pady=15, sticky=W)
    
    # ==================== 第1行：交易控制 ====================
    # 交易环境选择
    env = StringVar()
    
    env_label = Label(root, text='交易环境：', font=("黑体", 12, "bold"))
    env_label.grid(row=1, column=0, padx=(20, 5), pady=15, sticky=E)
    
    cmb_env = ttk.Combobox(root, font=("黑体", 12), textvariable=env, width=12)
    cmb_env['value'] = ('真实交易', '模拟交易')
    cmb_env.current(0)
    cmb_env.grid(row=1, column=1, padx=(0, 20), pady=15, sticky=W)
    cmb_env.bind("<<ComboboxSelected>>", callback)
    
    # 开始交易按钮
    ksjy_btn = Button(root, text="开始交易", font=("黑体", 12, "bold"), 
                     command=deal_thread, width=12, height=1)
    ksjy_btn.grid(row=1, column=2, padx=(0, 15), pady=15, ipadx=5)
    
    # 暂停交易按钮
    tzjy_btn = Button(root, text="暂停交易", state='disabled', 
                     font=("黑体", 12, "bold"), command=stop_thread, width=12, height=1)
    tzjy_btn.grid(row=1, column=3, padx=(0, 20), pady=15, ipadx=5)
    
    # ==================== 第2行：日志显示区 ====================
    # 创建滚动条和列表框的容器框架
    log_frame = Frame(root, relief=GROOVE, bd=1)
    log_frame.grid(row=2, column=0, columnspan=11, sticky=E+W+N+S, padx=20, pady=(0, 20))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    # 滚动条
    scrollbar = Scrollbar(log_frame, orient=VERTICAL)
    scrollbar.grid(row=0, column=1, sticky=N+S, pady=2)
    
    # 列表框
    listbox = Listbox(log_frame, width=100, height=23, 
                     font=("Consolas", 10), bg="#f5f5f5",
                     yscrollcommand=scrollbar.set,
                     selectbackground="#2196F3", selectforeground="white")
    listbox.grid(row=0, column=0, sticky=E+W+N+S, padx=(5, 0), pady=5)
    listbox.insert(END, '系统启动完成，等待用户操作...')
    
    # 滚动条配置
    scrollbar.config(command=listbox.yview)
    
    # 创建日志记录器
    log_2_file = Logger(listbox=listbox)
    
    root.mainloop()
