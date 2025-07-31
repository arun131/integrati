# New Tenant-Level OAuth Architecture

## Overview

The Integrati backend has been refactored from a **user-level OAuth** system to a **tenant-level OAuth** system with **multiple configs/profiles** per tenant. This provides a more realistic and scalable architecture where:

- **One human user = One tenant** with multiple profiles/configurations
- **OAuth tokens are shared** across all configs within a tenant  
- **Simplified OAuth management** - authorize once, use everywhere
- **Better UX** - no need to re-authenticate for each config

---

## Architecture Changes

### **Before (Old Architecture)**
```
Tenant → Multiple Users → Each User has OAuth tokens
```

### **After (New Architecture)**  
```
Tenant (Human User) → Multiple Configs/Profiles → Tenant has OAuth tokens (shared across all configs)
```

---

## Database Schema Changes

### **New Tables Added**

#### 1. `tenant_external_oauth_tokens`
Stores OAuth tokens at the tenant level (shared across all configs):
```sql
CREATE TABLE tenant_external_oauth_tokens (
    entity_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    token_data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, provider_name)
);
```

#### 2. `tenant_configs`
Stores configs/profiles for each tenant:
```sql
CREATE TABLE tenant_configs (
    entity_id TEXT NOT NULL,
    config_id TEXT NOT NULL,
    config_name TEXT NOT NULL,
    config_type TEXT NOT NULL DEFAULT 'profile',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    settings_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, config_id)
);
```

### **Legacy Tables (Maintained for Compatibility)**
- `user_external_oauth_tokens` - Legacy user-level tokens
- `plexus_user_auth_tokens` - User authentication (now represents configs)

---

## Updated Workflow

### **1. Admin Creates Tenant**
```http
POST /admin/tenants/
```
**Response:** Returns `entity_id` for the new tenant

### **2. System Creates Base Config** 
```http
POST /{entity_id}/plexus-auth/register-base-config
```
- Creates a default "base" config for the tenant
- Generates auth token for the base config
- Config ID: `"base"`, serves as the default profile

### **3. Tenant Initiates OAuth** 
```http
GET /gmail/login
Authorization: Bearer {plexus_user_auth_token}
```
- **State parameter:** Only contains `entity_id` (no user_id)
- OAuth tokens stored at tenant level
- Available to all configs within the tenant

### **4. OAuth Callback Processing**
```http
GET /gmail/callback?code={code}&state={entity_id}
```
- Parses state to get only `entity_id`
- Stores tokens in `tenant_external_oauth_tokens` table
- Tokens shared across all tenant configs

### **5. Create Additional Configs** (Optional)
```http
POST /{entity_id}/configs/
```
- Create additional profiles for the same human user
- Each config uses the same OAuth tokens
- Different preferences/settings per config

---

## API Endpoints

### **Tenant Management**
```http
# Create tenant
POST /admin/tenants/

# List tenants  
GET /admin/tenants/

# Get specific tenant
GET /admin/tenants/{entity_id}

# Update tenant
PUT /admin/tenants/{entity_id}

# Delete tenant
DELETE /admin/tenants/{entity_id}
```

### **Config Management**
```http
# Create config for tenant
POST /{entity_id}/configs/

# List configs for tenant
GET /{entity_id}/configs/

# Get specific config
GET /{entity_id}/configs/{config_id}

# Update config
PUT /{entity_id}/configs/{config_id}

# Delete config
DELETE /{entity_id}/configs/{config_id}

# Set default config
POST /{entity_id}/configs/{config_id}/set-default
```

### **Authentication & OAuth**
```http
# Register base config for tenant
POST /{entity_id}/plexus-auth/register-base-config

# Start Gmail OAuth (tenant-level)
GET /gmail/login
Authorization: Bearer {plexus_user_auth_token}

# OAuth callback
GET /gmail/callback?code={code}&state={entity_id}

# Check OAuth status
GET /gmail/status
Authorization: Bearer {plexus_user_auth_token}
```

### **Frontend Integration**
```http
# List integrations (supports both architectures)
GET /integrations

# Get integration status  
GET /integrations/{integration_name}/status

# Start OAuth flow (redirects to tenant-level)
POST /integrations/{integration_name}/auth

# Disconnect integration
DELETE /integrations/{integration_name}
```

---

## Code Architecture

### **New Components**

#### 1. **Tenant External Token Store**
- `AbstractTenantExternalTokenStore` - Interface
- `SQLiteTenantExternalTokenStore` - SQLite implementation
- Manages OAuth tokens at tenant level

#### 2. **Tenant Config Store**
- `AbstractTenantConfigStore` - Interface  
- `SQLiteTenantConfigStore` - SQLite implementation
- Manages configs/profiles within tenants

#### 3. **Unified OAuth Token Service**
- `UnifiedOAuthTokenService` - Provides unified access to both user-level and tenant-level tokens
- Supports backward compatibility during transition
- Prefer tenant-level tokens, fallback to user-level

#### 4. **Updated Auth Classes**
- `UnifiedGmailAuth` - Supports both token storage types
- Factory functions for different modes (legacy, tenant-level, unified)

### **Key Files**

