#!/usr/bin/python
# -*- coding: utf8 -*-

import sys
import os
sys.path.append('..')

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
def get_previous_trading_day_via_api(quote_ctx, target_date_str, log_2_file, market=TradeDateMarket.HK):
    """
    使用 request_trading_days 接口，精准获取指定日期（T日）的前一个交易日（T-1日）。
    
    Args:
        quote_ctx: 行情上下文对象
        target_date_str (str): 目标日期 'YYYY-MM-DD'
        market: 市场，默认港股
    
    Returns:
        str: 前一个交易日的日期字符串 'YYYY-MM-DD'
        None: 如果获取失败或 target_date 是第一个交易日
    """
    # 1. 将目标日期转换为datetime对象，并计算一个足够早的起始日期
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        start_date = (target_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = target_date_str
    except ValueError as e:
        log_2_file.error(f"❌ 日期格式错误: {e}")
        return None
    
    # 2. 调用接口获取交易日历
    ret, trading_days_list = quote_ctx.request_trading_days(
        market=market,
        start=start_date,
        end=end_date
    )
    
    if ret != RET_OK:
        log_2_file.error(f"获取交易日历失败: {trading_days_list}")
        return None
    
    # 3. 检查返回数据格式
    if not isinstance(trading_days_list, list):
        log_2_file.error(f"交易日历数据格式错误，期望 list，实际为 {type(trading_days_list)}")
        return None
    
    if not trading_days_list:
        log_2_file.warn("交易日历列表为空")
        return None
    
    # 4. 从列表中提取交易日（time字段）
    day_list = []
    for day_info in trading_days_list:
        if isinstance(day_info, dict) and 'time' in day_info:
            day_list.append(day_info['time'])
        else:
            log_2_file.warn(f"交易日数据格式异常: {day_info}")
    
    if not day_list:
        log_2_file.error("无法从交易日历数据中提取有效日期")
        return None
    
    # 5. 对日期列表进行排序
    day_list = sorted(day_list)
    
    # 6. 寻找目标日期的前一个交易日
    if target_date_str not in day_list:
        # 目标日期不是交易日（如周末、节假日）
        if len(day_list) >= 2:
            return day_list[-2]  # 取倒数第二个交易日
        else:
            log_2_file.warn("无法找到有效的前一个交易日（数据不足）。")
            return None
    else:
        # 目标日期是交易日
        idx = day_list.index(target_date_str)
        if idx == 0:
            log_2_file.warn("目标日期是查询范围内的第一个交易日，无前一日数据。")
            return None
        return day_list[idx - 1]


def save_snapshot_to_local(snapshot_df, target_date_str=None):
    """
    将快照数据保存到本地文件
    
    Args:
        snapshot_df: 快照数据的DataFrame
        target_date_str: 目标日期字符串，格式为'YYYYMMDD'或'YYYY-MM-DD'
                        如果为None，则使用当天日期
    """
    # 创建快照目录
    snapshot_dir = "./snapshot"
    if not os.path.exists(snapshot_dir):
        os.makedirs(snapshot_dir)
        print(f"📁 创建快照目录: {snapshot_dir}")
    
    # 处理日期格式
    if target_date_str is None:
        target_date_str = date.today().strftime("%Y%m%d")
    else:
        # 将可能的YYYY-MM-DD格式转换为YYYYMMDD
        if '-' in target_date_str:
            target_date_str = target_date_str.replace('-', '')
    
    # 构建文件名
    filename = f"snapshot{target_date_str}.csv"
    filepath = os.path.join(snapshot_dir, filename)
    
    try:
        # 保存为CSV文件
        snapshot_df.to_csv(filepath, index=False)
        log_2_file.info(f"快照数据已保存到: {filepath}")
        return True
    except Exception as e:
        log_2_file.error(f"保存快照数据失败: {e}")
        return False


def get_market_snapshot_batch(quote_ctx, log_2_file, all_stock_codes):
    """
    分批获取市场快照数据
    
    Args:
        quote_ctx: 行情上下文对象
        all_stock_codes: 所有股票代码列表
    
    Returns:
        DataFrame: 合并后的快照数据
    """
    all_snapshots = []
    total_stocks = len(all_stock_codes)
    
    for i in range(0, total_stocks, MAX_STOCKS_PER_REQUEST):
        batch_codes = all_stock_codes[i:i + MAX_STOCKS_PER_REQUEST]
        log_2_file.info(f"正在获取批次 {i//MAX_STOCKS_PER_REQUEST + 1} (股票 {i+1} 到 {min(i+MAX_STOCKS_PER_REQUEST, total_stocks)})...")
        
        ret, snapshot_data = quote_ctx.get_market_snapshot(batch_codes)
        if ret != RET_OK:
            log_2_file.info(f"批次 {i//MAX_STOCKS_PER_REQUEST + 1} 获取失败: {snapshot_data}")
            continue
        
        all_snapshots.append(snapshot_data)
    
    if not all_snapshots:
        log_2_file.error(f"所有批次请求均失败，无数据返回。")
        return None
    
    merged_df = pd.concat(all_snapshots, ignore_index=True)
    log_2_file.info(f"快照数据获取完成，共合并 {len(merged_df)} 条记录。")
    return merged_df


def load_snapshot_from_local(date_str):
    """
    从本地文件读取指定日期的快照数据
    
    Args:
        date_str: 日期字符串，格式为'YYYY-MM-DD'
    
    Returns:
        DataFrame: 快照数据，保持与原API调用相同的格式
    """
    # 处理日期格式，从'YYYY-MM-DD'转换为'YYYYMMDD'
    date_formatted = date_str.replace('-', '')
    
    # 构建文件路径
    filepath = f"./snapshot/snapshot{date_formatted}.csv"
    
    if os.path.exists(filepath):
        try:
            # 读取CSV文件，保持与原API返回相同的格式
            df = pd.read_csv(filepath)
            log_2_file.info(f"从本地加载T-1日快照数据: {filepath}")
            
            # 确保DataFrame格式与get_market_snapshot_batch返回的格式完全一致
            # 这里不需要做任何格式转换，直接返回读取的数据
            return df
        except Exception as e:
            log_2_file.error(f"加载快照数据失败: {e}")
            return None
    else:
        log_2_file.error(f"本地快照文件不存在: {filepath}")
        return None


def get_largest_turnover_resumed_stock(quote_ctx, log_2_file, target_date_str=None):
    """
    主函数：获取港股市场在指定交易日（默认为当天）的复牌股票列表，
           并从中找出交易量最大的那一支。
    
    Returns:
        dict or None: 交易量最大的复牌股票信息，格式为：
                      {'code': 'HK.00700', 'name': '腾讯控股', 'turnover': 10000000}
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
        prev_date_str = get_previous_trading_day_via_api(quote_ctx, target_date_str, log_2_file)
        if not prev_date_str:
            log_2_file.error(f"无法确定前一个交易日，终止查询。")
            return None
        log_2_file.info(f"精准日历对比：{target_date_str} (T日) vs {prev_date_str} (T-1日)")

        # Step 3: 分批获取T日（目标日）的市场快照
        snapshot_t = get_market_snapshot_batch(quote_ctx, log_2_file, all_stock_codes)
        if snapshot_t is None or snapshot_t.empty:
            log_2_file.error(f"获取 {target_date_str} 快照失败或无数据。")
            return None

        save_snapshot_to_local(snapshot_t, target_date_str=target_date_str)

        # Step 4: 分批获取T-1日（前一个交易日）的市场快照
        snapshot_t1 = load_snapshot_from_local(prev_date_str)
        if snapshot_t1 is None or snapshot_t1.empty:
            log_2_file.error(f"获取 {prev_date_str} 快照失败或无数据。")
            return None

        # Step 5: 数据合并与筛选 - 修复'security_status'列不存在的问题
        # 首先检查所需的列是否存在
        required_columns_t = ['code', 'name', 'sec_status', 'turnover']  # 此处已修正
        required_columns_t1 = ['code', 'sec_status']  # 此处已修正
        
        # 检查T日快照的列
        missing_columns_t = [col for col in required_columns_t if col not in snapshot_t.columns]
        if missing_columns_t:
            log_2_file.error(f"T日快照缺少必要的列: {missing_columns_t}")
            log_2_file.info(f"T日快照可用列: {list(snapshot_t.columns)}")
            return None
        
        # 检查T-1日快照的列
        missing_columns_t1 = [col for col in required_columns_t1 if col not in snapshot_t1.columns]
        if missing_columns_t1:
            log_2_file.error(f"T-1日快照缺少必要的列: {missing_columns_t1}")
            log_2_file.info(f"T-1日快照可用列: {list(snapshot_t1.columns)}")
            return None
        
        # 使用正确的列名进行数据合并
        df_t = snapshot_t.set_index('code')[['name', 'sec_status', 'turnover']].copy()  # 此处已修正
        df_t1 = snapshot_t1.set_index('code')[['sec_status']].copy()  # 此处已修正
        #df_t1.columns = ['sec_status_t1']  # 重命名，避免合并后列名冲突
        df_t1.columns = ['sec_status_t1']
        
        df_merge = df_t.join(df_t1, how='inner')
        log_2_file.info(f"可用于状态对比的有效股票数量: {len(df_merge)}")

        # Step 6: 核心筛选逻辑
        #condition_resumed = (df_merge['security_status_t1'] == SecurityStatus.SUSPENDED) & \
        #                    (df_merge['security_status'] == SecurityStatus.NORMAL)
        condition_resumed = (df_merge['sec_status_t1'] == SecurityStatus.SUSPENDED) & \
                            (df_merge['sec_status'] == SecurityStatus.NORMAL)
        resumed_stocks_df = df_merge[condition_resumed].reset_index()
        log_2_file.info(f"{target_date_str} 港股【复牌】股票数量: {len(resumed_stocks_df)}")
        
        # Step 7: 从复牌股票中找出交易量最大的那一支
        if resumed_stocks_df.empty:
            log_2_file.info(f"今日无复牌股票，无法比较交易量。")
            return None
        # 按turnover(成交额)降序排序
        resumed_stocks_df_sorted = resumed_stocks_df.sort_values(by='turnover', ascending=False)
        largest_turnover_stock = resumed_stocks_df_sorted.iloc[0]
        result = {
            'code': largest_turnover_stock['code'],
            'name': largest_turnover_stock['name'],
            'turnover': int(largest_turnover_stock['turnover'])  # 转换为整数类型
        }
        if result['volume'] >= 50000000: # 5千万
            log_2_file.info(f"交易量最大的复牌股票: {result['code']} {result['name']}, 成交额: {result['volume']:,}")
            return result['code']
        log_2_file.info(f"交易量最大的复牌股票: {result['code']} {result['name']}, 成交额: {result['volume']:,}小于5千万.")
        return None
    except Exception as e:
        log_2_file.error(f"程序执行异常: {e}")
        import traceback
        log_2_file.error(f"详细错误信息: {traceback.format_exc()}")
        return None
    finally:
        pass


if __name__ == '__main__':
    # 使用示例：查询当天（默认）复牌股票中交易量最大的一支
    # 注意：这里需要实际的Futu API连接
    try:
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        largest_stock = get_largest_turnover_resumed_stock(quote_ctx, log_2_file)
        
        if largest_stock:
            print(f"\n📈 交易量最大的复牌股票详情：")
            print(f"股票代码: {largest_stock['code']}")
            print(f"股票名称: {largest_stock['name']}")
            print(f"当日成交额: {largest_stock['turnover']:,}")
        else:
            print("⚠️ 未找到复牌股票，或查询失败。")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
    finally:
        if 'quote_ctx' in locals():
            quote_ctx.close()