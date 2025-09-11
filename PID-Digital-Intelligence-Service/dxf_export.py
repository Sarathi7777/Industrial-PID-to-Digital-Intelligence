import io
from typing import Any, Dict, List, Tuple

import ezdxf


def _estimate_canvas_size(data: Dict[str, Any]) -> Tuple[int, int]:
    max_x, max_y = 0, 0
    # From components bboxes
    for comp in data.get("components", []):
        bbox = comp.get("attributes", {}).get("bbox_pixels")
        if isinstance(bbox, list) and len(bbox) == 4:
            _, _, x2, y2 = bbox
            max_x = max(max_x, int(x2))
            max_y = max(max_y, int(y2))
    # From detected_lines
    for line in data.get("detected_lines", []):
        start = line.get("start")
        end = line.get("end")
        if start and end:
            max_x = max(max_x, int(start[0]), int(end[0]))
            max_y = max(max_y, int(start[1]), int(end[1]))
    # From connection_details line_coords
    for conn in data.get("connection_details", []):
        coords = conn.get("line_coords")
        if isinstance(coords, (list, tuple)) and len(coords) == 4:
            x1, y1, x2, y2 = coords
            max_x = max(max_x, int(x1), int(x2))
            max_y = max(max_y, int(y1), int(y2))
    if max_x == 0:
        max_x = 1000
    if max_y == 0:
        max_y = 1000
    return max_x, max_y


def _img_to_dxf_coords(x: int, y: int, height: int) -> Tuple[float, float]:
    # Flip Y to convert image coords (origin top-left, y down) to DXF coords (origin bottom-left, y up)
    return float(x), float(height - y)


def generate_dxf_bytes(data: Dict[str, Any]) -> bytes:
    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    # Layers
    if "COMPONENTS" not in doc.layers:
        doc.layers.new(name="COMPONENTS", dxfattribs={"color": 1})  # red
    if "TEXT" not in doc.layers:
        doc.layers.new(name="TEXT", dxfattribs={"color": 7})  # white
    if "LINES" not in doc.layers:
        doc.layers.new(name="LINES", dxfattribs={"color": 3})  # green

    width, height = _estimate_canvas_size(data)

    # Draw components as rectangles with labels
    for comp in data.get("components", []):
        attrs = comp.get("attributes", {})
        bbox = attrs.get("bbox_pixels")
        if not (isinstance(bbox, list) and len(bbox) == 4):
            continue
        x1, y1, x2, y2 = map(int, bbox)
        p1 = _img_to_dxf_coords(x1, y1, height)
        p2 = _img_to_dxf_coords(x2, y1, height)
        p3 = _img_to_dxf_coords(x2, y2, height)
        p4 = _img_to_dxf_coords(x1, y2, height)
        msp.add_lwpolyline([p1, p2, p3, p4, p1], dxfattribs={"layer": "COMPONENTS", "closed": True})
        # Label
        class_name = comp.get("component_class_name") or str(comp.get("component_class"))
        tag = comp.get("pid_tag") or ""
        label = f"{class_name} {tag}".strip()
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        tx, ty = _img_to_dxf_coords(cx, cy, height)
        txt = msp.add_text(label, dxfattribs={"layer": "TEXT", "height": 8})
        txt.dxf.insert = (tx, ty)

    # Draw connection lines: prefer connection_details, else detected_lines, else derive from connections_summary
    drew_any_line = False
    for conn in data.get("connection_details", []):
        coords = conn.get("line_coords")
        if isinstance(coords, (list, tuple)) and len(coords) == 4:
            x1, y1, x2, y2 = map(int, coords)
            p1 = _img_to_dxf_coords(x1, y1, height)
            p2 = _img_to_dxf_coords(x2, y2, height)
            msp.add_line(p1, p2, dxfattribs={"layer": "LINES"})
            drew_any_line = True

    if not drew_any_line:
        for line in data.get("detected_lines", []):
            start = line.get("start")
            end = line.get("end")
            if start and end and len(start) == 2 and len(end) == 2:
                x1, y1 = int(start[0]), int(end[1])  # will correct below
                # correct assignment
                x1, y1 = int(start[0]), int(start[1])
                x2, y2 = int(end[0]), int(end[1])
                p1 = _img_to_dxf_coords(x1, y1, height)
                p2 = _img_to_dxf_coords(x2, y2, height)
                msp.add_line(p1, p2, dxfattribs={"layer": "LINES"})
                drew_any_line = True

    if not drew_any_line:
        # Fallback: connect component centers from connections_summary
        id_to_center = {}
        for comp in data.get("components", []):
            attrs = comp.get("attributes", {})
            center = attrs.get("center")
            bbox = attrs.get("bbox_pixels")
            if center and len(center) == 2:
                id_to_center[comp["component_id"]] = (int(center[0]), int(center[1]))
            elif bbox and len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                id_to_center[comp["component_id"]] = (int((x1 + x2) / 2), int((y1 + y2) / 2))
        for cs in data.get("connections_summary", []):
            a, b = cs.get("from"), cs.get("to")
            if a in id_to_center and b in id_to_center:
                (x1, y1), (x2, y2) = id_to_center[a], id_to_center[b]
                p1 = _img_to_dxf_coords(x1, y1, height)
                p2 = _img_to_dxf_coords(x2, y2, height)
                msp.add_line(p1, p2, dxfattribs={"layer": "LINES"})

    # Save to bytes
    # ezdxf writes text content; use StringIO, then encode to bytes
    text_buf = io.StringIO()
    doc.write(text_buf)
    return text_buf.getvalue().encode("utf-8", errors="ignore")