```
mcp_plexus/
├── oauth/
│   ├── sqlite_tenant_external_token_store.py    # NEW: Tenant token storage
│   ├── unified_token_service.py                 # NEW: Unified token access
│   └── storage_interfaces.py                    # Updated with tenant interfaces
├── tenants/
│   ├── sqlite_tenant_config_store.py            # NEW: Config storage  
│   ├── models.py                                # Updated with config models
│   ├── storage_interfaces.py                    # Updated with config interfaces
│   └── endpoints.py                             # Updated with config endpoints
├── integrations/
│   └── gmail/
│       └── unified_auth.py                      # NEW: Unified Gmail auth
├── gmail_oauth/
│   └── endpoints.py                             # Updated for tenant-level OAuth
├── plexus_auth/
│   └── endpoints.py                             # Added base config registration
└── storage/
    └── sqlite_base.py                           # Updated schema
```

---

## Benefits of New Architecture

### ✅ **Simplified OAuth Management**
- One OAuth flow per service per tenant
- No need to re-authenticate for each config
- Centralized token storage and refresh

### ✅ **Realistic User Model** 
- One human = one tenant with multiple profiles
- Configs represent different personalities/settings
- More intuitive than multiple "users" per tenant

### ✅ **Better Scalability**
- Reduced OAuth API calls  
- Fewer tokens to manage and refresh
- Simplified permission model

### ✅ **Improved UX**
- User authorizes once, works everywhere
- Seamless switching between configs
- No OAuth re-authentication needed

### ✅ **Cleaner Architecture**
- Clear separation: tenant (identity) vs config (preferences)  
- Shared resources (OAuth) vs individual settings
- More maintainable codebase

---

## Usage Examples

### **Creating a Tenant with Base Config**

```python
# 1. Admin creates tenant
POST /admin/tenants/
{
    "entity_id": "tenant_123",
    "tenant_name": "John Doe",
    "status": "active"
}

# 2. Register base config  
POST /tenant_123/plexus-auth/register-base-config
Headers: X-Host-App-Secret: {secret}
{
    "user_id_from_host_app": "john_doe_id"
}

# Response:
{
    "plexus_user_auth_token": "auth_token_here",
    "persistent_user_id": "base",
    "message": "Base config registered and user token created successfully."
}
```

### **OAuth Authorization Flow**

```python
# 1. Start OAuth (tenant-level)
GET /gmail/login
Headers: Authorization: Bearer {auth_token}

# Redirects to Google with state=tenant_123

# 2. User authorizes, Google redirects back
GET /gmail/callback?code=auth_code&state=tenant_123

# 3. System stores tokens at tenant level
# All configs can now use Gmail tools
```

### **Creating Additional Configs**

```python
# Create additional config for same tenant
POST /tenant_123/configs/
Headers: X-Admin-API-Key: {admin_key}
{
    "entity_id": "tenant_123",
    "config_id": "work_profile", 
    "config_name": "Work Profile",
    "config_type": "profile",
    "is_default": false,
    "settings_json": {
        "email_signature": "Best regards, John Doe",
        "default_timezone": "America/New_York"
    }
}
```

### **Using Unified Token Service**

```python
from mcp_plexus.oauth.unified_token_service import get_unified_oauth_token_service

# Get tokens (tries tenant-level first, falls back to user-level)
unified_service = await get_unified_oauth_token_service()
tokens = await unified_service.get_oauth_tokens(
    entity_id="tenant_123",
    user_id="base", 
    provider_name="gmail",
    prefer_tenant_level=True  # Default
)

# Save tokens (to tenant-level storage)
success = await unified_service.save_oauth_tokens(
    entity_id="tenant_123",
    user_id="base",
    provider_name="gmail", 
    token_data=token_data,
    use_tenant_level=True  # Default
)
```

---

## Backward Compatibility

The new architecture maintains backward compatibility through:

### **1. Unified Token Service**
- Checks tenant-level tokens first
- Falls back to user-level tokens if needed
- Transparent to existing code

### **2. Dual Storage Support**
- Both user-level and tenant-level token tables exist
- Legacy endpoints continue to work
- Gradual transition possible

### **3. Config-as-User Model**
- Configs use the same authentication system
- `persistent_user_id` now represents config_id
- Existing auth flows continue working

---

## Testing the Implementation

### **1. Create a Tenant**
```bash
curl -X POST "http://localhost:8000/admin/tenants/" \
  -H "X-Admin-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "test_tenant",
    "tenant_name": "Test User",
    "status": "active"
  }'
```

### **2. Register Base Config**
```bash
curl -X POST "http://localhost:8000/test_tenant/plexus-auth/register-base-config" \
  -H "X-Host-App-Secret: your-host-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id_from_host_app": "test_user_123"
  }'
```

### **3. Test OAuth Flow**
```bash
# Use the token from step 2
curl -X GET "http://localhost:8000/gmail/login" \
  -H "Authorization: Bearer {token_from_step_2}"

# Follow the OAuth flow in browser
# Check status after authorization
curl -X GET "http://localhost:8000/gmail/status" \
  -H "Authorization: Bearer {token_from_step_2}"
```

### **4. Create Additional Config**
```bash
curl -X POST "http://localhost:8000/test_tenant/configs/" \
  -H "X-Admin-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "test_tenant",
    "config_id": "work_config",
    "config_name": "Work Profile", 
    "config_type": "profile",
    "is_default": false,
    "settings_json": {}
  }'
```

---

## Summary

This refactor provides a more realistic, scalable, and maintainable OAuth architecture that better reflects how users actually interact with the system. The tenant-level OAuth with multiple configs approach simplifies management while providing flexibility for different use cases and preferences.

The implementation maintains backward compatibility and provides smooth migration paths, making it safe to deploy in production environments. 