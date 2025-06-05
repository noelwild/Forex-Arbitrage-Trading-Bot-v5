from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import logging
import os
import uuid
import math
from pathlib import Path
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage
from credential_models import (
    BrokerCredentials, CredentialCreateRequest, CredentialUpdateRequest,
    CredentialValidationResult, encrypt_data, decrypt_data,
    OANDACredentials, InteractiveBrokersCredentials, FXCMCredentials,
    XMCredentials, MetaTraderCredentials, AnthropicCredentials
)
from broker_connectors import create_broker_connector, test_fake_credentials

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Claude API Key
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Forex data simulation (placeholder for real forex APIs)
class ForexDataSimulator:
    def __init__(self):
        self.base_rates = {
            'EUR/USD': 1.0850,
            'GBP/USD': 1.2650,
            'USD/JPY': 155.50,
            'AUD/USD': 0.6320,
            'USD/CHF': 0.9180,
            'USD/CAD': 1.4150,
            'NZD/USD': 0.5680,
            'EUR/GBP': 0.8580,
            'EUR/JPY': 168.70,
            'GBP/JPY': 196.60,
            'AUD/JPY': 98.30,
            'CHF/JPY': 169.40,
            'CAD/JPY': 109.90,
        }
        
        self.brokers = ['OANDA', 'Interactive Brokers', 'FXCM', 'XM', 'MetaTrader', 'Plus500']
    
    def get_live_rates(self):
        """Simulate live forex rates with slight variations between brokers"""
        rates = {}
        for broker in self.brokers:
            broker_rates = {}
            for pair, base_rate in self.base_rates.items():
                # Add random variation (±0.0001 to ±0.0005)
                import random
                variation = random.uniform(-0.0005, 0.0005)
                broker_rates[pair] = round(base_rate + variation, 5)
            rates[broker] = broker_rates
        return rates

forex_sim = ForexDataSimulator()

# Database models for position management
class Position(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config_id: str
    broker: str
    currency_pair: str
    position_type: str  # 'long' or 'short'
    amount: float
    entry_rate: float
    current_rate: float = Field(default=0.0)
    unrealized_pnl: float = Field(default=0.0)
    status: str = Field(default="open")  # open, closed
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    realized_pnl: Optional[float] = None

class BrokerBalance(BaseModel):
    broker: str
    currency: str
    amount: float
    config_id: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)
class TradingConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    starting_capital: float
    base_currency: str
    risk_tolerance: float = Field(ge=0.01, le=1.0)  # 1% to 100%
    max_position_size: float = Field(ge=0.01, le=0.5)  # 1% to 50% of capital
    trading_mode: str = Field(default="simulation")  # simulation, manual, autonomous, claude_assisted
    auto_execute: bool = Field(default=False)
    min_profit_threshold: float = Field(default=0.0001)  # Minimum profit to execute (0.01%)
    
    # Autonomous trading parameters
    auto_min_profit_pct: float = Field(default=0.005)  # Minimum 0.5% profit for auto execution
    auto_max_risk_pct: float = Field(default=0.02)  # Maximum 2% of capital per auto trade
    auto_min_confidence: float = Field(default=0.8)  # Minimum 80% confidence score
    auto_max_trades_per_hour: int = Field(default=10)  # Maximum trades per hour
    auto_max_daily_loss: float = Field(default=0.05)  # Maximum 5% daily loss before stopping
    auto_preferred_pairs: List[str] = Field(default=['EUR/USD', 'GBP/USD', 'USD/JPY'])  # Preferred currency pairs
    auto_excluded_brokers: List[str] = Field(default=[])  # Brokers to exclude from auto trading
    auto_trade_spatial: bool = Field(default=True)  # Allow spatial arbitrage
    auto_trade_triangular: bool = Field(default=True)  # Allow triangular arbitrage
    auto_claude_confirmation: bool = Field(default=False)  # Require Claude confirmation for auto trades
    # Claude-assisted trading parameters
    claude_min_profit_pct: float = Field(default=0.003)  # Minimum 0.3% profit for Claude recommendations
    claude_max_risk_pct: float = Field(default=0.03)  # Maximum 3% of capital per Claude trade
    claude_min_confidence: float = Field(default=0.75)  # Minimum 75% confidence for Claude execution
    claude_max_trades_per_session: int = Field(default=5)  # Maximum trades per Claude session (hour)
    claude_risk_preference: str = Field(default="moderate")  # conservative, moderate, aggressive
    claude_preferred_pairs: List[str] = Field(default=['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD'])
    claude_avoid_news_times: bool = Field(default=True)  # Avoid trading during major news releases
    claude_position_sizing_method: str = Field(default="fixed_percent")  # fixed_percent, kelly_criterion, equal_weight
    claude_stop_loss_pct: float = Field(default=0.01)  # 1% stop loss
    claude_take_profit_multiplier: float = Field(default=2.0)  # Take profit at 2x stop loss
    claude_max_concurrent_trades: int = Field(default=3)  # Maximum concurrent open positions
    claude_trading_hours_start: int = Field(default=8)  # Start trading at 8 AM UTC
    claude_trading_hours_end: int = Field(default=18)  # Stop trading at 6 PM UTC
    claude_require_multiple_confirmations: bool = Field(default=False)  # Require multiple analysis cycles
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ArbitrageOpportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # 'spatial', 'triangular', 'statistical'
    currency_pairs: List[str]
    brokers: List[str]
    buy_broker: Optional[str] = None
    sell_broker: Optional[str] = None
    buy_rate: Optional[float] = None
    sell_rate: Optional[float] = None
    profit_potential: float
    profit_percentage: float
    position_size: float
    confidence_score: float
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    executed: bool = Field(default=False)
    execution_details: Optional[Dict[str, Any]] = None

