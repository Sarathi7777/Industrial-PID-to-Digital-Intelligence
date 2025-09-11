import os
import io
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import numpy as np
import cv2
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

from pipeline_core import process_pid_image
from db import PIDResult, SessionLocal, init_db
from sqlalchemy.orm import Session
from dxf_export import generate_dxf_bytes

app = FastAPI(title="PID Digital Intelligence API")

# CORS for local dev and simple frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load environment variables from .env
load_dotenv()

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY environment variable not set. Chat functionality will be disabled.")

# Pydantic models for chat endpoint
class ChatRequest(BaseModel):
    question: str
    context_json: Dict[str, Any]

class ChatResponse(BaseModel):
    response: str


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/process")
async def process(file: UploadFile = File(...), db: Session = Depends(get_db)) -> JSONResponse:
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        if not any(file.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]):
            raise HTTPException(status_code=400, detail="Unsupported file type")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        result = process_pid_image(content)
        # Add document name metadata
        result.setdefault("metadata", {}).update({"document_name": file.filename})

        # Persist
        rec = PIDResult(document_name=file.filename, result_json=result)
        db.add(rec)
        db.commit()
        db.refresh(rec)
        # Generate and persist symbol detection overlay image
        try:
            overlay_path = _save_symbol_overlay_image(content, result.get("components", []), rec.id, result.get("metadata"))
            symbol_image_url = f"/results/{rec.id}/symbol-image"
        except Exception:
            overlay_path = None
            symbol_image_url = None

        result_with_id = {"id": rec.id, **result}
        if symbol_image_url:
            result_with_id["symbol_image_url"] = symbol_image_url
        return JSONResponse(content=result_with_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


@app.post("/export/dxf")
async def export_dxf(payload: Dict[str, Any]) -> StreamingResponse:
    try:
        dxf_bytes = generate_dxf_bytes(payload)
        return StreamingResponse(
            io.BytesIO(dxf_bytes),
            media_type="application/dxf",
            headers={
                "Content-Disposition": f"attachment; filename=pid_export.dxf"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DXF export failed: {e}")


# -------------------- Symbol Overlay Utilities & Endpoint --------------------

_OUTPUT_DIR = os.getenv("SYMBOL_OUTPUT_DIR", os.path.join(os.getcwd(), "symbol_outputs"))
os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _save_symbol_overlay_image(image_bytes: bytes, components: List[Dict[str, Any]], rec_id: int, meta: Dict[str, Any] | None = None) -> str:
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image for overlay")

    # Account for processing-time resizing
    scale = 1.0
    if meta:
        sizes = (meta.get("image_sizes") or {})
        scl = sizes.get("scale") if isinstance(sizes, dict) else None
        try:
            if scl and float(scl) > 0 and float(scl) != 1.0:
                # Components bboxes are on processed image; need to map back to original
                scale = float(scl)
        except Exception:
            pass

    # Draw bounding boxes and labels
    for comp in components:
        bbox = (((comp or {}).get("attributes") or {}).get("bbox_pixels"))
        if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        if scale != 1.0:
            x1, y1, x2, y2 = [int(round(v / scale)) for v in bbox]
        else:
            x1, y1, x2, y2 = [int(v) for v in bbox]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = (comp.get("component_class_name")
                 or f"Class {comp.get('component_class')}"
                 or comp.get("component_id")
                 or "symbol")
        conf = ((comp.get("attributes") or {}).get("detection_confidence"))
        if conf is not None:
            try:
                label = f"{label} {float(conf):.2f}"
            except Exception:
                pass
        # Put label above the box
        ((tw, th), _) = cv2.getTextSize(str(label), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        y_text = max(0, y1 - 6)
        cv2.rectangle(img, (x1, y_text - th - 4), (x1 + tw + 4, y_text), (0, 255, 0), -1)
        cv2.putText(img, str(label), (x1 + 2, y_text - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    out_path = os.path.join(_OUTPUT_DIR, f"{rec_id}_symbol_overlay.png")
    # Ensure PNG write
    success, encoded = cv2.imencode(".png", img)
    if not success:
        raise ValueError("Failed to encode overlay image")
    with open(out_path, "wb") as f:
        f.write(encoded.tobytes())
    return out_path


@app.get("/results/{rec_id}/symbol-image")
async def get_symbol_image(rec_id: int) -> StreamingResponse:
    path = os.path.join(_OUTPUT_DIR, f"{rec_id}_symbol_overlay.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Symbol image not found")
    try:
        return StreamingResponse(open(path, "rb"), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read symbol image: {e}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_pid_data(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint that uses Gemini AI to answer questions about P&ID data.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503, 
            detail="Chat service unavailable: GEMINI_API_KEY not configured"
        )
    
    try:
        # Initialize the Gemini model
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction="""You are APX CoPilot, an expert AI assistant for P&ID (Process & Instrumentation Diagram) Digital Intelligence Platform. You are a comprehensive knowledge base about this project and can help users with various aspects of P&ID digitization and analysis.

## PROJECT OVERVIEW
This is a complete P&ID digitization platform that converts static Process & Instrumentation Diagrams into structured, searchable digital data using advanced AI technologies.

## CORE CAPABILITIES
1. **Symbol Detection**: Uses YOLO (You Only Look Once) computer vision to detect industrial symbols like valves, pumps, tanks, instruments, etc.
2. **Text Recognition**: Employs TrOCR (Transformer-based OCR) for accurate text extraction from P&ID labels and annotations
3. **Connection Mapping**: Automatically traces process flow connections between components
4. **Data Validation**: Identifies missing tags, low-confidence detections, and isolated components
5. **Export Capabilities**: Supports multiple formats (JSON, XML, CSV, DXF)


## COMPONENT TYPES DETECTED
- Valves: Gate, Globe, Check, Ball, Angle, Needle, Three-Way, Diaphragm, Butterfly
- Instruments: Field Mounted, Board Mounted, with Lights, Generic
- Equipment: Pumps, Heat Exchangers, Tanks, Filters, Strainers
- Safety: Pressure Safety Valves, Pressure Indicators
- Fittings: Reducers, Flange Joints, Bleed/Drain points
- Actuators and Control Valves

## DATA STRUCTURE
The P&ID data includes:
- **Metadata**: Document info, processing stats, quality metrics
- **Components**: Each with ID, PID tag, class, status, confidence, bounding box, connections
- **Connections**: Process flow relationships between components
- **Quality Metrics**: Detection confidence, tagging ratios, connection analysis

## ANALYSIS FEATURES
- **Status Classification**: OK, Review Required, Warning, Isolated Component
- **Confidence Scoring**: Detection confidence for each component
- **Tag Validation**: P&ID tag parsing and validation
- **Connection Analysis**: Process flow mapping and validation
- **Quality Assessment**: Overall analysis quality metrics

## USER INTERACTIONS
You can help users with:
- Understanding P&ID analysis results
- Explaining component types and their functions
- Interpreting connection patterns and process flows
- Troubleshooting analysis issues
- Understanding quality metrics and confidence scores
- Explaining P&ID standards and conventions
- General questions about the platform capabilities

## RESPONSE GUIDELINES
- If P&ID data is provided, base your answers on that specific data
- If no P&ID data is provided, answer general questions about the platform
- Be helpful, accurate, and concise
- Use technical terms appropriately for the audience
- Provide actionable insights when possible
- If you cannot answer based on available data, clearly state this"""
        )
        
        # Prepare the context for the AI
        if request.context_json and len(request.context_json) > 0:
            context_str = f"""
P&ID Analysis Data:
{request.context_json}

User Question: {request.question}

Please analyze the P&ID data above and answer the user's question based on the information provided in the JSON data.
"""
        else:
            context_str = f"""
User Question: {request.question}

Please answer this question about the P&ID Digital Intelligence Platform. You have comprehensive knowledge about the platform's capabilities and features.
"""
        
        # Generate response using Gemini
        response = model.generate_content(context_str)
        
        return ChatResponse(response=response.text)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate chat response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    init_db()
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)


