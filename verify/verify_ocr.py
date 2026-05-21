"""
验证1：OCR 识别手写数学题
目标：确认 OCR 能否准确提取手写数学公式和中文
红线：公式关键符号（极限、积分、矩阵、根号等）保留率 ≥ 80%

使用方法：
  1. 准备 3 张手写数学题照片放到 test_images/ 目录
  2. pip install "mineru[core]"   # 首次安装（约需下载模型文件）
  3. python verify_ocr.py
"""

import sys
import json
from pathlib import Path

TEST_DIR = Path(__file__).parent / "test_images"


def check_mineru_installed():
    """检查 MinerU 是否可用"""
    try:
        from magic_pdf.data.data_reader_writer import FileBasedDataWriter
        from magic_pdf.data.dataset import ImageDataset
        from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
        from magic_pdf.config.enums import SupportedPdfParseMethod
        return True
    except ImportError:
        return False


def ocr_with_mineru(image_path: Path) -> dict:
    """使用 MinerU 识别图片中的数学内容"""
    from magic_pdf.data.data_reader_writer import FileBasedDataWriter
    from magic_pdf.data.dataset import PymuDocDataset

    output_dir = Path("ocr_output") / image_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    image_writer = FileBasedDataWriter(str(output_dir))
    markdown_writer = FileBasedDataWriter(str(output_dir))

    ds = PymuDocDataset(image_path)
    ds.pipe_ocr_mode(image_writer)
    ds.pipe_mk_cleanup(markdown_writer)
    ds.pipe_mk_format(markdown_writer)

    result_path = output_dir / f"{image_path.stem}_content_list.json"
    if result_path.exists():
        with open(result_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def ocr_with_paddle(image_path: Path) -> str:
    """备选方案：PaddleOCR（更轻量，但数学公式不如 MinerU）"""
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(lang="ch")
    result = ocr.ocr(str(image_path))
    lines = []
    for page in result:
        if page:
            for line in page:
                lines.append(line[1][0])
    return "\n".join(lines)


def evaluate_results(text: str) -> dict:
    """评估识别质量：检查数学符号保留情况"""
    math_symbols = {
        "极限": ["lim", "→", "∞"],
        "积分": ["∫", "dx", "∑"],
        "矩阵": ["[", "]", "det", "|"],
        "分数/根号": ["√", "/", "frac"],
        "三角函数": ["sin", "cos", "tan"],
    }
    found = {}
    for category, symbols in math_symbols.items():
        found[category] = [s for s in symbols if s.lower() in text.lower()]

    coverage = sum(1 for v in found.values() if len(v) > 0) / len(found)
    return {"found_symbols": found, "symbol_coverage": round(coverage * 100)}


def main():
    images = sorted(TEST_DIR.glob("*"))
    images = [p for p in images if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]

    if not images:
        print("=" * 60)
        print("  [!!] 未找到测试图片")
        print(f"  请将 3 张手写数学题照片放到: {TEST_DIR}")
        print("  支持格式: JPG / PNG")
        print("=" * 60)
        sys.exit(1)

    print(f"找到 {len(images)} 张测试图片\n")

    use_mineru = check_mineru_installed()

    if use_mineru:
        print("[OK] 使用 MinerU（数学公式 OCR 方案）\n")
    else:
        print("[!] MinerU 未安装，使用 PaddleOCR 备选方案")
        print("  安装 MinerU: pip install 'mineru[core]'\n")

    all_passed = True
    for img in images:
        print(f"--- {img.name} ---")

        if use_mineru:
            result = ocr_with_mineru(img)
            text = json.dumps(result, ensure_ascii=False)
        else:
            try:
                text = ocr_with_paddle(img)
            except ImportError:
                print("PaddleOCR 也未安装。请执行：")
                print("  pip install 'mineru[core]'    # 推荐")
                print("  pip install paddleocr         # 备选")
                sys.exit(1)

        if not text or len(text) < 10:
            print(f"  [!!] 识别内容过短（{len(text)} 字符），可能识别失败\n")
            all_passed = False
            continue

        eval_result = evaluate_results(text)
        coverage = eval_result["symbol_coverage"]

        print(f"  识别文本前200字: {text[:200]}")
        print(f"  符号覆盖率: {coverage}%")
        for cat, syms in eval_result["found_symbols"].items():
            status = "[OK]" if syms else "[!!]"
            print(f"    {status} {cat}: {syms if syms else '未识别'}")

        if coverage >= 80:
            print(f"  [OK] 通过（覆盖率 {coverage}% ≥ 80%）\n")
        else:
            print(f"  [!!] 未通过（覆盖率 {coverage}% < 80%）\n")
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("  [OK] OCR 验证通过 — 方案可行")
    else:
        print("  [!!] OCR 验证未通过 — 需调整方案")
    print("=" * 60)


if __name__ == "__main__":
    main()
