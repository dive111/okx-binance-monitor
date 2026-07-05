#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX和Binance交易所公告监控系统
每10分钟检查一次新公告，并通过Telegram发送到指定群组
"""

import json
import os
import time
import logging
import requests
from datetime import datetime
from telegram import Bot
from pathlib import Path

# 配置文件路径
CONFIG_FILE = "config.json"
SENT_FILE = "sent_announcements.json"

# 设置日志
def setup_logging(config):
    """配置日志系统"""
    log_file = config.get("logging", {}).get("log_file", "monitor.log")
    log_level = config.get("logging", {}).get("log_level", "INFO")
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def load_config():
    """加载配置文件"""
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 从环境变量读取敏感信息
    telegram_config = config.get('telegram', {})
    bot_token_env = telegram_config.get('bot_token_env', 'TELEGRAM_BOT_TOKEN')
    chat_id_env = telegram_config.get('chat_id_env', 'TELEGRAM_CHAT_ID')
    
    bot_token = os.environ.get(bot_token_env)
    chat_id = os.environ.get(chat_id_env)
    
    if not bot_token or not chat_id:
        raise ValueError(f"请设置环境变量: {bot_token_env} 和 {chat_id_env}")
    
    # 将环境变量值写入配置
    config['telegram']['bot_token'] = bot_token
    config['telegram']['chat_id'] = int(chat_id)
    
    return config

def load_sent_announcements():
    """加载已发送的公告ID列表"""
    if Path(SENT_FILE).exists():
        with open(SENT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"okx": [], "binance": []}

def save_sent_announcements(sent_data):
    """保存已发送的公告ID列表"""
    with open(SENT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sent_data, f, ensure_ascii=False, indent=2)

def get_okx_announcements(logger):
    """获取OKX最新公告"""
    try:
        # OKX API - 根据服务器位置选择合适的区域
        # 新加坡服务器使用 en-SG 或 zh-SG
        url = "https://www.okx.com/api/v5/support/announcements?catalogId=1&limit=20"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            logger.warning("OKX API返回404，尝试备用方案...")
            # 尝试直接访问帮助中心页面解析HTML
            return []
        
        response.raise_for_status()
        data = response.json()
        announcements = []
        
        # 解析OKX公告数据
        if data.get('code') == '0' and 'data' in data:
            for item in data['data']:
                ann = {
                    'id': str(item.get('indexId', '')),
                    'title': item.get('title', ''),
                    'link': f"https://www.okx.com/support/hc/articles/{item.get('indexId', '')}",
                    'time': item.get('publishTime', ''),
                    'type': item.get('typeName', '公告')
                }
                announcements.append(ann)
        
        logger.info(f"OKX: 获取到 {len(announcements)} 条公告")
        return announcements
        
    except Exception as e:
        logger.error(f"获取OKX公告失败: {str(e)}")
        return []

def get_binance_announcements(logger):
    """获取Binance最新公告"""
    try:
        # Binance 公告 API - 使用新加坡区域
        url = "https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query"
        
        payload = {
            "catalogId": "48",
            "pageNo": 1,
            "pageSize": 20
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        logger.info(f"Binance API响应状态码: {response.status_code}")
        
        if response.status_code == 400:
            logger.warning("Binance API返回400，尝试备用方案...")
            # 尝试不同的 catalogId
            for catalog_id in ["48", "49", "50", "51", "1"]:
                payload_test = {
                    "catalogId": catalog_id,
                    "pageNo": 1,
                    "pageSize": 20
                }
                response = requests.post(url, json=payload_test, headers=headers, timeout=30)
                logger.info(f"尝试 catalogId={catalog_id}, 状态码: {response.status_code}")
                if response.status_code != 400:
                    break
        
        if response.status_code != 200:
            logger.error(f"Binance API返回非200状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text[:200]}")
            return []
        
        data = response.json()
        announcements = []
        
        # 解析Binance公告数据
        if data.get('code') == '000000' and 'data' in data:
            articles = data['data'].get('articles', [])
            for item in articles:
                ann = {
                    'id': str(item.get('id', '')),
                    'title': item.get('title', ''),
                    'link': f"https://www.binance.com/zh-CN/support/announcement/{item.get('id', '')}",
                    'time': datetime.fromtimestamp(item.get('releaseDate', 0) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': item.get('catalogName', '公告')
                }
                announcements.append(ann)
        else:
            logger.warning(f"Binance API返回数据结构异常: code={data.get('code')}")
        
        logger.info(f"Binance: 获取到 {len(announcements)} 条公告")
        return announcements
        
    except Exception as e:
        logger.error(f"获取Binance公告失败: {str(e)}")
        return []

def send_telegram_message(bot_token, chat_id, message, logger):
    """发送Telegram消息"""
    try:
        bot = Bot(token=bot_token)
        bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        logger.info("消息发送成功")
        return True
    except Exception as e:
        logger.error(f"发送Telegram消息失败: {str(e)}")
        return False

def format_announcement_message(exchange, announcement):
    """格式化公告消息"""
    emoji = "🔔"
    exchange_name = "OKX" if exchange == "okx" else "Binance"
    
    message = f"{emoji} <b>{exchange_name} 新公告</b>\n\n"
    message += f"<b>标题：</b>{announcement['title']}\n"
    message += f"<b>类型：</b>{announcement['type']}\n"
    message += f"<b>时间：</b>{announcement['time']}\n"
    message += f"<b>链接：</b><a href='{announcement['link']}'>查看详情</a>"
    
    return message

def check_new_announcements(logger, config):
    """检查新公告并发送通知"""
    sent_data = load_sent_announcements()
    
    telegram_config = config['telegram']
    bot_token = telegram_config['bot_token']
    chat_id = telegram_config['chat_id']
    
    # 获取OKX公告
    logger.info("=" * 50)
    logger.info("开始检查OKX公告...")
    okx_announcements = get_okx_announcements(logger)
    
    new_okx_count = 0
    for ann in okx_announcements:
        if ann['id'] and ann['id'] not in sent_data['okx']:
            # 新公告
            message = format_announcement_message('okx', ann)
            logger.info(f"发现OKX新公告: {ann['title']}")
            
            # 发送消息
            if send_telegram_message(bot_token, chat_id, message, logger):
                sent_data['okx'].append(ann['id'])
                new_okx_count += 1
                logger.info(f"OKX公告已发送: {ann['title']}")
            else:
                logger.warning(f"OKX公告发送失败: {ann['title']}")
            
            # 避免频繁发送，每条消息间隔1秒
            time.sleep(1)
    
    logger.info(f"OKX: 本次发送 {new_okx_count} 条新公告")
    
    # 获取Binance公告
    logger.info("开始检查Binance公告...")
    binance_announcements = get_binance_announcements(logger)
    
    new_binance_count = 0
    for ann in binance_announcements:
        if ann['id'] and ann['id'] not in sent_data['binance']:
            # 新公告
            message = format_announcement_message('binance', ann)
            logger.info(f"发现Binance新公告: {ann['title']}")
            
            # 发送消息
            if send_telegram_message(bot_token, chat_id, message, logger):
                sent_data['binance'].append(ann['id'])
                new_binance_count += 1
                logger.info(f"Binance公告已发送: {ann['title']}")
            else:
                logger.warning(f"Binance公告发送失败: {ann['title']}")
            
            # 避免频繁发送，每条消息间隔1秒
            time.sleep(1)
    
    logger.info(f"Binance: 本次发送 {new_binance_count} 条新公告")
    
    # 保存已发送的公告ID
    save_sent_announcements(sent_data)
    
    total_new = new_okx_count + new_binance_count
    logger.info(f"本次检查完成，共发送 {total_new} 条新公告")
    logger.info("=" * 50)
    
    return total_new

def main():
    """主函数"""
    # 加载配置
    config = load_config()
    logger = setup_logging(config)
    
    check_interval = config['monitor']['check_interval_minutes'] * 60  # 转换为秒
    
    logger.info("=" * 50)
    logger.info("OKX/Binance 公告监控系统启动")
    logger.info(f"检查间隔: {config['monitor']['check_interval_minutes']} 分钟")
    logger.info(f"Telegram Chat ID: {config['telegram']['chat_id']}")
    logger.info("首次运行，只监控新公告（不发送历史公告）")
    logger.info("=" * 50)
    
    # 首次运行时，先加载现有公告ID（不发送）
    logger.info("初始化：加载现有公告ID...")
    sent_data = load_sent_announcements()
    
    # 获取当前公告并记录ID（不发送）
    okx_anns = get_okx_announcements(logger)
    for ann in okx_anns:
        if ann['id'] and ann['id'] not in sent_data['okx']:
            sent_data['okx'].append(ann['id'])
    
    binance_anns = get_binance_announcements(logger)
    for ann in binance_anns:
        if ann['id'] and ann['id'] not in sent_data['binance']:
            sent_data['binance'].append(ann['id'])
    
    save_sent_announcements(sent_data)
    logger.info("初始化完成，开始监控...\n")
    
    # 主循环
    while True:
        try:
            check_new_announcements(logger, config)
        except Exception as e:
            logger.error(f"检查过程出错: {str(e)}", exc_info=True)
        
        # 等待下一次检查
        logger.info(f"下次检查将在 {config['monitor']['check_interval_minutes']} 分钟后...")
        time.sleep(check_interval)

if __name__ == "__main__":
    main()
