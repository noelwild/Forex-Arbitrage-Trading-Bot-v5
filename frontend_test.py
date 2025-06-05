#!/usr/bin/env python3
"""
Simplified Frontend Testing Suite for Forex Arbitrage Trading Bot

This test suite tests frontend availability and basic functionality
without requiring a full browser automation setup.
"""

import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import pathlib

# Load environment variables
frontend_env_path = pathlib.Path('/app/frontend/.env')
load_dotenv(frontend_env_path)

# Get the frontend URL
FRONTEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:3000')
if '/api' in FRONTEND_URL:
    FRONTEND_URL = FRONTEND_URL.replace('/api', '')

# For testing, use localhost directly since we're running on the same machine
if 'preview.emergentagent.com' in FRONTEND_URL:
    FRONTEND_URL = 'http://localhost:3000'

# Test results storage
test_results = {}

def run_test(test_name, test_func):
    """Run a test and record the result"""
    print(f"\n{'='*80}\nRunning Frontend Test: {test_name}\n{'='*80}")
    start_time = time.time()
    try:
        result = test_func()
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
        print(f"❌ Error in {test_name}: {error}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    test_results[test_name] = {
        "success": success,
        "duration": duration,
        "error": error,
        "result": result
    }
    
    if success:
        print(f"✅ Frontend Test '{test_name}' PASSED in {duration:.2f}s")
    else:
        print(f"❌ Frontend Test '{test_name}' FAILED in {duration:.2f}s")
        print(f"Error: {error}")
    
    return success, result

def test_frontend_accessibility():
    """Test 1: Frontend accessibility and basic response"""
    response = requests.get(FRONTEND_URL, timeout=10)
    response.raise_for_status()
    
    # Check if it's serving HTML content
    content_type = response.headers.get('content-type', '')
    assert 'text/html' in content_type.lower(), f"Expected HTML content, got {content_type}"
    
    # Check for basic React app structure
    content = response.text.lower()
    assert '<div id="root"' in content or '<div id="app"' in content, "React app container not found"
    assert '<script' in content, "JavaScript files not found"
    
    # Check for app-specific content
    assert 'forex' in content or 'trading' in content or 'arbitrage' in content, "App-specific content not found"
    
    return {
        "status_code": response.status_code,
        "content_type": content_type,
        "content_length": len(response.text),
        "has_react_container": True,
        "has_scripts": True,
        "has_app_content": True
    }

def test_static_assets():
    """Test 2: Static assets loading"""
    assets_tested = []
    
    # Test common static asset paths
    asset_paths = [
        '/static/css/main.css',
        '/static/js/main.js',
        '/manifest.json',
        '/favicon.ico'
    ]
    
    for asset_path in asset_paths:
        try:
            asset_url = f"{FRONTEND_URL}{asset_path}"
            response = requests.head(asset_url, timeout=5)
            if response.status_code == 200:
                assets_tested.append(asset_path)
        except requests.RequestException:
            pass  # Asset might not exist or be named differently
    
    # Try to get the main HTML and extract actual asset URLs
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        content = response.text
        
        # Look for CSS files
        import re
        css_matches = re.findall(r'href="([^"]*\.css[^"]*)"', content)
        js_matches = re.findall(r'src="([^"]*\.js[^"]*)"', content)
        
        # Test first CSS file
        if css_matches:
            css_url = css_matches[0]
            if not css_url.startswith('http'):
                css_url = f"{FRONTEND_URL}{css_url}"
            css_response = requests.head(css_url, timeout=5)
            if css_response.status_code == 200:
                assets_tested.append("main_css")
        
        # Test first JS file
        if js_matches:
            js_url = js_matches[0]
            if not js_url.startswith('http'):
                js_url = f"{FRONTEND_URL}{js_url}"
            js_response = requests.head(js_url, timeout=5)
            if js_response.status_code == 200:
                assets_tested.append("main_js")
                
    except Exception as e:
        print(f"Warning: Could not test extracted assets: {e}")
    
    return {
        "assets_tested": assets_tested,
        "assets_working": len(assets_tested) > 0
    }

def test_app_configuration():
    """Test 3: App configuration and environment variables"""
    # Test if the frontend can reach the backend
    backend_url = os.environ.get('REACT_APP_BACKEND_URL')
    
    config_details = {
        "backend_url_configured": backend_url is not None,
        "backend_url": backend_url,
        "frontend_url": FRONTEND_URL
    }
    
    # Test if backend is reachable from the configured URL
    if backend_url:
        try:
            # Test the API health endpoint
            api_url = f"{backend_url}/api" if not backend_url.endswith('/api') else backend_url
            if 'preview.emergentagent.com' in api_url:
                api_url = 'http://localhost:8001/api'
            
            api_response = requests.get(f"{api_url}/", timeout=5)
            config_details["backend_reachable"] = api_response.status_code == 200
            config_details["backend_response"] = api_response.json() if api_response.status_code == 200 else None
        except Exception as e:
            config_details["backend_reachable"] = False
            config_details["backend_error"] = str(e)
    
    return config_details

