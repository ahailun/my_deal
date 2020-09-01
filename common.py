import re
import time
from logger import Logger
from futu import OpenUSTradeContext, OpenHKTradeContext, OpenQuoteContext, OrderStatus

#美/港股
# US_STOCK = {'MKT':'US', 'trd_ctx':OpenUSTradeContext(host='127.0.0.1', port=11111),'quote_ctx':OpenQuoteContext(host='127.0.0.1', port=11111), 'LASTTIME_BUY_PRIC':'cost_price'}
# HK_STOCK = {'MKT':'HK', 'trd_ctx':OpenHKTradeContext(host='127.0.0.1', port=11111), 'quote_ctx':OpenQuoteContext(host='127.0.0.1', port=11111), 'LASTTIME_BUY_PRIC':'cost_price'}
US_STOCK = {'MKT':'US', 'trd_ctx':OpenUSTradeContext, 'quote_ctx':OpenQuoteContext, 'LASTTIME_BUY_PRIC':'cost_price'}
HK_STOCK = {'MKT':'HK', 'trd_ctx':OpenHKTradeContext, 'quote_ctx':OpenQuoteContext, 'LASTTIME_BUY_PRIC':'cost_price'}

US_is_price_package1 = True
HK_is_price_package1 = True
HK_is_price_package1_mianyong = True

#佣金
YJ_LADDER = {
    'US': {
            '0.0100':[1, 500],
            '0.0080':[501, 1000],
            '0.0070':[1001, 5000],
            '0.0060':[5001, 10000],
            '0.0055':[10001, 50000],
            '0.0050':[50001, 200000],
            '0.0045':[200001, 500000],
            '0.0040':[500001, 1000000],
            '0.0035':[1000001, 5000000],
            '0.0030':[5000001, 30 * 60 * 12 * 22 * 100000000000],
    },
    'HK': {},
}


def get_cur_month_deal_total(trd_ctx, pwd_unlock, log_2_file, start_tm=None, end_tm=None):
    '''
    功能：获取本月成交数量
    限制：请求协议ID:2222, 30秒内请求最多10次，若只在卖出时调用可不考虑限制条件
         quote_ctx:OpenUSTradeContext/OpenHKTradeContext
    返回：成交总数(美股：总股数，港股：暂未知)
    '''
    tmp_month_qty = []
    if not start_tm:
        start_tm=time.strftime("%Y-%m-01 00:00:00",time.localtime()) 
    if not end_tm:
        end_tm = time.strftime("%Y-%m-%d %X",time.localtime())
    ret, data = trd_ctx.history_deal_list_query(start=start_tm,end=end_tm)
    if ret == 0:
        for index, row in data.iterrows():
            tmp_month_qty.append(row['qty'])
        return sum(tmp_month_qty)
    else:
        log_2_file.error('请求历史成交数据错误:'+data)

def get_last_order_status(trd_ctx, code, orderid, pwd_unlock, TRD_ENV):
    # time.sleep(1)
    if orderid: #下单后等待1s再查询订单状态
        ret, data = trd_ctx.order_list_query(order_id=orderid, trd_env=TRD_ENV)
    else:
        start_tm = time.strftime("2020-03-01 00:00:00",time.localtime()) #目的是尽量包含所有该支股票的信息
        end_tm = time.strftime("%Y-%m-%d %X",time.localtime())
        ret, data = trd_ctx.order_list_query(code=code, trd_env=TRD_ENV, start=start_tm, end=end_tm)
    if ret == 0:
        if len(data) != 0:
            if isinstance(data, str):
                raise Exception(data)
            for index, row in data.iterrows():
                if index==0:
                    return row['order_status'], row['trd_side']
        else:
            return None, None
    else:
        raise Exception(data)

def last_order_is_over(order_status):
    #return order_status in ['NONE','UNSUBMITTED','SUBMIT_FAILED','FILLED_ALL','CANCELLED_PART','CANCELLED_ALL','FAILED','DISABLED','DELETED']
    return order_status in [OrderStatus.NONE, OrderStatus.UNSUBMITTED, OrderStatus.SUBMIT_FAILED, \
                            OrderStatus.FILLED_ALL, OrderStatus.CANCELLED_PART, OrderStatus.CANCELLED_ALL, \
                            OrderStatus.FAILED, OrderStatus.DISABLED, OrderStatus.DELETED, \
                            None #未查询到状态时，返回为None
                            ]