class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config_id: str
    opportunity_id: str
    type: str  # 'spatial', 'triangular', 'statistical'
    currency_pairs: List[str]
    action: str  # 'buy', 'sell'
    broker: str
    amount: float
    rate: float
    profit: float
    status: str = Field(default="pending")  # pending, executed, failed
    execution_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClaudeAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    opportunity_id: Optional[str] = None
    analysis_type: str  # 'market_sentiment', 'risk_assessment', 'trade_recommendation'
    query: str
    response: str
    confidence: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ArbitrageEngine:
    def __init__(self):
        self.running = False
        self.opportunities = []
    
    def detect_spatial_arbitrage(self, rates_data):
        """Detect price differences for same pair across brokers"""
        opportunities = []
        
        # Use major pairs from forex provider
        major_pairs = [
            'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF', 
            'USD/CAD', 'NZD/USD', 'EUR/GBP', 'EUR/JPY', 'GBP/JPY',
            'AUD/JPY', 'CHF/JPY', 'CAD/JPY'
        ]
        
        for pair in major_pairs:
            broker_rates = [(broker, rates[pair]) for broker, rates in rates_data.items() if pair in rates]
            if len(broker_rates) < 2:
                continue
                
            min_rate = min(broker_rates, key=lambda x: x[1])
            max_rate = max(broker_rates, key=lambda x: x[1])
            
            # Calculate profit potential
            profit_potential = max_rate[1] - min_rate[1]
            profit_percentage = (profit_potential / min_rate[1]) * 100
            
            if profit_percentage > 0.001:  # Minimum 0.001% profit
                opportunity = ArbitrageOpportunity(
                    type="spatial",
                    currency_pairs=[pair],
                    brokers=[min_rate[0], max_rate[0]],
                    buy_broker=min_rate[0],
                    sell_broker=max_rate[0],
                    buy_rate=min_rate[1],
                    sell_rate=max_rate[1],
                    profit_potential=profit_potential,
                    profit_percentage=profit_percentage,
                    position_size=10000,  # Default position
                    confidence_score=0.85
                )
                opportunities.append(opportunity)
        
        return opportunities
    
    def detect_triangular_arbitrage(self, rates_data):
        """Detect triangular arbitrage opportunities"""
        opportunities = []
        
        # Example: EUR/USD * USD/JPY should equal EUR/JPY
        triangular_sets = [
            (['EUR/USD', 'USD/JPY', 'EUR/JPY'], 'EUR'),
            (['GBP/USD', 'USD/JPY', 'GBP/JPY'], 'GBP'),
            (['EUR/USD', 'EUR/GBP', 'GBP/USD'], 'USD'),
        ]
        
        for broker, rates in rates_data.items():
            for pairs, base_currency in triangular_sets:
                if all(pair in rates for pair in pairs):
                    # Calculate cross rate
                    if pairs == ['EUR/USD', 'USD/JPY', 'EUR/JPY']:
                        calculated_rate = rates['EUR/USD'] * rates['USD/JPY']
                        actual_rate = rates['EUR/JPY']
                        comparison_pair = 'EUR/JPY'
                    elif pairs == ['GBP/USD', 'USD/JPY', 'GBP/JPY']:
                        calculated_rate = rates['GBP/USD'] * rates['USD/JPY']
                        actual_rate = rates['GBP/JPY']
                        comparison_pair = 'GBP/JPY'
                    elif pairs == ['EUR/USD', 'EUR/GBP', 'GBP/USD']:
                        calculated_rate = rates['EUR/USD'] / rates['EUR/GBP']
                        actual_rate = rates['GBP/USD']
                        comparison_pair = 'GBP/USD'
                    
                    # Check for discrepancy
                    discrepancy = abs(calculated_rate - actual_rate)
                    profit_percentage = (discrepancy / actual_rate) * 100
                    
                    if profit_percentage > 0.002:  # Minimum 0.002% profit for triangular
                        opportunity = ArbitrageOpportunity(
                            type="triangular",
                            currency_pairs=pairs,
                            brokers=[broker],
                            profit_potential=discrepancy,
                            profit_percentage=profit_percentage,
                            position_size=10000,
                            confidence_score=0.75
                        )
                        opportunities.append(opportunity)
        
        return opportunities

arbitrage_engine = ArbitrageEngine()

