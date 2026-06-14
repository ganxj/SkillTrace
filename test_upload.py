#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import time
import json

# 配置
API_BASE = "http://localhost:8001/api/v1"
PDF_PATH = r"D:\360极速浏览器X下载\《指数基金   投资指南》.pdf"
DOMAIN_ID = None  # 设置为 None 表示创建新课程

def upload_and_monitor():
    """上传 PDF 并监控生成进度"""

    print(f"正在上传文件: {PDF_PATH}")

    try:
        # 上传文件
        with open(PDF_PATH, 'rb') as f:
            files = {'file': f}
            data = {'domain_id': DOMAIN_ID} if DOMAIN_ID else {}
            response = requests.post(f"{API_BASE}/imports", files=files, data=data)

        print(f"上传响应状态码: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")

        if response.status_code != 200:
            print(f"上传失败: {response.text}")
            return

        result = response.json()
        import_id = result['import_record']['id']
        print(f"\n上传成功！Import ID: {import_id}")
        print(f"开始监控生成进度...\n")

        # 监控进度
        while True:
            time.sleep(3)

            # 获取最新状态
            imports_response = requests.get(f"{API_BASE}/imports")
            imports = imports_response.json()

            # 找到当前的 import
            current = None
            for imp in imports:
                if imp['id'] == import_id:
                    current = imp
                    break

            if not current:
                print("未找到 import 记录")
                break

            status = current['status']
            step = current.get('current_step', '')
            total = current.get('total_segments', 0)
            processed = current.get('processed_segments', 0)

            progress = f"{processed}/{total}" if total > 0 else "解析中"
            print(f"[{status}] {step} - {progress}")

            if status in ['published', 'failed']:
                print(f"\n生成完成！状态: {status}")
                if status == 'failed':
                    print(f"错误信息: {current.get('error', '未知错误')}")
                break

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    upload_and_monitor()
