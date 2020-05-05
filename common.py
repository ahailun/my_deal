import re
from logger import Logger
from futu import *

#美/港股
US_STOCK = {'MKT':OpenUSTradeContext,'LASTTIME_BUY_PRIC':'cost_price'}
HK_STOCK = {'MKT':OpenHKTradeContext,'LASTTIME_BUY_PRIC':'cost_price'}

#是否能订阅
CAN_SUBSCRIBE = 0
CAN_NOT_SUBSCRIBE = 1

log =  Logger()

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
        from ftConn import HK_STOCK
        cur_mkt = HK_STOCK
    elif is_US_mkt(code_num):
        from ftConn import US_STOCK
        cur_mkt = US_STOCK
    else:
        log.error('找不到{code}对应的市场，请确定是否输入正确！'.format(code=code_num))
        return None
    return cur_mkt

if __name__ == "__main__":
    print(is_US_mkt('00700'))
    print(is_US_mkt('007ss00'))
    print(is_US_mkt('as22df'))