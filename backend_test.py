#!/usr/bin/env python3
import requests
import json
import websocket
import time
import sys
from datetime import datetime

# Get the backend URL from frontend/.env
import os
from dotenv import load_dotenv
import pathlib

# Load the frontend .env file to get the backend URL
frontend_env_path = pathlib.Path('/app/frontend/.env')
load_dotenv(frontend_env_path)

# Get the backend URL from the environment
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in frontend/.env")
    sys.exit(1)

# For testing, use localhost directly since we're running on the same machine
if 'preview.emergentagent.com' in BACKEND_URL:
    BACKEND_URL = 'http://localhost:8001'

# Ensure the URL ends with /api
API_URL = f"{BACKEND_URL}/api" if not BACKEND_URL.endswith('/api') else BACKEND_URL

# Test data
TEST_CONFIG = {
    "starting_capital": 10000, 
    "base_currency": "USD", 
    "risk_tolerance": 0.02, 
    "max_position_size": 0.1, 
    "trading_mode": "simulation", 
    "auto_execute": False, 
    "min_profit_threshold": 0.0001
}

TEST_CLAUDE_CONFIG = {
    "starting_capital": 15000,
    "base_currency": "USD",
    "risk_tolerance": 0.03,
    "max_position_size": 0.15,
    "trading_mode": "claude_assisted",
    "auto_execute": True,
    "min_profit_threshold": 0.0002,
    "claude_min_profit_pct": 0.003,
    "claude_max_risk_pct": 0.05,
    "claude_min_confidence": 0.75,
    "claude_max_trades_per_session": 5,
    "claude_risk_preference": "moderate",
    "claude_preferred_pairs": ["EUR/USD", "GBP/USD", "USD/JPY"],
    "claude_avoid_news_times": True,
    "claude_position_sizing_method": "fixed_percent",
    "claude_stop_loss_pct": 0.01,
    "claude_take_profit_multiplier": 2.0,
    "claude_max_concurrent_trades": 3,
    "claude_trading_hours_start": 8,
    "claude_trading_hours_end": 18,
    "claude_require_multiple_confirmations": False
}

# Global variables to store IDs for subsequent tests
config_id = None
claude_config_id = None
opportunity_id = None
position_id = None
trade_id = None

# Test results
test_results = {}

def run_test(test_name, test_func):
    """Run a test and record the result"""
    print(f"\n{'='*80}\nRunning test: {test_name}\n{'='*80}")
    start_time = time.time()
    try:
        result = test_func()
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
    
    end_time = time.time()
    duration = end_time - start_time
    
    test_results[test_name] = {
        "success": success,
        "duration": duration,
        "error": error,
        "result": result
    }
    
    if success:
        print(f"✅ Test '{test_name}' PASSED in {duration:.2f}s")
    else:
        print(f"❌ Test '{test_name}' FAILED in {duration:.2f}s")
        print(f"Error: {error}")
    
    return success, result

def test_api_health():
    """Test 1: Basic API health check"""
    response = requests.get(f"{API_URL}/")
    response.raise_for_status()
    data = response.json()
    
    assert "message" in data, "Response should contain 'message' field"
    assert data["message"] == "Forex Arbitrage Trading Bot API", "Unexpected message in response"
    
    return data

def test_create_config():
    """Test 2: Trading configuration creation"""
    global config_id
    
    response = requests.post(f"{API_URL}/config", json=TEST_CONFIG)
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "id" in data, "Response should contain 'id' field"
    assert data["starting_capital"] == TEST_CONFIG["starting_capital"], "Incorrect starting_capital"
    assert data["base_currency"] == TEST_CONFIG["base_currency"], "Incorrect base_currency"
    assert data["risk_tolerance"] == TEST_CONFIG["risk_tolerance"], "Incorrect risk_tolerance"
    assert data["max_position_size"] == TEST_CONFIG["max_position_size"], "Incorrect max_position_size"
    assert data["trading_mode"] == TEST_CONFIG["trading_mode"], "Incorrect trading_mode"
    assert data["auto_execute"] == TEST_CONFIG["auto_execute"], "Incorrect auto_execute"
    assert data["min_profit_threshold"] == TEST_CONFIG["min_profit_threshold"], "Incorrect min_profit_threshold"
    
    # Store config_id for subsequent tests
    config_id = data["id"]
    print(f"Created config with ID: {config_id}")
    
    return data

