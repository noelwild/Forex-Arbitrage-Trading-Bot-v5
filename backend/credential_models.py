from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import os
import json
import uuid

# Generate or load encryption key
def get_encryption_key():
    key_file = "/app/backend/.encryption_key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        return key

ENCRYPTION_KEY = get_encryption_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

class BrokerCredentials(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    broker_name: str  # OANDA, Interactive Brokers, FXCM, XM, MetaTrader
    user_id: Optional[str] = None  # For multi-user support later
    credentials: Dict[str, str]  # Encrypted credential data
    is_active: bool = Field(default=True)
    connection_status: Optional[str] = None  # connected, failed, untested
    last_tested: Optional[datetime] = None
    last_successful_connection: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OANDACredentials(BaseModel):
    api_key: str
    account_id: str
    environment: str = "practice"  # practice or live

class InteractiveBrokersCredentials(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7497  # 7497 for paper trading, 7496 for live
    client_id: int = 1
    username: Optional[str] = None
    password: Optional[str] = None

class FXCMCredentials(BaseModel):
    api_key: str
    environment: str = "demo"  # demo or real
    server_url: Optional[str] = None

class XMCredentials(BaseModel):
    username: str
    password: str
    server: str
    account_type: str = "demo"  # demo or real

class MetaTraderCredentials(BaseModel):
    login: str
    password: str
    server: str
    path: Optional[str] = None  # Path to MT5 terminal

class AnthropicCredentials(BaseModel):
    api_key: str

class CredentialValidationResult(BaseModel):
    success: bool
    broker_name: str
    message: str
    connection_details: Optional[Dict[str, Any]] = None
    tested_at: datetime = Field(default_factory=datetime.utcnow)

class CredentialCreateRequest(BaseModel):
    broker_name: str
    credentials: Dict[str, str]

class CredentialUpdateRequest(BaseModel):
    credentials: Dict[str, str]
    is_active: Optional[bool] = None
