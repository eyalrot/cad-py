#!/usr/bin/env python3
"""
CAD-PY Backend Test Script
Tests all backend functionality including API endpoints, database, and Redis connectivity.
"""

import json
import requests
import sys
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 5

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message: str, status: str = "INFO"):
    color = Colors.BLUE
    if status == "PASS":
        color = Colors.GREEN
    elif status == "FAIL":
        color = Colors.RED
    elif status == "WARN":
        color = Colors.YELLOW
    
    print(f"{color}[{status}]{Colors.END} {message}")

def test_endpoint(method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> Dict[str, Any]:
    """Test an API endpoint and return response data."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=TIMEOUT)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == expected_status:
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.content else {}
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text
            }
    
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Run all backend tests."""
    print_status("Starting CAD-PY Backend Tests", "INFO")
    print("=" * 50)
    
    passed_tests = 0
    total_tests = 0
    
    # Test 1: Health Check
    total_tests += 1
    print_status("Testing health endpoint...")
    result = test_endpoint("GET", "/health")
    if result["success"] and result["data"].get("status") == "healthy":
        print_status("✓ Health check passed", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Health check failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 2: Root Endpoint
    total_tests += 1
    print_status("Testing root endpoint...")
    result = test_endpoint("GET", "/")
    if result["success"] and result["data"].get("status") == "running":
        print_status("✓ Root endpoint passed", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Root endpoint failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 3: Info Endpoint
    total_tests += 1
    print_status("Testing info endpoint...")
    result = test_endpoint("GET", "/info")
    if result["success"] and "features" in result["data"]:
        features = result["data"]["features"]
        print_status(f"✓ Info endpoint passed ({len(features)} features listed)", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Info endpoint failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 4: Status Endpoint
    total_tests += 1
    print_status("Testing status endpoint...")
    result = test_endpoint("GET", "/api/v1/status")
    if result["success"] and result["data"].get("status") == "operational":
        services = result["data"].get("services", {})
        print_status(f"✓ Status endpoint passed (API: {services.get('api')}, DB: {services.get('database')}, Redis: {services.get('redis')})", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Status endpoint failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 5: List Documents
    total_tests += 1
    print_status("Testing list documents endpoint...")
    result = test_endpoint("GET", "/api/v1/documents")
    if result["success"] and "documents" in result["data"]:
        docs = result["data"]["documents"]
        print_status(f"✓ List documents passed ({len(docs)} documents found)", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ List documents failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 6: Get Default Document
    total_tests += 1
    print_status("Testing get document endpoint...")
    result = test_endpoint("GET", "/api/v1/documents/default")
    if result["success"] and result["data"].get("id") == "default":
        layers = result["data"].get("layers", [])
        print_status(f"✓ Get document passed ({len(layers)} layers found)", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Get document failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 7: Create Document
    total_tests += 1
    print_status("Testing create document endpoint...")
    test_doc = {"name": "Test Document"}
    result = test_endpoint("POST", "/api/v1/documents", test_doc)
    if result["success"] and result["data"].get("status") == "created":
        print_status("✓ Create document passed", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Create document failed: {result.get('error', 'Unknown error')}", "FAIL")
    
    # Test 8: Get Non-existent Document (should return 404)
    total_tests += 1
    print_status("Testing non-existent document endpoint...")
    result = test_endpoint("GET", "/api/v1/documents/nonexistent", expected_status=404)
    if result["success"]:
        print_status("✓ Non-existent document test passed (404 returned)", "PASS")
        passed_tests += 1
    else:
        print_status(f"✗ Non-existent document test failed: expected 404, got {result.get('status_code')}", "FAIL")
    
    # Test 9: Interactive API Documentation
    total_tests += 1
    print_status("Testing API documentation endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=TIMEOUT)
        if response.status_code == 200:
            print_status("✓ API docs endpoint accessible", "PASS")
            passed_tests += 1
        else:
            print_status(f"✗ API docs endpoint failed: {response.status_code}", "FAIL")
    except Exception as e:
        print_status(f"✗ API docs endpoint failed: {e}", "FAIL")
    
    # Summary
    print("\n" + "=" * 50)
    print_status(f"Tests completed: {passed_tests}/{total_tests} passed", "INFO")
    
    if passed_tests == total_tests:
        print_status("🎉 All tests passed! Backend is fully functional.", "PASS")
        return 0
    else:
        print_status(f"⚠️  {total_tests - passed_tests} test(s) failed. Please check the backend.", "WARN")
        return 1

if __name__ == "__main__":
    sys.exit(main())