#!/usr/bin/python
# -*- coding: utf8 -*-

# from futu import *
# quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
# print(quote_ctx.subscribe(['HK.00700'], [SubType.QUOTE]))
# quote_ctx.close()
# from futu import *
# import time
# import sys
# sys.stdout = open('hello.txt', 'a')
# quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
# code_list = ['HK.00700']
# start = time.time()
# print('*'*50)
# ss=quote_ctx.subscribe(code_list, [SubType.QUOTE])
# print('*'*50)
# ssss = quote_ctx.get_stock_quote(code_list)[1]
# print('ssss:',ssss)
# print(ssss.index)
# afd = ssss.columns.size 
# print(ssss.columns)
# print('---+++++++--',ssss.iloc[0].iat[3].item(),type(ssss.iloc[0].iat[3].item()),'--+++++--')
# print('------------',ssss['last_price'],'-----------')
# print('*'*50)
# end = time.time()
# print('used',end-start)
# print('*'*50)
# quote_ctx.close()
# import hashlib
# str_md5 = hashlib.md5(b'hailun123').hexdigest()
# print('MD5加密后为 ：' + str_md5)
# from futu import *
# pwd_unlock = '140108'
# trd_ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)
# trd_ctx.unlock_trade(pwd_unlock)
# order_id = "12345"
# print('-'*50)
# print(trd_ctx.history_order_list_query(start='2010-01-01 00:00:00',end='2020-05-01 00:00:00'))
# print('-'*50)
# print(trd_ctx.deal_list_query ())
# print('-'*50)
# trd_ctx.close()

# from futu import *
# pwd_unlock = '140108'
# trd_ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)
# trd_ctx.unlock_trade(pwd_unlock)
# print('-'*50)
# ret, df = trd_ctx.position_list_query()
# print(df)
# print('1',df['code'])
# print('2',df['stock_name'])
# print('3',df['cost_price'])
# print('-'*50)
# trd_ctx.close()

# import time
# import eventlet#导入eventlet这个模块
# eventlet.monkey_patch()#必须加这条代码
# with eventlet.Timeout(2,False):#设置超时时间为2秒
#    time.sleep(4)
#    print('没有跳过这条输出')
# print('跳过了输出')

# from futu import *
# quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
# code_list = ['HK.00700']
# print(quote_ctx.subscribe(code_list, [SubType.QUOTE]))
# print(quote_ctx.get_stock_quote(code_list))
# quote_ctx.close()\


# from futu import *
# quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
# # print(quote_ctx.query_subscription())
# sss=quote_ctx.query_subscription()[1]
# print(sss.get('sub_list').get('QUOTE'))
# quote_ctx.close()

# from futu import *
# pwd_unlock = '140108'
# trd_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
# trd_ctx.unlock_trade(pwd_unlock)
# a,b=trd_ctx.position_list_query()
# print(b)
# # print(b.iloc[0].iat[0])
# print(b['code'].item(),type(b['code'].item()))
# # print(b.iloc[0].iat[6])
# print(b['qty'].item(),type(b['qty'].item()))
# print(b['pl_val'].item(),type(b['pl_val'].item()))
# print(b['pl_ratio'].item(),type(b['pl_ratio'].item()))
# trd_ctx.close()

import time
start_tm = time.strftime("%Y-%m-01 00:00:00",time.localtime())
end_tm =  time.strftime("%Y-%m-%d %X",time.localtime())
from futu import *
pwd_unlock = '140108'
trd_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
start=time.time()
# print(trd_ctx.unlock_trade(pwd_unlock))
# for i in range(1,15):
a,b = trd_ctx.history_deal_list_query(start='2010-01-01 00:00:00',end='2020-05-01 00:00:00')
    # time.sleep(1)
# end=time.time()
# print('asdfasdf',end-start)
# print(trd_ctx.history_deal_list_query(start=start_tm,end=end_tm))

for index, row in b.iterrows():
     print(row['qty'])
trd_ctx.close()
def get_cur_month_deal_list(trd_ctx, pwd_unlock,start_tm=None, end_tm=None):
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
    trd_ctx.unlock_trade(pwd_unlock)
    ret, data = trd_ctx.history_deal_list_query(start=start_tm,end=end_tm)
    if ret == 0:
        for index, row in data.iterrows():
            tmp_month_qty.append(row['qty'])
        return sum(tmp_month_qty)
    else:
        print('请求历史成交数据错误')

if __name__ == '__main__':
    # trd_ctx = OpenUSTradeContext(host='127.0.0.1', port=11111)
    # aaa = get_cur_month_deal_list(trd_ctx, pwd_unlock,start_tm='2010-01-01 00:00:00',end_tm='2020-05-01 00:00:00')
    # print('aaa',aaa)
    # trd_ctx.close()
    # arr = [5000001,1000001,500001, 200001, 50001, 10001, 5001,  1001,  501,   1     ]
    # rat = [0.0030, 0.0035, 0.0040, 0.0045, 0.0050,0.0055,0.0060,0.0070,0.0080,0.0100]
    # # arr = [100, 60,   40,  20,  10,   0]  
    # # rat = [0.01,0.015,0.03,0.05,0.075,0.1]   
    # r = 0 
    # i =  200002
    # for idx in range(0,10): 
    #     if i>arr[idx]:  
    #         #print('i:',i,'arr:',arr[idx],'rat:',rat[idx],'tt:',(i-arr[idx]+1)*rat[idx]  )
    #         r+=(i-arr[idx]+1)*rat[idx]  
    #         i=arr[idx]-1
    # print(r) 
    from futu import *
    pwd_unlock = '140108'
    trd_ctx = OpenHKTradeContext(host='127.0.0.1', port=11111)
    dst_stock_num = ['HK.09988']

    ret, data = trd_ctx.order_list_query(code=dst_stock_num[0],trd_env=TrdEnv.SIMULATE,start='2010-01-01 00:00:00',end='2020-05-18 00:00:00')
    #ret, data = trd_ctx.order_list_query(order_id='816488873138429855', trd_env=TrdEnv.SIMULATE)
    for index, row in data.iterrows():
        print('index:',index, row['order_status'],row['qty'],row['trd_side'])
    #print(trd_ctx.order_list_query(order_id='816488873138429855', trd_env=TrdEnv.SIMULATE))
    trd_ctx.close()
        