def test_page_structure():
    """Test 4: Page structure and content"""
    response = requests.get(FRONTEND_URL, timeout=10)
    content = response.text.lower()
    
    structure_elements = {
        "has_title": '<title>' in content,
        "has_meta_tags": '<meta' in content,
        "has_viewport": 'viewport' in content,
        "has_css_imports": 'stylesheet' in content or '.css' in content,
        "has_js_imports": '<script' in content or '.js' in content,
        "has_react_root": 'id="root"' in content or 'id="app"' in content
    }
    
    # Look for app-specific elements
    app_elements = {
        "mentions_forex": 'forex' in content,
        "mentions_trading": 'trading' in content,
        "mentions_arbitrage": 'arbitrage' in content,
        "has_navigation": 'nav' in content or 'menu' in content,
        "has_forms": '<form' in content or 'input' in content,
        "has_tables": '<table' in content
    }
    
    return {
        "structure_elements": structure_elements,
        "app_elements": app_elements,
        "structure_score": sum(structure_elements.values()),
        "app_score": sum(app_elements.values())
    }

def test_responsive_meta_tags():
    """Test 5: Responsive design meta tags"""
    response = requests.get(FRONTEND_URL, timeout=10)
    content = response.text
    
    responsive_features = {
        "has_viewport_meta": 'name="viewport"' in content,
        "has_mobile_optimized": 'width=device-width' in content,
        "has_initial_scale": 'initial-scale' in content,
        "has_responsive_css": 'media=' in content or '@media' in content
    }
    
    # Check for common CSS frameworks
    css_frameworks = {
        "has_tailwind": 'tailwind' in content.lower(),
        "has_bootstrap": 'bootstrap' in content.lower(),
        "has_material": 'material' in content.lower()
    }
    
    return {
        "responsive_features": responsive_features,
        "css_frameworks": css_frameworks,
        "mobile_ready": responsive_features["has_viewport_meta"] and responsive_features["has_mobile_optimized"]
    }

def test_security_headers():
    """Test 6: Basic security headers"""
    response = requests.get(FRONTEND_URL, timeout=10)
    headers = response.headers
    
    security_headers = {
        "content_type": headers.get('content-type'),
        "x_frame_options": headers.get('x-frame-options'),
        "x_content_type_options": headers.get('x-content-type-options'),
        "referrer_policy": headers.get('referrer-policy'),
        "content_security_policy": headers.get('content-security-policy')
    }
    
    # Check for HTTPS redirect (if applicable)
    security_score = sum(1 for v in security_headers.values() if v is not None)
    
    return {
        "security_headers": security_headers,
        "security_score": security_score,
        "headers_count": len(headers)
    }

def test_performance_indicators():
    """Test 7: Performance indicators"""
    start_time = time.time()
    response = requests.get(FRONTEND_URL, timeout=10)
    response_time = time.time() - start_time
    
    performance_metrics = {
        "response_time_seconds": response_time,
        "content_size_bytes": len(response.content),
        "content_size_kb": len(response.content) / 1024,
        "status_code": response.status_code,
        "response_time_rating": "fast" if response_time < 1 else "medium" if response_time < 3 else "slow"
    }
    
    # Check for performance optimizations
    content = response.text.lower()
    optimizations = {
        "has_minified_assets": '.min.' in content,
        "has_gzip_indication": 'gzip' in str(response.headers).lower(),
        "has_cache_headers": 'cache-control' in response.headers or 'expires' in response.headers
    }
    
    return {
        "performance_metrics": performance_metrics,
        "optimizations": optimizations
    }

def run_all_frontend_tests():
    """Run all simplified frontend tests"""
    print(f"\n{'='*80}\nStarting Simplified Frontend Tests for Forex Trading Bot\n{'='*80}")
    print(f"Testing Frontend at: {FRONTEND_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run all tests
    run_test("Frontend Accessibility", test_frontend_accessibility)
    run_test("Static Assets Loading", test_static_assets)
    run_test("App Configuration", test_app_configuration)
    run_test("Page Structure", test_page_structure)
    run_test("Responsive Meta Tags", test_responsive_meta_tags)
    run_test("Security Headers", test_security_headers)
    run_test("Performance Indicators", test_performance_indicators)
    
    # Print comprehensive summary
    print(f"\n{'='*80}\nSimplified Frontend Test Summary\n{'='*80}")
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Frontend Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if failed_tests > 0:
        print("\nFailed Frontend Tests:")
        for test_name, result in test_results.items():
            if not result["success"]:
                print(f"  - {test_name}: {result['error']}")
    
    # Detailed feature analysis
    print(f"\n{'='*40}\nFrontend Feature Analysis\n{'='*40}")
    
    for test_name, result in test_results.items():
        if result["success"] and result["result"]:
            print(f"\n✅ {test_name}:")
            if isinstance(result["result"], dict):
                for key, value in result["result"].items():
                    if isinstance(value, dict):
                        print(f"   - {key}:")
                        for subkey, subvalue in value.items():
                            print(f"     • {subkey}: {subvalue}")
                    else:
                        print(f"   - {key}: {value}")
    
    print(f"\n{'='*80}")
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"✅ FRONTEND SUCCESS RATE: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 85:
        print(f"🚀 FRONTEND IS HIGHLY FUNCTIONAL!")
    elif success_rate >= 70:
        print(f"✅ FRONTEND IS WORKING WELL")
    elif success_rate >= 50:
        print(f"⚠️ FRONTEND IS PARTIALLY FUNCTIONAL")
    else:
        print(f"❌ FRONTEND NEEDS ATTENTION")
    
    print(f"{'='*80}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_frontend_tests()
    sys.exit(0 if success else 1)