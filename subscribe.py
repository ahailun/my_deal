#!/usr/bin/python
# -*- coding: utf8 -*-

from futu import *
import sys, time
from logger import Logger

log_2_file = Logger()

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
    