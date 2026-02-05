"""Data models for the derivatives trading dashboard."""

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class OptionType(str, Enum):
    CALL = "Call"
    PUT = "Put"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PortfolioItem(BaseModel):
    id: str
    symbol: str
    type: OptionType
    strike: float
    expiration: str
    quantity: int
    avgPrice: float
    marketPrice: float
    pnl: float
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float


class Alert(BaseModel):
    id: str
    title: str
    description: str
    timestamp: str
    priority: Priority
    read: bool


class DMADataPoint(BaseModel):
    time: str
    value: float


class IVDataPoint(BaseModel):
    strike: float
    iv: float


class CreatePositionRequest(BaseModel):
    symbol: str
    type: OptionType
    strike: float
    expiration: str
    quantity: int
    avg_price: float