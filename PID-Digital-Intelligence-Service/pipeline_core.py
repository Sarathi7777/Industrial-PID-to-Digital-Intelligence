import io
import os
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import defaultdict

import cv2
import numpy as np
import torch
from PIL import Image
from pytesseract import Output
import pytesseract
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from ultralytics import YOLO
import time


# --- Configuration ---
YOLO_MODEL_PATH = Path("best.pt")
CUSTOM_OCR_MODEL_PATH = Path("Custom-TrOCR-PID/checkpoint-1224")
MAX_OCR_REGIONS = int(os.getenv("MAX_OCR_REGIONS", "120"))
TROCR_BATCH_SIZE = int(os.getenv("TROCR_BATCH_SIZE", "16"))
RESIZE_LONG_SIDE = int(os.getenv("RESIZE_LONG_SIDE", "1600"))
TIME_BUDGET_MS = int(os.getenv("TIME_BUDGET_MS", "25000"))
CONNECTION_TOLERANCE = int(os.getenv("CONNECTION_TOLERANCE", "25"))


_MODELS_CACHE = {
    "yolo": None,
    "ocr_processor": None,
    "ocr_model": None,
    "device": None,
}

# Configure Tesseract binary path if provided (helps on Windows)
_DEFAULT_TESSERACT_WIN = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
_tess_path = os.getenv("TESSERACT_PATH") or (_DEFAULT_TESSERACT_WIN if os.name == "nt" and os.path.exists(_DEFAULT_TESSERACT_WIN) else None)
if _tess_path:
    pytesseract.pytesseract.tesseract_cmd = _tess_path


