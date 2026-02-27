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
import pandas as pd
from datetime import datetime, timedelta, date
from common import is_HK_mkt, is_US_mkt, get_code_list_type, get_last_order_status, get_mkt, \
                    last_order_is_over,myYjNow, is_validation, MAX_STOCKS_PER_REQUEST

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

def unlock(trd_ctx):
    ret, data = trd_ctx.unlock_trade(PWD_UNLOCK)
    if ret==RET_OK:
        return True
    return False

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

def get_first_5codes_by_change_rate(quote_ctx, log_2_file, plate_code):
    """
    獲取港股指定板塊漲幅前五的股票代碼
    Args:
        quote_ctx: 行情上下文
        log_2_file: 日誌記錄器
        plate_code: 板塊代碼，如 'HK.Motherboard'
    Returns:
        list: 漲幅前五的股票代碼列表
    """
    motherboard_list = []
    ret, data = quote_ctx.get_plate_stock(plate_code,
                                          sort_field=SortField.CHANGE_RATE,
                                          ascend=False)  # 改為 False 以獲取漲幅最大
    
    if ret == RET_OK:
        all_motherboard_list = data['code'].values.tolist() 
        motherboard_list = all_motherboard_list[:5] if len(all_motherboard_list) > 5 else all_motherboard_list
        log_2_file.info(f'獲取到 {plate_code} 漲幅前五股票: {motherboard_list}')
    else:
        log_2_file.error(f'尋找漲幅前五的數據時發生錯誤: {data}')
    
    return motherboard_list


def get_high_turnover_stocks(quote_ctx, log_2_file, threshold=1000000, plate_code='HK.Motherboard'):
    """
    篩選指定板塊中漲幅前五且成交額大於門檻的股票
    
    Args:
        quote_ctx: 行情上下文
        log_2_file: 日誌記錄器
        threshold: 成交額門檻（港元）
        plate_code: 板塊代碼
    
    Returns:
        list: 符合條件的股票代碼列表
    """
    # 1. 獲取漲幅前五的股票
    target_stocks = get_first_5codes_by_change_rate(quote_ctx, log_2_file, plate_code)
    if not target_stocks:
        log_2_file.warn('沒有找到漲幅前五的股票數據')
        return []
    for stock_num in target_stocks:
        subscribe_obj = SubsCribe(quote_ctx, stock_num, writer_handler=log_2_file)
        subscribe_obj.query_my_subscription()
        if subscribe_obj.sub_status == NEED_SUBSCRIBE:
            subscribe_obj.subscribe_mystock()
        if subscribe_obj.sub_status == CAN_NOT_SUBSCRIBE:
            subscribe_obj.unsubscribe_mystock_all()
            subscribe_obj.subscribe_mystock()
    ret, data = subscribe_obj.quote_ctx.get_stock_quote(target_stocks)
    if ret == RET_OK:
        result_codes = []
        for _, row in data.iterrows():
            if row['turnover'] > threshold:
                result_codes.append(row['code'])
        log_2_file.info(f'成交額大於 {threshold} 的股票: {result_codes}')
        return result_codes
    else:
        log_2_file.error(f'獲取股票報價時發生錯誤: {data}')
        return []


