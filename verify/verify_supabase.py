"""
验证3：Supabase 连接 + 额度估算
目标：确认数据库连接、建表、存储全部正常，估算免费额度够用多久
红线：个人使用一年内不超免费额度

使用方法：
  1. 在 Supabase 新建项目，获取 Project URL 和 API Key
  2. 设置环境变量:
     export SUPABASE_URL="https://xxx.supabase.co"
     export SUPABASE_KEY="eyJhb..."
  3. pip install supabase
  4. python verify_supabase.py
"""

import os
import sys
import json
import math
from datetime import datetime


def create_supabase_client():
    """初始化 Supabase 客户端"""
    try:
        from supabase import create_client, Client
    except ImportError:
        print("请安装 supabase: pip install supabase")
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("=" * 60)
        print("  ❌ 未设置 Supabase 凭据")
        print("  export SUPABASE_URL='https://xxx.supabase.co'")
        print("  export SUPABASE_KEY='eyJhb...'")
        print("=" * 60)
        sys.exit(1)
    return create_client(url, key)


def test_connection(client) -> bool:
    """测试数据库连接"""
    try:
        result = client.table("_prisma_migrations").select("*", count="exact").limit(1).execute()
        print("  ✓ 数据库连接成功")
        return True
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False


def create_test_tables(client) -> bool:
    """在 Supabase SQL Editor 中手动执行建表，这里只做存在性检查"""
    tables_needed = ["uploads", "ocr_results", "analysis_records", "knowledge_graph"]
    all_ok = True
    for table in tables_needed:
        try:
            result = client.table(table).select("*", count="exact").limit(1).execute()
            print(f"  ✓ 表 {table} 可访问")
        except Exception:
            print(f"  ✗ 表 {table} 不存在 — 请在 Supabase SQL Editor 中执行建表 SQL")
            all_ok = False
    return all_ok


def test_storage(client) -> bool:
    """测试文件存储"""
    try:
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        if "math-images" not in bucket_names:
            print("  ! 未找到 math-images 存储桶，尝试创建...")
            try:
                client.storage.create_bucket("math-images", {"public": False})
                print("  ✓ 存储桶 math-images 创建成功")
            except Exception as e:
                print(f"  ✗ 创建存储桶失败: {e}")
                return False
        else:
            print("  ✓ 存储桶 math-images 已存在")
        return True
    except Exception as e:
        print(f"  ✗ 存储测试失败: {e}")
        return False


def estimate_quota(client) -> dict:
    """估算免费额度够用多久"""
    # Supabase 免费计划限制
    FREE_LIMITS = {
        "database_size_mb": 500,
        "storage_size_mb": 1024,
        "bandwidth_gb": 5,
        "api_requests": 50000,
        "auth_users": 50000,
    }

    # 估算单次上传的存储和请求
    PER_UPLOAD = {
        "image_size_mb": 2.0,       # 手机拍照约 2MB/张
        "db_record_size_kb": 5.0,   # 一条完整记录（upload+ocr+analysis）约 5KB
        "api_calls": 3,             # 上传→存图→分析结果，约 3 次 API 调用
    }

    # 假设使用量：每天上传 10 张，使用 365 天
    daily_uploads = 10
    annual_uploads = daily_uploads * 365  # 3650

    usage = {
        "database_mb": annual_uploads * PER_UPLOAD["db_record_size_kb"] / 1024,
        "storage_mb": annual_uploads * PER_UPLOAD["image_size_mb"],
        "api_calls": annual_uploads * PER_UPLOAD["api_calls"],
        "bandwidth_gb": (annual_uploads * PER_UPLOAD["image_size_mb"]) / 1024 * 2,
    }

    return {
        "limits": FREE_LIMITS,
        "per_upload": PER_UPLOAD,
        "estimated_annual": usage,
        "within_limits": all(
            usage[k] < FREE_LIMITS[k]
            for k in ["database_size_mb", "storage_size_mb", "bandwidth_gb", "api_requests"]
        ),
    }


def print_quota_report(estimate: dict):
    """打印额度报告"""
    print("\n" + "=" * 60)
    print("  免费额度估算（假设每天上传 10 张，使用 1 年）")
    print("=" * 60)

    limits = estimate["limits"]
    usage = estimate["estimated_annual"]

    checks = [
        ("数据库", usage["database_mb"], limits["database_size_mb"], "MB"),
        ("文件存储", usage["storage_mb"], limits["storage_size_mb"], "MB"),
        ("带宽", usage["bandwidth_gb"], limits["bandwidth_gb"], "GB"),
        ("API 请求", usage["api_calls"], limits["api_requests"], "次"),
        ("认证用户", 1, limits["auth_users"], "人"),
    ]

    for name, used, limit, unit in checks:
        pct = used / limit * 100 if limit > 0 else 0
        bar = "█" * math.ceil(pct / 10) + "░" * (10 - math.ceil(pct / 10))
        status = "✓" if pct <= 80 else "⚠ 超标"
        print(f"  {name:8s} {bar}  {used:.1f}/{limit}{unit} ({pct:.0f}%) {status}")

    if estimate["within_limits"]:
        print("\n  ✅ 免费额度够用，无需升级")
    else:
        print("\n  ❌ 部分额度超限，需要优化或升级")
    print("=" * 60)


def main():
    print("Supabase 可行性验证\n")

    client = create_supabase_client()
    print(f"URL: {os.environ['SUPABASE_URL']}\n")

    # 1. 连接测试
    print("[1/4] 数据库连接")
    connected = test_connection(client)
    if not connected:
        sys.exit(1)
    print()

    # 2. 表存在性检查
    print("[2/4] 数据表检查")
    tables_ok = create_test_tables(client)
    if not tables_ok:
        print("\n  → 请在 Supabase SQL Editor 中执行建表 SQL（见设计文档）")
    print()

    # 3. 存储测试
    print("[3/4] 文件存储")
    storage_ok = test_storage(client)
    print()

    # 4. 额度估算
    print("[4/4] 额度估算")
    estimate = estimate_quota(client)
    print_quota_report(estimate)

    # 总结
    all_ok = connected and tables_ok and storage_ok and estimate["within_limits"]
    print(f"\n  总结: {'✅ 全部通过' if all_ok else '❌ 存在问题'}")

    if not tables_ok:
        print("\n  下一步：执行建表 SQL")
        print("  → 打开 Supabase Dashboard → SQL Editor")
        print("  → 粘贴设计文档中 5 张表的 CREATE TABLE 语句")


if __name__ == "__main__":
    main()
