import torch
from pathlib import Path
from PIL import Image
import cv2
import json
import math
import pytesseract
from pytesseract import Output
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from ultralytics import YOLO
import numpy as np
import re
from datetime import datetime, timezone
from itertools import combinations
from collections import defaultdict, deque

# --- 1. CONFIGURATION ---
YOLO_MODEL_PATH = Path("best.pt") # Your YOLOv8 model trained with class names
CUSTOM_OCR_MODEL_PATH = Path("trocr-finetuned-pid-final/final")
IMAGE_TO_PROCESS = Path("D:/ABB/Sarathi/Sarathi/pid/image_2/0.jpg") # The P&ID image you want to process
OUTPUT_JSON_PATH = Path("pid_output_WINNER_FINAL.json")
CONFIDENCE_THRESHOLD = 0.4 

# --- 2. ADVANCED CONNECTION ENGINE CLASS ---
class ConnectionEngine:
    def __init__(self, components):
        self.components = {comp['component_id']: comp for comp in components}
        self.adj = defaultdict(list)
        self.lines = []

    def _is_point_near_component(self, point, component_id, tolerance=30):
        x, y = point
        x1, y1, x2, y2 = self.components[component_id]['attributes']['bbox_pixels']
        # Check if point is within an expanded bounding box
        return (x1 - tolerance < x < x2 + tolerance) and (y1 - tolerance < y < y2 + tolerance)

    def detect_lines(self, image):
        print("  - Masking components and detecting pipeline segments...")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Create a mask to digitally erase all component areas
        mask = np.ones_like(gray) * 255
        for comp in self.components.values():
            x1, y1, x2, y2 = comp['attributes']['bbox_pixels']
            # Add padding to the mask to avoid detecting component edges
            cv2.rectangle(mask, (x1 - 5, y1 - 5), (x2 + 5, y2 + 5), 0, -1)
        
        masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
        edges = cv2.Canny(masked_gray, 50, 150, apertureSize=3)
        
        # Use fine-tuned parameters to find clean line segments
        detected_lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=25, minLineLength=20, maxLineGap=30)
        
        if detected_lines is not None:
            self.lines = [line[0] for line in detected_lines]
        print(f"  - Found {len(self.lines)} raw line segments.")

    def build_graph(self):
        print("  - Building direct connection graph...")
        # For each line, find which components its endpoints are attached to
        for line in self.lines:
            x1, y1, x2, y2 = line
            start_point, end_point = (x1, y1), (x2, y2)
            
            start_connections = [comp_id for comp_id in self.components if self._is_point_near_component(start_point, comp_id)]
            end_connections = [comp_id for comp_id in self.components if self._is_point_near_component(end_point, comp_id)]
            
            # Connect all components found at the ends of this single line segment
            for start_comp in start_connections:
                for end_comp in end_connections:
                    if start_comp != end_comp:
                        if end_comp not in self.adj[start_comp]: self.adj[start_comp].append(end_comp)
                        if start_comp not in self.adj[end_comp]: self.adj[end_comp].append(start_comp)

    def find_all_connections(self):
        print("  - Tracing all paths to find end-to-end connectivity...")
        all_connections = []
        temp_set = set()
        component_ids = list(self.components.keys())

        # For every possible pair of components, find if a path exists between them
        for start_node, end_node in combinations(component_ids, 2):
            q, visited = deque([start_node]), {start_node}
            path_found = False
            while q:
                curr_node = q.popleft()
                if curr_node == end_node:
                    path_found = True
                    break
                for neighbor in self.adj.get(curr_node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append(neighbor)
            
            if path_found:
                conn_id = tuple(sorted((start_node, end_node)))
                if conn_id not in temp_set:
                    all_connections.append({"from": conn_id[0], "to": conn_id[1], "status": "OK"})
                    temp_set.add(conn_id)
        return all_connections

# --- 3. HELPER FUNCTIONS ---
def get_box_center(box):
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)

def parse_pid_tag(tag_string):
    if not isinstance(tag_string, str): return None
    match = re.match(r'^([A-Z]{2,3})[- ]?(\d+[A-Z]?)$', tag_string.upper())
    if match: return {"type": match.group(1), "loop_id": match.group(2)}
    match = re.match(r'^([A-Z]{1,2})[- ]?(\d+[A-Z]?)$', tag_string.upper())
    if match: return {"equipment_type": match.group(1), "equipment_id": match.group(2)}
    return None

def run_ocr_on_crop(image_crop, processor, model, device):
    image = Image.fromarray(image_crop).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
    generated_ids = model.generate(pixel_values, max_new_tokens=32)
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

