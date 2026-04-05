"""WMCP credential API — B-010.

Credential management endpoints for WMCP proxy.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.middleware import require_operator
from services.wmcp_credential_manager import (
    WmcpCredentialError,
    WmcpCredentialManager,
)

router = APIRouter(tags=["wmcp-credentials"])

_manager: WmcpCredentialManager | None = None


def _get_manager() -> WmcpCredentialManager:
    global _manager
    if _manager is None:
        _manager = WmcpCredentialManager()
    return _manager


class CredentialRegisterRequest(BaseModel):
    credential_type: str = Field(..., pattern="^(api_key|proxy_token|bridge_secret)$")
    secret_value: str = Field(..., min_length=1)
    description: str = ""
    expires_at: str = ""


class CredentialRotateRequest(BaseModel):
    credential_type: str = Field(..., pattern="^(api_key|proxy_token|bridge_secret)$")
    new_secret: str = Field(..., min_length=1)
    expires_at: str = ""


class CredentialVerifyRequest(BaseModel):
    credential_type: str = Field(..., pattern="^(api_key|proxy_token|bridge_secret)$")
    test_value: str = Field(..., min_length=1)


@router.get("/wmcp/credentials/status")
async def wmcp_credential_status():
    """Get WMCP credential status summary."""
    mgr = _get_manager()
    return mgr.status()


@router.get("/wmcp/credentials")
async def list_wmcp_credentials(
    credential_type: str | None = None,
    active_only: bool = False,
):
    """List WMCP credentials (metadata only, no secrets)."""
    mgr = _get_manager()
    creds = mgr.list_credentials(
        credential_type=credential_type,
        active_only=active_only,
    )
    return {"credentials": creds, "total": len(creds)}


@router.post("/wmcp/credentials/register")
async def register_wmcp_credential(req: CredentialRegisterRequest, _operator=Depends(require_operator)):
    """Register a new WMCP credential."""
    mgr = _get_manager()
    try:
        cred = mgr.register(
            credential_type=req.credential_type,
            secret_value=req.secret_value,
            description=req.description,
            expires_at=req.expires_at,
        )
        from dataclasses import asdict
        return {"status": "registered", "credential": asdict(cred)}
    except WmcpCredentialError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wmcp/credentials/rotate")
async def rotate_wmcp_credential(req: CredentialRotateRequest, _operator=Depends(require_operator)):
    """Rotate a WMCP credential (deactivate old, register new)."""
    mgr = _get_manager()
    try:
        cred = mgr.rotate(
            credential_type=req.credential_type,
            new_secret=req.new_secret,
            expires_at=req.expires_at,
        )
        from dataclasses import asdict
        return {"status": "rotated", "credential": asdict(cred)}
    except WmcpCredentialError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wmcp/credentials/verify")
async def verify_wmcp_credential(req: CredentialVerifyRequest, _operator=Depends(require_operator)):
    """Verify if a value matches the active credential."""
    mgr = _get_manager()
    return mgr.verify(
        credential_type=req.credential_type,
        test_value=req.test_value,
    )


@router.post("/wmcp/credentials/migrate")
async def migrate_wmcp_credentials(_operator=Depends(require_operator)):
    """Migrate WMCP credentials from environment variables to SecretStore."""
    mgr = _get_manager()
    migrated = mgr.migrate_from_env()
    return {
        "status": "completed",
        "migrated": migrated,
        "count": len(migrated),
    }
