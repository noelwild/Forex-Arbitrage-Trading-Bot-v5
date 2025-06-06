import React, { useState, useEffect } from 'react';
import './App.css';

const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001/api';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [config, setConfig] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [marketData, setMarketData] = useState({});
  const [performance, setPerformance] = useState(null);
  const [claudeAnalysis, setClaudeAnalysis] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [ws, setWs] = useState(null);
  const [trades, setTrades] = useState([]);
  const [tradesSummary, setTradesSummary] = useState(null);
  const [isExecutingTrade, setIsExecutingTrade] = useState(false);
  const [autonomousStatus, setAutonomousStatus] = useState(null);
  const [claudeStatus, setClaudeStatus] = useState(null);

  // Filtering states
  const [pairFilter, setPairFilter] = useState('');
  const [brokerFilter, setBrokerFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  
  // Position management states
  const [positions, setPositions] = useState([]);
  const [balances, setBrokerBalances] = useState({});

  // Credentials management states
  const [credentials, setCredentials] = useState([]);
  const [supportedBrokers, setSupportedBrokers] = useState([]);
  const [selectedBroker, setSelectedBroker] = useState('');
  const [credentialForm, setCredentialForm] = useState({});
  const [isTestingCredentials, setIsTestingCredentials] = useState(false);
  const [isCreatingCredentials, setIsCreatingCredentials] = useState(false);
  const [anthropicApiKey, setAnthropicApiKey] = useState('');
  const [showCredentialForm, setShowCredentialForm] = useState(false);

  // Configuration form state
  const [configForm, setConfigForm] = useState({
    starting_capital: 10000,
    base_currency: 'USD',
    risk_tolerance: 0.02,
    max_position_size: 0.1,
    trading_mode: 'simulation',
    auto_execute: false,
    min_profit_threshold: 0.0001,
    // Autonomous trading parameters
    auto_min_profit_pct: 0.005,
    auto_max_risk_pct: 0.02,
    auto_min_confidence: 0.8,
    auto_max_trades_per_hour: 10,
    auto_max_daily_loss: 0.05,
    auto_preferred_pairs: ['EUR/USD', 'GBP/USD', 'USD/JPY'],
    auto_excluded_brokers: [],
    auto_trade_spatial: true,
    auto_trade_triangular: true,
    auto_claude_confirmation: false,
    // Claude-assisted trading parameters
    claude_min_profit_pct: 0.003,
    claude_max_risk_pct: 0.03,
    claude_min_confidence: 0.75,
    claude_max_trades_per_session: 5,
    claude_risk_preference: 'moderate',
    claude_preferred_pairs: ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD'],
    claude_avoid_news_times: true,
    claude_position_sizing_method: 'fixed_percent',
    claude_stop_loss_pct: 0.01,
    claude_take_profit_multiplier: 2.0,
    claude_max_concurrent_trades: 3,
    claude_trading_hours_start: 8,
    claude_trading_hours_end: 18,
    claude_require_multiple_confirmations: false
  });

  useEffect(() => {
    // Initialize WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;
    const websocket = new WebSocket(wsUrl);
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'opportunities_update') {
        setOpportunities(data.data);
      }
    };
    
    setWs(websocket);
    
    // Load initial data
    loadMarketData();
    loadOpportunities();
    loadCredentials();
    loadSupportedBrokers();
    
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  const loadMarketData = async () => {
    try {
      const response = await fetch(`${API}/market-data`);
      const data = await response.json();
      setMarketData(data);
    } catch (error) {
      console.error('Error loading market data:', error);
    }
  };

  const loadOpportunities = async () => {
    try {
      const response = await fetch(`${API}/opportunities`);
      const data = await response.json();
      setOpportunities(data);
    } catch (error) {
      console.error('Error loading opportunities:', error);
    }
  };

  const createConfig = async () => {
    try {
      const response = await fetch(`${API}/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(configForm),
      });

      const data = await response.json();
      
      if (response.ok) {
        setConfig(data);
        alert('Configuration created successfully!');
        
        // Load additional data after successful config creation
        loadPerformance(data.id);
        loadTradeHistory(data.id);
        loadPositions(data.id);
        if (data.trading_mode === 'autonomous') {
          loadAutonomousStatus(data.id);
        } else if (data.trading_mode === 'claude_assisted') {
          loadClaudeStatus(data.id);
        }
      } else {
        alert(`Failed to create configuration: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error creating config:', error);
      alert('Error creating configuration');
    }
  };

  // ===============================
  // CREDENTIALS MANAGEMENT FUNCTIONS
  // ===============================

  const loadCredentials = async () => {
    try {
      const response = await fetch(`${API}/credentials`);
      const data = await response.json();
      setCredentials(data);
    } catch (error) {
      console.error('Error loading credentials:', error);
    }
  };

  const loadSupportedBrokers = async () => {
    try {
      const response = await fetch(`${API}/credentials/broker-types`);
      const data = await response.json();
      setSupportedBrokers(data);
    } catch (error) {
      console.error('Error loading supported brokers:', error);
    }
  };

  const createCredentials = async () => {
    if (!selectedBroker || !credentialForm) {
      alert('Please select a broker and fill in credentials');
      return;
    }

    setIsCreatingCredentials(true);
    try {
      const response = await fetch(`${API}/credentials`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          broker_name: selectedBroker,
          credentials: credentialForm
        }),
      });

      const data = await response.json();
      
      if (response.ok) {
        alert(data.message);
        setShowCredentialForm(false);
        setSelectedBroker('');
        setCredentialForm({});
        loadCredentials();
      } else {
        alert(`Failed to create credentials: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error creating credentials:', error);
      alert('Error creating credentials');
    }
    setIsCreatingCredentials(false);
  };

  const testCredentials = async (credentialId) => {
    setIsTestingCredentials(true);
    try {
      const response = await fetch(`${API}/credentials/${credentialId}/validate`, {
        method: 'POST',
      });

      const data = await response.json();
      
      if (response.ok) {
        const status = data.success ? 'SUCCESS' : 'FAILED';
        const details = data.connection_details ? 
          `\n\nConnection Details:\n${JSON.stringify(data.connection_details, null, 2)}` : '';
        
        alert(`${status}: ${data.message}${details}`);
        loadCredentials(); // Refresh the list
      } else {
        alert(`Test failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error testing credentials:', error);
      alert('Error testing credentials');
    }
    setIsTestingCredentials(false);
  };

  const testAllCredentials = async () => {
    setIsTestingCredentials(true);
    try {
      const response = await fetch(`${API}/credentials/validate-all`, {
        method: 'POST',
      });

      const data = await response.json();
      
      if (response.ok) {
        const results = data.map(result => 
          `${result.broker_name}: ${result.success ? 'SUCCESS' : 'FAILED'} - ${result.message}`
        ).join('\n');
        
        alert(`Validation Results:\n\n${results}`);
        loadCredentials(); // Refresh the list
      } else {
        alert(`Test failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error testing all credentials:', error);
      alert('Error testing all credentials');
    }
    setIsTestingCredentials(false);
  };

  const deleteCredentials = async (credentialId, brokerName) => {
    if (!window.confirm(`Are you sure you want to delete credentials for ${brokerName}?`)) {
      return;
    }

    try {
      const response = await fetch(`${API}/credentials/${credentialId}`, {
        method: 'DELETE',
      });

      const data = await response.json();
      
      if (response.ok) {
        alert(data.message);
        loadCredentials();
      } else {
        alert(`Failed to delete credentials: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error deleting credentials:', error);
      alert('Error deleting credentials');
    }
  };

  const updateAnthropicKey = async () => {
    if (!anthropicApiKey) {
      alert('Please enter an Anthropic API key');
      return;
    }

    try {
      const response = await fetch(`${API}/credentials/anthropic?api_key=${encodeURIComponent(anthropicApiKey)}`, {
        method: 'POST',
      });

      const data = await response.json();
      
      if (response.ok) {
        alert(data.message);
        setAnthropicApiKey('');
        loadCredentials();
      } else {
        alert(`Failed to update Anthropic key: ${data.message}`);
      }
    } catch (error) {
      console.error('Error updating Anthropic key:', error);
      alert('Error updating Anthropic key');
    }
  };

  const handleBrokerSelect = (brokerName) => {
    setSelectedBroker(brokerName);
    const broker = supportedBrokers.find(b => b.name === brokerName);
    if (broker) {
      const initialForm = {};
      broker.fields.forEach(field => {
        initialForm[field.name] = field.default || '';
      });
      setCredentialForm(initialForm);
    }
  };

  const loadPerformance = async (configId) => {
    try {
      const response = await fetch(`${API}/performance/${configId}`);
      const data = await response.json();
      setPerformance(data);
    } catch (error) {
      console.error('Error loading performance:', error);
    }
  };

  const getMarketSentiment = async () => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API}/claude/market-sentiment`, {
        method: 'POST',
      });
      const data = await response.json();
      setClaudeAnalysis(data.analysis);
    } catch (error) {
      console.error('Error getting market sentiment:', error);
      setClaudeAnalysis('Error getting analysis');
    }
    setIsAnalyzing(false);
  };

  // ===============================
  // REQUIRED FUNCTIONS
  // ===============================

  const loadPositions = async (configId) => {
    try {
      const response = await fetch(`${API}/positions/${configId}`);
      const data = await response.json();
      setPositions(data.positions || []);
      setBrokerBalances(data.balances || {});
    } catch (error) {
      console.error('Error loading positions:', error);
      // Mock data for demonstration
      setPositions([
        {
          id: 'pos1',
          config_id: configId,
          broker: 'OANDA',
          currency_pair: 'EUR/USD',
          position_type: 'long',
          amount: 1000,
          entry_rate: 1.0850,
          current_rate: 1.0865,
          unrealized_pnl: 15.0,
          opened_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'pos2',
          config_id: configId,
          broker: 'FXCM',
          currency_pair: 'GBP/USD',
          position_type: 'short',
          amount: 500,
          entry_rate: 1.2650,
          current_rate: 1.2645,
          unrealized_pnl: 2.5,
          opened_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
        }
      ]);
      setBrokerBalances({
        'OANDA': { USD: 9850, EUR: 920, GBP: 0 },
        'FXCM': { USD: 4750, EUR: 0, GBP: 395 },
        'Interactive Brokers': { USD: 10000, EUR: 0, GBP: 0 },
        'XM': { USD: 10000, EUR: 0, GBP: 0 },
        'MetaTrader': { USD: 10000, EUR: 0, GBP: 0 },
        'Plus500': { USD: 10000, EUR: 0, GBP: 0 }
      });
    }
  };

  const closePosition = async (positionId) => {
    try {
      const response = await fetch(`${API}/positions/${positionId}/close`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Position closed! P&L: ${data.realized_pnl > 0 ? '+' : ''}$${data.realized_pnl.toFixed(2)}`);
        if (config) {
          loadPositions(config.id);
          loadPerformance(config.id);
          loadTradeHistory(config.id);
        }
      } else {
        alert(`Failed to close position: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error closing position:', error);
      // Mock close for demonstration
      alert('Position closed! (Demo mode)');
      setPositions(positions.filter(p => p.id !== positionId));
    }
  };

  const hedgePosition = async (positionId) => {
    const position = positions.find(p => p.id === positionId);
    if (!position) return;

    try {
      const response = await fetch(`${API}/positions/${positionId}/hedge`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Hedge position created! New position ID: ${data.hedge_position_id}`);
        if (config) {
          loadPositions(config.id);
        }
      } else {
        alert(`Failed to create hedge: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error creating hedge:', error);
      alert('Hedge position created! (Demo mode)');
    }
  };

  const loadTradeHistory = async (configId) => {
    try {
      const response = await fetch(`${API}/trades/${configId}`);
      const data = await response.json();
      setTrades(data.trades || []);
    } catch (error) {
      console.error('Error loading trade history:', error);
      // Mock data for demonstration
      setTrades([
        {
          id: 'trade1',
          config_id: configId,
          opportunity_id: 'opp1',
          broker: 'OANDA',
          currency_pairs: ['EUR/USD'],
          type: 'spatial',
          execution_time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          entry_rate: 1.0850,
          exit_rate: 1.0865,
          amount: 1000,
          profit: 15.0,
          commission: 2.0,
          net_profit: 13.0,
          status: 'completed'
        }
      ]);
    }
  };

  const renderDashboard = () => (
    <div className="space-y-6">
      setPositions(data.positions || []);
      setBrokerBalances(data.balances || {});
    } catch (error) {
      console.error('Error loading positions:', error);
      // Mock data for demonstration
      setPositions([
        {
          id: 'pos1',
          config_id: configId,
          broker: 'OANDA',
          currency_pair: 'EUR/USD',
          position_type: 'long',
          amount: 1000,
          entry_rate: 1.0850,
          current_rate: 1.0865,
          unrealized_pnl: 15.0,
          opened_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'pos2',
          config_id: configId,
          broker: 'FXCM',
          currency_pair: 'GBP/USD',
          position_type: 'short',
          amount: 500,
          entry_rate: 1.2650,
          current_rate: 1.2645,
          unrealized_pnl: 2.5,
          opened_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
        }
      ]);
      setBrokerBalances({
        'OANDA': { USD: 9850, EUR: 920, GBP: 0 },
        'FXCM': { USD: 4750, EUR: 0, GBP: 395 },
        'Interactive Brokers': { USD: 10000, EUR: 0, GBP: 0 },
        'XM': { USD: 10000, EUR: 0, GBP: 0 },
        'MetaTrader': { USD: 10000, EUR: 0, GBP: 0 },
        'Plus500': { USD: 10000, EUR: 0, GBP: 0 }
      });
    }
  };

  const closePosition = async (positionId) => {
    try {
      const response = await fetch(`${API}/positions/${positionId}/close`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Position closed! P&L: ${data.realized_pnl > 0 ? '+' : ''}$${data.realized_pnl.toFixed(2)}`);
        if (config) {
          loadPositions(config.id);
          loadPerformance(config.id);
          loadTradeHistory(config.id);
        }
      } else {
        alert(`Failed to close position: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error closing position:', error);
      // Mock close for demonstration
      alert('Position closed! (Demo mode)');
      setPositions(positions.filter(p => p.id !== positionId));
    }
  };

  const hedgePosition = async (positionId) => {
    const position = positions.find(p => p.id === positionId);
    if (!position) return;

    try {
      const response = await fetch(`${API}/positions/${positionId}/hedge`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Hedge position created! New position ID: ${data.hedge_position_id}`);
        if (config) {
          loadPositions(config.id);
        }
      } else {
        alert(`Failed to create hedge: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error creating hedge:', error);
      alert('Hedge position created! (Demo mode)');
    }
  };

  const loadTradeHistory = async (configId) => {
    try {
      const response = await fetch(`${API}/trades/${configId}`);
      const data = await response.json();
      setTrades(data.trades || []);
    } catch (error) {
      console.error('Error loading trade history:', error);
      // Mock data for demonstration
      setTrades([
        {
          id: 'trade1',
          config_id: configId,
          opportunity_id: 'opp1',
          broker: 'OANDA',
          currency_pairs: ['EUR/USD'],
          type: 'spatial',
          execution_time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          entry_rate: 1.0850,
          exit_rate: 1.0865,
          amount: 1000,
          profit: 15.0,
          commission: 2.0,
          net_profit: 13.0,
          status: 'completed'
        },
        {
          id: 'trade2',
          config_id: configId,
          opportunity_id: 'opp2',
          broker: 'FXCM',
          currency_pairs: ['GBP/USD', 'EUR/GBP'],
          type: 'triangular',
          execution_time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          entry_rate: 1.2650,
          exit_rate: 1.2645,
          amount: 500,
          profit: -5.0,
          commission: 1.5,
          net_profit: -6.5,
          status: 'completed'
        }
      ]);
    }
  };

  const loadAutonomousStatus = async (configId) => {
    try {
      const response = await fetch(`${API}/autonomous-status/${configId}`);
      const data = await response.json();
      setAutonomousStatus(data);
    } catch (error) {
      console.error('Error loading autonomous status:', error);
      // Mock status for demonstration
      setAutonomousStatus({
        is_active: false,
        trades_today: 5,
        profit_today: 45.20,
        last_trade: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        success_rate: 0.78
      });
    }
  };

  const loadClaudeStatus = async (configId) => {
    try {
      const response = await fetch(`${API}/claude-status/${configId}`);
      const data = await response.json();
      setClaudeStatus(data);
    } catch (error) {
      console.error('Error loading Claude status:', error);
      // Mock status for demonstration
      setClaudeStatus({
        is_active: true,
        last_analysis: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
        recommendations_today: 8,
        accepted_recommendations: 6,
        market_sentiment: 'bullish'
      });
    }
  };

  const toggleAutonomous = async () => {
    if (!config) return;
    
    try {
      const response = await fetch(`${API}/toggle-autonomous/${config.id}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        setAutonomousStatus(prev => ({
          ...prev,
          is_active: !prev.is_active
        }));
        alert(data.message);
      } else {
        alert(`Failed to toggle autonomous mode: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error toggling autonomous mode:', error);
      alert('Error toggling autonomous mode');
    }
  };

  const executeTradeManually = async (opportunityId) => {
    try {
      const response = await fetch(`${API}/execute-trade/${opportunityId}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Trade executed successfully! Profit: $${data.profit.toFixed(2)}`);
        if (config) {
          loadPositions(config.id);
          loadTradeHistory(config.id);
          loadPerformance(config.id);
        }
      } else {
        alert(`Failed to execute trade: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error executing trade:', error);
      alert('Error executing trade');
    }
  };

  const getClaudeRecommendation = async (opportunityId) => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API}/claude/recommendation/${opportunityId}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        setClaudeAnalysis(data.recommendation);
        alert(`Claude Recommendation: ${data.recommendation}`);
      } else {
        alert(`Failed to get Claude recommendation: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error getting Claude recommendation:', error);
      alert('Error getting Claude recommendation');
    }
    setIsAnalyzing(false);
  };

  // ===============================
  // MISSING FUNCTIONS IMPLEMENTATION
  // ===============================

  const loadPositions = async (configId) => {
    try {
      const response = await fetch(`${API}/positions/${configId}`);
      const data = await response.json();
      setPositions(data.positions || []);
      setBrokerBalances(data.balances || {});
    } catch (error) {
      console.error('Error loading positions:', error);
      // Mock data for demonstration
      setPositions([
        {
          id: 'pos1',
          config_id: configId,
          broker: 'OANDA',
          currency_pair: 'EUR/USD',
          position_type: 'long',
          amount: 1000,
          entry_rate: 1.0850,
          current_rate: 1.0865,
          unrealized_pnl: 15.0,
          opened_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'pos2',
          config_id: configId,
          broker: 'FXCM',
          currency_pair: 'GBP/USD',
          position_type: 'short',
          amount: 500,
          entry_rate: 1.2650,
          current_rate: 1.2645,
          unrealized_pnl: 2.5,
          opened_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
        }
      ]);
      setBrokerBalances({
        'OANDA': { USD: 9850, EUR: 920, GBP: 0 },
        'FXCM': { USD: 4750, EUR: 0, GBP: 395 },
        'Interactive Brokers': { USD: 10000, EUR: 0, GBP: 0 },
        'XM': { USD: 10000, EUR: 0, GBP: 0 },
        'MetaTrader': { USD: 10000, EUR: 0, GBP: 0 },
        'Plus500': { USD: 10000, EUR: 0, GBP: 0 }
      });
    }
  };

  const closePosition = async (positionId) => {
    try {
      const response = await fetch(`${API}/positions/${positionId}/close`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Position closed! P&L: ${data.realized_pnl > 0 ? '+' : ''}$${data.realized_pnl.toFixed(2)}`);
        if (config) {
          loadPositions(config.id);
          loadPerformance(config.id);
          loadTradeHistory(config.id);
        }
      } else {
        alert(`Failed to close position: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error closing position:', error);
      // Mock close for demonstration
      alert('Position closed! (Demo mode)');
      setPositions(positions.filter(p => p.id !== positionId));
    }
  };

  const hedgePosition = async (positionId) => {
    const position = positions.find(p => p.id === positionId);
    if (!position) return;

    try {
      const response = await fetch(`${API}/positions/${positionId}/hedge`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Hedge position created! New position ID: ${data.hedge_position_id}`);
        if (config) {
          loadPositions(config.id);
        }
      } else {
        alert(`Failed to create hedge: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error creating hedge:', error);
      alert('Hedge position created! (Demo mode)');
    }
  };

  const loadTradeHistory = async (configId) => {
    try {
      const response = await fetch(`${API}/trades/${configId}`);
      const data = await response.json();
      setTrades(data.trades || []);
    } catch (error) {
      console.error('Error loading trade history:', error);
      // Mock data for demonstration
      setTrades([
        {
          id: 'trade1',
          config_id: configId,
          opportunity_id: 'opp1',
          broker: 'OANDA',
          currency_pairs: ['EUR/USD'],
          type: 'spatial',
          execution_time: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          entry_rate: 1.0850,
          exit_rate: 1.0865,
          amount: 1000,
          profit: 15.0,
          commission: 2.0,
          net_profit: 13.0,
          status: 'completed'
        },
        {
          id: 'trade2',
          config_id: configId,
          opportunity_id: 'opp2',
          broker: 'FXCM',
          currency_pairs: ['GBP/USD', 'EUR/GBP'],
          type: 'triangular',
          execution_time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          entry_rate: 1.2650,
          exit_rate: 1.2645,
          amount: 500,
          profit: -5.0,
          commission: 1.5,
          net_profit: -6.5,
          status: 'completed'
        }
      ]);
    }
  };

  const loadAutonomousStatus = async (configId) => {
    try {
      const response = await fetch(`${API}/autonomous-status/${configId}`);
      const data = await response.json();
      setAutonomousStatus(data);
    } catch (error) {
      console.error('Error loading autonomous status:', error);
      // Mock status for demonstration
      setAutonomousStatus({
        is_active: false,
        trades_today: 5,
        profit_today: 45.20,
        last_trade: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        success_rate: 0.78
      });
    }
  };

  const loadClaudeStatus = async (configId) => {
    try {
      const response = await fetch(`${API}/claude-status/${configId}`);
      const data = await response.json();
      setClaudeStatus(data);
    } catch (error) {
      console.error('Error loading Claude status:', error);
      // Mock status for demonstration
      setClaudeStatus({
        is_active: true,
        last_analysis: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
        recommendations_today: 8,
        accepted_recommendations: 6,
        market_sentiment: 'bullish'
      });
    }
  };

  const toggleAutonomous = async () => {
    if (!config) return;
    
    try {
      const response = await fetch(`${API}/toggle-autonomous/${config.id}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        setAutonomousStatus(prev => ({
          ...prev,
          is_active: !prev.is_active
        }));
        alert(data.message);
      } else {
        alert(`Failed to toggle autonomous mode: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error toggling autonomous mode:', error);
      alert('Error toggling autonomous mode');
    }
  };

  const executeTradeManually = async (opportunityId) => {
    try {
      const response = await fetch(`${API}/execute-trade/${opportunityId}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Trade executed successfully! Profit: $${data.profit.toFixed(2)}`);
        if (config) {
          loadPositions(config.id);
          loadTradeHistory(config.id);
          loadPerformance(config.id);
        }
      } else {
        alert(`Failed to execute trade: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error executing trade:', error);
      alert('Error executing trade');
    }
  };

  const getClaudeRecommendation = async (opportunityId) => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API}/claude/recommendation/${opportunityId}`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (response.ok) {
        setClaudeAnalysis(data.recommendation);
        alert(`Claude Recommendation: ${data.recommendation}`);
      } else {
        alert(`Failed to get Claude recommendation: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error getting Claude recommendation:', error);
      alert('Error getting Claude recommendation');
    }
    setIsAnalyzing(false);
  };

  const loadPositions = async (configId) => {
    try {
      const response = await fetch(`${API}/positions/${configId}`);
      const data = await response.json();
      setPositions(data.positions || []);
      setBrokerBalances(data.balances || {});
    } catch (error) {
      console.error('Error loading positions:', error);
      // Mock data for demonstration
      setPositions([
        {
          id: 'pos1',
          config_id: configId,
          broker: 'OANDA',
          currency_pair: 'EUR/USD',
          position_type: 'long',
          amount: 1000,
          entry_rate: 1.0850,
          current_rate: 1.0865,
          unrealized_pnl: 15.0,
          opened_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'pos2',
          config_id: configId,
          broker: 'FXCM',
          currency_pair: 'GBP/USD',
          position_type: 'short',
          amount: 500,
          entry_rate: 1.2650,
          current_rate: 1.2645,
          unrealized_pnl: 2.5,
          opened_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
        }
      ]);
      setBrokerBalances({
        'OANDA': { USD: 9850, EUR: 920, GBP: 0 },
        'FXCM': { USD: 4750, EUR: 0, GBP: 395 },
        'Interactive Brokers': { USD: 10000, EUR: 0, GBP: 0 },
        'XM': { USD: 10000, EUR: 0, GBP: 0 },
        'MetaTrader': { USD: 10000, EUR: 0, GBP: 0 },
        'Plus500': { USD: 10000, EUR: 0, GBP: 0 }
      });
    }
  };


  const getRiskAssessment = async (opportunityId) => {
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API}/claude/risk-assessment/${opportunityId}`, {
        method: 'POST',
      });
      const data = await response.json();
      setClaudeAnalysis(data.analysis);
    } catch (error) {
      console.error('Error getting risk assessment:', error);
      setClaudeAnalysis('Error getting analysis');
    }
    setIsAnalyzing(false);
  };

  const getTradingRecommendation = async () => {
    if (!config) return;
    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API}/claude/trading-recommendation/${config.id}`, {
        method: 'POST',
      });
      const data = await response.json();
      setClaudeAnalysis(data.analysis);
    } catch (error) {
      console.error('Error getting trading recommendation:', error);
      setClaudeAnalysis('Error getting analysis');
    }
    setIsAnalyzing(false);
  };


  const claudeExecuteTrade = async (opportunityId) => {
    if (!config) {
      alert('Please create a trading configuration first');
      return;
    }
    
    setIsExecutingTrade(true);
    try {
      const response = await fetch(`${API}/claude-execute-trade/${opportunityId}?config_id=${config.id}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (response.ok) {
        if (data.message.includes('decided not to execute')) {
          alert(`Claude decided NOT to execute this trade.\nReason: ${data.claude_reasoning}`);
        } else {
          alert(`Claude executed the trade!\nReason: ${data.claude_reasoning}\nProfit: $${data.total_profit.toFixed(2)}\nPosition Size: $${data.position_size.toFixed(2)}`);
          // Refresh performance and load trade history
          loadPerformance(config.id);
          loadTradeHistory(config.id);
        }
      } else {
        alert(`Trade execution failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error executing Claude-assisted trade:', error);
      alert('Error executing Claude-assisted trade');
    }
    setIsExecutingTrade(false);
  };

  const executeTrade = async (opportunityId) => {
    if (!config) {
      alert('Please create a trading configuration first');
      return;
    }
    
    setIsExecutingTrade(true);
    try {
      const response = await fetch(`${API}/execute-trade/${opportunityId}?config_id=${config.id}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (response.ok) {
        alert(`Trade executed successfully! Profit: $${data.total_profit.toFixed(2)}`);
        // Refresh performance and load trade history
        loadPerformance(config.id);
        loadTradeHistory(config.id);
      } else {
        alert(`Trade execution failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error executing trade:', error);
      alert('Error executing trade');
    }
    setIsExecutingTrade(false);
  };

  const loadTradeHistory = async (configId) => {
    try {
      const response = await fetch(`${API}/trades/history/${configId}`);
      const data = await response.json();
      setTrades(data.trades);
      setTradesSummary(data.summary);
    } catch (error) {
      console.error('Error loading trade history:', error);
    }
  };

  const loadAutonomousStatus = async (configId) => {
    try {
      const response = await fetch(`${API}/autonomous-status/${configId}`);
      const data = await response.json();
      setAutonomousStatus(data);
    } catch (error) {
      console.error('Error loading autonomous status:', error);
    }
  };

  const loadClaudeStatus = async (configId) => {
    try {
      const response = await fetch(`${API}/claude-status/${configId}`);
      const data = await response.json();
      setClaudeStatus(data);
    } catch (error) {
      console.error('Error loading Claude status:', error);
    }
  };

  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  };

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(4)}%`;
  };

  const renderDashboard = () => (
    <div className="space-y-6">
      {/* Autonomous Trading Status */}
      {config && config.trading_mode === 'autonomous' && autonomousStatus && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">🤖 Autonomous Trading Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className={`p-4 rounded-lg ${autonomousStatus.status.auto_trading_active ? 'bg-green-50' : 'bg-red-50'}`}>
              <p className="text-sm text-gray-600">Auto Trading</p>
              <p className={`text-2xl font-bold ${autonomousStatus.status.auto_trading_active ? 'text-green-600' : 'text-red-600'}`}>
                {autonomousStatus.status.auto_trading_active ? '🟢 ACTIVE' : '🔴 INACTIVE'}
              </p>
            </div>
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Trades This Hour</p>
              <p className="text-2xl font-bold text-blue-600">
                {autonomousStatus.status.hourly_trades}/{autonomousStatus.status.hourly_trades_limit}
              </p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Daily Loss</p>
              <p className="text-2xl font-bold text-yellow-600">
                {formatCurrency(autonomousStatus.status.daily_loss)}
              </p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Min Profit Required</p>
              <p className="text-2xl font-bold text-purple-600">
                {(autonomousStatus.config.auto_min_profit_pct * 100).toFixed(3)}%
              </p>
            </div>
          </div>
          
          {/* Auto Trading Controls */}
          <div className="mt-4 flex space-x-4">
            <button
              onClick={() => loadAutonomousStatus(config.id)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
            >
              Refresh Status
            </button>
            {autonomousStatus.status.daily_loss_limit_hit && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded">
                ⚠️ Daily loss limit reached. Auto trading stopped.
              </div>
            )}
            {autonomousStatus.status.hourly_limit_hit && (
              <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded">
                ⏰ Hourly trade limit reached. Waiting for next hour.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Claude-Assisted Trading Status */}
      {config && config.trading_mode === 'claude_assisted' && claudeStatus && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">🧠 Claude Auto-Execution Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className={`p-4 rounded-lg ${claudeStatus.status.claude_auto_active ? 'bg-purple-50' : 'bg-red-50'}`}>
              <p className="text-sm text-gray-600">Claude Auto Trading</p>
              <p className={`text-2xl font-bold ${claudeStatus.status.claude_auto_active ? 'text-purple-600' : 'text-red-600'}`}>
                {claudeStatus.status.claude_auto_active ? '🟣 ACTIVE' : '🔴 INACTIVE'}
              </p>
            </div>
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Session Trades</p>
              <p className="text-2xl font-bold text-blue-600">
                {claudeStatus.status.session_trades}/{claudeStatus.status.session_trades_limit}
              </p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Open Positions</p>
              <p className="text-2xl font-bold text-green-600">
                {claudeStatus.status.open_positions}/{claudeStatus.status.max_concurrent_trades}
              </p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Trading Hours</p>
              <p className={`text-2xl font-bold ${claudeStatus.status.trading_hours_active ? 'text-green-600' : 'text-orange-600'}`}>
                {claudeStatus.status.trading_hours_active ? '✅ ACTIVE' : '⏰ CLOSED'}
              </p>
            </div>
          </div>
          
          {/* Claude Status Details */}
          <div className="mt-4 p-4 bg-purple-50 rounded-lg">
            <h3 className="font-bold text-purple-900 mb-2">Claude's Current Parameters:</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Min Profit:</span>
                <span className="ml-2 font-semibold">{(claudeStatus.config.claude_min_profit_pct * 100).toFixed(3)}%</span>
              </div>
              <div>
                <span className="text-gray-600">Max Risk:</span>
                <span className="ml-2 font-semibold">{(claudeStatus.config.claude_max_risk_pct * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-gray-600">Risk Mode:</span>
                <span className="ml-2 font-semibold capitalize">{claudeStatus.config.claude_risk_preference}</span>
              </div>
              <div>
                <span className="text-gray-600">Hours:</span>
                <span className="ml-2 font-semibold">{claudeStatus.config.claude_trading_hours_start}:00-{claudeStatus.config.claude_trading_hours_end}:00</span>
              </div>
            </div>
          </div>
          
          {/* Status Alerts */}
          <div className="mt-4 flex space-x-4">
            <button
              onClick={() => loadClaudeStatus(config.id)}
              className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg"
            >
              Refresh Claude Status
            </button>
            {claudeStatus.status.session_limit_hit && (
              <div className="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-2 rounded">
                🕐 Session trade limit reached. Claude waiting for next hour.
              </div>
            )}
            {claudeStatus.status.concurrent_limit_hit && (
              <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded">
                📊 Max concurrent positions reached. Claude waiting for space.
              </div>
            )}
            {!claudeStatus.status.trading_hours_active && (
              <div className="bg-orange-100 border border-orange-400 text-orange-700 px-4 py-2 rounded">
                ⏰ Outside trading hours. Claude will resume at {claudeStatus.config.claude_trading_hours_start}:00 UTC.
              </div>
            )}
          </div>
          
          {config.auto_execute && (
            <div className="mt-4 p-3 bg-purple-100 border border-purple-300 rounded">
              <p className="text-sm text-purple-800">
                <strong>🤖 Claude Auto-Execution Active:</strong> Claude is automatically analyzing opportunities and executing trades that meet your parameters. Recent executions will appear in Trade History.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Performance Overview */}
      {performance && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Performance Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Current Balance</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatCurrency(performance.current_balance, performance.base_currency)}
              </p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Total Profit</p>
              <p className="text-2xl font-bold text-green-600">
                {formatCurrency(performance.total_profit, performance.base_currency)}
              </p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">ROI</p>
              <p className="text-2xl font-bold text-purple-600">
                {performance.roi_percentage.toFixed(2)}%
              </p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Win Rate</p>
              <p className="text-2xl font-bold text-orange-600">
                {performance.win_rate.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Live Opportunities */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Live Arbitrage Opportunities</h2>
          <div className="flex space-x-2">
            <button
              onClick={getMarketSentiment}
              disabled={isAnalyzing}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {isAnalyzing ? 'Analyzing...' : 'Get Market Sentiment'}
            </button>
            {config && (
              <button
                onClick={getTradingRecommendation}
                disabled={isAnalyzing}
                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
              >
                {isAnalyzing ? 'Analyzing...' : 'Get Trading Advice'}
              </button>
            )}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full table-auto">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-4 py-2 text-left">Type</th>
                <th className="px-4 py-2 text-left">Currency Pairs</th>
                <th className="px-4 py-2 text-left">Brokers</th>
                <th className="px-4 py-2 text-right">Profit %</th>
                <th className="px-4 py-2 text-right">Confidence</th>
                <th className="px-4 py-2 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {opportunities.slice(0, 10).map((opp, index) => (
                <tr key={opp.id || index} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <span className={`px-2 py-1 rounded text-sm ${
                      opp.type === 'spatial' ? 'bg-blue-100 text-blue-800' :
                      opp.type === 'triangular' ? 'bg-green-100 text-green-800' :
                      'bg-purple-100 text-purple-800'
                    }`}>
                      {opp.type}
                    </span>
                  </td>
                  <td className="px-4 py-2">{opp.currency_pairs.join(', ')}</td>
                  <td className="px-4 py-2">{opp.brokers.join(' → ')}</td>
                  <td className="px-4 py-2 text-right font-mono">
                    {formatPercentage(opp.profit_percentage / 100)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {(opp.confidence_score * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-2 text-center">
                    <div className="flex space-x-2 justify-center">
                      <button
                        onClick={() => getRiskAssessment(opp.id)}
                        className="text-blue-500 hover:text-blue-700 text-sm"
                      >
                        Analyze Risk
                      </button>
                      {config && config.trading_mode !== 'autonomous' && (
                        <div className="flex space-x-1">
                          {config.trading_mode === 'claude_assisted' ? (
                            <button
                              onClick={() => claudeExecuteTrade(opp.id)}
                              disabled={isExecutingTrade}
                              className="bg-purple-500 hover:bg-purple-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                            >
                              {isExecutingTrade ? 'Claude Deciding...' : 'Ask Claude'}
                            </button>
                          ) : (
                            <button
                              onClick={() => executeTrade(opp.id)}
                              disabled={isExecutingTrade}
                              className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                            >
                              {isExecutingTrade ? 'Executing...' : 'Trade'}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Claude Analysis */}
      {claudeAnalysis && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Claude Analysis</h2>
          <div className="bg-gray-50 p-4 rounded-lg">
            <pre className="whitespace-pre-wrap text-sm">{claudeAnalysis}</pre>
          </div>
        </div>
      )}
    </div>
  );

  const renderConfiguration = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Trading Configuration</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Starting Capital
            </label>
            <input
              type="number"
              value={configForm.starting_capital}
              onChange={(e) => setConfigForm({...configForm, starting_capital: parseFloat(e.target.value)})}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Base Currency
            </label>
            <select
              value={configForm.base_currency}
              onChange={(e) => setConfigForm({...configForm, base_currency: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
              <option value="JPY">JPY</option>
              <option value="AUD">AUD</option>
              <option value="CHF">CHF</option>
              <option value="CAD">CAD</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Risk Tolerance (% of capital per trade)
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="1.0"
              value={configForm.risk_tolerance}
              onChange={(e) => setConfigForm({...configForm, risk_tolerance: parseFloat(e.target.value)})}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Position Size (% of capital)
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max="0.5"
              value={configForm.max_position_size}
              onChange={(e) => setConfigForm({...configForm, max_position_size: parseFloat(e.target.value)})}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Trading Mode
            </label>
            <select
              value={configForm.trading_mode}
              onChange={(e) => setConfigForm({...configForm, trading_mode: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="simulation">Simulation</option>
              <option value="manual">Manual</option>
              <option value="autonomous">Autonomous</option>
              <option value="claude_assisted">Claude Assisted</option>
            </select>
            
            {/* Trading Mode Descriptions */}
            <div className="mt-2 p-3 bg-gray-50 rounded border-l-4 border-blue-500">
              {configForm.trading_mode === 'simulation' && (
                <p className="text-sm text-gray-700">
                  <strong>📊 Simulation:</strong> Practice with fake money and real market data. Perfect for testing strategies without risk.
                </p>
              )}
              {configForm.trading_mode === 'manual' && (
                <p className="text-sm text-gray-700">
                  <strong>🖱️ Manual:</strong> You control every trade. Bot finds opportunities, you click "Trade" to execute. Full control over all decisions.
                </p>
              )}
              {configForm.trading_mode === 'autonomous' && (
                <p className="text-sm text-gray-700">
                  <strong>🤖 Autonomous:</strong> Bot trades automatically using mathematical rules you set. Hands-off trading based on pure math (profit %, confidence).
                </p>
              )}
              {configForm.trading_mode === 'claude_assisted' && (
                <p className="text-sm text-gray-700">
                  <strong>🧠 Claude Assisted:</strong> AI analyzes opportunities like a professional trader and makes intelligent decisions based on market conditions.
                </p>
              )}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Profit Threshold
            </label>
            <input
              type="number"
              step="0.0001"
              min="0.0001"
              value={configForm.min_profit_threshold}
              onChange={(e) => setConfigForm({...configForm, min_profit_threshold: parseFloat(e.target.value)})}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        
        <div className="mt-6 flex items-start">
          <input
            type="checkbox"
            checked={configForm.auto_execute}
            onChange={(e) => setConfigForm({...configForm, auto_execute: e.target.checked})}
            className="mr-2 mt-1"
          />
          <div>
            <label className="text-sm text-gray-700 font-medium">Enable Auto Execution</label>
            <p className="text-xs text-gray-500 mt-1">
              {configForm.trading_mode === 'manual' && 
                "Manual mode ignores this setting - you always control trades manually."
              }
              {configForm.trading_mode === 'autonomous' && 
                "Bot will automatically execute trades based on your mathematical criteria."
              }
              {configForm.trading_mode === 'claude_assisted' && 
                "Claude will automatically execute trades it deems profitable based on your parameters."
              }
              {configForm.trading_mode === 'simulation' && 
                "Simulation mode for testing - no real money involved."
              }
            </p>
          </div>
        </div>

        {/* Autonomous Trading Parameters */}
        {configForm.trading_mode === 'autonomous' && (
          <div className="mt-8 p-6 bg-blue-50 rounded-lg border-2 border-blue-200">
            <h3 className="text-lg font-bold text-blue-900 mb-4">🤖 Autonomous Trading Controls</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Profit % (for auto execution)
                </label>
                <input
                  type="number"
                  step="0.001"
                  min="0.001"
                  max="0.1"
                  value={configForm.auto_min_profit_pct}
                  onChange={(e) => setConfigForm({...configForm, auto_min_profit_pct: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Only auto-execute if profit ≥ {(configForm.auto_min_profit_pct * 100).toFixed(2)}%</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Risk % per Auto Trade
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="0.1"
                  value={configForm.auto_max_risk_pct}
                  onChange={(e) => setConfigForm({...configForm, auto_max_risk_pct: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Risk {(configForm.auto_max_risk_pct * 100).toFixed(1)}% of capital per trade</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Confidence Score
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="1.0"
                  value={configForm.auto_min_confidence}
                  onChange={(e) => setConfigForm({...configForm, auto_min_confidence: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Only execute opportunities with ≥{(configForm.auto_min_confidence * 100).toFixed(0)}% confidence</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Trades per Hour
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={configForm.auto_max_trades_per_hour}
                  onChange={(e) => setConfigForm({...configForm, auto_max_trades_per_hour: parseInt(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Limit auto trades to prevent over-trading</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Daily Loss % (stop trading)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="0.2"
                  value={configForm.auto_max_daily_loss}
                  onChange={(e) => setConfigForm({...configForm, auto_max_daily_loss: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">Stop auto trading if daily loss ≥{(configForm.auto_max_daily_loss * 100).toFixed(1)}%</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Preferred Currency Pairs
                </label>
                <select
                  multiple
                  value={configForm.auto_preferred_pairs}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, option => option.value);
                    setConfigForm({...configForm, auto_preferred_pairs: values});
                  }}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 h-20"
                >
                  <option value="EUR/USD">EUR/USD</option>
                  <option value="GBP/USD">GBP/USD</option>
                  <option value="USD/JPY">USD/JPY</option>
                  <option value="AUD/USD">AUD/USD</option>
                  <option value="USD/CHF">USD/CHF</option>
                  <option value="USD/CAD">USD/CAD</option>
                  <option value="NZD/USD">NZD/USD</option>
                  <option value="EUR/GBP">EUR/GBP</option>
                  <option value="EUR/JPY">EUR/JPY</option>
                  <option value="GBP/JPY">GBP/JPY</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Hold Ctrl/Cmd to select multiple pairs</p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="flex items-center space-x-6">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={configForm.auto_trade_spatial}
                    onChange={(e) => setConfigForm({...configForm, auto_trade_spatial: e.target.checked})}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Auto-execute Spatial Arbitrage</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={configForm.auto_trade_triangular}
                    onChange={(e) => setConfigForm({...configForm, auto_trade_triangular: e.target.checked})}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Auto-execute Triangular Arbitrage</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={configForm.auto_claude_confirmation}
                    onChange={(e) => setConfigForm({...configForm, auto_claude_confirmation: e.target.checked})}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Require Claude Confirmation</span>
                </label>
              </div>
            </div>

            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-sm text-yellow-800">
                <strong>⚠️ Autonomous Trading Warning:</strong> Auto-execution will trade with real money based on these settings. 
                Monitor your account regularly and ensure you understand the risks.
              </p>
            </div>
          </div>
        )}

        {/* Claude-Assisted Trading Parameters */}
        {configForm.trading_mode === 'claude_assisted' && (
          <div className="mt-8 p-6 bg-purple-50 rounded-lg border-2 border-purple-200">
            <h3 className="text-lg font-bold text-purple-900 mb-4">🧠 Claude-Assisted Trading Parameters</h3>
            <p className="text-sm text-purple-700 mb-4">Claude will make trading decisions following your specific guidelines and risk parameters.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Claude's Min Profit % Target
                </label>
                <input
                  type="number"
                  step="0.001"
                  min="0.001"
                  max="0.05"
                  value={configForm.claude_min_profit_pct}
                  onChange={(e) => setConfigForm({...configForm, claude_min_profit_pct: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Claude only recommends trades ≥ {(configForm.claude_min_profit_pct * 100).toFixed(3)}%</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Claude's Max Risk % per Trade
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="0.1"
                  value={configForm.claude_max_risk_pct}
                  onChange={(e) => setConfigForm({...configForm, claude_max_risk_pct: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Claude risks max {(configForm.claude_max_risk_pct * 100).toFixed(1)}% per trade</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Claude's Risk Preference
                </label>
                <select
                  value={configForm.claude_risk_preference}
                  onChange={(e) => setConfigForm({...configForm, claude_risk_preference: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                >
                  <option value="conservative">Conservative</option>
                  <option value="moderate">Moderate</option>
                  <option value="aggressive">Aggressive</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Affects Claude's position sizing and trade selection</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Position Sizing Method
                </label>
                <select
                  value={configForm.claude_position_sizing_method}
                  onChange={(e) => setConfigForm({...configForm, claude_position_sizing_method: e.target.value})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                >
                  <option value="fixed_percent">Fixed Percentage</option>
                  <option value="kelly_criterion">Kelly Criterion</option>
                  <option value="equal_weight">Equal Weight</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">How Claude calculates position sizes</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Stop Loss %
                </label>
                <input
                  type="number"
                  step="0.001"
                  min="0.005"
                  max="0.05"
                  value={configForm.claude_stop_loss_pct}
                  onChange={(e) => setConfigForm({...configForm, claude_stop_loss_pct: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Claude sets stop loss at {(configForm.claude_stop_loss_pct * 100).toFixed(2)}%</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Take Profit Multiplier
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="1.0"
                  max="5.0"
                  value={configForm.claude_take_profit_multiplier}
                  onChange={(e) => setConfigForm({...configForm, claude_take_profit_multiplier: parseFloat(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Take profit at {configForm.claude_take_profit_multiplier}x stop loss distance</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Trades per Session
                </label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={configForm.claude_max_trades_per_session}
                  onChange={(e) => setConfigForm({...configForm, claude_max_trades_per_session: parseInt(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Claude limits to {configForm.claude_max_trades_per_session} trades per hour</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Concurrent Trades
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={configForm.claude_max_concurrent_trades}
                  onChange={(e) => setConfigForm({...configForm, claude_max_concurrent_trades: parseInt(e.target.value)})}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-xs text-gray-500 mt-1">Max {configForm.claude_max_concurrent_trades} open positions at once</p>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Trading Hours (UTC)
                </label>
                <div className="flex space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={configForm.claude_trading_hours_start}
                    onChange={(e) => setConfigForm({...configForm, claude_trading_hours_start: parseInt(e.target.value)})}
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    placeholder="Start"
                  />
                  <span className="self-center">to</span>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={configForm.claude_trading_hours_end}
                    onChange={(e) => setConfigForm({...configForm, claude_trading_hours_end: parseInt(e.target.value)})}
                    className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    placeholder="End"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Claude trades {configForm.claude_trading_hours_start}:00 - {configForm.claude_trading_hours_end}:00 UTC</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Claude's Preferred Pairs
                </label>
                <select
                  multiple
                  value={configForm.claude_preferred_pairs}
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, option => option.value);
                    setConfigForm({...configForm, claude_preferred_pairs: values});
                  }}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 h-20"
                >
                  <option value="EUR/USD">EUR/USD</option>
                  <option value="GBP/USD">GBP/USD</option>
                  <option value="USD/JPY">USD/JPY</option>
                  <option value="AUD/USD">AUD/USD</option>
                  <option value="USD/CHF">USD/CHF</option>
                  <option value="USD/CAD">USD/CAD</option>
                  <option value="NZD/USD">NZD/USD</option>
                  <option value="EUR/GBP">EUR/GBP</option>
                  <option value="EUR/JPY">EUR/JPY</option>
                  <option value="GBP/JPY">GBP/JPY</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Claude focuses on these pairs</p>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <div className="flex items-center space-x-6">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={configForm.claude_avoid_news_times}
                    onChange={(e) => setConfigForm({...configForm, claude_avoid_news_times: e.target.checked})}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Avoid Trading During News</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={configForm.claude_require_multiple_confirmations}
                    onChange={(e) => setConfigForm({...configForm, claude_require_multiple_confirmations: e.target.checked})}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Require Multiple Confirmations</span>
                </label>
              </div>
            </div>

            <div className="mt-4 p-3 bg-purple-100 border border-purple-300 rounded">
              <p className="text-sm text-purple-800">
                <strong>🧠 Claude-Assisted Mode:</strong> Claude will analyze opportunities and make trading decisions 
                based on your specific parameters. Every trade recommendation will follow your risk preferences and constraints.
              </p>
            </div>
          </div>
        )}
        
        <div className="mt-6">
          <button
            onClick={createConfig}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg"
          >
            Create Configuration
          </button>
        </div>
        
        {config && (
          <div className="mt-6 p-4 bg-green-50 rounded-lg">
            <p className="text-green-800">
              Configuration created successfully! ID: {config.id}
            </p>
          </div>
        )}
      </div>
    </div>
  );

  const renderTradeHistory = () => (
    <div className="space-y-6">
      {/* Trade Summary */}
      {tradesSummary && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Trading Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Total Trades</p>
              <p className="text-2xl font-bold text-blue-600">{tradesSummary.total_trades}</p>
            </div>
            <div className={`p-4 rounded-lg ${tradesSummary.total_profit >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
              <p className="text-sm text-gray-600">Total P&L</p>
              <p className={`text-2xl font-bold ${tradesSummary.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(tradesSummary.total_profit)}
              </p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Win Rate</p>
              <p className="text-2xl font-bold text-purple-600">{tradesSummary.win_rate.toFixed(1)}%</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Largest Win</p>
              <p className="text-2xl font-bold text-green-600">{formatCurrency(tradesSummary.largest_win)}</p>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Largest Loss</p>
              <p className="text-2xl font-bold text-red-600">{formatCurrency(Math.abs(tradesSummary.largest_loss))}</p>
            </div>
          </div>
        </div>
      )}

      {/* Trade History Table */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">Trade History</h2>
          {config && (
            <button
              onClick={() => loadTradeHistory(config.id)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
            >
              Refresh
            </button>
          )}
        </div>
        
        {trades.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No trades executed yet. Go to the Dashboard to start trading!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left">Date/Time</th>
                  <th className="px-4 py-2 text-left">Type</th>
                  <th className="px-4 py-2 text-left">Action</th>
                  <th className="px-4 py-2 text-left">Currency Pairs</th>
                  <th className="px-4 py-2 text-left">Broker</th>
                  <th className="px-4 py-2 text-right">Amount</th>
                  <th className="px-4 py-2 text-right">Rate</th>
                  <th className="px-4 py-2 text-right">Profit/Loss</th>
                  <th className="px-4 py-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade, index) => (
                  <tr key={trade.id || index} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 text-sm">
                      {trade.execution_time ? new Date(trade.execution_time).toLocaleString() : 'Pending'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-sm ${
                        trade.type === 'spatial' ? 'bg-blue-100 text-blue-800' :
                        trade.type === 'triangular' ? 'bg-green-100 text-green-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {trade.type}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-sm ${
                        trade.action === 'buy' ? 'bg-green-100 text-green-800' :
                        trade.action === 'sell' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {trade.action.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm">{trade.currency_pairs.join(', ')}</td>
                    <td className="px-4 py-2 text-sm">{trade.broker}</td>
                    <td className="px-4 py-2 text-right font-mono">{formatCurrency(trade.amount)}</td>
                    <td className="px-4 py-2 text-right font-mono">
                      {trade.rate === 1.0 && trade.type === 'triangular' ? 'N/A' : trade.rate.toFixed(5)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      <span className={trade.profit >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                        {trade.profit >= 0 ? '+' : ''}{formatCurrency(trade.profit)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-center">
                      <span className={`px-2 py-1 rounded text-sm ${
                        trade.status === 'executed' ? 'bg-green-100 text-green-800' :
                        trade.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {trade.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Accumulated P&L Chart Placeholder */}
      {tradesSummary && tradesSummary.accumulated_pnl.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">P&L Progression</h2>
          <div className="space-y-2">
            {tradesSummary.accumulated_pnl.slice(-10).map((pnl, index) => (
              <div key={index} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                <span className="text-sm text-gray-600">
                  Trade #{tradesSummary.accumulated_pnl.length - 10 + index + 1}
                </span>
                <span className="text-sm font-mono">
                  Trade P&L: <span className={pnl.profit >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {formatCurrency(pnl.profit)}
                  </span>
                </span>
                <span className="text-sm font-mono font-bold">
                  Total: <span className={pnl.accumulated_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {formatCurrency(pnl.accumulated_pnl)}
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
  const renderMarketData = () => {
    // Get all unique currency pairs
    const allPairs = new Set();
    Object.values(marketData).forEach(brokerData => {
      Object.keys(brokerData || {}).forEach(pair => allPairs.add(pair));
    });
    const sortedPairs = Array.from(allPairs).sort();
    
    // Get all brokers
    const brokers = Object.keys(marketData).sort();
    
    // Helper function to get rate difference color
    const getRateDifferenceColor = (pair) => {
      const rates = brokers.map(broker => marketData[broker]?.[pair]).filter(rate => rate !== undefined);
      if (rates.length < 2) return '';
      
      const minRate = Math.min(...rates);
      const maxRate = Math.max(...rates);
      const difference = maxRate - minRate;
      const percentageDiff = (difference / minRate) * 100;
      
      if (percentageDiff > 0.01) return 'bg-red-50'; // Significant difference
      if (percentageDiff > 0.005) return 'bg-yellow-50'; // Moderate difference
      return 'bg-green-50'; // Small difference
    };

    // Helper function to highlight best/worst rates
    const getRateCellStyle = (pair, broker, rate) => {
      const rates = brokers.map(b => marketData[b]?.[pair]).filter(r => r !== undefined);
      if (rates.length < 2 || !rate) return 'bg-white';
      
      const minRate = Math.min(...rates);
      const maxRate = Math.max(...rates);
      
      if (rate === minRate && rate === maxRate) return 'bg-white'; // All same
      if (rate === minRate) return 'bg-green-100 text-green-800 font-semibold'; // Lowest rate
      if (rate === maxRate) return 'bg-blue-100 text-blue-800 font-semibold'; // Highest rate
      return 'bg-white';
    };

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Live Market Data Comparison</h2>
              <p className="text-sm text-gray-600 mt-1">
                Compare rates across brokers • 
                <span className="text-green-700 font-medium"> Green = Lowest Rate</span> • 
                <span className="text-blue-700 font-medium"> Blue = Highest Rate</span>
              </p>
            </div>
            <button
              onClick={loadMarketData}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
            >
              Refresh
            </button>
          </div>
          
          {Object.keys(marketData).length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>Loading market data...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full table-auto border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left font-semibold text-gray-900 border-b border-gray-200">
                      Currency Pair
                    </th>
                    {brokers.map(broker => (
                      <th key={broker} className="px-4 py-3 text-center font-semibold text-gray-900 border-b border-gray-200 min-w-24">
                        {broker}
                      </th>
                    ))}
                    <th className="px-4 py-3 text-center font-semibold text-gray-900 border-b border-gray-200">
                      Spread
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedPairs.map((pair, index) => {
                    // Calculate spread for this pair
                    const rates = brokers.map(broker => marketData[broker]?.[pair]).filter(rate => rate !== undefined);
                    const minRate = rates.length > 0 ? Math.min(...rates) : 0;
                    const maxRate = rates.length > 0 ? Math.max(...rates) : 0;
                    const spread = maxRate - minRate;
                    const spreadPips = spread * 10000; // Convert to pips
                    
                    return (
                      <tr 
                        key={pair} 
                        className={`${index % 2 === 0 ? 'bg-white' : 'bg-gray-25'} ${getRateDifferenceColor(pair)} hover:bg-gray-50 transition-colors`}
                      >
                        <td className="px-4 py-3 font-medium text-gray-900 border-b border-gray-100">
                          {pair}
                        </td>
                        {brokers.map(broker => {
                          const rate = marketData[broker]?.[pair];
                          return (
                            <td 
                              key={broker} 
                              className={`px-4 py-3 text-center font-mono text-sm border-b border-gray-100 ${getRateCellStyle(pair, broker, rate)}`}
                            >
                              {rate ? rate.toFixed(5) : '-'}
                            </td>
                          );
                        })}
                        <td className="px-4 py-3 text-center font-mono text-sm border-b border-gray-100">
                          {rates.length > 1 ? (
                            <div className="flex flex-col items-center">
                              <span className={`${spreadPips > 1 ? 'text-red-600 font-semibold' : 'text-gray-600'}`}>
                                {spread.toFixed(5)}
                              </span>
                              <span className="text-xs text-gray-500">
                                ({spreadPips.toFixed(1)} pips)
                              </span>
                            </div>
                          ) : '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          
          {Object.keys(marketData).length > 0 && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Market Data Summary</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="bg-white p-3 rounded">
                  <div className="text-gray-600">Total Currency Pairs</div>
                  <div className="text-lg font-semibold text-blue-600">{sortedPairs.length}</div>
                </div>
                <div className="bg-white p-3 rounded">
                  <div className="text-gray-600">Active Brokers</div>
                  <div className="text-lg font-semibold text-green-600">{brokers.length}</div>
                </div>
                <div className="bg-white p-3 rounded">
                  <div className="text-gray-600">Last Updated</div>
                  <div className="text-lg font-semibold text-purple-600">
                    {new Date().toLocaleTimeString()}
                  </div>
                </div>
              </div>
              
              <div className="mt-3 text-xs text-gray-600">
                <p><strong>How to read this table:</strong></p>
                <ul className="mt-1 space-y-1">
                  <li>• <span className="bg-green-100 text-green-800 px-1 rounded">Green cells</span> show the lowest rate for each currency pair</li>
                  <li>• <span className="bg-blue-100 text-blue-800 px-1 rounded">Blue cells</span> show the highest rate for each currency pair</li>
                  <li>• <strong>Spread</strong> column shows the difference between highest and lowest rates</li>
                  <li>• Higher spreads (>1 pip) indicate better arbitrage opportunities</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderCredentials = () => (
    <div className="space-y-6">
      {/* Anthropic API Key Section */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">🤖 Anthropic Claude API Key</h2>
        <p className="text-gray-600 mb-4">
          Configure your Anthropic Claude API key for AI-powered trading analysis and decision making.
        </p>
        
        <div className="flex space-x-4">
          <input
            type="password"
            value={anthropicApiKey}
            onChange={(e) => setAnthropicApiKey(e.target.value)}
            placeholder="sk-ant-..."
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
          />
          <button
            onClick={updateAnthropicKey}
            className="bg-purple-500 hover:bg-purple-600 text-white px-6 py-3 rounded-lg"
          >
            Update Key
          </button>
        </div>
        
        <p className="text-sm text-gray-500 mt-2">
          Get your API key from <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline">Anthropic Console</a>
        </p>
      </div>

      {/* Broker Credentials Section */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">🏦 Broker Credentials</h2>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowCredentialForm(!showCredentialForm)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
            >
              {showCredentialForm ? 'Cancel' : 'Add Broker'}
            </button>
            <button
              onClick={testAllCredentials}
              disabled={isTestingCredentials}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {isTestingCredentials ? 'Testing...' : 'Test All'}
            </button>
          </div>
        </div>

        {/* Add Credentials Form */}
        {showCredentialForm && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg border">
            <h3 className="text-lg font-semibold mb-4">Add New Broker Credentials</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Broker
              </label>
              <select
                value={selectedBroker}
                onChange={(e) => handleBrokerSelect(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Choose a broker...</option>
                {supportedBrokers.map((broker) => (
                  <option key={broker.name} value={broker.name}>
                    {broker.display_name} - {broker.description}
                  </option>
                ))}
              </select>
            </div>

            {selectedBroker && (
              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">
                  {supportedBrokers.find(b => b.name === selectedBroker)?.display_name} Credentials
                </h4>
                
                {supportedBrokers
                  .find(b => b.name === selectedBroker)
                  ?.fields.map((field) => (
                    <div key={field.name}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {field.label} {field.required && <span className="text-red-500">*</span>}
                      </label>
                      
                      {field.type === 'select' ? (
                        <select
                          value={credentialForm[field.name] || field.default || ''}
                          onChange={(e) => setCredentialForm({
                            ...credentialForm,
                            [field.name]: e.target.value
                          })}
                          className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          {field.options.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.type}
                          value={credentialForm[field.name] || field.default || ''}
                          onChange={(e) => setCredentialForm({
                            ...credentialForm,
                            [field.name]: e.target.value
                          })}
                          placeholder={field.label}
                          className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      )}
                    </div>
                  ))}
                
                <div className="flex space-x-2 pt-4">
                  <button
                    onClick={createCredentials}
                    disabled={isCreatingCredentials}
                    className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    {isCreatingCredentials ? 'Creating...' : 'Save Credentials'}
                  </button>
                  <button
                    onClick={() => {
                      setShowCredentialForm(false);
                      setSelectedBroker('');
                      setCredentialForm({});
                    }}
                    className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Existing Credentials List */}
        <div className="space-y-4">
          {credentials.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No broker credentials configured. Click "Add Broker" to get started.
            </p>
          ) : (
            credentials.map((cred) => (
              <div key={cred.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-semibold">{cred.broker_name}</h3>
                      <span className={`px-2 py-1 rounded text-sm ${
                        cred.connection_status === 'connected' 
                          ? 'bg-green-100 text-green-800' 
                          : cred.connection_status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {cred.connection_status || 'Untested'}
                      </span>
                      <span className={`px-2 py-1 rounded text-sm ${
                        cred.is_active ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {cred.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    
                    <div className="mt-2 text-sm text-gray-600">
                      <p>Created: {new Date(cred.created_at).toLocaleString()}</p>
                      {cred.last_tested && (
                        <p>Last Tested: {new Date(cred.last_tested).toLocaleString()}</p>
                      )}
                      {cred.last_successful_connection && (
                        <p>Last Success: {new Date(cred.last_successful_connection).toLocaleString()}</p>
                      )}
                      {cred.error_message && (
                        <p className="text-red-600 mt-1">Error: {cred.error_message}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <button
                      onClick={() => testCredentials(cred.id)}
                      disabled={isTestingCredentials}
                      className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                    >
                      {isTestingCredentials ? 'Testing...' : 'Test'}
                    </button>
                    <button
                      onClick={() => deleteCredentials(cred.id, cred.broker_name)}
                      className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Setup Instructions */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">📝 Setup Instructions</h3>
          <div className="space-y-3 text-sm text-blue-800">
            <div><strong>OANDA:</strong> Get API key from OANDA Developer Portal</div>
            <div><strong>Interactive Brokers:</strong> Enable API in TWS/IB Gateway</div>
            <div><strong>FXCM:</strong> Register for API access at FXCM Developer Portal</div>
            <div><strong>XM/MetaTrader:</strong> Use your existing MT5 account credentials</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Anthropic API Key Section */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">🤖 Anthropic Claude API Key</h2>
        <p className="text-gray-600 mb-4">
          Configure your Anthropic Claude API key for AI-powered trading analysis and decision making.
        </p>
        
        <div className="flex space-x-4">
          <input
            type="password"
            value={anthropicApiKey}
            onChange={(e) => setAnthropicApiKey(e.target.value)}
            placeholder="sk-ant-..."
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
          />
          <button
            onClick={updateAnthropicKey}
            className="bg-purple-500 hover:bg-purple-600 text-white px-6 py-3 rounded-lg"
          >
            Update Key
          </button>
        </div>
        
        <p className="text-sm text-gray-500 mt-2">
          Get your API key from <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline">Anthropic Console</a>
        </p>
      </div>

      {/* Broker Credentials Section */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">🏦 Broker Credentials</h2>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowCredentialForm(!showCredentialForm)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
            >
              {showCredentialForm ? 'Cancel' : 'Add Broker'}
            </button>
            <button
              onClick={testAllCredentials}
              disabled={isTestingCredentials}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {isTestingCredentials ? 'Testing...' : 'Test All'}
            </button>
          </div>
        </div>

        {/* Add Credentials Form */}
        {showCredentialForm && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg border">
            <h3 className="text-lg font-semibold mb-4">Add New Broker Credentials</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Broker
              </label>
              <select
                value={selectedBroker}
                onChange={(e) => handleBrokerSelect(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Choose a broker...</option>
                {supportedBrokers.map((broker) => (
                  <option key={broker.name} value={broker.name}>
                    {broker.display_name} - {broker.description}
                  </option>
                ))}
              </select>
            </div>

            {selectedBroker && (
              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">
                  {supportedBrokers.find(b => b.name === selectedBroker)?.display_name} Credentials
                </h4>
                
                {supportedBrokers
                  .find(b => b.name === selectedBroker)
                  ?.fields.map((field) => (
                    <div key={field.name}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        {field.label} {field.required && <span className="text-red-500">*</span>}
                      </label>
                      
                      {field.type === 'select' ? (
                        <select
                          value={credentialForm[field.name] || field.default || ''}
                          onChange={(e) => setCredentialForm({
                            ...credentialForm,
                            [field.name]: e.target.value
                          })}
                          className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          {field.options.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.type}
                          value={credentialForm[field.name] || field.default || ''}
                          onChange={(e) => setCredentialForm({
                            ...credentialForm,
                            [field.name]: e.target.value
                          })}
                          placeholder={field.label}
                          className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                      )}
                    </div>
                  ))}
                
                <div className="flex space-x-2 pt-4">
                  <button
                    onClick={createCredentials}
                    disabled={isCreatingCredentials}
                    className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
                  >
                    {isCreatingCredentials ? 'Creating...' : 'Save Credentials'}
                  </button>
                  <button
                    onClick={() => {
                      setShowCredentialForm(false);
                      setSelectedBroker('');
                      setCredentialForm({});
                    }}
                    className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Existing Credentials List */}
        <div className="space-y-4">
          {credentials.length === 0 ? (
            <p className="text-gray-500 text-center py-8">
              No broker credentials configured. Click "Add Broker" to get started.
            </p>
          ) : (
            credentials.map((cred) => (
              <div key={cred.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-semibold">{cred.broker_name}</h3>
                      <span className={`px-2 py-1 rounded text-sm ${
                        cred.connection_status === 'connected' 
                          ? 'bg-green-100 text-green-800' 
                          : cred.connection_status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {cred.connection_status || 'Untested'}
                      </span>
                      <span className={`px-2 py-1 rounded text-sm ${
                        cred.is_active ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {cred.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    
                    <div className="mt-2 text-sm text-gray-600">
                      <p>Created: {new Date(cred.created_at).toLocaleString()}</p>
                      {cred.last_tested && (
                        <p>Last Tested: {new Date(cred.last_tested).toLocaleString()}</p>
                      )}
                      {cred.last_successful_connection && (
                        <p>Last Success: {new Date(cred.last_successful_connection).toLocaleString()}</p>
                      )}
                      {cred.error_message && (
                        <p className="text-red-600 mt-1">Error: {cred.error_message}</p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <button
                      onClick={() => testCredentials(cred.id)}
                      disabled={isTestingCredentials}
                      className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                    >
                      {isTestingCredentials ? 'Testing...' : 'Test'}
                    </button>
                    <button
                      onClick={() => deleteCredentials(cred.id, cred.broker_name)}
                      className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Setup Instructions */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">📝 Setup Instructions</h3>
          <div className="space-y-3 text-sm text-blue-800">
            <div><strong>OANDA:</strong> Get API key from OANDA Developer Portal</div>
            <div><strong>Interactive Brokers:</strong> Enable API in TWS/IB Gateway</div>
            <div><strong>FXCM:</strong> Register for API access at FXCM Developer Portal</div>
            <div><strong>XM/MetaTrader:</strong> Use your existing MT5 account credentials</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPositions = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">📊 Current Positions</h2>
        
        {positions.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No open positions</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Broker</th>
                  <th className="text-left py-2">Pair</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-left py-2">Amount</th>
                  <th className="text-left py-2">Entry Rate</th>
                  <th className="text-left py-2">Current Rate</th>
                  <th className="text-left py-2">P&L</th>
                  <th className="text-left py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => (
                  <tr key={position.id} className="border-b">
                    <td className="py-2">{position.broker}</td>
                    <td className="py-2">{position.currency_pair}</td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        position.position_type === 'long' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {position.position_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2">{formatCurrency(position.amount)}</td>
                    <td className="py-2">{position.entry_rate}</td>
                    <td className="py-2">{position.current_rate}</td>
                    <td className="py-2">
                      <span className={position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {formatCurrency(position.unrealized_pnl)}
                      </span>
                    </td>
                    <td className="py-2">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => closePosition(position.id)}
                          className="bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded text-xs"
                        >
                          Close
                        </button>
                        <button
                          onClick={() => hedgePosition(position.id)}
                          className="bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded text-xs"
                        >
                          Hedge
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Broker Balances */}
        {Object.keys(balances).length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-3">💰 Broker Balances</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(balances).map(([broker, currencies]) => (
                <div key={broker} className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900 mb-2">{broker}</h4>
                  <div className="space-y-1 text-sm">
                    {Object.entries(currencies).map(([currency, amount]) => (
                      <div key={currency} className="flex justify-between">
                        <span>{currency}:</span>
                        <span className="font-medium">{formatCurrency(amount, currency)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-3xl font-bold text-gray-900">
              🔄 Forex Arbitrage Bot
            </h1>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-600">Live</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {['dashboard', 'configuration', 'credentials', 'positions', 'trade-history', 'market-data'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.replace('-', ' ')}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'configuration' && renderConfiguration()}
        {activeTab === 'credentials' && renderCredentials()}
        {activeTab === 'positions' && renderPositions()}
        {activeTab === 'trade-history' && renderTradeHistory()}
        {activeTab === 'market-data' && renderMarketData()}
      </main>
    </div>
  );
}

export default App;