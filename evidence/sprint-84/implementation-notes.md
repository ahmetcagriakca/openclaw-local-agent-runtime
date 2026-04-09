# S84 Implementation Notes

## T-84.01: OAuth2/OIDC Provider Integration
- Created `agent/auth/oauth_provider.py`: OAuthProvider protocol, GitHubOAuthProvider, GenericOAuthProvider
- Config: env vars (VEZIR_OAUTH_*) or config/oauth.json, with auto-detection
- CSRF state tokens: generate/validate with 10-minute TTL, auto-prune stale entries
- Created `agent/auth/jwt_tokens.py`: HS256 JWT, access (1h) + refresh (7d), rotation on refresh
- Token revocation: in-memory JTI set, consumed on validation
- Created `agent/api/auth_api.py`: 6 endpoints (/config, /login, /callback, /refresh, /logout, /me)
- Wired to server.py with `app.include_router(auth_router)`

## T-84.02: RBAC
- Created `agent/auth/rbac.py`: 3 roles (admin > operator > viewer), 21 permissions
- Permission matrix: viewer=read-only, operator=read+mutations, admin=all+system
- Role mapping: config/role-mappings.json with provider/field/value matching
- Upgraded `agent/auth/middleware.py`: `AuthenticatedUser` dataclass, dual API key + JWT validation
- Added `require_admin` dependency for admin-only endpoints
- `has_minimum_role()` for hierarchy checks

## T-84.03: Frontend Auth Flow
- Updated `AuthContext.tsx`: unified OAuth + API key state, auto-refresh interval (50 min)
- Updated `LoginPage.tsx`: SSO button (GitHub OAuth), API key form, callback handler
- Created `ProtectedRoute.tsx`: route guard with role check, redirect to /login
- Updated `App.tsx`: AuthProvider wraps SSEProvider, all routes protected
- Updated `SessionManager.tsx`: shows role badge, provider, email
- Updated `LoginPage.test.tsx` and `SessionManager.test.tsx` for new interfaces

## T-84.04: Migration + Backward Compatibility
- .gitignore: .jwt_secret, oauth.json, auth.json excluded
- .env.example: all VEZIR_OAUTH_*, VEZIR_SSO_ENABLED, VEZIR_JWT_SECRET documented
- VEZIR_AUTH_BYPASS=1 still bypasses all auth (tested)
- Existing API keys work unchanged (tested with 55 legacy tests)
- SSO_ENABLED=0 disables OAuth gracefully (tested)
