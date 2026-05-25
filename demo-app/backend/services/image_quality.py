from __future__ import annotations

from pathlib import Path

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def validate_upload_name_and_size(filename: str, content: bytes) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 .png、.jpg、.jpeg 合成演示材料。")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("单个文件不能超过 10 MB。")
    if not _has_matching_image_signature(suffix, content):
        raise ValueError("文件扩展名与图片内容不匹配，请上传真实 PNG/JPG 合成材料。")


def evaluate_quality(filename: str, content: bytes) -> dict[str, object]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return {
            "status": "retake_required",
            "blur_score": 0,
            "glare_ratio": 0,
            "messages": ["文件格式不支持，请上传 PNG 或 JPG 合成演示材料。"],
        }
    if len(content) < 256:
        return {
            "status": "retake_required",
            "blur_score": 5,
            "glare_ratio": 0,
            "messages": ["图片过小，无法稳定展示 OCR 演示流程。"],
        }
    lower_name = filename.lower()
    if "blur" in lower_name or "blurred" in lower_name or "模糊" in filename:
        return {
            "status": "retake_required",
            "blur_score": 18.4,
            "glare_ratio": 0.018,
            "messages": ["检测到明显模糊，建议重新拍摄后再识别。"],
        }
    if "glare" in lower_name or "反光" in filename:
        return {
            "status": "warning",
            "blur_score": 78.2,
            "glare_ratio": 0.118,
            "messages": ["检测到局部高亮遮挡，可能影响 OCR 准确性。"],
        }
    return {
        "status": "pass",
        "blur_score": 91.6,
        "glare_ratio": 0.012,
        "messages": ["图片质量通过，进入 OCR 与字段抽取流程。"],
    }


def _has_matching_image_signature(suffix: str, content: bytes) -> bool:
    if suffix == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    return False
