import streamlit as st
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
import os

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="P&ID Digital Intelligence")

# --- CONFIGURATION & MAPPINGS ---
# (Final check: Ensure this map is 100% complete and accurate!)
CLASS_ID_TO_NAME_MAP = {
    1: "Gate Valve", 2: "Globe Valve", 3: "Check Valve", 4: "Check Valve", 5: "Ball Valve",
    6: "Pressure Indicator", 7: "Control Valve", 8: "Angle Valve", 9: "Needle Valve",
    10: "Three-Way Valve", 11: "Diaphragm Valve", 12: "Butterfly Valve", 13: "Heat Exchanger",
    14: "Pressure Safety Valve", 15: "Instrument (Field Mounted)", 16: "Instrument (Board Mounted)",
    17: "Instrument with Light", 18: "Instrument (Board Mounted)", 19: "Instrument with Light", 20: "Reducer",
    21: "Flange Joint", 22: "Actuator", 23: "Filter/Strainer", 24: "Bleed/Drain",
    25: "Generic Equipment", 26: "Pipe Size Spec", 27: "Gate Valve", 28: "Instrument (Generic)",
    29: "Instrument (Generic)", 30: "Check Valve", 31: "Instrument (Generic)", 32: "Instrument (Generic)"
}

YOLO_MODEL_PATH = Path("D:/ABB/Sarathi/Sarathi/pid/best.pt")
CUSTOM_OCR_MODEL_PATH = Path("trocr-finetuned-pid-pro/checkpoint-4890")

# --- MODEL LOADING (Cached for performance) ---
@st.cache_resource
def load_models():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    yolo_model = YOLO(YOLO_MODEL_PATH)
    ocr_processor = TrOCRProcessor.from_pretrained(CUSTOM_OCR_MODEL_PATH)
    ocr_model = VisionEncoderDecoderModel.from_pretrained(CUSTOM_OCR_MODEL_PATH).to(device)
    st.sidebar.success(f"Models loaded on {device}!")
    return yolo_model, ocr_processor, ocr_model, device

# --- HELPER FUNCTIONS ---
def get_box_center(box):
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)

def is_point_on_line_segment(p, a, b, tolerance=15): # Stricter tolerance to prevent spiderwebs
    p, a, b = np.array(p), np.array(a), np.array(b)
    line_vec, p_vec = b - a, p - a
    line_len_sq = np.sum(line_vec**2)
    if line_len_sq == 0.0: return False
    cross_product = np.cross(p_vec, line_vec)
    dist = np.linalg.norm(cross_product) / np.linalg.norm(line_vec)
    if dist > tolerance: return False
    dot_product = np.dot(p_vec, line_vec)
    return -tolerance <= dot_product <= line_len_sq + tolerance

def parse_pid_tag(tag_string):
    if not isinstance(tag_string, str): return None
    match = re.match(r'^([A-Z]{1,2})([A-Z]{1,2})[- ]?(\d+)([A-Z]?)$', tag_string.upper())
    if match: return {"measurement_type": match.group(1), "function": match.group(2), "loop_id": match.group(3), "suffix": match.group(4) or None}
    match = re.match(r'^([A-Z]{1,2})[- ]?(\d+[A-Z]?)$', tag_string.upper())
    if match: return {"equipment_type": match.group(1), "equipment_id": match.group(2)}
    return None

# --- MAIN UI AND PIPELINE LOGIC ---
st.title("🧠 AI P&ID Digital Intelligence Platform")
st.write("An advanced AI solution to transform static P&ID diagrams into rich, structured, and interconnected digital models.")

try:
    yolo, ocr_processor, ocr_model, device = load_models()
except Exception as e:
    st.error(f"Error loading models: {e}. Please ensure model files are in the correct directories ('runs/detect/train5' and 'trocr-finetuned-pid-final').")
    st.stop()

st.sidebar.title("Live AI Controls")
# Tuned default values for better initial results
conf_threshold = st.sidebar.slider("Symbol Confidence Threshold", 0.10, 1.0, 0.45, 0.05)
line_threshold = st.sidebar.slider("Line Detection Threshold", 20, 150, 50, 5)
min_line_length = st.sidebar.slider("Minimum Line Length (px)", 20, 200, 50, 5)
max_line_gap = st.sidebar.slider("Maximum Line Gap (px)", 10, 50, 20, 5)