def is_HK_mkt(num):
    pattern = re.compile(r'\d+')   # 查找数字
    result = pattern.findall(num)
    if result:
        return len(num) == len(result[0])
    else:
        return False

def is_US_mkt(num):
    pattern = re.compile(r'[A-Za-z.]+')   # 查找数字
    result = pattern.findall(num)
    if result:
        return len(num) == len(result[0])
    else:
        return False

def get_mkt(code_num):
    if is_HK_mkt(code_num):
        cur_mkt = HK_STOCK
    elif is_US_mkt(code_num):
        cur_mkt = US_STOCK
    else:
        raise Exception('找不到{code}对应的市场，请确定是否输入正确！'.format(code=code_num))
    return cur_mkt


def get_code_list_type(stock_code):
    if is_HK_mkt(stock_code):
        code_list = ['HK.%s' % stock_code]
    elif is_US_mkt(stock_code):
        code_list = ['US.%s' % stock_code]
    else:
        code_list = []  #其他市场类型的股票暂不支持
        raise Exception('找不到该股票的市场列表!')
    return code_list

def myYjNow(trd_ctx, pwd_unlock, stock_num, now_qty, log_2_file, realTimePrice, is_debug_or_not):
    '''
    计算佣金yj和平台使用费platcost
    '''
    cur_mkt = get_mkt(stock_num).get('MKT')
    if 'US' in cur_mkt:          #若当前交易为美股
        total_cost = now_qty * realTimePrice
        price_ladder = YJ_LADDER.get(cur_mkt, None)
        if US_is_price_package1: #美股套餐一
            yongjin_tmp = now_qty * 0.0049 if now_qty * 0.0049 > 0.99 else 0.99
            pingtaishiyongfei_tmp = now_qty * 0.005 if now_qty * 0.005 > 1 else 1
            jiaoshoufei_tmp = now_qty * 0.003 #交收费
            zjhgf = max(0.01, 0.0000221*total_cost)#证监会规费,0.0000221*交易金额，最低0.01 美元
            #交易活动费
            return yongjin_tmp+jiaoshoufei_tmp+pingtaishiyongfei_tmp+zjhgf
        else:                    #美股阶梯收费
            month_qty = get_cur_month_deal_total(trd_ctx, pwd_unlock, log_2_file)
            price_ladder_price = []
            price_ladder_num = []
            platcost = 0.000 
            for i in sorted(price_ladder, reverse=False): 
                price_ladder_price.append(i)
                price_ladder_num.append(price_ladder[i][0])
            #print(price_ladder_price,price_ladder_num)
            if not len(price_ladder_price) == len(price_ladder_num):
                raise Exception('阶梯价格设置对应格式错误')
            for idx in range(0, len(price_ladder_price)): 
                if now_qty+month_qty>price_ladder_num[idx]:  
                    if price_ladder_num[idx]==1:
                        platcost+=now_qty*float(price_ladder_price[idx])
                    else:
                        platcost+=(now_qty+month_qty-price_ladder_num[idx]+1)*float(price_ladder_price[idx])
                        if price_ladder_num[idx]-1-month_qty > 0:
                            platcost+=(price_ladder_num[idx]-1-month_qty)*float(price_ladder_price[idx+1])
                    break
            yj = now_qty * 0.0049 if now_qty * 0.0049 > 0.99 else 0.99
            return platcost + yj
    if 'HK' in cur_mkt:
        total_cost = now_qty * realTimePrice
        if HK_is_price_package1:
            if is_debug_or_not:
                yj = max(3, total_cost * 3 / 10000) #模拟交易时佣金一定存在
            else:
                yj = 0 if HK_is_price_package1_mianyong else max(3, total_cost * 3 / 10000) #港股佣金0.03%,若免用则为0
            platcost = 15 #平台使用费
            jyxt_syf = 0.5 #交易系统使用费
            jiaoshoufei_tmp = min(100, max(2, total_cost * 2 /100000))    #港股交收费0.002%,最低2港元，最高100港元
            yhs = max(1, 0.1 * total_cost / 100)  #印花税
            jyf = max(0.01, 5 * total_cost / 100000 ) #交易费
            jyzf = max(0.01, 27 * total_cost / 1000000) #交易征费
            return yj + platcost + jyxt_syf + jiaoshoufei_tmp + yhs + jyf + jyzf

if __name__ == "__main__":
    myYjNow('trd_ctx', 'pwd_unlock', 'stocknum', 'now_qty', 100)