# Claude Integration
class ClaudeAdvisor:
    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
    
    async def analyze_market_sentiment(self, market_data: Dict):
        """Get Claude's analysis of current market sentiment"""
        if not self.api_key:
            return "Claude API key not configured - using mock analysis: Current market sentiment appears bullish with EUR/USD showing strength against USD. Volatility is moderate across major pairs."
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"market_sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                system_message="You are an expert forex market analyst. Analyze market data and provide sentiment analysis."
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            query = f"""
            Analyze the current forex market data:
            {json.dumps(market_data, indent=2)}
            
            Provide:
            1. Overall market sentiment (bullish/bearish/neutral)
            2. Key currency trends
            3. Risk factors to consider
            4. Market volatility assessment
            
            Keep response concise but insightful.
            """
            
            user_message = UserMessage(text=query)
            response = await chat.send_message(user_message)
            return response
        except Exception as e:
            # Fallback to mock analysis if API fails
            return f"Claude API unavailable (Error: {str(e)}) - Mock Analysis: Market showing mixed signals with EUR/USD at current levels. Consider reduced position sizes due to API limitations."
    
    async def assess_arbitrage_risk(self, opportunity: ArbitrageOpportunity):
        """Get Claude's risk assessment for an arbitrage opportunity"""
        if not self.api_key:
            return f"Claude API key not configured - Mock Risk Assessment: {opportunity.type} arbitrage opportunity with {opportunity.profit_percentage:.4f}% profit potential. Risk Level: 3/10. Recommended position size: 5% of capital. Execute: Yes - Low risk opportunity."
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"risk_assessment_{opportunity.id}",
                system_message="You are an expert forex risk analyst. Assess arbitrage opportunities for potential risks and execution viability."
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            query = f"""
            Assess this arbitrage opportunity:
            
            Type: {opportunity.type}
            Currency Pairs: {opportunity.currency_pairs}
            Brokers: {opportunity.brokers}
            Profit Potential: {opportunity.profit_percentage:.4f}%
            Confidence Score: {opportunity.confidence_score}
            
            Provide:
            1. Risk assessment (1-10 scale, 10 being highest risk)
            2. Execution recommendations
            3. Potential pitfalls
            4. Optimal position sizing advice
            5. Should execute? (Yes/No/Caution)
            
            Be specific and actionable.
            """
            
            user_message = UserMessage(text=query)
            response = await chat.send_message(user_message)
            return response
        except Exception as e:
            return f"Claude API unavailable (Error: {str(e)}) - Mock Risk Assessment: {opportunity.type} opportunity showing {opportunity.profit_percentage:.4f}% profit. Risk: Moderate. Proceed with caution and smaller position size."
    
    async def get_trading_recommendation(self, opportunities: List[ArbitrageOpportunity], config: TradingConfig):
        """Get Claude's trading recommendations following user-defined parameters"""
        if not self.api_key:
            return f"Claude API key not configured - Mock Trading Recommendation: Based on {len(opportunities)} opportunities, recommend focusing on spatial arbitrage with {config.risk_tolerance*100}% risk tolerance. Start with 2-3 best opportunities with position sizes of {config.max_position_size*100}% max. Current market suitable for conservative approach."
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"trading_rec_{config.id}",
                system_message=f"""You are an expert forex trading advisor making decisions for a client with specific requirements. 
                
                STRICT PARAMETERS YOU MUST FOLLOW:
                - Only recommend trades with profit ≥ {config.claude_min_profit_pct * 100:.3f}%
                - Maximum risk per trade: {config.claude_max_risk_pct * 100:.1f}% of capital
                - Minimum confidence required: {config.claude_min_confidence * 100:.0f}%
                - Risk preference: {config.claude_risk_preference}
                - Position sizing method: {config.claude_position_sizing_method}
                - Stop loss: {config.claude_stop_loss_pct * 100:.1f}%
                - Take profit: {config.claude_take_profit_multiplier}x stop loss
                - Max concurrent trades: {config.claude_max_concurrent_trades}
                - Trading hours: {config.claude_trading_hours_start}:00 - {config.claude_trading_hours_end}:00 UTC
                - Preferred pairs: {', '.join(config.claude_preferred_pairs)}
                - Avoid news times: {'Yes' if config.claude_avoid_news_times else 'No'}
                
                You must STRICTLY adhere to these parameters. Do not recommend any trade that violates these rules."""
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            # Filter opportunities based on Claude's parameters
            filtered_opportunities = []
            for opp in opportunities[:10]:
                # Check if opportunity meets Claude's criteria
                profit_ok = (opp.profit_percentage / 100) >= config.claude_min_profit_pct
                confidence_ok = opp.confidence_score >= config.claude_min_confidence
                pair_ok = not config.claude_preferred_pairs or any(pair in opp.currency_pairs for pair in config.claude_preferred_pairs)
                
                if profit_ok and confidence_ok and pair_ok:
                    filtered_opportunities.append({
                        'id': opp.id,
                        'type': opp.type,
                        'pairs': opp.currency_pairs,
                        'profit_pct': opp.profit_percentage,
                        'confidence': opp.confidence_score,
                        'brokers': opp.brokers
                    })
            
            current_hour = datetime.utcnow().hour
            trading_hours_ok = config.claude_trading_hours_start <= current_hour <= config.claude_trading_hours_end
            
            query = f"""
            CLAUDE-ASSISTED TRADING ANALYSIS
            
            Trading Configuration:
            - Capital: {config.starting_capital} {config.base_currency}
            - Your risk preference: {config.claude_risk_preference}
            - Your max risk per trade: {config.claude_max_risk_pct * 100:.1f}%
            - Your min profit requirement: {config.claude_min_profit_pct * 100:.3f}%
            - Current time: {current_hour}:00 UTC (Trading hours: {config.claude_trading_hours_start}:00-{config.claude_trading_hours_end}:00)
            - Trading hours status: {'✅ WITHIN HOURS' if trading_hours_ok else '❌ OUTSIDE HOURS'}
            
            Pre-filtered Opportunities (meeting your criteria):
            {json.dumps(filtered_opportunities, indent=2) if filtered_opportunities else "No opportunities meet your strict criteria"}
            
            INSTRUCTIONS:
            1. If outside trading hours, recommend waiting
            2. Only recommend trades from the pre-filtered list
            3. Calculate position sizes using {config.claude_position_sizing_method} method
            4. Ensure stop loss at {config.claude_stop_loss_pct * 100:.1f}% and take profit at {config.claude_take_profit_multiplier}x stop loss
            5. Limit recommendations to max {config.claude_max_concurrent_trades} concurrent positions
            6. Be specific with entry/exit prices and position sizes
            7. Rank opportunities by risk-adjusted return
            
            Provide specific trading instructions following ALL your parameters.
            """
            
            user_message = UserMessage(text=query)
            response = await chat.send_message(user_message)
            return response
        except Exception as e:
            return f"Claude API unavailable (Error: {str(e)}) - Mock Recommendation: Focus on top 3 opportunities with conservative 2-5% position sizes. Monitor for 15-30 minutes before execution. Risk management: Stop loss at 1% total portfolio risk."
    
    async def claude_assisted_trade_decision(self, opportunity: ArbitrageOpportunity, config: TradingConfig):
        """Get Claude's specific decision on whether to execute a trade"""
        if not self.api_key:
            return {
                "decision": "execute" if opportunity.profit_percentage > 0.01 else "skip",
                "position_size": config.starting_capital * config.claude_max_risk_pct,
                "reasoning": "Mock decision - API not available"
            }
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"claude_decision_{opportunity.id}",
                system_message=f"""You are a forex trading AI making REAL MONEY DECISIONS. You must follow these EXACT parameters and provide a clear EXECUTE or SKIP decision.

MANDATORY REQUIREMENTS:
- Only EXECUTE if profit ≥ {config.claude_min_profit_pct * 100:.3f}%
- Only EXECUTE if confidence ≥ {config.claude_min_confidence * 100:.0f}%
- Max position size: {config.claude_max_risk_pct * 100:.1f}% of capital
- Risk preference: {config.claude_risk_preference}
- Must be in preferred pairs: {config.claude_preferred_pairs}
- Trading hours: {config.claude_trading_hours_start}:00-{config.claude_trading_hours_end}:00 UTC

CRITICAL: You must provide a clear decision. If ALL criteria are met, decide EXECUTE. If ANY criteria fails, decide SKIP.

Respond with JSON: {{"decision": "execute|skip", "position_size": dollar_amount, "reasoning": "detailed_explanation"}}"""
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            current_hour = datetime.utcnow().hour
            trading_hours_ok = config.claude_trading_hours_start <= current_hour <= config.claude_trading_hours_end
            
            # Check if opportunity meets basic criteria
            profit_ok = (opportunity.profit_percentage / 100) >= config.claude_min_profit_pct
            confidence_ok = opportunity.confidence_score >= config.claude_min_confidence
            pair_ok = not config.claude_preferred_pairs or any(pair in opportunity.currency_pairs for pair in config.claude_preferred_pairs)
            
            query = f"""
TRADE EXECUTION DECISION REQUIRED

Opportunity Analysis:
- Type: {opportunity.type}
- Currency Pairs: {opportunity.currency_pairs}
- Profit Potential: {opportunity.profit_percentage:.4f}%
- Confidence Score: {opportunity.confidence_score * 100:.0f}%
- Brokers: {opportunity.brokers}

CRITERIA VERIFICATION:
✅ Profit Requirement: {config.claude_min_profit_pct * 100:.3f}% | This trade: {opportunity.profit_percentage:.4f}% {'✅ PASS' if profit_ok else '❌ FAIL'}
✅ Confidence Requirement: {config.claude_min_confidence * 100:.0f}% | This trade: {opportunity.confidence_score * 100:.0f}% {'✅ PASS' if confidence_ok else '❌ FAIL'}
✅ Preferred Pairs: {config.claude_preferred_pairs} | This trade: {opportunity.currency_pairs} {'✅ PASS' if pair_ok else '❌ FAIL'}
✅ Trading Hours: {config.claude_trading_hours_start}-{config.claude_trading_hours_end} UTC | Current: {current_hour} UTC {'✅ PASS' if trading_hours_ok else '❌ FAIL'}

Account Details:
- Available Capital: {config.starting_capital} {config.base_currency}
- Max Position Size: {config.claude_max_risk_pct * 100:.1f}% = ${config.starting_capital * config.claude_max_risk_pct:.2f}
- Risk Preference: {config.claude_risk_preference}

DECISION REQUIRED:
If ALL criteria show ✅ PASS, then decision = "execute"
If ANY criteria shows ❌ FAIL, then decision = "skip"

Calculate exact position size and provide detailed reasoning.
Include specific numbers and explain your decision clearly.

Respond ONLY with valid JSON format.
"""
            
            user_message = UserMessage(text=query)
            response = await chat.send_message(user_message)
            
            # Try to parse JSON response
            try:
                import json
                decision_data = json.loads(response.strip())
                
                # Ensure position size doesn't exceed limits
                max_position = config.starting_capital * config.claude_max_risk_pct
                if decision_data.get("position_size", 0) > max_position:
                    decision_data["position_size"] = max_position
                
                return decision_data
            except:
                # Fallback parsing if JSON fails
                response_lower = response.lower()
                if "execute" in response_lower and all([profit_ok, confidence_ok, pair_ok, trading_hours_ok]):
                    return {
                        "decision": "execute",
                        "position_size": config.starting_capital * config.claude_max_risk_pct,
                        "reasoning": f"All criteria met. Profit: {opportunity.profit_percentage:.4f}%, Confidence: {opportunity.confidence_score * 100:.0f}%"
                    }
                else:
                    return {
                        "decision": "skip",
                        "position_size": 0,
                        "reasoning": "Failed to parse Claude response or criteria not met"
                    }
                
        except Exception as e:
            return {
                "decision": "skip",
                "position_size": 0,
                "reasoning": f"Claude API error: {str(e)}"
            }

