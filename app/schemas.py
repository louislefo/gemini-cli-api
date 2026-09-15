from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class PromptRequest(BaseModel):
    """Request payload for sending a prompt to Gemini."""

    prompt: str = Field(
        ...,
        min_length=1,
        description="The prompt message or instruction to send to Gemini",
    )
    new_chat: bool = Field(
        default=False,
        description="Whether to start a fresh new conversation before sending the prompt",
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=5,
        le=600,
        description="Maximum execution timeout in seconds for this request",
    )
    model: str | None = Field(
        default=None,
        description="Optional model identifier to select (e.g., 'pro', 'flash', 'flash-lite', 'thinking')",
    )


class ModelInfo(BaseModel):
    """Information regarding an available Gemini model."""

    id: str = Field(..., description="Normalized model identifier")
    name: str = Field(..., description="Full display name in Gemini")
    is_active: bool = Field(default=False, description="Indicates if this model is currently active")


class ModelsResponse(BaseModel):
    """List of available models and currently active model."""

    current_model: str = Field(..., description="Currently selected model")
    models: list[ModelInfo] = Field(default_factory=list, description="List of supported Gemini models")


class ModelSelectRequest(BaseModel):
    """Request payload for selecting a model."""

    model: str = Field(..., description="Model name or identifier to select (e.g. 'pro', 'flash', 'flash-lite', 'thinking')")


class ModelSelectResponse(BaseModel):
    """Response payload for model selection."""

    status: str = "success"
    current_model: str = Field(..., description="Name of the newly active model")
    message: str


class ConversationInfo(BaseModel):
    """Information regarding a saved Gemini conversation."""

    id: str = Field(..., description="Unique conversation identifier")
    title: str = Field(..., description="Conversation title")
    url: str = Field(..., description="Full URL to the conversation")


class ConversationsResponse(BaseModel):
    """List of conversation history entries from Gemini."""

    total: int = Field(..., description="Total number of conversations found")
    conversations: list[ConversationInfo] = Field(default_factory=list)


class ConversationSelectResponse(BaseModel):
    """Response payload for loading/resuming a conversation."""

    status: str = "success"
    conversation_id: str
    title: str
    url: str
    message: str


class UsageMetricsResponse(BaseModel):
    """Usage limits and quota metrics from Gemini."""

    tier: str = Field(default="PRO", description="Plan tier type (e.g., PRO, FREE, ULTRA)")
    current_usage: str = Field(..., description="Current quota usage text (e.g., '3 % used')")
    current_percent: float = Field(default=0.0, description="Current usage percentage")
    current_reset_time: str = Field(..., description="Current limit reset date or time")
    weekly_usage: str = Field(..., description="Weekly quota usage text (e.g., '1 % used')")
    weekly_percent: float = Field(default=0.0, description="Weekly usage percentage")
    weekly_reset_time: str = Field(..., description="Weekly reset date or time")
    description: str | None = Field(default=None, description="General plan tier description")


class ChatResponse(BaseModel):
    """Structured response returned by the API."""

    response: str = Field(..., description="Generated text response from Gemini")
    duration_seconds: float = Field(..., description="Total generation duration in seconds")
    status: Literal["success", "error", "timeout"] = Field(
        default="success",
        description="Execution status",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
    )


class OpenAIChatMessage(BaseModel):
    """Standard OpenAI chat message."""

    role: Literal["system", "user", "assistant"] = "user"
    content: str


class OpenAIChatCompletionRequest(BaseModel):
    """Request payload compatible with OpenAI /v1/chat/completions."""

    model: str = Field(default="gemini-web", description="Model identifier")
    messages: list[OpenAIChatMessage] = Field(
        ...,
        min_length=1,
        description="Message history list",
    )
    stream: bool = Field(default=False, description="Enable streaming mode")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class OpenAIChatChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class OpenAIChatChoice(BaseModel):
    index: int = 0
    message: OpenAIChatChoiceMessage
    finish_reason: str = "stop"


class OpenAIChatCompletionResponse(BaseModel):
    """Response payload compatible with OpenAI chat completion."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str = "gemini-web"
    choices: list[OpenAIChatChoice]


class CDPStatusResponse(BaseModel):
    """Health and connection status of the Chrome CDP bridge and Gemini tab."""

    connected: bool = Field(..., description="Indicates if CDP connection succeeded")
    cdp_url: str = Field(..., description="Target CDP URL")
    gemini_tab_found: bool = Field(..., description="Indicates if a Gemini tab was found")
    page_title: str | None = Field(default=None, description="Active Gemini page title")
    url: str | None = Field(default=None, description="Active page URL")
    details: str | None = Field(default=None, description="Diagnostic details or error message")


class HealthResponse(BaseModel):
    """General API health status."""

    status: str = "ok"
    app_name: str
    version: str