# --- 4. MAIN PIPELINE ---
def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    print("Loading models...")
    yolo_model = YOLO(YOLO_MODEL_PATH)
    ocr_processor = TrOCRProcessor.from_pretrained(CUSTOM_OCR_MODEL_PATH)
    ocr_model = VisionEncoderDecoderModel.from_pretrained(CUSTOM_OCR_MODEL_PATH).to(device)
    print("All models loaded successfully.")

    print(f"\nProcessing image: {IMAGE_TO_PROCESS.name}")
    img_cv_color = cv2.imread(str(IMAGE_TO_PROCESS))
    
    # STAGE 1: Symbol Detection
    print("Stage 1: Detecting symbols with class names...")
    yolo_results = yolo_model.predict(source=img_cv_color, conf=CONFIDENCE_THRESHOLD, verbose=False)
    final_components = []
    for i, box in enumerate(yolo_results[0].boxes):
        class_id = int(box.cls[0].item())
        component = {
            "component_id": f"symbol_{i}",
            "pid_tag": "N/A",
            "component_class": yolo_model.names[class_id],
            "status": "OK",
            "parsed_tag": None,
            "attributes": {
                "detection_confidence": round(box.conf[0].item(), 2),
                "bbox_pixels": [int(c) for c in box.xyxy[0].tolist()]
            }
        }
        final_components.append(component)
    print(f"Found {len(final_components)} symbols.")

    # STAGE 2 & 3: OCR and Smart Association
    print("\nStage 2 & 3: Extracting text and associating tags...")
    ocr_df = pytesseract.image_to_data(img_cv_color, config=r'--psm 6', output_type=Output.DATAFRAME)
    ocr_df = ocr_df[(ocr_df.conf > 40) & (ocr_df.text.notna())]
    extracted_text = [{"text": str(row['text']).strip(), "bbox": [row['left'], row['top'], row['left'] + row['width'], row['top'] + row['height']]} for _, row in ocr_df.iterrows()]
    
    for component in final_components:
        symbol_center = get_box_center(component['attributes']['bbox_pixels'])
        candidates = []
        for text_info in extracted_text:
            distance = math.sqrt((symbol_center[0] - get_box_center(text_info['bbox'])[0])**2 + (symbol_center[1] - get_box_center(text_info['bbox'])[1])**2)
            if distance < 250:
                score = 0
                if parse_pid_tag(text_info['text']): score = 100
                candidates.append((distance - score, text_info['text']))
        
        if candidates:
            candidates.sort(key=lambda x: x[0])
            component['pid_tag'] = candidates[0][1]
        
        component['parsed_tag'] = parse_pid_tag(component['pid_tag'])

    print(f"Associated tags for {len(final_components)} components.")
    
    # STAGE 4: Advanced Connection Tracing
    print("\nStage 4: Tracing connections with the Advanced Engine...")
    connection_engine = ConnectionEngine(final_components)
    connection_engine.detect_lines(img_cv_color)
    connection_engine.build_graph()
    detected_connections = connection_engine.find_all_connections()
    print(f"Found {len(detected_connections)} unique end-to-end connections.")

    # STAGE 5: Final JSON Polishing
    print("\nStage 5: Finalizing JSON output...")
    review_count = 0
    for component in final_components:
        component_id = component['component_id']
        connections_to = [conn['to'] if conn['from'] == component_id else conn['from'] for conn in detected_connections if component_id in (conn['from'], conn['to'])]
        component['connections_to'] = sorted(list(set(connections_to)))
        
        if component['pid_tag'] == "N/A": component['status'] = "Review Required: Missing Tag"
        elif component['parsed_tag'] is None and not component['pid_tag'].replace('.','',1).isdigit(): component['status'] = "Review Required: Non-standard Tag"
        elif not component['connections_to']: component['status'] = "Warning: Isolated Component"
        
        if component['status'] != "OK": review_count += 1
    
    output_data = {
        "metadata": {"document_name": IMAGE_TO_PROCESS.name, "summary": {"component_count": len(final_components), "connection_count": len(detected_connections), "review_required_count": review_count}},
        "components": final_components,
        "connections_summary": detected_connections
    }
    with open(OUTPUT_JSON_PATH, 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"\n--- 🚀 HACKATHON WINNING PIPELINE COMPLETE 🚀 ---")
    print(f"Saved ultimate structured data to '{OUTPUT_JSON_PATH}'")

if __name__ == '__main__':
    # We are temporarily removing the TrOCR model to focus on the connection engine
    # In a real app, you would uncomment the ocr model loading and use run_ocr_on_crop
    main()