uploaded_file = st.file_uploader("Upload a P&ID Image", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Save uploaded file to a consistent path
    file_path = Path("temp_uploaded_image.png")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button("🚀 Digitize P&ID", use_container_width=True):
        with st.spinner("🤖 AI at work... This may take a few minutes..."):
            
            img_cv_color = cv2.imread(str(file_path))
            original_pil_image = Image.open(file_path).convert("RGB")
            
            # --- FULL PIPELINE LOGIC ---
            # STAGE 1: Symbol Detection
            yolo_results = yolo.predict(source=img_cv_color, conf=conf_threshold, verbose=False)
            detected_symbols = [{"id": f"symbol_{i}", "class_id": int(b.cls[0].item()), "confidence": b.conf[0].item(), "bbox": [int(c) for c in b.xyxy[0].tolist()]} for i, b in enumerate(yolo_results[0].boxes)]
            
            # STAGE 2: Text Detection & Recognition
            ocr_df = pytesseract.image_to_data(img_cv_color, config=r'--psm 6', output_type=Output.DATAFRAME)
            ocr_df = ocr_df[(ocr_df.conf > 40) & (ocr_df.text.notna())]
            extracted_text = []
            for _, row in ocr_df.iterrows():
                x, y, w, h = row['left'], row['top'], row['width'], row['height']
                if w < 5 or h < 5 or w > 500: continue
                text_crop_img = img_cv_color[y:y+h, x:x+w]
                image = Image.fromarray(text_crop_img).convert("RGB")
                pixel_values = ocr_processor(images=image, return_tensors="pt").pixel_values.to(device)
                generated_ids = ocr_model.generate(pixel_values, max_new_tokens=32)
                recognized_text = ocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
                if recognized_text:
                    extracted_text.append({"text": recognized_text, "bbox": [x, y, x + w, y + h]})

            # STAGE 3: Association and Flagging
            final_components = []
            for symbol in detected_symbols:
                symbol_center = get_box_center(symbol['bbox'])
                candidates = []
                for text_info in extracted_text:
                    distance = math.sqrt((symbol_center[0] - get_box_center(text_info['bbox'])[0])**2 + (symbol_center[1] - get_box_center(text_info['bbox'])[1])**2)
                    if distance < 300: candidates.append((distance, text_info['text']))
                closest_text = "N/A"
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    best_candidate = next((c[1] for c in candidates if parse_pid_tag(c[1])), candidates[0][1])
                    closest_text = best_candidate
                status, parsed_data = "OK", parse_pid_tag(closest_text)
                if closest_text == "N/A": status = "Review Required: Missing Tag"
                elif parsed_data is None and not closest_text.replace('.','',1).isdigit(): status = "Review Required: Non-standard Tag"
                component_class_name = CLASS_ID_TO_NAME_MAP.get(symbol['class_id'], f"Unknown ClassID {symbol['class_id']}")
                component = {"component_id": symbol['id'], "pid_tag": closest_text, "component_class": component_class_name, "status": status, "parsed_tag": parsed_data, "attributes": {"detection_confidence": round(symbol['confidence'], 2), "bbox_pixels": symbol['bbox']}}
                final_components.append(component)

            # STAGE 4: Connection Tracing
            adj = {comp['component_id']: [] for comp in final_components}
            gray = cv2.cvtColor(img_cv_color, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=line_threshold, minLineLength=min_line_length, maxLineGap=max_line_gap)
            if lines is not None:
                for comp1, comp2 in combinations(final_components, 2):
                    center1, center2 = get_box_center(comp1['attributes']['bbox_pixels']), get_box_center(comp2['attributes']['bbox_pixels'])
                    for line in lines:
                        p1, p2 = (line[0][0], line[0][1]), (line[0][2], line[0][3])
                        if is_point_on_line_segment(center1, p1, p2) and is_point_on_line_segment(center2, p1, p2):
                            if comp2['component_id'] not in adj[comp1['component_id']]: adj[comp1['component_id']].append(comp2['component_id'])
                            if comp1['component_id'] not in adj[comp2['component_id']]: adj[comp2['component_id']].append(comp1['component_id'])
                            break
            
            # STAGE 5: Final JSON Polishing
            review_count = 0
            for component in final_components:
                component['connections_to'] = sorted(list(set(adj.get(component['component_id'], []))))
                if component['status'] != "OK": review_count += 1
                elif not component['connections_to']: component['status'] = "Warning: Isolated Component"
            
            connections_summary_list = []
            temp_set = set()
            for start_node, end_nodes in adj.items():
                for end_node in end_nodes:
                    conn_id = tuple(sorted((start_node, end_node)))
                    if conn_id not in temp_set:
                        connections_summary_list.append({"from": conn_id[0], "to": conn_id[1], "status": "OK"})
                        temp_set.add(conn_id)

            output_data = {"metadata": {"document_name": uploaded_file.name, "summary": {"component_count": len(final_components), "connection_count": len(connections_summary_list), "review_required_count": review_count}}, "components": final_components, "connections_summary": connections_summary_list}
            
            # --- VISUALIZATION LOGIC ---
            ocr_viz = img_cv_color.copy()
            twin_viz = img_cv_color.copy()

            for text_data in extracted_text:
                x1, y1, x2, y2 = text_data['bbox']
                cv2.rectangle(ocr_viz, (x1, y1), (x2, y2), (255, 0, 0), 2) # Blue for text
            
            for conn in connections_summary_list:
                # Find the component dicts from the IDs to get their centers
                comp_from = next((c for c in final_components if c['component_id'] == conn['from']), None)
                comp_to = next((c for c in final_components if c['component_id'] == conn['to']), None)
                if comp_from and comp_to:
                    center1 = get_box_center(comp_from['attributes']['bbox_pixels'])
                    center2 = get_box_center(comp_to['attributes']['bbox_pixels'])
                    cv2.arrowedLine(twin_viz, center1, center2, (255, 200, 0), 2, tipLength=0.03)

            for comp in final_components:
                x1, y1, x2, y2 = comp['attributes']['bbox_pixels']
                cv2.rectangle(twin_viz, (x1, y1), (x2, y2), (0, 255, 0), 3) # Green for symbols

            st.success("Digitization Complete!")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Original P&ID")
                st.image(original_pil_image, use_container_width=True)
            with col2:
                st.subheader("AI Analysis Layers")
                tab1, tab2 = st.tabs(["👁️ OCR Layer", "🔗 Digital Twin Layer"])
                with tab1:
                    st.image(ocr_viz, channels="BGR", use_container_width=True)
                with tab2:
                    st.image(twin_viz, channels="BGR", use_container_width=True)
            
            st.divider()
            st.subheader("Extracted Structured Data (JSON)")
            st.json(output_data)

            st.download_button(label="⬇️ Download Full JSON Output", data=json.dumps(output_data, indent=4), file_name=f"{file_path.stem}_output.json", mime="application/json", use_container_width=True)