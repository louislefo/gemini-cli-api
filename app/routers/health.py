from fastapi import APIRouter, Depends
from app.config import settings
from app.schemas import CDPStatusResponse, HealthResponse
from app.dependencies import get_cdp_manager
from app.services.cdp_manager import CDPManager

router = APIRouter(tags=["Status & Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """General availability check for the FastAPI server."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.get("/cdp/status", response_model=CDPStatusResponse)
async def cdp_status(
    cdp: CDPManager = Depends(get_cdp_manager),
) -> CDPStatusResponse:
    """Verifies Chrome CDP connection and checks for an active Gemini tab."""
    status_data = await cdp.check_status()
    return CDPStatusResponse(**status_data)