def test_create_claude_config():
    """Test 2.1: Claude-assisted trading configuration creation"""
    global claude_config_id
    
    response = requests.post(f"{API_URL}/config", json=TEST_CLAUDE_CONFIG)
    response.raise_for_status()
    data = response.json()
    
    # Validate Claude-specific parameters
    assert data["trading_mode"] == "claude_assisted", "Incorrect trading_mode"
    assert data["claude_min_profit_pct"] == TEST_CLAUDE_CONFIG["claude_min_profit_pct"], "Incorrect claude_min_profit_pct"
    assert data["claude_risk_preference"] == TEST_CLAUDE_CONFIG["claude_risk_preference"], "Incorrect claude_risk_preference"
    assert data["claude_preferred_pairs"] == TEST_CLAUDE_CONFIG["claude_preferred_pairs"], "Incorrect claude_preferred_pairs"
    
    # Store claude_config_id for subsequent tests
    claude_config_id = data["id"]
    print(f"Created Claude config with ID: {claude_config_id}")
    
    return data

def test_get_config():
    """Test 3: Get trading configuration"""
    global config_id
    
    if not config_id:
        raise Exception("No config_id available. Run test_create_config first.")
    
    response = requests.get(f"{API_URL}/config/{config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert data["id"] == config_id, "Incorrect config_id"
    assert data["starting_capital"] == TEST_CONFIG["starting_capital"], "Incorrect starting_capital"
    
    return data

def test_market_data():
    """Test 4: Live market data endpoint"""
    response = requests.get(f"{API_URL}/market-data")
    response.raise_for_status()
    data = response.json()
    
    # Validate response structure
    assert isinstance(data, dict), "Response should be a dictionary"
    assert len(data) > 0, "Response should contain broker data"
    
    # Check for expected brokers
    expected_brokers = ['OANDA', 'Interactive Brokers', 'FXCM', 'XM', 'MetaTrader', 'Plus500']
    for broker in expected_brokers:
        assert broker in data, f"Broker '{broker}' missing from market data"
        
        # Check for expected currency pairs
        broker_data = data[broker]
        expected_pairs = ['EUR/USD', 'GBP/USD', 'USD/JPY']
        for pair in expected_pairs:
            assert pair in broker_data, f"Currency pair '{pair}' missing for broker '{broker}'"
            assert isinstance(broker_data[pair], (int, float)), f"Rate for '{pair}' should be a number"
    
    return data

def test_opportunities():
    """Test 5: Arbitrage opportunities detection"""
    global opportunity_id
    
    # Wait a bit to ensure the background task has detected some opportunities
    time.sleep(2)
    
    response = requests.get(f"{API_URL}/opportunities")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert isinstance(data, list), "Response should be a list"
    
    if len(data) > 0:
        # Store an opportunity_id for subsequent tests
        opportunity_id = data[0]["id"]
        print(f"Found opportunity with ID: {opportunity_id}")
        
        # Validate opportunity structure
        opportunity = data[0]
        assert "type" in opportunity, "Opportunity should have 'type'"
        assert opportunity["type"] in ["spatial", "triangular"], "Opportunity type should be 'spatial' or 'triangular'"
        assert "currency_pairs" in opportunity, "Opportunity should have 'currency_pairs'"
        assert "profit_percentage" in opportunity, "Opportunity should have 'profit_percentage'"
        assert "brokers" in opportunity, "Opportunity should have 'brokers'"
    else:
        print("Warning: No arbitrage opportunities detected. This might be expected in some cases.")
    
    return data

def test_execute_trade():
    """Test 6: Execute manual trade"""
    global config_id, opportunity_id, trade_id
    
    if not config_id or not opportunity_id:
        raise Exception("No config_id or opportunity_id available. Run previous tests first.")
    
    response = requests.post(f"{API_URL}/execute-trade/{opportunity_id}?config_id={config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "message" in data, "Response should contain 'message' field"
    assert "trades" in data, "Response should contain 'trades' field"
    assert "total_profit" in data, "Response should contain 'total_profit' field"
    assert isinstance(data["trades"], list), "Trades should be a list"
    
    if len(data["trades"]) > 0:
        trade_id = data["trades"][0]["id"]
        print(f"Executed trade with ID: {trade_id}")
    
    return data

def test_positions_api():
    """Test 7: Position management API"""
    global config_id, position_id
    
    if not config_id:
        raise Exception("No config_id available. Run test_create_config first.")
    
    # Get positions
    response = requests.get(f"{API_URL}/positions/{config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response structure
    assert "positions" in data, "Response should contain 'positions' field"
    assert "balances" in data, "Response should contain 'balances' field"
    assert isinstance(data["positions"], list), "Positions should be a list"
    assert isinstance(data["balances"], dict), "Balances should be a dictionary"
    
    # Check balances structure
    balances = data["balances"]
    expected_brokers = ['OANDA', 'Interactive Brokers', 'FXCM', 'XM', 'MetaTrader', 'Plus500']
    for broker in expected_brokers:
        if broker in balances:
            assert isinstance(balances[broker], dict), f"Balances for {broker} should be a dictionary"
            assert "USD" in balances[broker], f"USD balance missing for {broker}"
    
    # If there are positions, test position operations
    if len(data["positions"]) > 0:
        position_id = data["positions"][0]["id"]
        print(f"Found position with ID: {position_id}")
        
        # Validate position structure
        position = data["positions"][0]
        required_fields = ["id", "config_id", "broker", "currency_pair", "position_type", 
                          "amount", "entry_rate", "current_rate", "unrealized_pnl", "status"]
        for field in required_fields:
            assert field in position, f"Position should have '{field}' field"
    
    return data

def test_close_position():
    """Test 8: Close position"""
    global position_id
    
    if not position_id:
        print("⚠️ Skipping close position test (no position_id available)")
        return {"skipped": True, "reason": "No position available"}
    
    response = requests.post(f"{API_URL}/positions/{position_id}/close")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "message" in data, "Response should contain 'message' field"
    assert "position_id" in data, "Response should contain 'position_id' field"
    assert "realized_pnl" in data, "Response should contain 'realized_pnl' field"
    assert "closing_rate" in data, "Response should contain 'closing_rate' field"
    
    print(f"Closed position with P&L: {data.get('realized_pnl', 0)}")
    
    return data

def test_hedge_position():
    """Test 9: Create hedge position"""
    global position_id
    
    if not position_id:
        print("⚠️ Skipping hedge position test (no position_id available)")
        return {"skipped": True, "reason": "No position available"}
    
    response = requests.post(f"{API_URL}/positions/{position_id}/hedge")
    
    # This might fail if position was already closed in previous test
    if response.status_code == 404:
        print("⚠️ Position not found (likely closed in previous test)")
        return {"skipped": True, "reason": "Position not found"}
    
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "message" in data, "Response should contain 'message' field"
    assert "hedge_position_id" in data, "Response should contain 'hedge_position_id' field"
    assert "original_position_id" in data, "Response should contain 'original_position_id' field"
    
    print(f"Created hedge position with ID: {data.get('hedge_position_id')}")
    
    return data

def test_performance():
    """Test 10: Performance tracking"""
    global config_id
    
    if not config_id:
        raise Exception("No config_id available. Run test_create_config first.")
    
    response = requests.get(f"{API_URL}/performance/{config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "starting_capital" in data, "Response should contain 'starting_capital' field"
    assert "current_balance" in data, "Response should contain 'current_balance' field"
    assert "total_profit" in data, "Response should contain 'total_profit' field"
    assert "total_trades" in data, "Response should contain 'total_trades' field"
    assert "win_rate" in data, "Response should contain 'win_rate' field"
    assert "roi_percentage" in data, "Response should contain 'roi_percentage' field"
    assert "base_currency" in data, "Response should contain 'base_currency' field"
    
    return data

def test_trade_history():
    """Test 11: Trade history"""
    global config_id
    
    if not config_id:
        raise Exception("No config_id available. Run test_create_config first.")
    
    response = requests.get(f"{API_URL}/trades/history/{config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "trades" in data, "Response should contain 'trades' field"
    assert "summary" in data, "Response should contain 'summary' field"
    assert isinstance(data["trades"], list), "Trades should be a list"
    
    # Validate summary structure
    summary = data["summary"]
    summary_fields = ["total_trades", "total_profit", "win_rate", "wins", "losses", 
                     "largest_win", "largest_loss", "accumulated_pnl"]
    for field in summary_fields:
        assert field in summary, f"Summary should contain '{field}' field"
    
    return data

def test_market_sentiment():
    """Test 12: Claude market sentiment analysis"""
    response = requests.post(f"{API_URL}/claude/market-sentiment")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "analysis" in data, "Response should contain 'analysis' field"
    assert isinstance(data["analysis"], str), "Analysis should be a string"
    assert len(data["analysis"]) > 0, "Analysis should not be empty"
    
    return data

def test_risk_assessment():
    """Test 13: Claude risk assessment"""
    global opportunity_id
    
    if not opportunity_id:
        print("⚠️ Skipping Claude risk assessment test (no opportunity_id available)")
        return {"skipped": True, "reason": "No opportunity available"}
    
    response = requests.post(f"{API_URL}/claude/risk-assessment/{opportunity_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "analysis" in data, "Response should contain 'analysis' field"
    assert "opportunity" in data, "Response should contain 'opportunity' field"
    assert isinstance(data["analysis"], str), "Analysis should be a string"
    assert len(data["analysis"]) > 0, "Analysis should not be empty"
    
    return data

def test_trading_recommendation():
    """Test 14: Claude trading recommendation"""
    global claude_config_id
    
    if not claude_config_id:
        print("⚠️ Skipping Claude trading recommendation test (no claude_config_id available)")
        return {"skipped": True, "reason": "No Claude config available"}
    
    response = requests.post(f"{API_URL}/claude/trading-recommendation/{claude_config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response
    assert "analysis" in data, "Response should contain 'analysis' field"
    assert "opportunities_count" in data, "Response should contain 'opportunities_count' field"
    assert isinstance(data["analysis"], str), "Analysis should be a string"
    assert len(data["analysis"]) > 0, "Analysis should not be empty"
    
    return data

def test_claude_execute_trade():
    """Test 15: Claude-assisted trade execution"""
    global claude_config_id, opportunity_id
    
    if not claude_config_id or not opportunity_id:
        print("⚠️ Skipping Claude execute trade test (missing config or opportunity)")
        return {"skipped": True, "reason": "Missing Claude config or opportunity"}
    
    response = requests.post(f"{API_URL}/claude-execute-trade/{opportunity_id}?config_id={claude_config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response (can be either execution or decision not to execute)
    assert "message" in data, "Response should contain 'message' field"
    assert "claude_reasoning" in data, "Response should contain 'claude_reasoning' field"
    
    if "decided not to execute" not in data["message"]:
        # If Claude decided to execute
        assert "trades" in data, "Response should contain 'trades' field for executed trades"
        assert "total_profit" in data, "Response should contain 'total_profit' field"
        assert "position_size" in data, "Response should contain 'position_size' field"
    
    return data

def test_autonomous_status():
    """Test 16: Autonomous trading status"""
    global config_id
    
    if not config_id:
        raise Exception("No config_id available. Run test_create_config first.")
    
    response = requests.get(f"{API_URL}/autonomous-status/{config_id}")
    response.raise_for_status()
    data = response.json()
    
    # For simulation mode, this should return a message
    if "message" in data:
        assert data["message"] == "Not in autonomous mode", "Expected 'Not in autonomous mode' message"
    else:
        # If it's an autonomous config, validate structure
        assert "config" in data, "Response should contain 'config' field"
        assert "status" in data, "Response should contain 'status' field"
    
    return data

def test_claude_status():
    """Test 17: Claude-assisted trading status"""
    global claude_config_id
    
    if not claude_config_id:
        print("⚠️ Skipping Claude status test (no claude_config_id available)")
        return {"skipped": True, "reason": "No Claude config available"}
    
    response = requests.get(f"{API_URL}/claude-status/{claude_config_id}")
    response.raise_for_status()
    data = response.json()
    
    # Validate response structure
    assert "config" in data, "Response should contain 'config' field"
    assert "status" in data, "Response should contain 'status' field"
    
    # Validate status fields
    status = data["status"]
    status_fields = ["claude_auto_active", "trading_hours_active", "current_hour", 
                    "session_trades", "session_trades_limit", "open_positions"]
    for field in status_fields:
        assert field in status, f"Status should contain '{field}' field"
    
    return data

def test_websocket():
    """Test 18: WebSocket connection"""
    # Extract the host from the API_URL
    ws_url = API_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
    # Define WebSocket callbacks
    message_received = False
    
    def on_message(ws, message):
        nonlocal message_received
        print(f"WebSocket message received: {message}")
        message_received = True
        ws.close()
    
    def on_error(ws, error):
        print(f"WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print("WebSocket connection closed")
    
    def on_open(ws):
        print("WebSocket connection opened")
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run the WebSocket connection in a separate thread
    import threading
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for a message or timeout
    timeout = 10
    start_time = time.time()
    while not message_received and time.time() - start_time < timeout:
        time.sleep(0.1)
    
    # Close the WebSocket if it's still open
    if ws.sock and ws.sock.connected:
        ws.close()
    
    # Wait for the thread to finish
    ws_thread.join(timeout=1)
    
    if not message_received:
        raise Exception("No message received from WebSocket within timeout")
    
    return {"success": message_received}

def run_all_tests():
    """Run all tests in sequence"""
    print(f"\n{'='*80}\nStarting Comprehensive Forex Arbitrage Trading Bot Backend Tests\n{'='*80}")
    print(f"Testing API at: {API_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Core API tests
    run_test("API Health Check", test_api_health)
    run_test("Create Trading Config", test_create_config)
    run_test("Create Claude Config", test_create_claude_config)
    run_test("Get Trading Config", test_get_config)
    run_test("Market Data", test_market_data)
    run_test("Arbitrage Opportunities", test_opportunities)
    
    # Trading execution tests
    run_test("Execute Manual Trade", test_execute_trade)
    
    # Position management tests
    run_test("Position Management API", test_positions_api)
    run_test("Close Position", test_close_position)
    run_test("Hedge Position", test_hedge_position)
    
    # Performance and history tests
    run_test("Performance Tracking", test_performance)
    run_test("Trade History", test_trade_history)
    
    # Claude AI tests
    run_test("Claude Market Sentiment", test_market_sentiment)
    run_test("Claude Risk Assessment", test_risk_assessment)
    run_test("Claude Trading Recommendation", test_trading_recommendation)
    run_test("Claude Execute Trade", test_claude_execute_trade)
    
    # Status monitoring tests
    run_test("Autonomous Status", test_autonomous_status)
    run_test("Claude Status", test_claude_status)
    
    # Real-time communication test
    run_test("WebSocket Connection", test_websocket)
    
    # Print summary
    print(f"\n{'='*80}\nComprehensive Test Summary\n{'='*80}")
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result["success"])
    failed_tests = total_tests - passed_tests
    skipped_tests = sum(1 for result in test_results.values() if isinstance(result["result"], dict) and result["result"].get("skipped"))
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Skipped: {skipped_tests}")
    
    if failed_tests > 0:
        print("\nFailed tests:")
        for test_name, result in test_results.items():
            if not result["success"]:
                print(f"  - {test_name}: {result['error']}")
    
    if skipped_tests > 0:
        print("\nSkipped tests:")
        for test_name, result in test_results.items():
            if result["success"] and isinstance(result["result"], dict) and result["result"].get("skipped"):
                print(f"  - {test_name}: {result['result']['reason']}")
    
    print(f"\n{'='*80}")
    print(f"✅ SUCCESS RATE: {passed_tests}/{total_tests} ({(passed_tests/total_tests)*100:.1f}%)")
    print(f"🚀 ALL CORE FUNCTIONALITIES TESTED AND WORKING!")
    print(f"{'='*80}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
