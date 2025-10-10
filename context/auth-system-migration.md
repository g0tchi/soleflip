# Authentication System Migration (v2.2.6)

**Date**: 2025-10-08
**Migration Status**: ✅ JWT Auth Removed, ⏳ API Key System Pending

## Overview

The SoleFlipper API authentication system is being migrated from JWT-based authentication to API Key authentication. This change was driven by:

1. **Service-to-Service Communication**: The API primarily serves automated systems (Budibase, n8n, Metabase) rather than end users
2. **Complexity vs. Value**: JWT auth with token refresh/blacklisting added unnecessary complexity for our use case
3. **Auth Blocker**: JWT implementation had enum validation issues preventing endpoint testing
4. **User Request**: Explicit decision to simplify and use API Keys instead

## What Was Removed (Step 1 & 2: Complete)

### 1. JWT Auth Dependencies from All Endpoints

**Files Modified** (Step 1):
- `domains/orders/api/router.py` - Removed auth from `/active` endpoint
- `domains/auth/api/router.py` - Updated `/me` to return 501 during migration
- `domains/inventory/api/router.py` - Removed all auth dependencies
- `domains/suppliers/api/account_router.py` - Updated audit logging to use "system" instead of user IDs
- `domains/admin/api/router.py` - Removed admin auth checks
- `domains/integration/api/commerce_intelligence_router.py` - Removed auth
- `domains/integration/api/quickflip_router.py` - Removed auth
- `domains/integration/api/webhooks.py` - Removed commented auth dependency
- `domains/integration/api/upload_router.py` - Already had no auth (left as-is)

**Changes Made**:
- Removed all `require_authenticated_user` dependencies
- Removed all `require_admin_role` dependencies
- Removed imports of `shared.auth.dependencies`
- Total: 32 occurrences removed from 9 files

### 2. JWT Middleware and Blacklist System

**main.py Changes** (Step 2):
```python
# REMOVED:
from shared.auth.token_blacklist import initialize_token_blacklist, shutdown_token_blacklist

# REMOVED from lifespan startup:
await initialize_token_blacklist(redis_client)

# REMOVED from lifespan shutdown:
await shutdown_token_blacklist()
```

**Impact**: API now starts without initializing JWT token blacklist system.

### 3. Preserved Files (Not Deleted)

The following JWT auth files were **NOT deleted** to preserve implementation details for reference:
- `shared/auth/jwt_handler.py` - JWT token creation/validation logic
- `shared/auth/token_blacklist.py` - Token blacklist with Redis support
- `shared/auth/dependencies.py` - Auth dependency injection functions
- `shared/auth/models.py` - User, UserRole, TokenPayload models
- `shared/auth/password_hasher.py` - Password hashing utilities

**Reason**: These may be useful reference if we need to restore JWT auth or migrate select features.

### 4. Auth Endpoints (Preserved)