"""
富途OpenAPI：查询指定日期港股复牌股票列表，并返回其中交易量最大的股票
功能：1. 查询复牌股票 2. 按成交量取最大值
"""
def get_previous_trading_day_via_api(quote_ctx, target_date_str, market=Market.HK):
    """（此函数保持不变）"""
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    start_date = (target_date - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = target_date_str

    ret, trading_days_data = quote_ctx.request_trading_days(
        market=market,
        start=start_date,
        end=end_date
    )
    if ret != RET_OK:
        log_2_file.warn(f"获取交易日历失败: {trading_days_data}")
        return None
    day_list = sorted(trading_days_data['trading_day'].tolist())
    if target_date_str not in day_list:
        if len(day_list) >= 2:
            return day_list[-2]
        else:
            log_2_file.warn(f"无法找到有效的前一个交易日（数据不足）。")
            return None
    else:
        idx = day_list.index(target_date_str)
        if idx == 0:
            log_2_file.warn(f"目标日期是查询范围内的第一个交易日，无前一日数据。")
            return None
        return day_list[idx - 1]

def get_market_snapshot_batch(quote_ctx, all_stock_codes, date_str):
    """（此函数保持不变，分批获取快照）"""
    all_snapshots = []
    total_stocks = len(all_stock_codes)
    
    for i in range(0, total_stocks, MAX_STOCKS_PER_REQUEST):
        batch_codes = all_stock_codes[i:i + MAX_STOCKS_PER_REQUEST]
        log_2_file.info(f"正在获取批次 {i//MAX_STOCKS_PER_REQUEST + 1} (股票 {i+1} 到 {min(i+MAX_STOCKS_PER_REQUEST, total_stocks)})...")
        
        ret, snapshot_data = quote_ctx.get_market_snapshot(batch_codes, date_str=date_str)
        if ret != RET_OK:
            log_2_file.info(f"批次 {i//MAX_STOCKS_PER_REQUEST + 1} 获取失败: {snapshot_data}")
            continue
        
        all_snapshots.append(snapshot_data)
    
    if not all_snapshots:
        log_2_file.errornfo(f"所有批次请求均失败，无数据返回。")
        return None
    
    merged_df = pd.concat(all_snapshots, ignore_index=True)
    log_2_file.info(f"快照数据获取完成，共合并 {len(merged_df)} 条记录。")
    return merged_df

def get_largest_volume_resumed_stock(quote_ctx, target_date_str=None):
    """
    主函数：获取港股市场在指定交易日（默认为当天）的复牌股票列表，
           并从中找出交易量最大的那一支。
    
    Returns:
        dict or None: 交易量最大的复牌股票信息，格式为：
                      {'code': 'HK.00700', 'name': '腾讯控股', 'volume': 10000000}
                      如果无复牌股票或查询失败，则返回 None。
    """
    try:
        # Step 0: 确定目标日期
        if target_date_str is None:
            today = date.today()
            target_date_str = today.strftime('%Y-%m-%d')
            log_2_file.warn(f"未指定日期，默认使用当天：{target_date_str}")
        else:
            log_2_file.warn(f"用户指定目标日期：{target_date_str}")

        # Step 1: 获取港股所有正股列表
        ret, data = quote_ctx.get_stock_basicinfo(Market.HK, SecurityType.STOCK)
        if ret != RET_OK:
            log_2_file.error(f"获取股票列表失败: {data}")
            return None
        all_stock_codes = data['code'].tolist()
        log_2_file.info(f"基础股票池数量: {len(all_stock_codes)}")
        log_2_file.info(f"预计需要拆分为 { (len(all_stock_codes) + MAX_STOCKS_PER_REQUEST - 1) // MAX_STOCKS_PER_REQUEST } 个批次进行请求。")

        # Step 2: 使用API获取前一个交易日
        prev_date_str = get_previous_trading_day_via_api(quote_ctx, target_date_str)
        if not prev_date_str:
            log_2_file.error(f"无法确定前一个交易日，终止查询。")
            return None
        log_2_file.info(f"精准日历对比：{target_date_str} (T日) vs {prev_date_str} (T-1日)")

        # Step 3: 分批获取T日（目标日）的市场快照
        snapshot_t = get_market_snapshot_batch(quote_ctx, all_stock_codes, target_date_str)
        if snapshot_t is None or snapshot_t.empty:
            log_2_file.error(f"获取 {target_date_str} 快照失败或无数据。")
            return None

        # Step 4: 分批获取T-1日（前一个交易日）的市场快照
        snapshot_t1 = get_market_snapshot_batch(quote_ctx, all_stock_codes, prev_date_str)
        if snapshot_t1 is None or snapshot_t1.empty:
            log_2_file.error(f"获取 {prev_date_str} 快照失败或无数据。")
            return None

        # Step 5: 数据合并与筛选
        df_t = snapshot_t.set_index('code')[['name', 'security_status', 'volume']].copy()  # 【新增】包含volume
        df_t1 = snapshot_t1.set_index('code')[['security_status']].copy()
        df_t1.columns = ['security_status_t1']
        
        df_merge = df_t.join(df_t1, how='inner')
        log_2_file.info(f"可用于状态对比的有效股票数量: {len(df_merge)}")

        # Step 6: 核心筛选逻辑
        condition_resumed = (df_merge['security_status_t1'] == SecurityStatus.SUSPENDED) & \
                            (df_merge['security_status'] == SecurityStatus.NORMAL)
        resumed_stocks_df = df_merge[condition_resumed].reset_index()
        log_2_file.info(f"{target_date_str} 港股准确【复牌】股票数量: {len(resumed_stocks_df)}")
        # Step 7: 【新增核心】从复牌股票中找出交易量最大的那一支
        if resumed_stocks_df.empty:
            print("ℹ️  今日无复牌股票，无法比较交易量。")
            return None
        # 按 volume（成交量）降序排序
        # 注意：快照中的 volume 字段代表当日累计成交量，单位为股
        resumed_stocks_df_sorted = resumed_stocks_df.sort_values(by='volume', ascending=False)
        largest_volume_stock = resumed_stocks_df_sorted.iloc[0]
        result = {
            'code': largest_volume_stock['code'],
            'name': largest_volume_stock['name'],
            'volume': int(largest_volume_stock['volume'])  # 转换为整数类型
        }
        log_2_file.info(f"🏆 交易量最大的复牌股票: {result['code']} {result['name']}, 成交量: {result['volume']:,} 股")
        return result

    except Exception as e:
        log_2_file.error(f"💥 程序执行异常: {e}")
        return None
    finally:
        pass


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
                if my_subscribe_list and get_code_list_type(self.stock_code)[0] in my_subscribe_list:
                    self.writer_handler.info('已订阅该股票{},不需要再次订阅。'.format(self.stock_code))
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
    
def get_gpdm(quote_ctx, log_2_file):
    the_code_for_2nd_stratergy = get_largest_volume_resumed_stock() # 使用示例：查询当天（默认）复牌股票中交易量最大的一支
    if the_code_for_2nd_stratergy:
        #log_2_file.info(f"交易量最大的复牌股票详情：股票代码: {the_code_for_2nd_stratergy['code']}, 股票名称: {the_code_for_2nd_stratergy['name']},当日成交量: {the_code_for_2nd_stratergy['volume']:,} 股")
        return the_code_for_2nd_stratergy
    else:
        log_2_file.warn(f"未找到符合【复牌】定义的股票,将按照涨幅选股。")
        while True:
            the_code_for_1st_stratergy = get_high_turnover_stocks(quote_ctx, log_2_file)   #方案一：涨幅百分比前五名且成交额大于指定数值
            if the_code_for_1st_stratergy:
                return the_code_for_1st_stratergy

def deal(gpdm, gmsl, mbz, zsx, jryk, log_2_file):
    global lock
    lock.acquire()
    ksjy_btn['state'] = DISABLED
    if (tzjy_btn['state'] == DISABLED):
        tzjy_btn['state'] =NORMAL 
    global DEAL_PAUSE
    DEAL_PAUSE = False
    mktInfo = get_mkt(gpdm)
    trd_ctx = mktInfo.get('trd_ctx')(host='127.0.0.1', port=11111)
    quote_ctx = mktInfo.get('quote_ctx')(host='127.0.0.1', port=11111)
    code_str = gpdm
    unlock(trd_ctx)
    try:
        if not is_validation(jryk):
            raise Exception('今日盈亏上限只能填写整数或小数！')
        #def start_to_deal(trd_ctx, quote_ctx, meibi_zhuan, code, ZHISUNXIAN, now_qty, log_2_file)
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
    # #gpdm, gmsl, mbz, zsx
    print(gpdm_entry.get(), gmsl_entry.get(), mbz_entry3.get(),zsx_entry.get(), log_2_file)
    th=threading.Thread(target=deal, args=(gpdm_entry.get(), int(gmsl_entry.get()), float(mbz_entry3.get()),float(zsx_entry.get()), jryk_entry.get().strip(), log_2_file))        
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