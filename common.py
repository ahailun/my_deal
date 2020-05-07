import re
from logger import Logger
from futu import *

#美/港股
US_STOCK = {'MKT':'US', 'trd_ctx':OpenUSTradeContext,'LASTTIME_BUY_PRIC':'cost_price'}
HK_STOCK = {'MKT':'HK', 'trd_ctx':OpenHKTradeContext,'LASTTIME_BUY_PRIC':'cost_price'}

#佣金
YJ = {
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

def myYjNow(stock_num, qt):
    cur_mkt = get_mkt(stock_num).get('MKT')
    price_ladder = YJ.get(cur_mkt, None)
    for i in sorted(price_ladder, reverse=True) : 
        print(i, price_ladder[i])




def is_HK_mkt(num):
    pattern = re.compile(r'\d+')   # 查找数字
    result = pattern.findall(num)
    if result:
        return len(num) == len(result[0])
    else:
        return False

def is_US_mkt(num):
    pattern = re.compile(r'[A-Za-z]+')   # 查找数字
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


def get_code_list(stock_code):
    if is_HK_mkt(stock_code):
        code_list = ['HK.%s' % stock_code]
    if is_US_mkt(stock_code):
        code_list = ['US.%s' % stock_code]
    else:
        code_list = []  #其他市场类型的股票暂不支持
        raise Exception('找不到该股票的市场列表!')
    return code_list

if __name__ == "__main__":
    myYjNow('stocknum', 'qt')