class EnhancedConnectionDetector:
    """Advanced connection detection for P&ID components."""
    
    def __init__(self, tolerance: int = CONNECTION_TOLERANCE):
        self.tolerance = tolerance
        self.detected_lines = []
        
    def distance_point_to_line_segment(self, point: Tuple[int, int], 
                                     line_start: Tuple[int, int], 
                                     line_end: Tuple[int, int]) -> float:
        """Calculate minimum distance from a point to a line segment with high precision."""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Convert to numpy arrays for precision
        p = np.array([x0, y0], dtype=np.float32)
        a = np.array([x1, y1], dtype=np.float32)
        b = np.array([x2, y2], dtype=np.float32)
        
        line_vec = b - a
        line_len_sq = np.sum(line_vec ** 2)
        
        if line_len_sq < 1e-6:  # Line is essentially a point
            return float(np.linalg.norm(p - a))
        
        # Calculate parameter t for closest point on line segment
        t = max(0.0, min(1.0, np.dot(p - a, line_vec) / line_len_sq))
        
        # Find closest point and calculate distance
        closest_point = a + t * line_vec
        return float(np.linalg.norm(p - closest_point))
    
    def is_point_near_symbol_edge(self, point: Tuple[int, int], bbox: List[int]) -> bool:
        """Enhanced method to check if point is near symbol boundary."""
        x, y = point
        x1, y1, x2, y2 = bbox
        
        # Calculate distances to all edges and corners
        distances = []
        
        # Edge distances (only if point is aligned with edge)
        if x1 <= x <= x2:  # Point is horizontally aligned
            distances.extend([abs(y - y1), abs(y - y2)])  # Top and bottom edges
        
        if y1 <= y <= y2:  # Point is vertically aligned
            distances.extend([abs(x - x1), abs(x - x2)])  # Left and right edges
        
        # Corner distances
        corners = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
        corner_distances = [math.sqrt((x - cx)**2 + (y - cy)**2) for cx, cy in corners]
        distances.extend(corner_distances)
        
        # Also check if point is just outside the bounding box but very close
        if not distances:  # Point is not aligned with any edge
            # Calculate distance to closest edge
            if x < x1:
                if y < y1:
                    distances.append(math.sqrt((x - x1)**2 + (y - y1)**2))
                elif y > y2:
                    distances.append(math.sqrt((x - x1)**2 + (y - y2)**2))
                else:
                    distances.append(x1 - x)
            elif x > x2:
                if y < y1:
                    distances.append(math.sqrt((x - x2)**2 + (y - y1)**2))
                elif y > y2:
                    distances.append(math.sqrt((x - x2)**2 + (y - y2)**2))
                else:
                    distances.append(x - x2)
            else:  # x1 <= x <= x2
                if y < y1:
                    distances.append(y1 - y)
                else:  # y > y2
                    distances.append(y - y2)
        
        min_distance = min(distances) if distances else float('inf')
        return min_distance <= self.tolerance
    
    def preprocess_image_for_lines(self, image: np.ndarray) -> np.ndarray:
        """Enhanced image preprocessing for better line detection."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(filtered, (5, 5), 0)
        
        return blurred
    
    def create_enhanced_mask(self, image_shape: Tuple[int, int], components: List[Dict]) -> np.ndarray:
        """Create enhanced mask to exclude symbol areas with adaptive padding."""
        mask = np.ones(image_shape, dtype=np.uint8) * 255
        
        for comp in components:
            x1, y1, x2, y2 = comp["attributes"]["bbox_pixels"]
            
            # Adaptive padding based on symbol size
            symbol_area = (x2 - x1) * (y2 - y1)
            if symbol_area > 10000:  # Large symbol
                pad = 8
            elif symbol_area > 5000:  # Medium symbol
                pad = 6
            else:  # Small symbol
                pad = 4
            
            # Apply padding with bounds checking
            x1_padded = max(0, x1 - pad)
            y1_padded = max(0, y1 - pad)
            x2_padded = min(image_shape[1], x2 + pad)
            y2_padded = min(image_shape[0], y2 + pad)
            
            # Create exclusion rectangle
            cv2.rectangle(mask, (x1_padded, y1_padded), (x2_padded, y2_padded), 0, -1)
        
        return mask
    
    def detect_lines_enhanced(self, image: np.ndarray, components: List[Dict]) -> List[Dict]:
        """Enhanced line detection with multiple parameter sets."""
        preprocessed = self.preprocess_image_for_lines(image)
        mask = self.create_enhanced_mask(image.shape[:2], components)
        
        # Apply mask to exclude symbol areas
        masked_image = cv2.bitwise_and(preprocessed, preprocessed, mask=mask)
        
        # Enhanced edge detection with morphological operations
        edges = cv2.Canny(masked_image, 30, 80, apertureSize=3)
        
        # Morphological operations to connect broken lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        detected_lines = []
        
        # Try multiple parameter sets for different line types
        parameter_sets = [
            {"threshold": 30, "minLineLength": 20, "maxLineGap": 15},  # Standard lines
            {"threshold": 20, "minLineLength": 15, "maxLineGap": 20},  # Broken/faint lines
            {"threshold": 40, "minLineLength": 30, "maxLineGap": 10},  # Strong lines
        ]
        
        for params in parameter_sets:
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=params["threshold"],
                minLineLength=params["minLineLength"],
                maxLineGap=params["maxLineGap"]
            )
            
            if lines is not None:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    line_dict = {
                        'start': (int(x1), int(y1)),
                        'end': (int(x2), int(y2)),
                        'length': math.sqrt((x2-x1)**2 + (y2-y1)**2),
                        'params': params
                    }
                    detected_lines.append(line_dict)
        
        # Remove duplicate lines (lines that are very similar)
        filtered_lines = self._remove_duplicate_lines(detected_lines)
        self.detected_lines = filtered_lines
        
        return filtered_lines
    
    def _remove_duplicate_lines(self, lines: List[Dict], distance_threshold: float = 10.0) -> List[Dict]:
        """Remove duplicate or very similar lines."""
        if not lines:
            return lines
        
        # Sort by length (keep longer lines when duplicates exist)
        lines.sort(key=lambda x: x['length'], reverse=True)
        
        filtered = []
        for line in lines:
            is_duplicate = False
            start1, end1 = line['start'], line['end']
            
            for existing in filtered:
                start2, end2 = existing['start'], existing['end']
                
                # Check if lines are similar (endpoints are close)
                dist1 = math.sqrt((start1[0] - start2[0])**2 + (start1[1] - start2[1])**2)
                dist2 = math.sqrt((end1[0] - end2[0])**2 + (end1[1] - end2[1])**2)
                
                # Also check reversed direction
                dist3 = math.sqrt((start1[0] - end2[0])**2 + (start1[1] - end2[1])**2)
                dist4 = math.sqrt((end1[0] - start2[0])**2 + (end1[1] - start2[1])**2)
                
                if ((dist1 < distance_threshold and dist2 < distance_threshold) or
                    (dist3 < distance_threshold and dist4 < distance_threshold)):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                filtered.append(line)
        
        return filtered
    
    def find_connected_symbols(self, line: Dict, components: List[Dict]) -> List[int]:
        """Find symbols that are connected by a specific line."""
        connected_indices = []
        start_point, end_point = line['start'], line['end']
        
        for idx, component in enumerate(components):
            bbox = component["attributes"]["bbox_pixels"]
            
            # Check if either endpoint is near this symbol
            start_near = self.is_point_near_symbol_edge(start_point, bbox)
            end_near = self.is_point_near_symbol_edge(end_point, bbox)
            
            if start_near or end_near:
                connected_indices.append(idx)
        
        return connected_indices
    
    def build_connection_graph(self, components: List[Dict], lines: List[Dict]) -> Dict[str, List[str]]:
        """Build enhanced connection graph from detected lines and components."""
        connections = defaultdict(list)
        connection_details = []
        
        for line_idx, line in enumerate(lines):
            connected_symbols = self.find_connected_symbols(line, components)
            
            # Handle different connection scenarios
            if len(connected_symbols) == 2:
                # Direct connection between two symbols
                idx1, idx2 = connected_symbols
                comp1_id = components[idx1]["component_id"]
                comp2_id = components[idx2]["component_id"]
                
                if comp2_id not in connections[comp1_id]:
                    connections[comp1_id].append(comp2_id)
                if comp1_id not in connections[comp2_id]:
                    connections[comp2_id].append(comp1_id)
                
                connection_details.append({
                    "from": comp1_id,
                    "to": comp2_id,
                    "line_id": line_idx,
                    "connection_type": "direct",
                    "line_coords": (*line['start'], *line['end'])
                })
                
            elif len(connected_symbols) > 2:
                # Junction point - connect all pairs
                for i in range(len(connected_symbols)):
                    for j in range(i + 1, len(connected_symbols)):
                        idx1, idx2 = connected_symbols[i], connected_symbols[j]
                        comp1_id = components[idx1]["component_id"]
                        comp2_id = components[idx2]["component_id"]
                        
                        if comp2_id not in connections[comp1_id]:
                            connections[comp1_id].append(comp2_id)
                        if comp1_id not in connections[comp2_id]:
                            connections[comp2_id].append(comp1_id)
                
                # Add junction details
                junction_components = [components[idx]["component_id"] for idx in connected_symbols]
                connection_details.append({
                    "junction_components": junction_components,
                    "line_id": line_idx,
                    "connection_type": "junction",
                    "line_coords": (*line['start'], *line['end'])
                })
        
        return dict(connections), connection_details


def _load_models() -> Tuple[YOLO, TrOCRProcessor, VisionEncoderDecoderModel, str]:
    if _MODELS_CACHE["yolo"] is not None:
        return (
            _MODELS_CACHE["yolo"],
            _MODELS_CACHE["ocr_processor"],
            _MODELS_CACHE["ocr_model"],
            _MODELS_CACHE["device"],
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    yolo_model = YOLO(YOLO_MODEL_PATH)
    try:
        yolo_model.to(device)
    except Exception:
        pass
    ocr_processor = TrOCRProcessor.from_pretrained(CUSTOM_OCR_MODEL_PATH)
    ocr_model = VisionEncoderDecoderModel.from_pretrained(CUSTOM_OCR_MODEL_PATH).to(device)

    _MODELS_CACHE.update({
        "yolo": yolo_model,
        "ocr_processor": ocr_processor,
        "ocr_model": ocr_model,
        "device": device,
    })
    return yolo_model, ocr_processor, ocr_model, device


def _get_box_center(box: List[int]) -> Tuple[int, int]:
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def _parse_pid_tag(tag_string: Any):
    if not isinstance(tag_string, str):
        return None
    match = re.match(r"^([A-Z]{1,2})([A-Z]{1,2})[- ]?(\d+)([A-Z]?)$", tag_string.upper())
    if match:
        return {
            "measurement_type": match.group(1),
            "function": match.group(2),
            "loop_id": match.group(3),
            "suffix": match.group(4) or None,
        }
    match = re.match(r"^([A-Z]{1,2})[- ]?(\d+[A-Z]?)$", tag_string.upper())
    if match:
        return {"equipment_type": match.group(1), "equipment_id": match.group(2)}
    return None


def _decode_image(image_bytes: bytes) -> Tuple[np.ndarray, Image.Image]:
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_cv_color = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img_cv_color is None:
        raise ValueError("Failed to decode image bytes")
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return img_cv_color, pil_image


def process_pid_image(image_bytes: bytes, *, 
                     conf_threshold: float = 0.45, 
                     resize_long_side: int | None = None, 
                     max_ocr_regions: int | None = None,
                     connection_tolerance: int | None = None) -> Dict[str, Any]:
    """
    Enhanced P&ID image processing with advanced connection detection.
    
    Args:
        image_bytes: Input image as bytes
        conf_threshold: YOLO confidence threshold
        resize_long_side: Maximum dimension for image resizing
        max_ocr_regions: Maximum OCR regions to process
        connection_tolerance: Distance tolerance for connection detection
    
    Returns:
        Dictionary containing processed P&ID data with enhanced connection information
    """
    yolo, ocr_processor, ocr_model, device = _load_models()

    t0 = time.perf_counter()
    img_cv_color, original_pil_image = _decode_image(image_bytes)
    
    # Adaptive downscaling for very large images
    original_shape = img_cv_color.shape[:2]
    resize_info = {"scale": 1.0, "original_size": None, "processed_size": None}
    try:
        h, w = img_cv_color.shape[:2]
        target_long = resize_long_side or RESIZE_LONG_SIDE
        long_side = max(h, w)
        if long_side > target_long:
            scale = target_long / float(long_side)
            new_w, new_h = int(w * scale), int(h * scale)
            img_cv_color = cv2.resize(img_cv_color, (new_w, new_h), interpolation=cv2.INTER_AREA)
            resize_info = {"scale": float(scale), "original_size": [int(w), int(h)], "processed_size": [int(new_w), int(new_h)]}
        else:
            resize_info = {"scale": 1.0, "original_size": [int(w), int(h)], "processed_size": [int(w), int(h)]}
    except Exception:
        pass

    # Stage 1: Symbol Detection
    yolo_results = yolo.predict(
        source=img_cv_color,
        conf=conf_threshold,
        verbose=False,
        device=device,
        half=True if device == "cuda" else False,
    )
    detected_symbols = []
    for i, b in enumerate(yolo_results[0].boxes):
        detected_symbols.append({
            "id": f"symbol_{i}",
            "class_id": int(b.cls[0].item()),
            "confidence": float(b.conf[0].item()),
            "bbox": [int(c) for c in b.xyxy[0].tolist()],
        })

    t1 = time.perf_counter()
    
    # Stage 2: Text Detection & Recognition (batch TrOCR for speed)
    ocr_df = pytesseract.image_to_data(img_cv_color, config=r"--psm 6", output_type=Output.DATAFRAME)
    ocr_df = ocr_df[(ocr_df.conf > 40) & (ocr_df.text.notna())]
    if not ocr_df.empty:
        cap = max_ocr_regions if max_ocr_regions is not None else MAX_OCR_REGIONS
        ocr_df = ocr_df.sort_values(by=["conf"], ascending=False).head(cap)
    
    extracted_text: List[Dict[str, Any]] = []
    crops: List[Image.Image] = []
    boxes: List[List[int]] = []
    
    for _, row in ocr_df.iterrows():
        x, y, w, h = int(row["left"]), int(row["top"]), int(row["width"]), int(row["height"])
        if w < 5 or h < 5 or w > 500:
            continue
        crop = img_cv_color[y : y + h, x : x + w]
        crops.append(Image.fromarray(crop).convert("RGB"))
        boxes.append([x, y, x + w, y + h])
    
    # Process OCR crops in batches
    for i in range(0, len(crops), TROCR_BATCH_SIZE):
        batch_images = crops[i : i + TROCR_BATCH_SIZE]
        batch_boxes = boxes[i : i + TROCR_BATCH_SIZE]
        if not batch_images:
            continue
        with torch.inference_mode():
            pixel_values = ocr_processor(images=batch_images, return_tensors="pt").pixel_values.to(device)
            generated_ids = ocr_model.generate(pixel_values, max_new_tokens=32, num_beams=1)
        texts = ocr_processor.batch_decode(generated_ids, skip_special_tokens=True)
        for txt, bbox in zip(texts, batch_boxes):
            txt = (txt or "").strip()
            if txt:
                extracted_text.append({"text": txt, "bbox": bbox})

    t2 = time.perf_counter()
    
    # Stage 3: Association and Flagging
    final_components: List[Dict[str, Any]] = []
    for symbol in detected_symbols:
        symbol_center = _get_box_center(symbol["bbox"])
        candidates: List[Tuple[float, str]] = []
        for text_info in extracted_text:
            distance = math.sqrt(
                (symbol_center[0] - _get_box_center(text_info["bbox"])[0]) ** 2
                + (symbol_center[1] - _get_box_center(text_info["bbox"])[1]) ** 2
            )
            if distance < 300:
                candidates.append((distance, text_info["text"]))
        
        closest_text = "N/A"
        if candidates:
            candidates.sort(key=lambda x: x[0])
            best_candidate = next((c[1] for c in candidates if _parse_pid_tag(c[1])), candidates[0][1])
            closest_text = best_candidate
        
        status = "OK"
        parsed_data = _parse_pid_tag(closest_text)
        if closest_text == "N/A":
            status = "Review Required: Missing Tag"
        elif parsed_data is None and not closest_text.replace(".", "", 1).isdigit():
            status = "Review Required: Non-standard Tag"
        
        class_id = int(symbol["class_id"])
        class_name = None
        try:
            class_name = (getattr(yolo, "names", None) or {}).get(class_id)
        except Exception:
            class_name = f"Class_{class_id}"
        
        component = {
            "component_id": symbol["id"],
            "pid_tag": closest_text,
            "component_class": int(symbol["class_id"]),
            "component_class_name": class_name,
            "status": status,
            "parsed_tag": parsed_data,
            "attributes": {
                "detection_confidence": round(float(symbol["confidence"]), 2),
                "bbox_pixels": symbol["bbox"],
                "center": _get_box_center(symbol["bbox"])
            },
        }
        final_components.append(component)

    t3 = time.perf_counter()
    
    # Stage 4: Connection Detection (user-requested algorithm)
    tolerance = connection_tolerance or CONNECTION_TOLERANCE
    # Prepare symbols for masking and proximity checks
    symbols_for_mask = [
        {"bbox": comp["attributes"]["bbox_pixels"], "center": _get_box_center(comp["attributes"]["bbox_pixels"]) }
        for comp in final_components
    ]
    # Build mask to exclude symbol areas
    gray_image = cv2.cvtColor(img_cv_color, cv2.COLOR_BGR2GRAY)
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    mask = np.ones_like(gray_image, dtype=np.uint8) * 255
    for sym in symbols_for_mask:
        x1, y1, x2, y2 = sym["bbox"]
        padding = 5
        x1_p = max(0, x1 - padding)
        y1_p = max(0, y1 - padding)
        x2_p = min(mask.shape[1], x2 + padding)
        y2_p = min(mask.shape[0], y2 + padding)
        cv2.rectangle(mask, (x1_p, y1_p), (x2_p, y2_p), 0, -1)
    masked_image = cv2.bitwise_and(blurred_image, blurred_image, mask=mask)
    edges = cv2.Canny(masked_image, threshold1=20, threshold2=60, apertureSize=3)
    # Detect lines with the specified parameters
    hough_lines = cv2.HoughLinesP(
        edges, rho=1, theta=np.pi/180, threshold=20, minLineLength=20, maxLineGap=30
    )
    # Graph build per user logic
    adj = {comp["component_id"]: [] for comp in final_components}
    detected_lines = []
    connection_details = []
    def _is_point_near_symbol(point: Tuple[int, int], bbox: List[int], tol: int) -> bool:
        x, y = point
        x1, y1, x2, y2 = bbox
        distances = [
            abs(y - y1) if x1 <= x <= x2 else float('inf'),
            abs(y - y2) if x1 <= x <= x2 else float('inf'),
            abs(x - x1) if y1 <= y <= y2 else float('inf'),
            abs(x - x2) if y1 <= y <= y2 else float('inf'),
        ]
        corner_distances = [
            math.hypot(x - x1, y - y1),
            math.hypot(x - x2, y - y1),
            math.hypot(x - x1, y - y2),
            math.hypot(x - x2, y - y2),
        ]
        min_distance = min(min(distances), min(corner_distances))
        return min_distance <= tol
    if hough_lines is not None:
        for line in hough_lines:
            x1, y1, x2, y2 = line[0]
            detected_lines.append({
                "start": (int(x1), int(y1)),
                "end": (int(x2), int(y2)),
                "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                "length": float(math.hypot(int(x2)-int(x1), int(y2)-int(y1)))
            })
            line_start, line_end = (int(x1), int(y1)), (int(x2), int(y2))
            connected_indices: List[int] = []
            for idx, comp in enumerate(final_components):
                bbox = comp["attributes"]["bbox_pixels"]
                if _is_point_near_symbol(line_start, bbox, tolerance) or _is_point_near_symbol(line_end, bbox, tolerance):
                    connected_indices.append(idx)
            if len(connected_indices) == 2:
                a, b = connected_indices
                ida = final_components[a]["component_id"]
                idb = final_components[b]["component_id"]
                if idb not in adj[ida]:
                    adj[ida].append(idb)
                if ida not in adj[idb]:
                    adj[idb].append(ida)
                connection_details.append({
                    "from": ida,
                    "to": idb,
                    "line_coords": (int(x1), int(y1), int(x2), int(y2)),
                    "connection_type": "direct"
                })
            elif len(connected_indices) > 2:
                # junction: connect all pairs
                ids = [final_components[i]["component_id"] for i in connected_indices]
                for i in range(len(ids)):
                    for j in range(i+1, len(ids)):
                        a_id, b_id = ids[i], ids[j]
                        if b_id not in adj[a_id]:
                            adj[a_id].append(b_id)
                        if a_id not in adj[b_id]:
                            adj[b_id].append(a_id)
                connection_details.append({
                    "junction_components": ids,
                    "line_coords": (int(x1), int(y1), int(x2), int(y2)),
                    "connection_type": "junction"
                })

    t4 = time.perf_counter()
    
    # Stage 5: Final Processing and Status Updates
    review_count = 0
    warning_count = 0
    
    for component in final_components:
        component["connections_to"] = sorted(list(set(adj.get(component["component_id"], []))))
        
        if "Review Required" in component["status"]:
            review_count += 1
        elif not component["connections_to"]:
            component["status"] = "Warning: Isolated Component"
            warning_count += 1

    # Generate connections summary
    connections_summary_list: List[Dict[str, Any]] = []
    temp_set = set()
    for start_node, end_nodes in adj.items():
        for end_node in end_nodes:
            conn_id = tuple(sorted((start_node, end_node)))
            if conn_id not in temp_set:
                connections_summary_list.append({
                    "from": conn_id[0], 
                    "to": conn_id[1], 
                    "status": "OK"
                })
                temp_set.add(conn_id)

    t5 = time.perf_counter()
    
    # Compile comprehensive output
    output_data: Dict[str, Any] = {
        "metadata": {
            "device": device,
            "timings_ms": {
                "total": int((t5 - t0) * 1000),
                "yolo": int((t1 - t0) * 1000),
                "ocr": int((t2 - t1) * 1000),
                "association": int((t3 - t2) * 1000),
                "connections": int((t4 - t3) * 1000),
                "finalization": int((t5 - t4) * 1000),
            },
            "summary": {
                "component_count": len(final_components),
                "connection_count": len(connections_summary_list),
                "review_required_count": review_count,
                "warning_count": warning_count,
                "text_regions_found": len(extracted_text),
            },
            "quality_metrics": {
                "avg_detection_confidence": round(
                    sum(c["attributes"]["detection_confidence"] for c in final_components) / 
                    max(len(final_components), 1), 3
                ),
                "tagged_components_ratio": round(
                    len([c for c in final_components if c["pid_tag"] != "N/A"]) / 
                    max(len(final_components), 1), 3
                ),
                "connected_components_ratio": round(
                    len([c for c in final_components if c["connections_to"]]) / 
                    max(len(final_components), 1), 3
                )
            },
            "image_sizes": resize_info
        },
        "components": final_components,
        "connections_summary": connections_summary_list,
    }
    
    # Add connection details if available
    if 'connection_details' in locals() and connection_details:
        output_data["connection_details"] = connection_details
    
    # Add detected lines information
    if 'detected_lines' in locals() and isinstance(detected_lines, list) and detected_lines:
        output_data["detected_lines"] = [
            {
                "line_id": i,
                "start": line.get("start") or (line.get("x1"), line.get("y1")),
                "end": line.get("end") or (line.get("x2"), line.get("y2")),
                "length": round(float(line.get("length") or math.hypot(
                    (line.get("end")[0] if line.get("end") else line.get("x2")) - (line.get("start")[0] if line.get("start") else line.get("x1")),
                    (line.get("end")[1] if line.get("end") else line.get("y2")) - (line.get("start")[1] if line.get("start") else line.get("y1"))
                )), 2)
            }
            for i, line in enumerate(detected_lines)
        ]
    
    # Set processing status
    processing_time = int((t5 - t0) * 1000)
    output_data["metadata"]["status"] = (
        "partial" if processing_time > TIME_BUDGET_MS else "complete"
    )
    
    return output_data