**`domains/auth/api/router.py`** endpoints remain active:
- `POST /auth/login` - Still functional (returns JWT tokens, but tokens aren't checked)
- `POST /auth/register` - Still functional (creates users)
- `GET /auth/me` - Returns HTTP 501 with migration notice
- `POST /auth/logout` - Returns success (no actual logout logic needed)
- `GET /auth/users` - Still functional (lists users)
- `PATCH /auth/users/{id}/activate` - Still functional
- `PATCH /auth/users/{id}/deactivate` - Still functional

**Reason**: User management endpoints may be useful for managing API key owners later.

## Known Issues with Old JWT System

### Enum Validation Failure

**Error**:
```
'admin' is not among the defined enum values. Enum name: userrole.
Possible values: ADMIN, USER, READONLY
```

**Root Cause**:
- Database `users.role` column has lowercase enum values: `'admin'`, `'user'`, `'readonly'`
- Python `UserRole` enum has uppercase names with lowercase values: `UserRole.ADMIN = "admin"`
- Pydantic validation failed when converting DB model to response model
- This happened in `domains/auth/api/router.py:77`: `UserResponse.model_validate(user)`

**Impact**: Login endpoint was completely broken - no users could authenticate.

## Migration Plan (Remaining Steps)

### Step 3: Document Removed Auth System ✅ (This Document)

### Step 4: Create API Key Database Model and Migration ⏳

**Requirements**:
- New table: `auth.api_keys`
- Fields:
  - `id` (UUID, PK)
  - `key_hash` (VARCHAR, indexed) - Hashed API key (don't store plaintext)
  - `name` (VARCHAR) - Friendly name (e.g., "Budibase Production")
  - `description` (TEXT, nullable)
  - `service` (VARCHAR) - Service identifier (e.g., "budibase", "n8n", "metabase")
  - `scopes` (JSONB) - Permission scopes (e.g., `["read:orders", "write:inventory"]`)
  - `is_active` (BOOLEAN, default true)
  - `created_by` (UUID, FK to users) - Who created this key
  - `created_at` (TIMESTAMP)
  - `last_used_at` (TIMESTAMP, nullable)
  - `expires_at` (TIMESTAMP, nullable)

**Alembic Migration**:
```bash
alembic revision --autogenerate -m "Create API keys table for service authentication"
```

### Step 5: Implement API Key Validation Middleware ⏳

**Create**: `shared/auth/api_key_handler.py`

**Responsibilities**:
- Extract API key from `X-API-Key` header
- Hash and lookup key in database
- Validate key is active and not expired
- Update `last_used_at` timestamp
- Inject service context into request state

**Middleware**: `shared/security/api_key_middleware.py`

**Behavior**:
- Check `X-API-Key` header on all requests (except health/docs)
- Return 401 if missing or invalid
- Return 403 if key is inactive/expired
- Attach service info to `request.state` for logging/audit

### Step 6: Create API Key Management Endpoints ⏳

**New Router**: `domains/auth/api/api_key_router.py`

**Endpoints**:
- `POST /auth/api-keys` - Create new API key (returns plaintext key once)
- `GET /auth/api-keys` - List all API keys (hashed, no plaintext)
- `GET /auth/api-keys/{id}` - Get single API key details
- `PATCH /auth/api-keys/{id}` - Update API key (name, scopes, expiration)
- `DELETE /auth/api-keys/{id}` - Delete/revoke API key
- `PATCH /auth/api-keys/{id}/rotate` - Rotate API key (invalidate old, create new)

**Security**:
- Only show full plaintext API key once during creation
- All subsequent views show only last 8 characters for identification
- Log all API key operations for audit trail

### Step 7: Generate Initial API Keys ⏳

**Script**: `scripts/generate_initial_api_keys.py`

**Keys to Generate**:
```python
services = [
    {
        "name": "Budibase Production",
        "service": "budibase",
        "scopes": ["read:*", "write:inventory", "write:suppliers"],
    },
    {
        "name": "n8n Automation",
        "service": "n8n",
        "scopes": ["read:*", "write:integration"],
    },
    {
        "name": "Metabase Analytics",
        "service": "metabase",
        "scopes": ["read:*"],
    },
]
```

**Output**: Print API keys to console for manual configuration in services.

### Step 8: Test API Key Authentication ⏳

**Test Scenarios**:
1. ✅ Valid API key in header → Request succeeds
2. ✅ Missing API key → 401 Unauthorized
3. ✅ Invalid API key → 401 Unauthorized
4. ✅ Expired API key → 403 Forbidden
5. ✅ Inactive API key → 403 Forbidden
6. ✅ API key with insufficient scopes → 403 Forbidden
7. ✅ `last_used_at` timestamp updates on each use

**Test Endpoints**:
- `GET /api/v1/orders/active` (with valid Budibase key)
- `GET /health` (should not require API key)
- `GET /docs` (should not require API key)

### Step 9: Document New API Key System ⏳

**Documentation Needed**:
- Update `CLAUDE.md` with API key setup instructions
- Create `docs/guides/api_key_setup.md` with detailed guide
- Add API key example to Budibase/n8n integration docs
- Update OpenAPI/Swagger docs with security scheme

### Step 10: Create Git Commit ⏳

**Commit Message**:
```
feat: Replace JWT auth with API Key authentication (v2.2.6)

BREAKING CHANGE: JWT authentication has been removed and replaced with API Key authentication.

What Changed:
- Removed JWT auth dependencies from all API endpoints (32 occurrences in 9 files)
- Removed JWT token blacklist initialization from main.py
- Removed all require_authenticated_user and require_admin_role dependencies
- Updated /auth/me endpoint to return 501 during migration
- Updated supplier account audit logging to use "system" instead of user IDs

Why:
- Simplified service-to-service authentication
- Removed complexity of JWT token refresh/blacklisting
- Fixed blocking enum validation issues in old auth system
- Better suited for automated systems (Budibase, n8n, Metabase)

Migration Path:
- API Key system implemented (see context/auth-system-migration.md)
- Initial API keys generated for services
- All endpoints now use X-API-Key header for authentication

Files Modified:
- main.py
- domains/orders/api/router.py
- domains/auth/api/router.py
- domains/inventory/api/router.py
- domains/suppliers/api/account_router.py
- domains/admin/api/router.py
- domains/integration/api/commerce_intelligence_router.py
- domains/integration/api/quickflip_router.py
- domains/integration/api/webhooks.py

Docs:
- context/auth-system-migration.md
```

## Security Considerations

### API Key Storage

**DO**:
✅ Store only hashed API keys in database (use bcrypt/argon2)
✅ Generate cryptographically secure random keys (32+ bytes)
✅ Show plaintext key only once during creation
✅ Use indexed hash column for fast lookup
✅ Implement rate limiting per API key
✅ Log all API key usage with service/endpoint

**DON'T**:
❌ Store plaintext API keys in database
❌ Use predictable patterns for key generation
❌ Return full keys in list/get endpoints
❌ Allow keys without expiration dates in production
❌ Skip rate limiting (prevents abuse)

### API Key Rotation

**Best Practices**:
- Implement key rotation every 90 days
- Support overlapping validity periods during rotation
- Provide rotation endpoint: `PATCH /auth/api-keys/{id}/rotate`
- Notify service owners before expiration
- Log all rotation events for audit

### Scope-Based Permissions

**Scope Format**: `<action>:<resource>`

**Examples**:
- `read:orders` - Read orders only
- `write:inventory` - Create/update inventory
- `read:*` - Read all resources
- `write:*` - Write all resources (use sparingly)

**Validation**: Check scopes in middleware before calling endpoint handler.

## Rollback Plan

If API Key system fails, JWT auth can be restored:

1. **Revert main.py changes**:
   ```python
   from shared.auth.token_blacklist import initialize_token_blacklist, shutdown_token_blacklist
   # Re-add initialization/shutdown calls
   ```

2. **Restore endpoint dependencies**:
   - Add back `require_authenticated_user` imports
   - Add back `current_user = Depends(require_authenticated_user)` parameters

3. **Fix enum validation issue** (if needed):
   - Update `UserResponse` model to handle enum conversion
   - OR update database enum values to uppercase
   - OR add custom Pydantic validator for role field

4. **Restart API**: `make dev`

**Note**: User data (users table) is preserved, so JWT auth would work immediately after rollback.

## Timeline

- **2025-10-08 05:00**: JWT auth removal started
- **2025-10-08 05:45**: Step 1 complete (endpoint auth removed)
- **2025-10-08 06:00**: Step 2 complete (middleware removed)
- **2025-10-08 06:15**: Step 3 complete (this documentation)
- **TBD**: Steps 4-10 (API Key implementation)

## Related Files

### Modified Files (Steps 1-2)
- `main.py`
- `domains/orders/api/router.py`
- `domains/auth/api/router.py`
- `domains/inventory/api/router.py`
- `domains/suppliers/api/account_router.py`
- `domains/admin/api/router.py`
- `domains/integration/api/commerce_intelligence_router.py`
- `domains/integration/api/quickflip_router.py`
- `domains/integration/api/webhooks.py`

### Preserved Files (Reference Only)
- `shared/auth/jwt_handler.py`
- `shared/auth/token_blacklist.py`
- `shared/auth/dependencies.py`
- `shared/auth/models.py`
- `shared/auth/password_hasher.py`
- `shared/security/middleware.py` (other security features preserved)

### New Files (To Be Created)
- `shared/auth/api_key_handler.py`
- `shared/security/api_key_middleware.py`
- `domains/auth/api/api_key_router.py`
- `scripts/generate_initial_api_keys.py`
- `alembic/versions/XXXX_create_api_keys_table.py`
- `docs/guides/api_key_setup.md`

## Testing Notes

### Testing Endpoints Without Auth (Current State)

All endpoints are currently **unprotected** during migration:

```bash
# These work without any authentication (temporary):
curl http://localhost:8000/api/v1/orders/active
curl http://localhost:8000/api/v1/inventory/products
curl http://localhost:8000/api/v1/suppliers/accounts
```

**⚠️ WARNING**: Do not deploy to production in this state. API is completely open during migration.

### Testing with API Keys (After Implementation)

```bash
# With API key:
curl -H "X-API-Key: sk_live_abc123..." http://localhost:8000/api/v1/orders/active

# Without API key (should fail):
curl http://localhost:8000/api/v1/orders/active
# Expected: 401 Unauthorized
```

## References

- **Original Issue**: JWT enum validation error blocking `/orders/active` endpoint testing
- **User Request**: "ist das sicher wenn wir mit api keys arbeiten? dann kann das ganze auth kram vor erst weg"
- **Decision**: "wäre es nicht sinnvoll erst das alte auth system zu enfernen?!" → Remove first, then rebuild
- **Context File**: This document
- **Version**: v2.2.6
