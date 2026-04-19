from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


COLOR_MASKS_HSV: dict[str, list[tuple[tuple[int, int, int], tuple[int, int, int]]]] = {
    "BLACK": [((0, 0, 0), (180, 255, 60))],
    "WHITE": [((0, 0, 185), (180, 35, 255))],
    "GRAY": [((0, 0, 70), (180, 55, 205))],
    "BROWN": [((5, 55, 40), (20, 255, 190))],
    "RED": [((0, 70, 70), (8, 255, 255)), ((170, 70, 70), (180, 255, 255))],
    "ORANGE": [((8, 75, 100), (22, 255, 255))],
    "YELLOW": [((22, 55, 110), (35, 255, 255))],
    "GREEN": [((35, 35, 55), (90, 255, 255))],
    "BLUE": [((85, 35, 45), (140, 255, 255))],
    "PINK": [((135, 35, 90), (170, 255, 255))],
}


@dataclass
class AnalysisSettings:
    white_l_min: int = 190
    white_sat_max: int = 45
    distance_thresholds: tuple[float, ...] = (18.0, 22.0, 26.0, 30.0)
    min_area_ratio: float = 0.01
    max_area_ratio: float = 0.60
    min_fill_ratio: float = 0.45
    min_solidity: float = 0.70
    resize_max_side: int = 1200


@dataclass
class CandidateFinding:
    image_name: str
    candidate_index: int
    x: int
    y: int
    w: int
    h: int
    area: float
    aspect_ratio: float
    circularity: float
    solidity: float
    fill_ratio: float
    dominant_color: str
    second_color: str
    dominant_ratio: float
    second_ratio: float
    is_bicolor: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_name": self.image_name,
            "candidate_index": self.candidate_index,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "area": round(self.area, 2),
            "aspect_ratio": round(self.aspect_ratio, 4),
            "circularity": round(self.circularity, 4),
            "solidity": round(self.solidity, 4),
            "fill_ratio": round(self.fill_ratio, 4),
            "dominant_color": self.dominant_color,
            "second_color": self.second_color,
            "dominant_ratio": round(self.dominant_ratio, 4),
            "second_ratio": round(self.second_ratio, 4),
            "is_bicolor": self.is_bicolor,
        }


def _resize_for_analysis(image_bgr: np.ndarray, max_side: int) -> np.ndarray:
    scale = min(1.0, max_side / max(image_bgr.shape[:2]))
    if scale == 1.0:
        return image_bgr.copy()
    size = (max(1, int(image_bgr.shape[1] * scale)), max(1, int(image_bgr.shape[0] * scale)))
    return cv2.resize(image_bgr, size, interpolation=cv2.INTER_AREA)


