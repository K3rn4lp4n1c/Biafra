from werkzeug.datastructures import FileStorage
from statistics import mean

import cv2
import numpy as np

FIXED_REGIONS = {
    "seal": (0.03, 0.03, 0.19, 0.16),
    "header_title": (0.18, 0.02, 0.90, 0.12),
    "invoice_label": (0.70, 0.12, 0.93, 0.20),
    "from_to_block": (0.04, 0.16, 0.69, 0.34),
    "table_lines": (0.05, 0.37, 0.92, 0.63),
    "stamp": (0.11, 0.56, 0.48, 0.77),
    "payment_block": (0.04, 0.82, 0.41, 0.96),
    "ship_note": (0.66, 0.80, 0.93, 0.96),
}

EDIT_REGIONS = {
    "invoice_no_val": (0.22, 0.285, 0.44, 0.325),
    "date_val": (0.22, 0.315, 0.34, 0.355),
    "order_code_val": (0.22, 0.345, 0.42, 0.39),
    "item_desc_val": (0.05, 0.42, 0.42, 0.50),
    "item_qty_val": (0.47, 0.42, 0.58, 0.50),
    "item_price_val": (0.60, 0.42, 0.77, 0.50),
    "item_total_val": (0.78, 0.42, 0.93, 0.50),
    "subtotal_val": (0.79, 0.54, 0.93, 0.585),
    "tax_val": (0.79, 0.585, 0.93, 0.635),
    "total_due_val": (0.79, 0.63, 0.93, 0.69),
}

CRITICAL_DELTA_THRESHOLDS = {
    "invoice_no_val": 0.01,
    "date_val": 0.01,
    "order_code_val": 0.05,
    "item_desc_val": 0.12,
    "item_qty_val": 0.08,
    "item_price_val": 0.08,
    "item_total_val": 0.10,
    "subtotal_val": 0.08,
    "tax_val": 0.08,
    "total_due_val": 0.08,
}

LAYOUT_THRESHOLD = 0.54
EDIT_THRESHOLD = 0.12

