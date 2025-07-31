# mcp_plexus/tenants/models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TenantBase(BaseModel):
    """Base model containing common tenant fields shared across operations."""
    tenant_name: str
    status: str = Field(
        default="active", 
        description="Tenant status (e.g., active, inactive)"
    )
    settings_json: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="JSON blob for tenant-specific settings"
    )


class TenantCreate(TenantBase):
    """Model for tenant creation requests, includes entity_id as required field."""
    entity_id: str = Field(
        description="Unique identifier for the tenant (URL slug, etc.)"
    )


class TenantUpdate(BaseModel):
    """Model for partial tenant updates - all fields are optional."""
    tenant_name: Optional[str] = None
    status: Optional[str] = None
    settings_json: Optional[Dict[str, Any]] = None


class TenantInDBBase(TenantBase):
    """Base model for tenant records stored in database, includes system fields."""
    entity_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class Tenant(TenantInDBBase):
    """Model for tenant data in API responses."""
    pass


class TenantInDB(TenantInDBBase):
    """Model for tenant data as stored in database."""
    pass


class TenantConfigCreate(BaseModel):
    """Request model for creating a new tenant configuration."""
    entity_id: str = Field(description="The tenant's entity ID")
    config_id: str = Field(description="Unique identifier for the config within the tenant")
    config_name: str = Field(description="Human-readable name for the config")
    config_type: str = Field(default="profile", description="Type of config (e.g., 'profile', 'workspace')")
    is_default: bool = Field(default=False, description="Whether this is the default config for the tenant")
    settings_json: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuration settings as JSON")


class TenantConfigUpdate(BaseModel):
    """Request model for updating an existing tenant configuration."""
    config_name: Optional[str] = Field(None, description="Updated human-readable name for the config")
    config_type: Optional[str] = Field(None, description="Updated config type")
    is_default: Optional[bool] = Field(None, description="Whether this should be the default config")
    settings_json: Optional[Dict[str, Any]] = Field(None, description="Updated configuration settings")


class TenantConfigInDB(BaseModel):
    """Database model representing a tenant configuration with all stored fields."""
    entity_id: str
    config_id: str
    config_name: str
    config_type: str
    is_default: bool
    settings_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TenantConfigResponse(BaseModel):
    """Response model for tenant configuration API endpoints."""
    entity_id: str
    config_id: str
    config_name: str
    config_type: str
    is_default: bool
    settings_json: Dict[str, Any]
    created_at: str  # ISO format for API responses
    updated_at: str  # ISO format for API responses