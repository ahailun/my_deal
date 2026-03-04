#!/usr/bin/python
# -*- coding: utf8 -*-

import pandas as pd
from datetime import datetime, timedelta, date
from subscribe import SubsCribe
from futu import *
from logger import Logger
from common import MAX_STOCKS_PER_REQUEST, NEED_SUBSCRIBE, CAN_NOT_SUBSCRIBE, NEED_NOT_SUBSCRIBE

log_2_file = Logger()

"""
富途OpenAPI：查询指定日期港股复牌股票列表，并返回其中交易量最大的股票
功能：1. 查询复牌股票 2. 按成交量取最大值
"""
def get_previous_trading_day_via_api(quote_ctx, target_date_str, market='Market.HK'):
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
            log_2_file.info(f"今日无复牌股票，无法比较交易量。")
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
        log_2_file.info(f"交易量最大的复牌股票: {result['code']} {result['name']}, 成交量: {result['volume']:,} 股")
        return result['code']
    except Exception as e:
        log_2_file.error(f"程序执行异常: {e}")
        return None
    finally:
        pass
