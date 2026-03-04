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