def _classify_colors(image_hsv: np.ndarray, object_mask: np.ndarray) -> tuple[list[str], list[float], dict[str, int]]:
    object_mask = (object_mask > 0).astype(np.uint8) * 255
    total_pixels = max(int(np.count_nonzero(object_mask)), 1)
    min_region_area = max(80, int(total_pixels * 0.012))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    color_counts: dict[str, int] = {}

    for color_name, hsv_ranges in COLOR_MASKS_HSV.items():
        color_mask = np.zeros(object_mask.shape, dtype=np.uint8)
        for lower, upper in hsv_ranges:
            color_mask = cv2.bitwise_or(
                color_mask,
                cv2.inRange(image_hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8)),
            )
        color_mask = cv2.bitwise_and(color_mask, object_mask)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel_open, iterations=1)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel_close, iterations=1)
        contours, _ = cv2.findContours(color_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        kept_area = 0
        for contour in contours:
            area = int(cv2.contourArea(contour))
            if area >= min_region_area:
                kept_area += area
        if kept_area > 0:
            color_counts[color_name] = kept_area

    sorted_pairs = sorted(color_counts.items(), key=lambda item: item[1], reverse=True)
    colors = [pair[0] for pair in sorted_pairs[:3]]
    props = [float(pair[1] / total_pixels) for pair in sorted_pairs[:3]]
    if not colors:
        colors = ["UNKNOWN"]
        props = [0.0]
    return colors, props, color_counts


def _find_print_region(image_bgr: np.ndarray, settings: AnalysisSettings) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    l_channel = lab[:, :, 0].astype(np.float32)
    sat = hsv[:, :, 1].astype(np.float32)
    white_mask = ((l_channel >= settings.white_l_min) & (sat <= settings.white_sat_max)).astype(np.uint8) * 255
    content_mask = cv2.bitwise_not(white_mask)
    content_mask = cv2.morphologyEx(
        content_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)),
        iterations=2,
    )
    content_mask = cv2.morphologyEx(
        content_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)),
        iterations=1,
    )
    contours, _ = cv2.findContours(content_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image_bgr.copy(), (0, 0, image_bgr.shape[1], image_bgr.shape[0])

    biggest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    pad = max(8, min(image_bgr.shape[:2]) // 50)
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(image_bgr.shape[1], x + w + pad)
    y2 = min(image_bgr.shape[0], y + h + pad)
    return image_bgr[y1:y2, x1:x2].copy(), (x1, y1, x2 - x1, y2 - y1)


def analyze_image_array(image_bgr: np.ndarray, image_name: str, settings: AnalysisSettings | None = None) -> dict[str, Any]:
    settings = settings or AnalysisSettings()
    image_bgr = _resize_for_analysis(image_bgr, settings.resize_max_side)
    work_bgr, print_bbox = _find_print_region(image_bgr, settings)
    work_lab = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2LAB)
    work_hsv = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2HSV)
    work_gray = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2GRAY)

    border = max(10, min(work_bgr.shape[:2]) // 18)
    border_lab = np.concatenate(
        [
            work_lab[:border, :, :].reshape(-1, 3),
            work_lab[-border:, :, :].reshape(-1, 3),
            work_lab[:, :border, :].reshape(-1, 3),
            work_lab[:, -border:, :].reshape(-1, 3),
        ],
        axis=0,
    ).astype(np.float32)

    bg_lab = np.median(border_lab, axis=0)
    bg_distance = np.linalg.norm(work_lab.astype(np.float32) - bg_lab.reshape(1, 1, 3), axis=2)

    mask_candidates = np.zeros(work_gray.shape, dtype=np.uint8)
    for threshold in settings.distance_thresholds:
        distance_mask = (bg_distance > threshold).astype(np.uint8) * 255
        distance_mask = cv2.morphologyEx(
            distance_mask,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
            iterations=1,
        )
        distance_mask = cv2.morphologyEx(
            distance_mask,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)),
            iterations=2,
        )
        mask_candidates = cv2.max(mask_candidates, distance_mask)

    contours, _ = cv2.findContours(mask_candidates, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    work_area = float(work_bgr.shape[0] * work_bgr.shape[1])
    findings: list[CandidateFinding] = []
    debug_image = image_bgr.copy()

    for index, contour in enumerate(contours, start=1):
        area = float(cv2.contourArea(contour))
        if area < work_area * settings.min_area_ratio or area > work_area * settings.max_area_ratio:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 40 or h < 40:
            continue
        fill_ratio = area / max(float(w * h), 1.0)
        if fill_ratio < settings.min_fill_ratio:
            continue
        perimeter = max(cv2.arcLength(contour, True), 1.0)
        circularity = float(4.0 * np.pi * area / (perimeter * perimeter))
        hull = cv2.convexHull(contour)
        hull_area = max(float(cv2.contourArea(hull)), 1.0)
        solidity = float(area / hull_area)
        if solidity < settings.min_solidity:
            continue

        candidate_mask = np.zeros(work_gray.shape, dtype=np.uint8)
        cv2.drawContours(candidate_mask, [contour], -1, 255, -1)
        colors, props, _ = _classify_colors(work_hsv, candidate_mask)
        dominant_color = colors[0]
        second_color = colors[1] if len(colors) > 1 else ""
        dominant_ratio = props[0]
        second_ratio = props[1] if len(props) > 1 else 0.0
        is_bicolor = (
            len(colors) > 1
            and dominant_color != second_color
            and dominant_ratio >= 0.12
            and second_ratio >= 0.12
        )

        global_x = x + print_bbox[0]
        global_y = y + print_bbox[1]
        findings.append(
            CandidateFinding(
                image_name=image_name,
                candidate_index=index,
                x=global_x,
                y=global_y,
                w=w,
                h=h,
                area=area,
                aspect_ratio=float(w / max(h, 1)),
                circularity=circularity,
                solidity=solidity,
                fill_ratio=fill_ratio,
                dominant_color=dominant_color,
                second_color=second_color,
                dominant_ratio=dominant_ratio,
                second_ratio=second_ratio,
                is_bicolor=is_bicolor,
            )
        )

        color = (0, 200, 0) if not is_bicolor else (0, 200, 255)
        cv2.rectangle(debug_image, (global_x, global_y), (global_x + w, global_y + h), color, 2)
        label = dominant_color if not is_bicolor else f"{dominant_color}/{second_color}"
        cv2.putText(
            debug_image,
            f"{index}: {label}",
            (global_x, max(20, global_y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return {
        "image_name": image_name,
        "print_bbox": {
            "x": int(print_bbox[0]),
            "y": int(print_bbox[1]),
            "w": int(print_bbox[2]),
            "h": int(print_bbox[3]),
        },
        "candidate_count": len(findings),
        "candidates": [item.to_dict() for item in findings],
        "debug_image_bgr": debug_image,
        "mask_candidates": mask_candidates,
        "settings": asdict(settings),
        "background_lab": [float(x) for x in bg_lab],
    }


def analyze_image(image_path: str | Path, settings: AnalysisSettings | None = None) -> dict[str, Any]:
    image_path = Path(image_path)
    image_bgr = cv2.imread(str(image_path))
    if image_bgr is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")
    result = analyze_image_array(image_bgr, image_path.name, settings=settings)
    result["image_path"] = str(image_path)
    return result


def _candidate_similarity(candidate: dict[str, Any], reference: dict[str, Any]) -> float:
    score = 0.0
    score += 1.0 - min(abs(candidate["aspect_ratio"] - reference["aspect_ratio"]) / max(reference["aspect_ratio"], 0.2), 1.0)
    score += 1.0 - min(abs(candidate["circularity"] - reference["circularity"]) / max(reference["circularity"], 0.2), 1.0)
    score += 1.0 - min(abs(candidate["solidity"] - reference["solidity"]) / max(reference["solidity"], 0.2), 1.0)
    if candidate["dominant_color"] == reference["dominant_color"]:
        score += 1.0
    elif candidate["dominant_color"] in {reference["dominant_color"], reference.get("second_color", "")}:
        score += 0.6
    if candidate["is_bicolor"] == reference["is_bicolor"]:
        score += 0.4
    return score / 4.4


def calibrate_frame_against_reference(
    reference_path: str | Path,
    frame_bgr: np.ndarray,
    frame_name: str = "camera_frame",
) -> dict[str, Any]:
    reference_result = analyze_image(reference_path)
    if not reference_result["candidates"]:
        raise ValueError("La referencia no produjo candidatos. Ajusta primero la foto de referencia.")

    reference_candidate = reference_result["candidates"][0]
    settings_grid = [
        AnalysisSettings(white_l_min=175, white_sat_max=60, distance_thresholds=(14.0, 18.0, 22.0, 26.0), min_fill_ratio=0.40, min_solidity=0.66),
        AnalysisSettings(white_l_min=185, white_sat_max=50, distance_thresholds=(16.0, 20.0, 24.0, 28.0), min_fill_ratio=0.42, min_solidity=0.68),
        AnalysisSettings(white_l_min=190, white_sat_max=45, distance_thresholds=(18.0, 22.0, 26.0, 30.0), min_fill_ratio=0.45, min_solidity=0.70),
        AnalysisSettings(white_l_min=200, white_sat_max=40, distance_thresholds=(20.0, 24.0, 28.0, 32.0), min_fill_ratio=0.48, min_solidity=0.72),
    ]

    trials: list[dict[str, Any]] = []
    for index, settings in enumerate(settings_grid, start=1):
        result = analyze_image_array(frame_bgr, frame_name, settings=settings)
        best_similarity = 0.0
        best_candidate = None
        for candidate in result["candidates"]:
            similarity = _candidate_similarity(candidate, reference_candidate)
            if similarity > best_similarity:
                best_similarity = similarity
                best_candidate = candidate

        detection_bonus = min(result["candidate_count"], 3) / 3.0
        final_score = 0.75 * best_similarity + 0.25 * detection_bonus
        trials.append(
            {
                "trial_index": index,
                "settings": asdict(settings),
                "candidate_count": result["candidate_count"],
                "best_similarity": round(best_similarity, 4),
                "final_score": round(final_score, 4),
                "best_candidate": best_candidate,
                "analysis": result,
            }
        )

    trials.sort(key=lambda item: item["final_score"], reverse=True)
    best_trial = trials[0]
    return {
        "reference": reference_result,
        "best_trial": best_trial,
        "trials": trials,
    }


def write_findings_report(results: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    json_rows: list[dict[str, Any]] = []
    for result in results:
        json_rows.append(
            {
                "image_name": result["image_name"],
                "image_path": result.get("image_path", ""),
                "print_bbox": result["print_bbox"],
                "candidate_count": result["candidate_count"],
                "candidates": result["candidates"],
                "settings": result.get("settings", {}),
                "background_lab": result.get("background_lab", []),
            }
        )
        if result["candidates"]:
            rows.extend(result["candidates"])
        else:
            rows.append(
                {
                    "image_name": result["image_name"],
                    "candidate_index": 0,
                    "x": "",
                    "y": "",
                    "w": "",
                    "h": "",
                    "area": 0.0,
                    "aspect_ratio": 0.0,
                    "circularity": 0.0,
                    "solidity": 0.0,
                    "fill_ratio": 0.0,
                    "dominant_color": "NONE",
                    "second_color": "",
                    "dominant_ratio": 0.0,
                    "second_ratio": 0.0,
                    "is_bicolor": False,
                }
            )

        debug_overlay_path = debug_dir / f"{Path(result['image_name']).stem}_overlay.png"
        mask_path = debug_dir / f"{Path(result['image_name']).stem}_mask.png"
        debug_image = result.get("debug_image_bgr")
        if debug_image is None:
            debug_image = np.zeros((240, 320, 3), dtype=np.uint8)
        mask_image = result.get("mask_candidates")
        if mask_image is None:
            mask_image = np.zeros(debug_image.shape[:2], dtype=np.uint8)
        cv2.imwrite(str(debug_overlay_path), debug_image)
        cv2.imwrite(str(mask_path), mask_image)

    csv_path = output_dir / "hallazgos.csv"
    json_path = output_dir / "hallazgos.json"
    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8")
    json_path.write_text(json.dumps(json_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"csv": csv_path, "json": json_path, "debug_dir": debug_dir}


def write_camera_calibration_report(session_rows: list[dict[str, Any]], output_dir: str | Path) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "camera_calibration.json"
    csv_path = output_dir / "camera_calibration.csv"
    pd.DataFrame(session_rows).to_csv(csv_path, index=False, encoding="utf-8")
    json_path.write_text(json.dumps(session_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"csv": csv_path, "json": json_path}
