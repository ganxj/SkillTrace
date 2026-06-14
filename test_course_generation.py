#!/usr/bin/env python3
"""测试课程生成流程：上传PDF文件并监控生成状态"""
import time
import requests
from pathlib import Path

API_BASE = "http://localhost:8001/api/v1"
PDF_PATH = r"D:\360极速浏览器X下载\《指数基金   投资指南》.pdf"

def upload_file():
    """上传PDF文件，创建导入任务"""
    print(f"📤 正在上传文件: {PDF_PATH}")

    if not Path(PDF_PATH).exists():
        print(f"❌ 文件不存在: {PDF_PATH}")
        return None

    with open(PDF_PATH, "rb") as f:
        files = {"file": (Path(PDF_PATH).name, f, "application/pdf")}
        response = requests.post(f"{API_BASE}/imports", files=files)

    if response.status_code != 200:
        print(f"❌ 上传失败: {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    import_id = data["import_record"]["id"]
    print(f"✅ 上传成功，导入ID: {import_id}")
    print(f"   初始状态: {data['import_record']['status']}")
    print(f"   当前步骤: {data['import_record']['current_step']}")
    return import_id

def check_status(import_id):
    """查询导入任务状态"""
    response = requests.get(f"{API_BASE}/imports/{import_id}")
    if response.status_code != 200:
        print(f"❌ 查询失败: {response.status_code}")
        return None
    return response.json()

def monitor_progress(import_id, timeout=600):
    """监控生成进度，直到完成或失败"""
    print(f"\n📊 开始监控生成进度 (超时: {timeout}秒)")
    print("-" * 60)

    start_time = time.time()
    last_status = None
    last_step = None

    while time.time() - start_time < timeout:
        status_data = check_status(import_id)
        if not status_data:
            time.sleep(2)
            continue

        status = status_data["status"]
        current_step = status_data.get("current_step", "")
        total = status_data.get("total_segments", 0)
        processed = status_data.get("processed_segments", 0)

        # 只在状态或步骤变化时打印
        if status != last_status or current_step != last_step:
            timestamp = time.strftime("%H:%M:%S")
            progress_info = f" [{processed}/{total}]" if total > 0 else ""
            print(f"[{timestamp}] 状态: {status:12s} | {current_step}{progress_info}")
            last_status = status
            last_step = current_step

        # 检查终止状态
        if status == "published":
            print("-" * 60)
            print(f"✅ 课程生成成功！")
            print(f"   课程名称: {status_data.get('domain', {}).get('name', 'N/A')}")
            print(f"   课程slug: {status_data.get('domain', {}).get('slug', 'N/A')}")
            print(f"   总耗时: {int(time.time() - start_time)}秒")
            return True

        elif status == "failed":
            print("-" * 60)
            print(f"❌ 课程生成失败！")
            print(f"   错误信息: {status_data.get('error', 'Unknown error')}")
            print(f"   当前步骤: {current_step}")
            return False

        time.sleep(2)

    print("-" * 60)
    print(f"⏱️  监控超时 ({timeout}秒)")
    return False

def main():
    print("=" * 60)
    print("🚀 课程生成测试")
    print("=" * 60)

    # 1. 上传文件
    import_id = upload_file()
    if not import_id:
        return

    # 2. 监控进度
    success = monitor_progress(import_id, timeout=600)

    # 3. 最终状态
    print("\n" + "=" * 60)
    if success:
        final_status = check_status(import_id)
        if final_status and final_status.get("domain"):
            domain = final_status["domain"]
            print(f"📚 课程详情:")
            print(f"   ID: {domain['id']}")
            print(f"   名称: {domain['name']}")
            print(f"   描述: {domain.get('description', '')[:100]}...")
            print(f"   版本: {domain['version']}")
    else:
        print("❌ 测试失败")
    print("=" * 60)

if __name__ == "__main__":
    main()
