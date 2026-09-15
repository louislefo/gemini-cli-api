import json
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_gemini_driver
from app.schemas import (
    ChatResponse,
    ConversationSelectResponse,
    ConversationsResponse,
    ModelSelectRequest,
    ModelSelectResponse,
    ModelsResponse,
    OpenAIChatChoice,
    OpenAIChatChoiceMessage,
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    PromptRequest,
    UsageMetricsResponse,
)
from app.services.gemini_driver import GeminiDriver

router = APIRouter(tags=["Gemini Chat"])


@router.post("/chat/new")
async def start_new_chat(
    driver: GeminiDriver = Depends(get_gemini_driver),
):
    """Starts a fresh new conversation session on Gemini."""
    try:
        await driver.reset_session()
        return {"status": "success", "message": "New conversation initialized on Gemini."}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting session: {exc}",
        ) from exc


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    driver: GeminiDriver = Depends(get_gemini_driver),
) -> ModelsResponse:
    """Retrieves the list of available Gemini models and the active model."""
    try:
        data = await driver.get_available_models()
        return ModelsResponse(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching models: {exc}",
        ) from exc


@router.post("/models/select", response_model=ModelSelectResponse)
async def select_model(
    request: ModelSelectRequest,
    driver: GeminiDriver = Depends(get_gemini_driver),
) -> ModelSelectResponse:
    """Switches the active model on Gemini."""
    try:
        result = await driver.set_model(request.model)
        return ModelSelectResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting model: {exc}",
        ) from exc


@router.get("/conversations", response_model=ConversationsResponse)
async def list_conversations(
    driver: GeminiDriver = Depends(get_gemini_driver),
) -> ConversationsResponse:
    """Retrieves previous chat conversations from Gemini sidebar history."""
    try:
        convs = await driver.list_conversations()
        return ConversationsResponse(total=len(convs), conversations=convs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching conversations: {exc}",
        ) from exc


@router.post("/conversations/{conversation_id}/load", response_model=ConversationSelectResponse)
async def load_conversation(
    conversation_id: str,
    driver: GeminiDriver = Depends(get_gemini_driver),
) -> ConversationSelectResponse:
    """Loads and resumes a previous conversation in the active session."""
    try:
        result = await driver.load_conversation(conversation_id)
        return ConversationSelectResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading conversation: {exc}",
        ) from exc


@router.get("/usage", response_model=UsageMetricsResponse)
async def get_usage(
    driver: GeminiDriver = Depends(get_gemini_driver),
) -> UsageMetricsResponse:
    """Retrieves current and weekly quota usage limits from the Gemini account."""
    try:
        data = await driver.get_usage_metrics()
        return UsageMetricsResponse(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching usage metrics: {exc}",
        ) from exc



@router.post("/chat", response_model=ChatResponse)
async def send_chat_prompt(
    request: PromptRequest,
    driver: GeminiDriver = Depends(get_gemini_driver),
) -> ChatResponse:
    """Sends a prompt to Google Gemini and returns the full response in JSON."""
    start_time = time.time()
    try:
        response_text = await driver.send_prompt(
            prompt=request.prompt,
            new_chat=request.new_chat,
            timeout_seconds=request.timeout_seconds,
            model=request.model,
        )
        duration = round(time.time() - start_time, 2)
        return ChatResponse(
            response=response_text,
            duration_seconds=duration,
            status="success",
        )
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during Gemini interaction: {exc}",
        ) from exc


@router.post("/chat/stream")
async def stream_chat_prompt(
    request: PromptRequest,
    driver: GeminiDriver = Depends(get_gemini_driver),
):
    """Sends a prompt and streams the response via Server-Sent Events (SSE)."""

    async def event_generator():
        try:
            final_text = ""
            async for chunk, full_text in driver.stream_prompt(
                prompt=request.prompt,
                new_chat=request.new_chat,
                timeout_seconds=request.timeout_seconds,
                model=request.model,
            ):
                final_text = full_text
                yield {"event": "message", "data": json.dumps({"chunk": chunk, "full_text": full_text})}
            yield {"event": "done", "data": json.dumps({"status": "done", "full_text": final_text})}
            yield {"event": "done", "data": "[DONE]"}
        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(event_generator())


@router.post("/v1/chat/completions", response_model=OpenAIChatCompletionResponse)
async def openai_chat_completions(
    request: OpenAIChatCompletionRequest,
    driver: GeminiDriver = Depends(get_gemini_driver),
):
    """OpenAI Chat Completions standard compatible endpoint."""
    user_prompts = [msg.content for msg in request.messages if msg.role == "user"]
    if not user_prompts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No message with 'user' role found.",
        )

    system_prompts = [msg.content for msg in request.messages if msg.role == "system"]
    prompt_to_send = ""
    if system_prompts:
        prompt_to_send += f"System Instructions: {system_prompts[0]}\n\n"
    prompt_to_send += user_prompts[-1]

    target_model = request.model if request.model != "gemini-web" else None

    if request.stream:
        async def openai_stream():
            req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
            created = int(time.time())
            try:
                async for chunk, _ in driver.stream_prompt(prompt=prompt_to_send, model=target_model):
                    chunk_data = {
                        "id": req_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"

                final_data = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                err_data = {"error": {"message": str(exc), "type": "gemini_error"}}
                yield f"data: {json.dumps(err_data)}\n\n"

        return StreamingResponse(openai_stream(), media_type="text/event-stream")

    try:
        response_text = await driver.send_prompt(prompt=prompt_to_send, model=target_model)
        req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        return OpenAIChatCompletionResponse(
            id=req_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                OpenAIChatChoice(
                    index=0,
                    message=OpenAIChatChoiceMessage(content=response_text),
                    finish_reason="stop",
                )
            ],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