claude_advisor = ClaudeAdvisor()

# WebSocket Manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Background task for continuous arbitrage detection
async def arbitrage_monitor():
    while True:
        try:
            # Get live rates
            rates_data = forex_sim.get_live_rates()
            
            # Detect opportunities
            spatial_ops = arbitrage_engine.detect_spatial_arbitrage(rates_data)
            triangular_ops = arbitrage_engine.detect_triangular_arbitrage(rates_data)
            
            all_opportunities = spatial_ops + triangular_ops
            
            # Sort by profit potential
            all_opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
            
            # Store in global state (in production, use Redis/cache)
            arbitrage_engine.opportunities = all_opportunities[:20]  # Keep top 20
            
            # Check for autonomous trading execution
            await check_autonomous_trading(all_opportunities)
            
            # Broadcast to connected clients
            if all_opportunities:
                # Convert opportunities to dict with JSON-serializable datetime
                opportunities_data = []
                for opp in all_opportunities[:10]:
                    opp_dict = opp.dict()
                    # Convert datetime to ISO string
                    if 'detected_at' in opp_dict:
                        opp_dict['detected_at'] = opp_dict['detected_at'].isoformat()
                    opportunities_data.append(opp_dict)
                
                await manager.broadcast(json.dumps({
                    'type': 'opportunities_update',
                    'data': opportunities_data
                }))
            
            await asyncio.sleep(1)  # Check every second
            
        except Exception as e:
            logging.error(f"Error in arbitrage monitor: {e}")
            await asyncio.sleep(5)

async def check_autonomous_trading(opportunities):
    """Check and execute autonomous trades based on user criteria"""
    try:
        # Get all autonomous trading configs
        autonomous_configs = await db.trading_configs.find({
            "trading_mode": "autonomous", 
            "auto_execute": True
        }).to_list(100)
        
        # Get all Claude-assisted configs that should auto-execute
        claude_configs = await db.trading_configs.find({
            "trading_mode": "claude_assisted", 
            "auto_execute": True
        }).to_list(100)
        
        # Process autonomous configs
        for config_data in autonomous_configs:
            config = TradingConfig(**config_data)
            await process_autonomous_config(config, opportunities)
        
        # Process Claude-assisted configs
        for config_data in claude_configs:
            config = TradingConfig(**config_data)
            await process_claude_assisted_config(config, opportunities)
            
    except Exception as e:
        logger.error(f"Error in autonomous trading check: {e}")

async def process_autonomous_config(config, opportunities):
    """Process autonomous trading for a specific config"""
    try:
        # Check daily loss limit
        daily_loss = await get_daily_loss(config.id)
        if daily_loss >= config.auto_max_daily_loss * config.starting_capital:
            logger.info(f"Daily loss limit reached for config {config.id}, skipping auto trades")
            return
        
        # Check hourly trade limit
        hourly_trades = await get_hourly_trade_count(config.id)
        if hourly_trades >= config.auto_max_trades_per_hour:
            logger.info(f"Hourly trade limit reached for config {config.id}, skipping auto trades")
            return
        
        # Filter opportunities based on criteria
        eligible_opportunities = []
        for opp in opportunities:
            if await is_opportunity_eligible(opp, config):
                eligible_opportunities.append(opp)
        
        # Execute eligible opportunities
        for opp in eligible_opportunities[:3]:  # Limit to top 3 per cycle
            try:
                if config.auto_claude_confirmation:
                    # Get Claude confirmation
                    claude_analysis = await claude_advisor.assess_arbitrage_risk(opp)
                    if "execute: yes" not in claude_analysis.lower() and "yes" not in claude_analysis.lower():
                        continue
                
                # Execute the trade
                await execute_autonomous_trade(opp, config)
                logger.info(f"Executed autonomous trade for opportunity {opp.id}")
                
            except Exception as e:
                logger.error(f"Error executing autonomous trade: {e}")
                
    except Exception as e:
        logger.error(f"Error in autonomous config processing: {e}")

async def process_claude_assisted_config(config, opportunities):
    """Process Claude-assisted automatic trading for a specific config"""
    try:
        # Check session limits (hourly for Claude)
        session_trades = await get_hourly_trade_count(config.id)
        if session_trades >= config.claude_max_trades_per_session:
            logger.info(f"Claude session trade limit reached for config {config.id}")
            return
        
        # Check trading hours
        current_hour = datetime.utcnow().hour
        if not (config.claude_trading_hours_start <= current_hour <= config.claude_trading_hours_end):
            logger.info(f"Outside Claude trading hours for config {config.id}")
            return
        
        # Get current open positions
        open_positions = await get_open_positions_count(config.id)
        if open_positions >= config.claude_max_concurrent_trades:
            logger.info(f"Max concurrent trades reached for Claude config {config.id}")
            return
        
        # Filter opportunities based on Claude's basic criteria first
        claude_eligible = []
        for opp in opportunities:
            if await is_claude_opportunity_eligible(opp, config):
                claude_eligible.append(opp)
        
        # Let Claude analyze and decide on top opportunities
        for opp in claude_eligible[:5]:  # Analyze top 5 opportunities
            try:
                # Get Claude's specific trading decision
                claude_decision = await claude_advisor.claude_assisted_trade_decision(opp, config)
                
                if claude_decision["decision"] == "execute":
                    # Execute the trade automatically
                    await execute_claude_assisted_trade(opp, config, claude_decision)
                    logger.info(f"Claude executed trade for opportunity {opp.id}: {claude_decision['reasoning']}")
                else:
                    logger.info(f"Claude skipped opportunity {opp.id}: {claude_decision['reasoning']}")
                    
            except Exception as e:
                logger.error(f"Error in Claude trade decision: {e}")
                
    except Exception as e:
        logger.error(f"Error in Claude-assisted config processing: {e}")

