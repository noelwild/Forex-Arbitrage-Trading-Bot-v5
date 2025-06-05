import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json

# Broker-specific imports
try:
    import oandapyV20
    from oandapyV20 import API
    from oandapyV20.endpoints import accounts, pricing
    OANDA_AVAILABLE = True
except ImportError:
    OANDA_AVAILABLE = False

try:
    from ib_insync import IB, Contract
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    # Create dummy classes to avoid NameError
    class IB:
        pass
    class Contract:
        pass

try:
    import fxcmpy
    FXCM_AVAILABLE = True
except ImportError:
    FXCM_AVAILABLE = False

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from .credential_models import (
    OANDACredentials, InteractiveBrokersCredentials, 
    FXCMCredentials, XMCredentials, MetaTraderCredentials,
    CredentialValidationResult
)

logger = logging.getLogger(__name__)

class BrokerConnector:
    """Base class for broker connectors"""
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.connection = None
        self.is_connected = False
    
    async def validate_credentials(self) -> CredentialValidationResult:
        """Validate broker credentials by attempting connection"""
        raise NotImplementedError
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        raise NotImplementedError
    
    async def get_market_data(self, instruments: list) -> Dict[str, Any]:
        """Get market data for specified instruments"""
        raise NotImplementedError
    
    async def disconnect(self):
        """Disconnect from broker"""
        if self.connection:
            try:
                await self.connection.close()
            except:
                pass
        self.is_connected = False

class OANDAConnector(BrokerConnector):
    """OANDA broker connector"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if not OANDA_AVAILABLE:
            raise ImportError("oandapyV20 library not available")
    
    async def validate_credentials(self) -> CredentialValidationResult:
        try:
            creds = OANDACredentials(**self.credentials)
            
            # Initialize OANDA client
            client = API(
                access_token=creds.api_key,
                environment=creds.environment
            )
            
            # Test connection by getting account details
            account_request = accounts.AccountDetails(accountID=creds.account_id)
            response = client.request(account_request)
            
            self.connection = client
            self.is_connected = True
            
            return CredentialValidationResult(
                success=True,
                broker_name="OANDA",
                message="Successfully connected to OANDA",
                connection_details={
                    "account_id": creds.account_id,
                    "environment": creds.environment,
                    "account_currency": response.get("account", {}).get("currency"),
                    "account_balance": response.get("account", {}).get("balance")
                }
            )
            
        except Exception as e:
            return CredentialValidationResult(
                success=False,
                broker_name="OANDA",
                message=f"OANDA connection failed: {str(e)}"
            )
    
    async def get_account_info(self) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("Not connected to OANDA")
        
        creds = OANDACredentials(**self.credentials)
        account_request = accounts.AccountDetails(accountID=creds.account_id)
        response = self.connection.request(account_request)
        return response.get("account", {})
    
    async def get_market_data(self, instruments: list) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("Not connected to OANDA")
        
        creds = OANDACredentials(**self.credentials)
        params = {"instruments": ",".join(instruments)}
        pricing_request = pricing.PricingInfo(accountID=creds.account_id, params=params)
        response = self.connection.request(pricing_request)
        return response

class InteractiveBrokersConnector(BrokerConnector):
    """Interactive Brokers connector"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if not IB_AVAILABLE:
            raise ImportError("ib_insync library not available")
    
    async def validate_credentials(self) -> CredentialValidationResult:
        try:
            creds = InteractiveBrokersCredentials(**self.credentials)
            
            # Initialize IB connection
            ib = IB()
            await asyncio.wait_for(
                asyncio.create_task(self._connect_ib(ib, creds)), 
                timeout=10.0
            )
            
            # Test connection by getting account summary
            account_summary = ib.accountSummary()
            if not account_summary:
                raise Exception("Could not retrieve account summary")
            
            self.connection = ib
            self.is_connected = True
            
            return CredentialValidationResult(
                success=True,
                broker_name="Interactive Brokers",
                message="Successfully connected to Interactive Brokers",
                connection_details={
                    "host": creds.host,
                    "port": creds.port,
                    "client_id": creds.client_id,
                    "account_count": len(account_summary)
                }
            )
            
        except asyncio.TimeoutError:
            return CredentialValidationResult(
                success=False,
                broker_name="Interactive Brokers",
                message="Connection timeout - ensure TWS/IB Gateway is running and API is enabled"
            )
        except Exception as e:
            return CredentialValidationResult(
                success=False,
                broker_name="Interactive Brokers",
                message=f"IB connection failed: {str(e)}"
            )
    
    async def _connect_ib(self, ib: IB, creds: InteractiveBrokersCredentials):
        """Helper method to connect to IB"""
        ib.connect(creds.host, creds.port, clientId=creds.client_id)
    
    async def disconnect(self):
        if self.connection:
            self.connection.disconnect()
        await super().disconnect()

