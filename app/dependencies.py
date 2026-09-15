from app.services.gemini_driver import GeminiDriver, gemini_driver
from app.services.cdp_manager import CDPManager, cdp_manager


def get_gemini_driver() -> GeminiDriver:
    """Provides the singleton instance of GeminiDriver."""
    return gemini_driver


def get_cdp_manager() -> CDPManager:
    """Provides the singleton instance of CDPManager."""
    return cdp_manager