async def is_claude_opportunity_eligible(opportunity, config):
    """Check if an opportunity meets Claude's basic criteria"""
    # Check profit percentage
    if (opportunity.profit_percentage / 100) < config.claude_min_profit_pct:
        return False
    
    # Check confidence score
    if opportunity.confidence_score < config.claude_min_confidence:
        return False
    
    # Check preferred currency pairs
    if config.claude_preferred_pairs:
        pair_match = any(pair in opportunity.currency_pairs for pair in config.claude_preferred_pairs)
        if not pair_match:
            return False
    
    # Check if already executed
    if opportunity.executed:
        return False
    
    return True

async def execute_claude_assisted_trade(opportunity, config, claude_decision):
    """Execute a Claude-assisted trade"""
    position_value = claude_decision["position_size"]
    
    # Create trades
    trades = []
    current_time = datetime.utcnow()
    
    if opportunity.type == "spatial":
        # Buy trade
        buy_trade = Trade(
            config_id=config.id,
            opportunity_id=opportunity.id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="buy",
            broker=opportunity.buy_broker,
            amount=position_value,
            rate=opportunity.buy_rate,
            profit=0,
            status="executed",
            execution_time=current_time
        )
        
        # Sell trade
        sell_trade = Trade(
            config_id=config.id,
            opportunity_id=opportunity.id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="sell",
            broker=opportunity.sell_broker,
            amount=position_value,
            rate=opportunity.sell_rate,
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [buy_trade, sell_trade]
        
    elif opportunity.type == "triangular":
        trade = Trade(
            config_id=config.id,
            opportunity_id=opportunity.id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="triangular",
            broker=opportunity.brokers[0],
            amount=position_value,
            rate=1.0,
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [trade]
    
    # Store trades in database
    for trade in trades:
        await db.trades.insert_one(trade.dict())
    
    # Create position records for spatial arbitrage
    if opportunity.type == "spatial":
        # Create long position for buy side
        buy_position = Position(
            config_id=config.id,
            broker=opportunity.buy_broker,
            currency_pair=opportunity.currency_pairs[0],
            position_type="long",
            amount=position_value,
            entry_rate=opportunity.buy_rate,
            current_rate=opportunity.buy_rate
        )
        await db.positions.insert_one(buy_position.dict())
        
        # Create short position for sell side  
        sell_position = Position(
            config_id=config.id,
            broker=opportunity.sell_broker,
            currency_pair=opportunity.currency_pairs[0],
            position_type="short",
            amount=position_value,
            entry_rate=opportunity.sell_rate,
            current_rate=opportunity.sell_rate
        )
        await db.positions.insert_one(sell_position.dict())
    
    elif opportunity.type == "triangular":
        # For triangular arbitrage, create a synthetic position
        triangular_position = Position(
            config_id=config.id,
            broker=opportunity.brokers[0],
            currency_pair=','.join(opportunity.currency_pairs),  # Multi-pair position
            position_type="triangular",
            amount=position_value,
            entry_rate=1.0,  # Triangular uses calculated rates
            current_rate=1.0
        )
        await db.positions.insert_one(triangular_position.dict())
    
    # Mark opportunity as executed
    opportunity.executed = True
    opportunity.execution_details = {
        "config_id": config.id,
        "executed_at": current_time.isoformat(),
        "position_value": position_value,
        "trade_count": len(trades),
        "execution_type": "claude_assisted_auto",
        "claude_reasoning": claude_decision["reasoning"]
    }

async def get_open_positions_count(config_id):
    """Get number of currently open positions (simplified - assumes all recent trades are still open)"""
    # In a real system, this would track actual open/closed positions
    # For simulation, we'll count recent trades as "open" positions
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    count = await db.trades.count_documents({
        "config_id": config_id,
        "execution_time": {"$gte": one_hour_ago}
    })
    
    return count

async def is_opportunity_eligible(opportunity, config):
    """Check if an opportunity meets the autonomous trading criteria"""
    # Check profit percentage
    if opportunity.profit_percentage / 100 < config.auto_min_profit_pct:
        return False
    
    # Check confidence score
    if opportunity.confidence_score < config.auto_min_confidence:
        return False
    
    # Check trade type preferences
    if opportunity.type == "spatial" and not config.auto_trade_spatial:
        return False
    if opportunity.type == "triangular" and not config.auto_trade_triangular:
        return False
    
    # Check preferred currency pairs
    if config.auto_preferred_pairs:
        pair_match = any(pair in opportunity.currency_pairs for pair in config.auto_preferred_pairs)
        if not pair_match:
            return False
    
    # Check excluded brokers
    if config.auto_excluded_brokers:
        broker_excluded = any(broker in opportunity.brokers for broker in config.auto_excluded_brokers)
        if broker_excluded:
            return False
    
    # Check if already executed
    if opportunity.executed:
        return False
    
    return True

async def execute_autonomous_trade(opportunity, config):
    """Execute an autonomous trade"""
    # Calculate position size based on auto risk percentage
    position_value = config.starting_capital * config.auto_max_risk_pct
    
    # Create trades
    trades = []
    current_time = datetime.utcnow()
    
    if opportunity.type == "spatial":
        # Buy trade
        buy_trade = Trade(
            config_id=config.id,
            opportunity_id=opportunity.id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="buy",
            broker=opportunity.buy_broker,
            amount=position_value,
            rate=opportunity.buy_rate,
            profit=0,
            status="executed",
            execution_time=current_time
        )
        
        # Sell trade
        sell_trade = Trade(
            config_id=config.id,
            opportunity_id=opportunity.id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="sell",
            broker=opportunity.sell_broker,
            amount=position_value,
            rate=opportunity.sell_rate,
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [buy_trade, sell_trade]
        
    elif opportunity.type == "triangular":
        trade = Trade(
            config_id=config.id,
            opportunity_id=opportunity.id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="triangular",
            broker=opportunity.brokers[0],
            amount=position_value,
            rate=1.0,
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [trade]
    
    # Store trades in database
    for trade in trades:
        await db.trades.insert_one(trade.dict())
    
    # Mark opportunity as executed
    opportunity.executed = True
    opportunity.execution_details = {
        "config_id": config.id,
        "executed_at": current_time.isoformat(),
        "position_value": position_value,
        "trade_count": len(trades),
        "execution_type": "autonomous"
    }

async def get_daily_loss(config_id):
    """Get total loss for today"""
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    
    trades = await db.trades.find({
        "config_id": config_id,
        "execution_time": {"$gte": start_of_day},
        "profit": {"$lt": 0}
    }).to_list(1000)
    
    return sum(abs(trade.get('profit', 0)) for trade in trades)

async def get_hourly_trade_count(config_id):
    """Get number of trades in the last hour"""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    count = await db.trades.count_documents({
        "config_id": config_id,
        "execution_time": {"$gte": one_hour_ago}
    })
    
    return count

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Forex Arbitrage Trading Bot API"}

@api_router.post("/config", response_model=TradingConfig)
async def create_trading_config(config_data: dict):
    config = TradingConfig(**config_data)
    await db.trading_configs.insert_one(config.dict())
    return config

@api_router.get("/config/{config_id}", response_model=TradingConfig)
async def get_trading_config(config_id: str):
    config = await db.trading_configs.find_one({"id": config_id})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return TradingConfig(**config)

@api_router.get("/opportunities", response_model=List[ArbitrageOpportunity])
async def get_opportunities():
    return arbitrage_engine.opportunities

@api_router.get("/market-data")
async def get_market_data():
    return forex_sim.get_live_rates()

@api_router.post("/claude/market-sentiment")
async def get_market_sentiment():
    market_data = forex_sim.get_live_rates()
    analysis = await claude_advisor.analyze_market_sentiment(market_data)
    
    # Store analysis
    claude_analysis = ClaudeAnalysis(
        session_id=f"sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        analysis_type="market_sentiment",
        query="Market sentiment analysis",
        response=analysis
    )
    await db.claude_analyses.insert_one(claude_analysis.dict())
    
    return {"analysis": analysis}

@api_router.post("/claude/risk-assessment/{opportunity_id}")
async def get_risk_assessment(opportunity_id: str):
    # Find opportunity
    opportunity = next((opp for opp in arbitrage_engine.opportunities if opp.id == opportunity_id), None)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    analysis = await claude_advisor.assess_arbitrage_risk(opportunity)
    
    # Store analysis
    claude_analysis = ClaudeAnalysis(
        session_id=f"risk_{opportunity_id}",
        opportunity_id=opportunity_id,
        analysis_type="risk_assessment",
        query=f"Risk assessment for opportunity {opportunity_id}",
        response=analysis
    )
    await db.claude_analyses.insert_one(claude_analysis.dict())
    
    return {"analysis": analysis, "opportunity": opportunity.dict()}

@api_router.post("/claude/trading-recommendation/{config_id}")
async def get_trading_recommendation(config_id: str):
    # Get config
    config_data = await db.trading_configs.find_one({"id": config_id})
    if not config_data:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = TradingConfig(**config_data)
    opportunities = arbitrage_engine.opportunities
    
    analysis = await claude_advisor.get_trading_recommendation(opportunities, config)
    
    # Store analysis
    claude_analysis = ClaudeAnalysis(
        session_id=f"trading_rec_{config_id}",
        analysis_type="trade_recommendation",
        query=f"Trading recommendation for config {config_id}",
        response=analysis
    )
    await db.claude_analyses.insert_one(claude_analysis.dict())
    
    return {"analysis": analysis, "opportunities_count": len(opportunities)}

@api_router.post("/execute-trade/{opportunity_id}")
async def execute_trade(opportunity_id: str, config_id: str):
    """Execute a trade based on an arbitrage opportunity"""
    # Find opportunity
    opportunity = next((opp for opp in arbitrage_engine.opportunities if opp.id == opportunity_id), None)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Get config
    config_data = await db.trading_configs.find_one({"id": config_id})
    if not config_data:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = TradingConfig(**config_data)
    
    # Calculate position size based on config
    max_position_value = config.starting_capital * config.max_position_size
    risk_position_value = config.starting_capital * config.risk_tolerance
    position_value = min(max_position_value, risk_position_value * 10)  # Conservative sizing
    
    # Create trades for the arbitrage opportunity
    trades = []
    current_time = datetime.utcnow()
    
    if opportunity.type == "spatial":
        # Buy trade
        buy_trade = Trade(
            config_id=config_id,
            opportunity_id=opportunity_id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="buy",
            broker=opportunity.buy_broker,
            amount=position_value,
            rate=opportunity.buy_rate,
            profit=0,  # Will be calculated after both trades
            status="executed",
            execution_time=current_time
        )
        
        # Sell trade
        sell_trade = Trade(
            config_id=config_id,
            opportunity_id=opportunity_id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="sell",
            broker=opportunity.sell_broker,
            amount=position_value,
            rate=opportunity.sell_rate,
            profit=opportunity.profit_potential * (position_value / 10000),  # Scale profit to position size
            status="executed",
            execution_time=current_time
        )
        
        trades = [buy_trade, sell_trade]
        
    elif opportunity.type == "triangular":
        # Simplified triangular trade execution
        trade = Trade(
            config_id=config_id,
            opportunity_id=opportunity_id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="triangular",
            broker=opportunity.brokers[0],
            amount=position_value,
            rate=1.0,  # Triangular doesn't have single rate
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [trade]
    
    # Store trades in database
    for trade in trades:
        await db.trades.insert_one(trade.dict())
    
    # Mark opportunity as executed
    opportunity.executed = True
    opportunity.execution_details = {
        "config_id": config_id,
        "executed_at": current_time.isoformat(),
        "position_value": position_value,
        "trade_count": len(trades)
    }
    
    return {
        "message": "Trade executed successfully",
        "opportunity": opportunity.dict(),
        "trades": [trade.dict() for trade in trades],
        "total_profit": sum(trade.profit for trade in trades)
    }

@api_router.get("/trades/history/{config_id}")
async def get_trade_history(config_id: str):
    """Get detailed trade history with accumulated P&L"""
    # Get all trades for this config
    trades = await db.trades.find({"config_id": config_id}).sort("execution_time", 1).to_list(1000)
    
    if not trades:
        return {
            "trades": [],
            "summary": {
                "total_trades": 0,
                "total_profit": 0,
                "win_rate": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "accumulated_pnl": []
            }
        }
    
    # Calculate accumulated P&L and statistics
    accumulated_pnl = 0
    pnl_history = []
    wins = 0
    losses = 0
    largest_win = 0
    largest_loss = 0
    
    for trade in trades:
        profit = trade.get('profit', 0)
        accumulated_pnl += profit
        
        pnl_history.append({
            "trade_id": trade.get('id'),
            "execution_time": trade.get('execution_time'),
            "profit": profit,
            "accumulated_pnl": accumulated_pnl
        })
        
        if profit > 0:
            wins += 1
            largest_win = max(largest_win, profit)
        elif profit < 0:
            losses += 1
            largest_loss = min(largest_loss, profit)
    
    total_trades = len(trades)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    return {
        "trades": [Trade(**trade) for trade in trades],
        "summary": {
            "total_trades": total_trades,
            "total_profit": accumulated_pnl,
            "win_rate": win_rate,
            "wins": wins,
            "losses": losses,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "accumulated_pnl": pnl_history
        }
    }

@api_router.get("/performance/{config_id}")
async def get_performance(config_id: str):
    # Get config
    config_data = await db.trading_configs.find_one({"id": config_id})
    if not config_data:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = TradingConfig(**config_data)
    
    # Get trades
    trades = await db.trades.find({"config_id": config_id, "status": "executed"}).to_list(1000)
    
    total_profit = sum(trade.get('profit', 0) for trade in trades)
    total_trades = len(trades)
    win_rate = len([t for t in trades if t.get('profit', 0) > 0]) / max(total_trades, 1) * 100
    
    current_balance = config.starting_capital + total_profit
    roi_percentage = (total_profit / config.starting_capital) * 100
    
    return {
        "starting_capital": config.starting_capital,
        "current_balance": current_balance,
        "total_profit": total_profit,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "roi_percentage": roi_percentage,
        "base_currency": config.base_currency
    }

@api_router.post("/claude-execute-trade/{opportunity_id}")
async def claude_execute_trade(opportunity_id: str, config_id: str):
    """Execute a Claude-assisted trade with Claude's decision-making"""
    # Find opportunity
    opportunity = next((opp for opp in arbitrage_engine.opportunities if opp.id == opportunity_id), None)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Get config
    config_data = await db.trading_configs.find_one({"id": config_id})
    if not config_data:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = TradingConfig(**config_data)
    
    if config.trading_mode != "claude_assisted":
        raise HTTPException(status_code=400, detail="Config not in Claude-assisted mode")
    
    # Get Claude's decision
    claude_decision = await claude_advisor.claude_assisted_trade_decision(opportunity, config)
    
    if claude_decision["decision"] != "execute":
        return {
            "message": "Claude decided not to execute this trade",
            "claude_reasoning": claude_decision["reasoning"],
            "decision": claude_decision["decision"]
        }
    
    # Execute the trade with Claude's recommended position size
    position_value = claude_decision["position_size"]
    
    # Create trades
    trades = []
    current_time = datetime.utcnow()
    
    if opportunity.type == "spatial":
        # Buy trade
        buy_trade = Trade(
            config_id=config_id,
            opportunity_id=opportunity_id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="buy",
            broker=opportunity.buy_broker,
            amount=position_value,
            rate=opportunity.buy_rate,
            profit=0,
            status="executed",
            execution_time=current_time
        )
        
        # Sell trade
        sell_trade = Trade(
            config_id=config_id,
            opportunity_id=opportunity_id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="sell",
            broker=opportunity.sell_broker,
            amount=position_value,
            rate=opportunity.sell_rate,
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [buy_trade, sell_trade]
        
    elif opportunity.type == "triangular":
        trade = Trade(
            config_id=config_id,
            opportunity_id=opportunity_id,
            type=opportunity.type,
            currency_pairs=opportunity.currency_pairs,
            action="triangular",
            broker=opportunity.brokers[0],
            amount=position_value,
            rate=1.0,
            profit=opportunity.profit_potential * (position_value / 10000),
            status="executed",
            execution_time=current_time
        )
        
        trades = [trade]
    
    # Store trades in database
    for trade in trades:
        await db.trades.insert_one(trade.dict())
    
    # Mark opportunity as executed
    opportunity.executed = True
    opportunity.execution_details = {
        "config_id": config_id,
        "executed_at": current_time.isoformat(),
        "position_value": position_value,
        "trade_count": len(trades),
        "execution_type": "claude_assisted",
        "claude_reasoning": claude_decision["reasoning"]
    }
    
    return {
        "message": "Trade executed successfully with Claude's guidance",
        "claude_reasoning": claude_decision["reasoning"],
        "opportunity": opportunity.dict(),
        "trades": [trade.dict() for trade in trades],
        "total_profit": sum(trade.profit for trade in trades),
        "position_size": position_value
    }

@api_router.get("/autonomous-status/{config_id}")
async def get_autonomous_status(config_id: str):
    """Get autonomous trading status and statistics"""
    # Get config
    config_data = await db.trading_configs.find_one({"id": config_id})
    if not config_data:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = TradingConfig(**config_data)
    
    if config.trading_mode != "autonomous":
        return {"message": "Not in autonomous mode"}
    
    # Get current statistics
    daily_loss = await get_daily_loss(config_id)
    hourly_trades = await get_hourly_trade_count(config_id)
    
    # Get recent auto trades
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_trades = await db.trades.find({
        "config_id": config_id,
        "execution_time": {"$gte": one_hour_ago}
    }).sort("execution_time", -1).to_list(10)
    
    # Check if auto trading is currently active
    daily_loss_limit_hit = daily_loss >= config.auto_max_daily_loss * config.starting_capital
    hourly_limit_hit = hourly_trades >= config.auto_max_trades_per_hour
    
    return {
        "config": config.dict(),
        "status": {
            "auto_trading_active": config.auto_execute and not daily_loss_limit_hit and not hourly_limit_hit,
            "daily_loss": daily_loss,
            "daily_loss_limit": config.auto_max_daily_loss * config.starting_capital,
            "daily_loss_limit_hit": daily_loss_limit_hit,
            "hourly_trades": hourly_trades,
            "hourly_trades_limit": config.auto_max_trades_per_hour,
            "hourly_limit_hit": hourly_limit_hit
        },
        "recent_auto_trades": recent_trades
    }

@api_router.get("/claude-status/{config_id}")
async def get_claude_status(config_id: str):
    """Get Claude-assisted trading status and recent decisions"""
    # Get config
    config_data = await db.trading_configs.find_one({"id": config_id})
    if not config_data:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = TradingConfig(**config_data)
    
    if config.trading_mode != "claude_assisted":
        return {"message": "Not in Claude-assisted mode"}
    
    # Get current statistics
    session_trades = await get_hourly_trade_count(config_id)
    open_positions = await get_open_positions_count(config_id)
    
    # Get recent Claude trades
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_claude_trades = await db.trades.find({
        "config_id": config_id,
        "execution_time": {"$gte": one_hour_ago}
    }).sort("execution_time", -1).to_list(10)
    
    # Check if Claude auto trading is currently active
    current_hour = datetime.utcnow().hour
    trading_hours_ok = config.claude_trading_hours_start <= current_hour <= config.claude_trading_hours_end
    session_limit_hit = session_trades >= config.claude_max_trades_per_session
    concurrent_limit_hit = open_positions >= config.claude_max_concurrent_trades
    
    return {
        "config": config.dict(),
        "status": {
            "claude_auto_active": config.auto_execute and trading_hours_ok and not session_limit_hit and not concurrent_limit_hit,
            "trading_hours_active": trading_hours_ok,
            "current_hour": current_hour,
            "session_trades": session_trades,
            "session_trades_limit": config.claude_max_trades_per_session,
            "session_limit_hit": session_limit_hit,
            "open_positions": open_positions,
            "max_concurrent_trades": config.claude_max_concurrent_trades,
            "concurrent_limit_hit": concurrent_limit_hit
        },
        "recent_claude_trades": recent_claude_trades
    }

@api_router.get("/positions/{config_id}")
async def get_positions(config_id: str):
    """Get all positions and balances for a trading configuration"""
    # Get open positions
    positions_cursor = db.positions.find({"config_id": config_id, "status": "open"})
    positions_data = await positions_cursor.to_list(100)
    
    # Update current rates and unrealized P&L for each position
    current_rates = forex_sim.get_live_rates()
    updated_positions = []
    
    for pos_data in positions_data:
        position = Position(**pos_data)
        
        # Find current rate from any broker (using first available)
        current_rate = None
        for broker, rates in current_rates.items():
            if position.currency_pair in rates:
                current_rate = rates[position.currency_pair]
                break
        
        if current_rate:
            position.current_rate = current_rate
            
            # Calculate unrealized P&L
            if position.position_type == 'long':
                position.unrealized_pnl = (current_rate - position.entry_rate) * position.amount
            else:  # short
                position.unrealized_pnl = (position.entry_rate - current_rate) * position.amount
            
            # Update in database
            await db.positions.update_one(
                {"id": position.id},
                {"$set": {
                    "current_rate": position.current_rate,
                    "unrealized_pnl": position.unrealized_pnl
                }}
            )
        
        updated_positions.append(position)
    
    # Get broker balances
    balances_cursor = db.broker_balances.find({"config_id": config_id})
    balances_data = await balances_cursor.to_list(100)
    
    # Organize balances by broker
    balances = {}
    for balance in balances_data:
        broker = balance['broker']
        if broker not in balances:
            balances[broker] = {}
        balances[broker][balance['currency']] = balance['amount']
    
    # If no balances exist, create initial balances
    if not balances:
        config_data = await db.trading_configs.find_one({"id": config_id})
        if config_data:
            config = TradingConfig(**config_data)
            # Initialize balances for all brokers
            brokers = ['OANDA', 'Interactive Brokers', 'FXCM', 'XM', 'MetaTrader', 'Plus500']
            for broker in brokers:
                balances[broker] = {config.base_currency: config.starting_capital}
                # Store in database
                balance_doc = BrokerBalance(
                    broker=broker,
                    currency=config.base_currency,
                    amount=config.starting_capital,
                    config_id=config_id
                )
                await db.broker_balances.insert_one(balance_doc.dict())
    
    return {
        "positions": [pos.dict() for pos in updated_positions],
        "balances": balances
    }

@api_router.post("/positions/{position_id}/close")
async def close_position(position_id: str):
    """Close a specific position"""
    # Find the position
    position_data = await db.positions.find_one({"id": position_id, "status": "open"})
    if not position_data:
        raise HTTPException(status_code=404, detail="Position not found or already closed")
    
    position = Position(**position_data)
    
    # Get current rate
    current_rates = forex_sim.get_live_rates()
    current_rate = None
    for broker, rates in current_rates.items():
        if position.currency_pair in rates:
            current_rate = rates[position.currency_pair]
            break
    
    if not current_rate:
        raise HTTPException(status_code=400, detail="Unable to get current rate for position")
    
    # Calculate realized P&L
    if position.position_type == 'long':
        realized_pnl = (current_rate - position.entry_rate) * position.amount
    else:  # short
        realized_pnl = (position.entry_rate - current_rate) * position.amount
    
    # Update position as closed
    await db.positions.update_one(
        {"id": position_id},
        {"$set": {
            "status": "closed",
            "closed_at": datetime.utcnow(),
            "current_rate": current_rate,
            "realized_pnl": realized_pnl
        }}
    )
    
    # Update broker balance
    config_data = await db.trading_configs.find_one({"id": position.config_id})
    if config_data:
        config = TradingConfig(**config_data)
        
        # Add profit/loss to broker balance
        await db.broker_balances.update_one(
            {"broker": position.broker, "currency": config.base_currency, "config_id": position.config_id},
            {"$inc": {"amount": realized_pnl}},
            upsert=True
        )
    
    # Create a closing trade record
    closing_trade = Trade(
        config_id=position.config_id,
        opportunity_id=f"close_{position_id}",
        type="position_close",
        currency_pairs=[position.currency_pair],
        action="close",
        broker=position.broker,
        amount=position.amount,
        rate=current_rate,
        profit=realized_pnl,
        status="executed",
        execution_time=datetime.utcnow()
    )
    await db.trades.insert_one(closing_trade.dict())
    
    return {
        "message": "Position closed successfully",
        "position_id": position_id,
        "realized_pnl": realized_pnl,
        "closing_rate": current_rate
    }

@api_router.post("/positions/{position_id}/hedge")
async def hedge_position(position_id: str):
    """Create a hedge position for an existing position"""
    # Find the original position
    position_data = await db.positions.find_one({"id": position_id, "status": "open"})
    if not position_data:
        raise HTTPException(status_code=404, detail="Position not found or already closed")
    
    original_position = Position(**position_data)
    
    # Create opposite position with same amount
    hedge_type = 'short' if original_position.position_type == 'long' else 'long'
    
    # Get current rate
    current_rates = forex_sim.get_live_rates()
    current_rate = None
    for broker, rates in current_rates.items():
        if original_position.currency_pair in rates:
            current_rate = rates[original_position.currency_pair]
            break
    
    if not current_rate:
        raise HTTPException(status_code=400, detail="Unable to get current rate for hedge")
    
    # Create hedge position
    hedge_position = Position(
        config_id=original_position.config_id,
        broker=original_position.broker,  # Use same broker
        currency_pair=original_position.currency_pair,
        position_type=hedge_type,
        amount=original_position.amount,  # Same amount for perfect hedge
        entry_rate=current_rate,
        current_rate=current_rate,
        unrealized_pnl=0.0
    )
    
    # Store hedge position
    await db.positions.insert_one(hedge_position.dict())
    
    # Create a hedge trade record
    hedge_trade = Trade(
        config_id=original_position.config_id,
        opportunity_id=f"hedge_{position_id}",
        type="hedge",
        currency_pairs=[original_position.currency_pair],
        action=hedge_type,
        broker=original_position.broker,
        amount=original_position.amount,
        rate=current_rate,
        profit=0.0,  # Hedge should have neutral P&L initially
        status="executed",
        execution_time=datetime.utcnow()
    )
    await db.trades.insert_one(hedge_trade.dict())
    
    return {
        "message": "Hedge position created successfully",
        "hedge_position_id": hedge_position.id,
        "original_position_id": position_id,
        "hedge_type": hedge_type,
        "hedge_rate": current_rate
    }

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Start background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(arbitrage_monitor())

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
