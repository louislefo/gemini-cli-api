"""Complete test script for the Gemini CDP Bridge API.

This script tests the various endpoints:
1. Server health check (/health)
2. CDP status and active Gemini tab (/cdp/status)
3. Simple prompt test (/chat)
4. Prompt with new chat session (/chat)
5. Real-time streaming SSE test (/chat/stream)
6. OpenAI-compatible format test (/v1/chat/completions)
"""

import json
import time
import urllib.request
import urllib.error


BASE_URL = "http://127.0.0.1:8000"


def print_separator(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health():
    print_separator("1. Test GET /health")
    url = f"{BASE_URL}/health"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            print("Response:", json.dumps(data, indent=2, ensure_ascii=False))
            assert data["status"] == "ok"
            print("Success: Server available.")
    except Exception as e:
        print("Error:", e)


def test_cdp_status():
    print_separator("2. Test GET /cdp/status")
    url = f"{BASE_URL}/cdp/status"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            print("Response:", json.dumps(data, indent=2, ensure_ascii=False))
            if data["connected"]:
                print("Success: CDP connection established with Chrome.")
            else:
                print("Warning: Chrome not connected. Start Chrome on port 9222.")
    except Exception as e:
        print("Error:", e)


def test_chat_simple():
    print_separator("3. Test POST /chat (Simple prompt)")
    url = f"{BASE_URL}/chat"
    payload = {
        "prompt": "Explain the difference between a compiler and an interpreter in 2 short bullet points.",
        "new_chat": False,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"Sending prompt: \"{payload['prompt']}\"")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            elapsed = round(time.time() - start, 2)
            print(f"Duration: {elapsed}s")
            print("Status:", result.get("status"))
            print("\n--- Gemini Response ---")
            print(result.get("response"))
            print("-----------------------")
    except Exception as e:
        print("Error sending prompt:", e)


def test_chat_new_session():
    print_separator("4. Test POST /chat (New session)")
    url = f"{BASE_URL}/chat"
    payload = {
        "prompt": "Give me a philosophical quote and its author.",
        "new_chat": True,
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"Sending with new_chat=True: \"{payload['prompt']}\"")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("\n--- Gemini Response (New chat) ---")
            print(result.get("response"))
            print("----------------------------------")
    except Exception as e:
        print("Error:", e)


def test_chat_stream():
    print_separator("5. Test POST /chat/stream (SSE Streaming)")
    url = f"{BASE_URL}/chat/stream"
    payload = {
        "prompt": "Write a 4-line poem about Python code.",
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"Sending streaming request: \"{payload['prompt']}\"\n")
    print("Receiving stream:")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            for line in response:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data:"):
                    raw_data = decoded[5:].strip()
                    if raw_data == "[DONE]":
                        break
                    try:
                        parsed = json.loads(raw_data)
                        chunk = parsed.get("chunk", "")
                        print(chunk, end="", flush=True)
                    except Exception:
                        pass
            print("\n\nEnd of stream.")
    except Exception as e:
        print("Streaming error:", e)


def test_openai_format():
    print_separator("6. Test POST /v1/chat/completions (OpenAI Format)")
    url = f"{BASE_URL}/v1/chat/completions"
    payload = {
        "model": "gemini-web",
        "messages": [
            {"role": "system", "content": "You are a cybersecurity expert."},
            {"role": "user", "content": "Give 2 basic rules for a strong password."},
        ],
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print("Sending request in standard OpenAI format...")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("Response ID:", result.get("id"))
            print("Model:", result.get("model"))
            content = result["choices"][0]["message"]["content"]
            print("\n--- Response Content ---")
            print(content)
            print("------------------------")
    except Exception as e:
        print("OpenAI format error:", e)


if __name__ == "__main__":
    print("Starting Gemini CDP API tests...")
    test_health()
    test_cdp_status()
    # Uncomment lines below to test with Gemini active:
    # test_chat_simple()
    # test_chat_new_session()
    # test_chat_stream()
    # test_openai_format()
    print("\nInitial tests completed.")

