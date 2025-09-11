#!/usr/bin/env python3
"""
Test script for the chat endpoint
"""
import os
import sys
import json
import requests
from typing import Dict, Any

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chat_endpoint():
    """Test the chat endpoint with sample P&ID data"""
    
    # Sample P&ID data (simplified version of what the API would return)
    sample_pid_data = {
        "metadata": {
            "document_name": "test_pid.png",
            "summary": {
                "component_count": 5,
                "connection_count": 3,
                "review_required_count": 1,
                "warning_count": 0
            },
            "quality_metrics": {
                "avg_detection_confidence": 0.85,
                "tagged_components_ratio": 0.8,
                "connected_components_ratio": 0.6
            },
            "timings_ms": {
                "total": 2500
            },
            "status": "completed",
            "device": "cpu"
        },
        "components": [
            {
                "component_id": "symbol_1",
                "pid_tag": "P-101",
                "component_class_name": "Pump",
                "status": "OK",
                "attributes": {
                    "detection_confidence": 0.92,
                    "bbox_pixels": [100, 150, 200, 250]
                },
                "connections_to": ["symbol_2", "symbol_3"]
            },
            {
                "component_id": "symbol_2",
                "pid_tag": "V-101",
                "component_class_name": "Gate Valve",
                "status": "OK",
                "attributes": {
                    "detection_confidence": 0.88,
                    "bbox_pixels": [250, 150, 300, 200]
                },
                "connections_to": ["symbol_1", "symbol_4"]
            },
            {
                "component_id": "symbol_3",
                "pid_tag": "T-101",
                "component_class_name": "Tank",
                "status": "Review Required: Missing Tag",
                "attributes": {
                    "detection_confidence": 0.75,
                    "bbox_pixels": [400, 100, 500, 300]
                },
                "connections_to": ["symbol_1"]
            }
        ],
        "connections_summary": [
            {"from": "symbol_1", "to": "symbol_2", "status": "OK"},
            {"from": "symbol_1", "to": "symbol_3", "status": "OK"},
            {"from": "symbol_2", "to": "symbol_4", "status": "OK"}
        ]
    }
    
    # Test questions
    test_questions = [
        "How many components are detected in this P&ID?",
        "What is the average detection confidence?",
        "Which components need review?",
        "What is the pump connected to?",
        "How many connections are there in total?"
    ]
    
    # API endpoint
    base_url = "http://localhost:8000"
    chat_url = f"{base_url}/api/chat"
    
    print("Testing Chat Endpoint")
    print("=" * 50)
    
    # Check if server is running
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server health check failed")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Make sure the FastAPI server is running on http://localhost:8000")
        return
    
    # Test each question
    for i, question in enumerate(test_questions, 1):
        print(f"\nTest {i}: {question}")
        print("-" * 40)
        
        try:
            response = requests.post(
                chat_url,
                json={
                    "question": question,
                    "context_json": sample_pid_data
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response: {data['response']}")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_chat_endpoint()
