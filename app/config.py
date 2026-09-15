from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """FastAPI application and Chrome CDP configuration settings."""

    APP_NAME: str = "Gemini CDP Bridge API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Chrome CDP configuration
    CDP_URL: str = Field(
        default="http://127.0.0.1:9222",
        description="Remote debugging URL for Chrome DevTools Protocol",
    )
    GEMINI_URL: str = Field(
        default="https://gemini.google.com/app",
        description="Base URL for Google Gemini web interface",
    )

    # Timeouts and intervals
    DEFAULT_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Maximum timeout in seconds for Gemini response generation",
    )
    PAGE_LOAD_TIMEOUT_MS: int = Field(
        default=30000,
        description="Initial page load timeout in milliseconds",
    )
    POLL_INTERVAL_MS: int = Field(
        default=300,
        description="DOM polling interval in milliseconds",
    )

    # DOM selectors for Gemini Web
    INPUT_SELECTORS: list[str] = [
        "rich-textarea .ql-editor",
        "div.ql-editor[contenteditable='true']",
        "div[contenteditable='true'][role='textbox']",
        "textarea.text-input-field",
        "textarea",
    ]

    SEND_BUTTON_SELECTORS: list[str] = [
        "button[aria-label*='Envoyer le message']",
        "button[aria-label*='Send message']",
        "button[aria-label*='Envoyer']",
        "button[aria-label*='Send']",
        "button.send-button",
        "button[mattooltip*='Envoyer']",
        "button[mattooltip*='Send']",
    ]

    STOP_BUTTON_SELECTORS: list[str] = [
        "button[aria-label*='Arrêter la réponse']",
        "button[aria-label*='Stop response']",
        "button[aria-label*='Arrêter']",
        "button[aria-label*='Stop']",
    ]

    RESPONSE_CONTAINER_SELECTORS: list[str] = [
        "message-content",
        "model-response",
        ".model-response-text",
        ".response-container",
        "div[data-test-id='model-response']",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

