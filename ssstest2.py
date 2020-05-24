import time
asdf = 'asdf'
def aaaa(func, t, n):
    '''
    t时间间隔内的最多n次交易
    '''
    cycle_period_start=time.time()
    cycle_period_count = 0
    while True:
        cycle_period_now = time.time()
        if cycle_period_now - cycle_period_start <= int(t):
            print('cycle_period_now:%s,cycle_period_start:%s' % (cycle_period_now,cycle_period_start), cycle_period_now-cycle_period_start)
            if cycle_period_count <= int(n):
                print('间隔小于15次,可以执行，cycle_period_now=%s,cycle_period_count=%s'%(cycle_period_now,cycle_period_count))
                func()
                #cycle_period_start = time.time()
                cycle_period_count += 1
            else:
                print('当前{period_t}s内已执行{period_n}次，无法交易需等待下一次交易机会。'.format(period_t=t, period_n=n))
        else:
            print('cycle_period_now:%s,cycle_period_start:%s' % (cycle_period_now, cycle_period_start),cycle_period_now-cycle_period_start)
            print('间隔超过30s可以执行，cycle_period_count=%s'%(cycle_period_count))
            func()
            cycle_period_start = time.time()
            cycle_period_count = 0
        time.sleep(20)

def ffff():
    print(asdf)

if __name__=='__main__':
    #aaaa(ffff, 30, 15)
    #ffff()
    from futu import *
    US_STOCK = {'MKT':'US', 'trd_ctx':OpenUSTradeContext(host='127.0.0.1', port=11111),'LASTTIME_BUY_PRIC':'cost_price'}
    xx=US_STOCK.get('trd_ctx')
    xx.close()
    print(US_STOCK)
    print(xx)
