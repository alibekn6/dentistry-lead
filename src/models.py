"""Database models for the dentistry lead generation system."""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class LeadStatus(str, Enum):
    COLD = "cold"
    WARM = "warm"
    REPLIED = "replied"
    STOPPED = "stopped"
    BLACKLISTED = "blacklisted"


class ChannelType(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PHONE = "phone"


class InteractionStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    REPLIED = "replied"


class BlacklistType(str, Enum):
    DOMAIN = "domain"
    COMPANY_NAME = "company_name"
    PHONE = "phone"
    EMAIL = "email"


class Lead(SQLModel, table=True):
    """Lead model - potential customers."""
    __tablename__ = "leads"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True
    )
    company_name: str = Field(max_length=255, index=True)
    email: Optional[str] = Field(default=None, max_length=255, unique=True, index=True)
    phone: Optional[str] = Field(default=None, max_length=50, index=True)
    instagram_url: Optional[str] = Field(default=None)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    website_url: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    status: LeadStatus = Field(default=LeadStatus.COLD, index=True)
    last_step_completed: Optional[int] = Field(default=None)
    source: str = Field(default="googlemaps", max_length=100, index=True)
    premium_score: int = Field(default=0, ge=0, le=10)
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    interactions: List["Interaction"] = Relationship(back_populates="lead")


class Interaction(SQLModel, table=True):
    """Interaction model - communication history."""
    __tablename__ = "interactions"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True
    )
    lead_id: str = Field(foreign_key="leads.id", index=True)
    channel: ChannelType
    step: int = Field(ge=0, le=2)
    message_template: Optional[str] = Field(default=None, max_length=100)
    message_content: Optional[str] = Field(default=None)
    sent_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    status: InteractionStatus = Field(default=InteractionStatus.SENT, index=True)
    external_id: Optional[str] = Field(default=None, max_length=255)
    error_message: Optional[str] = Field(default=None)
    
    # Relationships
    lead: Optional[Lead] = Relationship(back_populates="interactions")


class Blacklist(SQLModel, table=True):
    """Blacklist model - blocked entities."""
    __tablename__ = "blacklist"
    
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True
    )
    type: BlacklistType
    value: str = Field(max_length=255, index=True)
    reason: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    class Config:
        # Ensure unique combination of type and value
        schema_extra = {
            "indexes": [
                {"fields": ["type", "value"], "unique": True}
            ]
        }
