#!/usr/bin/python
# -*- coding: utf8 -*-

import pandas as pd
from datetime import datetime, timedelta, date
from subscribe import SubsCribe
from futu import *
from logger import Logger
from common import MAX_STOCKS_PER_REQUEST, NEED_SUBSCRIBE, CAN_NOT_SUBSCRIBE, NEED_NOT_SUBSCRIBE

log_2_file = Logger()


def get_first_5codes_by_change_rate(quote_ctx, log_2_file, plate_code):
    """
    获取港股指定板块涨幅前五的股票代码
    get_plate_stock:每 30 秒内最多请求 10 次获取板块内股票列表接口
    Args:
        quote_ctx: 行情上下文
        log_2_file: 日志记录器
        plate_code: 板块代码，如 'HK.Motherboard'
    Returns:
        list: 涨幅前五的股票代码列表
    """
    motherboard_list = []
    ret, data = quote_ctx.get_plate_stock(plate_code,
                                          sort_field=SortField.CHANGE_RATE,
                                          ascend=False)  # 改为 False 以获取涨幅最大
    
    if ret == RET_OK:
        all_motherboard_list = data['code'].values.tolist() 
        motherboard_list = all_motherboard_list[:5] if len(all_motherboard_list) > 5 else all_motherboard_list
        log_2_file.info(f'获取到 {plate_code} 涨幅前五股票: {motherboard_list}')
    else:
        log_2_file.error(f'寻找涨幅前五的数据时发生错误: {data}')
    
    return motherboard_list


def get_high_turnover_stocks(quote_ctx, log_2_file, threshold=50000000, plate_code='HK.Motherboard'):
    """
    筛选指定板块中涨幅前五且成交额大于门槛的股票
    Args:
        quote_ctx: 行情上下文
        log_2_file: 日志记录器
        threshold: 成交额门槛（港元）
        plate_code: 板块代码
    Returns:
        list: 符合条件的股票代码列表
    """
    # 1. 獲取漲幅前五的股票
    target_stocks = get_first_5codes_by_change_rate(quote_ctx, log_2_file, plate_code)
    if not target_stocks:
        log_2_file.warn('没有找到涨幅前五的股票数据')
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
            if row['sec_status']== SecurityStatus.NORMAL and row['turnover'] > threshold:
                result_codes.append([row['code'], float(row['turnover'])])
        return result_codes
    else:
        log_2_file.error(f'获取股票报价时发生错误: {data}')
        return []