def read_image_from_upload(file_storage: FileStorage) -> np.ndarray | None:
    data = np.frombuffer(file_storage.read(), np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def crop_region(image: np.ndarray, region: tuple[float, float, float, float]) -> np.ndarray:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = region

    left = max(0, min(width, int(x1 * width)))
    top = max(0, min(height, int(y1 * height)))
    right = max(left + 1, min(width, int(x2 * width)))
    bottom = max(top + 1, min(height, int(y2 * height)))

    return image[top:bottom, left:right]

def normalize_gray(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    normalized = np.zeros_like(gray)
    return cv2.normalize(gray, normalized, 0, 255, cv2.NORM_MINMAX)

def text_mask(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask

def layout_similarity(a: np.ndarray, b: np.ndarray) -> float:
    ga = normalize_gray(a)
    gb = normalize_gray(b)
    gb = cv2.resize(gb, (ga.shape[1], ga.shape[0]), interpolation=cv2.INTER_AREA)

    edge_a = cv2.Canny(ga, 60, 160)
    edge_b = cv2.Canny(gb, 60, 160)

    intersection = np.logical_and(edge_a > 0, edge_b > 0).sum()
    union = np.logical_or(edge_a > 0, edge_b > 0).sum()
    edge_iou = intersection / union if union else 1.0

    mae = 1.0 - (np.mean(cv2.absdiff(ga, gb)) / 255.0)
    score = 0.35 * mae + 0.65 * edge_iou
    return float(max(0.0, min(1.0, score)))

def text_similarity(a: np.ndarray, b: np.ndarray) -> float:
    ta = text_mask(a)
    tb = text_mask(b)
    tb = cv2.resize(tb, (ta.shape[1], ta.shape[0]), interpolation=cv2.INTER_NEAREST)

    a_on = ta > 0
    b_on = tb > 0

    intersection = np.logical_and(a_on, b_on).sum()
    union = np.logical_or(a_on, b_on).sum()
    sum_a = a_on.sum()
    sum_b = b_on.sum()

    iou = intersection / union if union else 1.0
    dice = (2 * intersection) / (sum_a + sum_b) if (sum_a + sum_b) else 1.0
    score = 0.5 * iou + 0.5 * dice
    return float(max(0.0, min(1.0, score)))

def align_to_target(uploaded: np.ndarray, target: np.ndarray) -> np.ndarray:
    target_h, target_w = target.shape[:2]
    uploaded_resized = cv2.resize(uploaded, (target_w, target_h), interpolation=cv2.INTER_AREA)

    target_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
    upload_gray = cv2.cvtColor(uploaded_resized, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(nfeatures=4000)
    kp1, des1 = orb.detectAndCompute(upload_gray, None)
    kp2, des2 = orb.detectAndCompute(target_gray, None)

    if des1 is None or des2 is None or len(kp1) < 12 or len(kp2) < 12:
        return uploaded_resized

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(des1, des2)
    matches = sorted(matches, key=lambda m: m.distance)

    if len(matches) < 18:
        return uploaded_resized

    good_matches = matches[:150]
    src_pts = np.array([kp1[m.queryIdx].pt for m in good_matches], dtype=np.float32).reshape(-1, 1, 2)
    dst_pts = np.array([kp2[m.trainIdx].pt for m in good_matches], dtype=np.float32).reshape(-1, 1, 2)

    homography, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if homography is None:
        return uploaded_resized

    aligned = cv2.warpPerspective(
        uploaded_resized,
        homography,
        (target_w, target_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    return aligned

def build_feedback(layout_score: float, edit_score: float, region_scores: dict) -> list[str]:
    feedback: list[str] = []

    if layout_score < LAYOUT_THRESHOLD:
        feedback.append(
            "The overall invoice layout does not match the exchange template closely enough."
        )
    else:
        feedback.append(
            "The overall document structure is close enough to the expected marketplace template."
        )

    if edit_score < EDIT_THRESHOLD:
        feedback.append(
            "The edited text regions still look closer to the damaged invoice than the clean target."
        )
    else:
        feedback.append(
            "The edited fields are trending toward the clean target image."
        )

    low_regions = [
        name
        for name, values in region_scores.items()
        if values["delta"] < CRITICAL_DELTA_THRESHOLDS.get(name, 0.0)
    ]

    if low_regions:
        feedback.append(
            "The weakest edited regions are: " + ", ".join(low_regions[:4]) + "."
        )

    if region_scores.get("item_desc_val", {}).get("delta", -1) < CRITICAL_DELTA_THRESHOLDS["item_desc_val"]:
        feedback.append(
            "The item description row still needs more work."
        )

    if region_scores.get("item_price_val", {}).get("delta", -1) < CRITICAL_DELTA_THRESHOLDS["item_price_val"]:
        feedback.append(
            "The unit price area is not close enough to the target yet."
        )

    if region_scores.get("total_due_val", {}).get("delta", -1) < CRITICAL_DELTA_THRESHOLDS["total_due_val"]:
        feedback.append(
            "The total due field still does not resemble the clean target closely enough."
        )

    return feedback

def evaluate_invoice(uploaded: np.ndarray, TARGET_IMAGE: np.ndarray, WORN_IMAGE: np.ndarray, FLAG: str) -> dict:
    aligned = align_to_target(uploaded, TARGET_IMAGE)

    fixed_scores = {
        name: layout_similarity(crop_region(aligned, region), crop_region(TARGET_IMAGE, region))
        for name, region in FIXED_REGIONS.items()
    }

    region_scores: dict[str, dict[str, float]] = {}
    for name, region in EDIT_REGIONS.items():
        upload_crop = crop_region(aligned, region)
        target_crop = crop_region(TARGET_IMAGE, region)
        worn_crop = crop_region(WORN_IMAGE, region)

        target_similarity = text_similarity(upload_crop, target_crop)
        worn_similarity = text_similarity(upload_crop, worn_crop)
        delta = target_similarity - worn_similarity

        region_scores[name] = {
            "target_similarity": round(target_similarity, 6),
            "worn_similarity": round(worn_similarity, 6),
            "delta": round(delta, 6),
        }

    layout_score = float(mean(fixed_scores.values()))
    edit_score = float(mean(values["delta"] for values in region_scores.values()))

    critical_checks = all(
        region_scores[name]["delta"] >= threshold
        for name, threshold in CRITICAL_DELTA_THRESHOLDS.items()
    )

    passed = (
        layout_score >= LAYOUT_THRESHOLD
        and edit_score >= EDIT_THRESHOLD
        and critical_checks
    )

    overall_score = round((layout_score * 0.4 + ((edit_score + 1.0) / 2.0) * 0.6), 6)
    feedback = build_feedback(layout_score, edit_score, region_scores)

    if passed: message = "Verification successful. Receipt accepted."
    else: message = "Verification failed. Keep refining the invoice."

    return {
        "passed": passed,
        "message": message,
        "layout_score": round(layout_score, 6),
        "edit_score": round(edit_score, 6),
        "overall_score": overall_score,
        "fixed_scores": {k: round(v, 6) for k, v in fixed_scores.items()},
        "region_scores": region_scores,
        "feedback": feedback,
        "flag": FLAG if passed else None,
    }