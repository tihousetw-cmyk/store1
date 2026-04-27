#!/usr/bin/env python3
"""
LINE Daily Message Bot
每天在指定時間透過 LINE Messaging API 推送訊息。

使用方式:
  1. 複製 .env.example 為 .env 並填入你的 TOKEN 與 USER_ID
  2. 執行: python line_daily.py
"""

import os
import sys
import logging
import requests
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

from messages import get_today_message

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("line_daily.log"),
    ],
)
log = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def send_line_message(text: str) -> bool:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.getenv("LINE_USER_ID")

    if not token or not user_id:
        log.error("缺少環境變數：請確認 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_USER_ID 已設定。")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }

    try:
        resp = requests.post(LINE_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        log.info("訊息發送成功！")
        return True
    except requests.HTTPError as e:
        log.error("LINE API 錯誤：%s - %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as e:
        log.error("網路錯誤：%s", e)
        return False


def daily_job():
    message = get_today_message()
    log.info("準備發送今日訊息：%s", message)
    send_line_message(message)


def main():
    send_time = os.getenv("SEND_TIME", "08:00")
    log.info("LINE 每日訊息排程啟動，發送時間：%s", send_time)

    # 立即測試發送（可選，設 TEST_ON_START=true 啟用）
    if os.getenv("TEST_ON_START", "false").lower() == "true":
        log.info("TEST_ON_START 已啟用，立即發送測試訊息...")
        daily_job()

    schedule.every().day.at(send_time).do(daily_job)
    log.info("排程已設定，等待 %s 發送...", send_time)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