class FXCMConnector(BrokerConnector):
    """FXCM broker connector"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if not FXCM_AVAILABLE:
            raise ImportError("fxcmpy library not available")
    
    async def validate_credentials(self) -> CredentialValidationResult:
        try:
            creds = FXCMCredentials(**self.credentials)
            
            # Initialize FXCM connection
            connection = fxcmpy.fxcmpy(
                access_token=creds.api_key,
                log_level='error',
                server=creds.environment
            )
            
            # Test connection by getting account info
            account_info = connection.get_accounts()
            if not account_info:
                raise Exception("Could not retrieve account information")
            
            self.connection = connection
            self.is_connected = True
            
            return CredentialValidationResult(
                success=True,
                broker_name="FXCM",
                message="Successfully connected to FXCM",
                connection_details={
                    "environment": creds.environment,
                    "account_id": account_info.get("accountId"),
                    "account_name": account_info.get("accountName")
                }
            )
            
        except Exception as e:
            return CredentialValidationResult(
                success=False,
                broker_name="FXCM",
                message=f"FXCM connection failed: {str(e)}"
            )

class XMConnector(BrokerConnector):
    """XM broker connector (using MetaTrader 5)"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 library not available")
    
    async def validate_credentials(self) -> CredentialValidationResult:
        try:
            creds = XMCredentials(**self.credentials)
            
            # Initialize MT5 connection
            if not mt5.initialize():
                raise Exception("Failed to initialize MetaTrader5")
            
            # Login to account
            login_result = mt5.login(
                login=int(creds.username),
                password=creds.password,
                server=creds.server
            )
            
            if not login_result:
                mt5.shutdown()
                raise Exception(f"Login failed: {mt5.last_error()}")
            
            # Get account info
            account_info = mt5.account_info()
            if not account_info:
                mt5.shutdown()
                raise Exception("Could not retrieve account information")
            
            self.is_connected = True
            
            return CredentialValidationResult(
                success=True,
                broker_name="XM",
                message="Successfully connected to XM via MetaTrader5",
                connection_details={
                    "login": creds.username,
                    "server": creds.server,
                    "account_type": creds.account_type,
                    "balance": account_info.balance,
                    "currency": account_info.currency
                }
            )
            
        except Exception as e:
            mt5.shutdown()
            return CredentialValidationResult(
                success=False,
                broker_name="XM",
                message=f"XM connection failed: {str(e)}"
            )
    
    async def disconnect(self):
        if self.is_connected:
            mt5.shutdown()
        await super().disconnect()

class MetaTraderConnector(BrokerConnector):
    """Generic MetaTrader 5 connector"""
    
    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 library not available")
    
    async def validate_credentials(self) -> CredentialValidationResult:
        try:
            creds = MetaTraderCredentials(**self.credentials)
            
            # Initialize MT5 with custom path if provided
            if creds.path:
                if not mt5.initialize(path=creds.path):
                    raise Exception("Failed to initialize MetaTrader5 with custom path")
            else:
                if not mt5.initialize():
                    raise Exception("Failed to initialize MetaTrader5")
            
            # Login to account
            login_result = mt5.login(
                login=int(creds.login),
                password=creds.password,
                server=creds.server
            )
            
            if not login_result:
                mt5.shutdown()
                raise Exception(f"Login failed: {mt5.last_error()}")
            
            # Get account info
            account_info = mt5.account_info()
            if not account_info:
                mt5.shutdown()
                raise Exception("Could not retrieve account information")
            
            self.is_connected = True
            
            return CredentialValidationResult(
                success=True,
                broker_name="MetaTrader",
                message="Successfully connected to MetaTrader5",
                connection_details={
                    "login": creds.login,
                    "server": creds.server,
                    "balance": account_info.balance,
                    "currency": account_info.currency,
                    "company": account_info.company
                }
            )
            
        except Exception as e:
            mt5.shutdown()
            return CredentialValidationResult(
                success=False,
                broker_name="MetaTrader",
                message=f"MetaTrader connection failed: {str(e)}"
            )
    
    async def disconnect(self):
        if self.is_connected:
            mt5.shutdown()
        await super().disconnect()

# Factory function to create appropriate connector
def create_broker_connector(broker_name: str, credentials: Dict[str, str]) -> BrokerConnector:
    """Factory function to create the appropriate broker connector"""
    
    broker_name = broker_name.upper()
    
    if broker_name == "OANDA":
        return OANDAConnector(credentials)
    elif broker_name == "INTERACTIVE BROKERS" or broker_name == "IB":
        return InteractiveBrokersConnector(credentials)
    elif broker_name == "FXCM":
        return FXCMConnector(credentials)
    elif broker_name == "XM":
        return XMConnector(credentials)
    elif broker_name == "METATRADER" or broker_name == "MT5":
        return MetaTraderConnector(credentials)
    else:
        raise ValueError(f"Unsupported broker: {broker_name}")

# Test function for fake credentials
async def test_fake_credentials(broker_name: str) -> CredentialValidationResult:
    """Test function that always returns failure for fake credentials"""
    fake_messages = {
        "OANDA": "Invalid API key or account ID. Please check your OANDA credentials.",
        "INTERACTIVE BROKERS": "Connection refused. Ensure TWS/IB Gateway is running with API enabled.",
        "FXCM": "Invalid access token. Please verify your FXCM API key.",
        "XM": "Login failed. Invalid username, password, or server settings.",
        "METATRADER": "Authentication failed. Check login, password, and server details."
    }
    
    return CredentialValidationResult(
        success=False,
        broker_name=broker_name,
        message=fake_messages.get(broker_name.upper(), f"Invalid credentials for {broker_name}")
    )
