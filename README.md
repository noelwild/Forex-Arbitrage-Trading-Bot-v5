# 🚀 Forex Arbitrage Trading Bot

**An AI-Powered, Real-Time Forex Arbitrage Trading Platform with Claude AI Integration**

[![Status](https://img.shields.io/badge/Status-Production_Ready-green.svg)](https://github.com/noelwild/Forex-Arbitrage-Trading-Bot)
[![Tests](https://img.shields.io/badge/Backend_Tests-19/19_Passing-brightgreen.svg)](./test_result.md)
[![AI Integration](https://img.shields.io/badge/AI-Claude_3.5_Sonnet-blue.svg)](https://www.anthropic.com/)
[![Framework](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React_18-61DAFB.svg)](https://reactjs.org/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [API Keys & Accounts](#api-keys--accounts)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Trading Modes](#trading-modes)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## 🎯 Overview

This Forex Arbitrage Trading Bot is a sophisticated financial application that automatically detects and can execute arbitrage opportunities in the foreign exchange market. It combines real-time market data analysis, AI-powered decision making through Claude AI, and comprehensive risk management in a modern web application.

### Key Capabilities

- **🔍 Real-Time Arbitrage Detection**: Spatial and triangular arbitrage across multiple brokers
- **🧠 AI-Powered Trading**: Claude AI integration for intelligent market analysis and decision making
- **⚡ Live Data Streaming**: WebSocket-based real-time market data and opportunity updates
- **🛡️ Advanced Risk Management**: Multiple safety layers and configurable risk parameters
- **📊 Comprehensive Analytics**: Performance tracking, P&L analysis, and trade history
- **🎮 Multiple Trading Modes**: Simulation, Manual, Autonomous, and Claude-Assisted trading

---

## ✨ Features

### Trading Features
- **Spatial Arbitrage**: Detect price differences for the same currency pair across different brokers
- **Triangular Arbitrage**: Exploit rate inconsistencies in currency triangles (e.g., EUR/USD × USD/JPY ≠ EUR/JPY)
- **4 Trading Modes**: Simulation, Manual, Autonomous, Claude-Assisted
- **Real-Time Execution**: Sub-second opportunity detection and execution
- **Position Management**: Track open positions with real-time P&L updates

### AI Integration
- **Market Sentiment Analysis**: Claude AI analyzes current market conditions
- **Risk Assessment**: AI-powered risk evaluation for each trading opportunity
- **Trading Recommendations**: Intelligent suggestions based on user preferences
- **Autonomous Decision Making**: Claude can automatically execute trades based on your criteria

### Risk Management
- **Daily Loss Limits**: Automatic trading suspension if losses exceed thresholds
- **Position Size Controls**: Configurable maximum position sizes
- **Confidence Scoring**: Only execute high-confidence opportunities
- **Trading Hours**: Restrict trading to specific time windows
- **Concurrent Position Limits**: Control maximum open positions

### Analytics & Monitoring
- **Real-Time Dashboard**: Live performance metrics and opportunity tracking
- **Trade History**: Detailed transaction history with P&L tracking
- **Performance Analytics**: ROI, win rate, largest wins/losses
- **Live Market Data**: Real-time rates from multiple brokers

---

## 📋 Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows 10+
- **Node.js**: Version 18.0.0 or higher
- **Python**: Version 3.11 or higher
- **MongoDB**: Version 5.0 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB free space

### Development Tools
- **Git**: For repository cloning
- **Yarn**: Node.js package manager (preferred over npm)
- **pip**: Python package manager
- **Code Editor**: VS Code, PyCharm, or similar

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/noelwild/Forex-Arbitrage-Trading-Bot.git
cd Forex-Arbitrage-Trading-Bot
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Configure Environment Variables
```bash
# Copy and edit the environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env
```

**Required Environment Variables in `backend/.env`:**
```env
# Database Configuration
MONGO_URL="mongodb://localhost:27017"
DB_NAME="forex_arbitrage_db"

# AI Integration (Required for Claude features)
ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

### 3. Frontend Setup

#### Install Node.js Dependencies
```bash
cd ../frontend
yarn install
```

#### Configure Frontend Environment
```bash
# Edit the frontend environment file
nano .env
```

**Frontend Environment Variables in `frontend/.env`:**
```env
WDS_SOCKET_PORT=443
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 4. Database Setup

#### Start MongoDB
```bash
# Ubuntu/Debian
sudo systemctl start mongod

# macOS (if installed via Homebrew)
brew services start mongodb/brew/mongodb-community

# Windows (run as Administrator)
net start MongoDB
```

#### Verify MongoDB Connection
```bash
# Connect to MongoDB and verify
mongosh
> use forex_arbitrage_db
> db.stats()
> exit
```

### 5. Start the Application

#### Option A: Manual Start (Development)
```bash
# Terminal 1: Start Backend
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start Frontend
cd frontend
yarn start
```

#### Option B: Using Supervisor (Production-like)
```bash
# If using supervisor (Linux/macOS)
sudo supervisorctl restart all
```

### 6. Verify Installation

1. **Backend API**: Visit `http://localhost:8001/api/` - should return `{"message": "Forex Arbitrage Trading Bot API"}`
2. **Frontend App**: Visit `http://localhost:3000` - should show the trading dashboard
3. **WebSocket**: Check browser console for WebSocket connection messages

---

## 🔑 API Keys & Accounts

### Required API Keys

#### 1. Anthropic Claude API (Required for AI Features)

**Where to Get:**
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Sign up for an account or log in
3. Navigate to "API Keys" section
4. Click "Create New Key"
5. Name your key (e.g., "Forex Trading Bot")
6. Copy the key (starts with `sk-ant-`)

**Pricing Information:**
- **Free Tier**: $5 in free credits (enough for testing)
- **Pay-as-you-go**: ~$0.01-0.03 per request depending on model
- **Monthly Costs**: Typical usage $10-50/month depending on trading frequency

**Configuration:**
```env
ANTHROPIC_API_KEY="sk-ant-api03-YOUR-KEY-HERE"
```

**Features Enabled:**
- Market sentiment analysis
- Risk assessment for trades
- Trading recommendations
- Autonomous decision making

### Optional Broker API Keys (For Live Trading)

> **⚠️ IMPORTANT**: This application currently uses **simulated market data**. To trade with real money, you'll need to integrate with actual broker APIs.

#### Recommended Forex Brokers

1. **OANDA** (Recommended for beginners)
   - **Website**: [developer.oanda.com](https://developer.oanda.com/)
   - **Account Type**: Standard or Professional
   - **API Access**: Free with funded account
   - **Features**: REST API, streaming rates, demo accounts

2. **Interactive Brokers**
   - **Website**: [interactivebrokers.com](https://www.interactivebrokers.com/)
   - **Account Type**: Individual or Professional
   - **API Access**: TWS API (free)
   - **Features**: Advanced trading tools, low costs

3. **FXCM**
   - **Website**: [fxcm.com](https://www.fxcm.com/)
   - **Account Type**: Standard
   - **API Access**: REST API
   - **Features**: Social trading, market analysis

4. **XM**
   - **Website**: [xm.com](https://www.xm.com/)
   - **Account Type**: Micro, Standard, or XM Zero
   - **API Access**: MetaTrader API
   - **Features**: No minimum deposit, educational resources

#### Setting Up Broker Accounts

**Step 1: Choose Your Brokers**
- Start with 2-3 brokers to test arbitrage opportunities
- Ensure they offer API access
- Check their fee structures and minimum deposits

**Step 2: Account Registration**
1. Complete KYC (Know Your Customer) verification
2. Fund accounts with minimum required amounts
3. Request API access (usually requires account verification)

**Step 3: API Integration**
1. Obtain API credentials from each broker
2. Test API connections in sandbox/demo environments
3. Configure API keys in the application

**Step 4: Risk Management**
- Start with small amounts (under $1,000 per broker)
- Test in demo mode extensively before live trading
- Monitor performance closely during initial weeks

---

## ⚙️ Configuration

### Trading Configuration Options

#### Basic Settings
- **Starting Capital**: Amount available for trading ($1,000 - $1,000,000)
- **Base Currency**: Account currency (USD, EUR, GBP, JPY, etc.)
- **Risk Tolerance**: Percentage of capital at risk per trade (0.1% - 100%)
- **Max Position Size**: Maximum position as percentage of capital (1% - 50%)

#### Trading Mode Selection

**1. Simulation Mode** 📊
- **Purpose**: Risk-free testing and learning
- **Features**: 
  - Uses real market data patterns
  - No real money involved
  - Perfect for strategy testing
- **Recommended for**: Beginners, strategy development

**2. Manual Mode** 🖱️
- **Purpose**: Human-controlled trading
- **Features**:
  - Bot finds opportunities
  - You decide when to execute
  - Full control over every trade
- **Recommended for**: Experienced traders

**3. Autonomous Mode** 🤖
- **Purpose**: Fully automated mathematical trading
- **Features**:
  - Configurable profit thresholds (0.1% - 10%)
  - Risk limits per trade (1% - 10% of capital)
  - Daily loss limits (1% - 20%)
  - Hourly trade limits (1-100 trades)
- **Recommended for**: Systematic trading

**4. Claude-Assisted Mode** 🧠
- **Purpose**: AI-powered intelligent trading
- **Features**:
  - Market context analysis
  - Dynamic decision making
  - Risk-adjusted position sizing
  - Trading hours restrictions
- **Recommended for**: AI-enhanced trading

---

## 📖 Usage Guide

### Getting Started

#### 1. Initial Setup
1. **Start the Application**: Follow installation steps above
2. **Access Dashboard**: Navigate to `http://localhost:3000`
3. **Create Configuration**: Go to "Configuration" tab
4. **Set Basic Parameters**: Starting capital, currency, risk tolerance
5. **Choose Trading Mode**: Start with "Simulation" for safety

#### 2. Understanding the Dashboard

**Performance Overview**
- **Current Balance**: Your account balance including unrealized P&L
- **Total Profit**: Cumulative profit/loss from all trades
- **ROI**: Return on investment percentage
- **Win Rate**: Percentage of profitable trades

**Live Opportunities**
- **Type**: Spatial or Triangular arbitrage
- **Currency Pairs**: Involved currency pairs
- **Brokers**: Brokers offering the opportunity
- **Profit %**: Expected profit percentage
- **Confidence**: Algorithm confidence score (0-100%)

**Trading Controls**
- **Analyze Risk**: Get Claude's risk assessment
- **Execute Trade**: Manual trade execution
- **Ask Claude**: AI-assisted trade decision (Claude mode only)

#### 3. Using Claude AI Features

**Market Sentiment Analysis**
```bash
# Click "Get Market Sentiment" button
# Claude analyzes current market conditions
# Provides bullish/bearish/neutral assessment
# Includes risk factors and volatility analysis
```

**Risk Assessment**
```bash
# Click "Analyze Risk" for any opportunity
# Claude evaluates the specific trade
# Provides risk score (1-10 scale)
# Suggests optimal position sizing
# Recommends execute/skip decision
```

**Trading Recommendations**
```bash
# Click "Get Trading Advice" (requires configuration)
# Claude analyzes all current opportunities
# Ranks them by risk-adjusted returns
# Provides specific entry/exit strategies
# Follows your risk preferences exactly
```

---

## 🎮 Trading Modes

### 1. Simulation Mode 📊

**Purpose**: Risk-free learning and strategy testing

**Features**:
- Uses real market data patterns
- No actual money at risk
- Full functionality testing
- Performance tracking

**Best For**:
- New users learning the system
- Testing new strategies
- Understanding market dynamics
- Validating configuration settings

### 2. Manual Mode 🖱️

**Purpose**: Human-controlled trading decisions

**Features**:
- Bot detects opportunities
- User controls all executions
- Real-time alerts and notifications
- Full trade history tracking

**Best For**:
- Experienced traders who want control
- Learning market patterns
- Selective opportunity execution
- Building confidence before automation

### 3. Autonomous Mode 🤖

**Purpose**: Fully automated mathematical trading

**Features**:
- Algorithm-based decision making
- Configurable profit/risk thresholds
- Automatic position sizing
- Safety limits and controls

**Best For**:
- High-frequency trading
- Systematic approach
- Hands-off operation
- Consistent execution

### 4. Claude-Assisted Mode 🧠

**Purpose**: AI-powered intelligent trading

**Features**:
- Market context analysis
- Dynamic decision making
- Risk-adjusted position sizing
- Intelligent timing

**Best For**:
- AI-enhanced trading
- Market-aware decisions
- Dynamic risk adjustment
- Learning from AI insights

---

## 🧪 Testing

### Automated Testing

#### Backend Tests
```bash
cd backend
python backend_test.py
```

**Current Status**: 19/19 tests passing (100%)

**Test Coverage**:
- ✅ API Health Check
- ✅ Trading Configuration Management
- ✅ Market Data Simulation
- ✅ Arbitrage Opportunity Detection
- ✅ Claude AI Integration (all endpoints)
- ✅ Trade Execution (manual and Claude-assisted)
- ✅ WebSocket Connections
- ✅ Database Operations
- ✅ Performance Metrics
- ✅ Autonomous Trading Status

### Manual Testing

#### Testing Trading Modes

**1. Simulation Mode Testing**
```bash
1. Create configuration with simulation mode
2. Set starting capital to $10,000
3. Monitor for opportunities
4. Execute several trades manually
5. Verify no real money is involved
6. Check performance tracking
```

**2. Claude-Assisted Testing**
```bash
1. Configure Claude parameters
2. Enable auto-execution
3. Monitor Claude's decision making
4. Review Claude's reasoning for each trade
5. Verify AI follows your parameters
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'emergentintegrations'`
```bash
# Solution: Install emergentintegrations
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

**Error**: `MongoDB connection failed`
```bash
# Solution: Start MongoDB service
sudo systemctl start mongod

# Or check if MongoDB is running
sudo systemctl status mongod
```

#### 2. Claude AI Issues

**Error**: `Claude API key not configured`
```bash
# Solution: Add API key to backend/.env
echo 'ANTHROPIC_API_KEY="your-key-here"' >> backend/.env

# Restart backend
sudo supervisorctl restart backend
```

### Log Analysis

#### Important Log Locations
```bash
# Backend logs
/var/log/supervisor/backend.out.log  # Standard output
/var/log/supervisor/backend.err.log  # Error output

# Monitor real-time logs
tail -f /var/log/supervisor/backend.*.log
```

---

## 📞 Support

### Getting Help

#### Community Support
- **GitHub Issues**: [Report bugs or request features](https://github.com/noelwild/Forex-Arbitrage-Trading-Bot/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/noelwild/Forex-Arbitrage-Trading-Bot/discussions)

#### Quick Start Help
If you're having trouble getting started:
1. Check the [Prerequisites](#prerequisites) section
2. Follow the [Installation & Setup](#installation--setup) guide step by step
3. Verify your [API Keys & Accounts](#api-keys--accounts) are configured correctly
4. Run the automated tests to ensure everything is working

### Frequently Asked Questions

**Q: Is this safe to use with real money?**
A: Start with simulation mode and small amounts. This is educational software - always understand the risks of forex trading.

**Q: How much does it cost to run?**
A: The main cost is the Claude AI API (~$10-50/month depending on usage). Broker fees apply for live trading.

**Q: Does this guarantee profits?**
A: No. Arbitrage opportunities are rare and small. This is a tool for learning and experimentation, not guaranteed profits.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⚠️ Risk Disclaimer**: Forex trading involves substantial risk of loss and is not suitable for all investors. This software is for educational purposes only. Always trade responsibly and never risk more than you can afford to lose.

---

*Last updated: June 2025*
*Version: 1.0.0*
*Maintained by: Forex Trading Bot Community*
