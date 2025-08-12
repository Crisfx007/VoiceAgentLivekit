# 🎙 LiveKit Voice Onboarding Agent

## 📌 Overview
This project is a **real-time voice onboarding assistant** built using [LiveKit](https://livekit.io/) and OpenAI’s GPT-4o models.  
The agent interacts with users entirely in **voice** — introducing your service, collecting onboarding details, validating them, and confirming in real time.

It works just like a human onboarding agent:
- Welcomes the user.
- Asks for **Name, Email, Phone Number, and Country**.
- Validates inputs using **Pydantic**.
- Stores all onboarding data and the **entire conversation** in a per-session JSON file.
- Provides summaries and can re-ask for invalid inputs.
- All communication is in **voice** (both input and output).

---

## ⚙ Tech Stack

### **Framework**
- **[LiveKit Agents SDK](https://github.com/livekit/agents)** — For real-time voice interaction, STT, TTS, and session management.

### **LLM (Language Model)**
- **OpenAI GPT-4o-mini** — For conversation flow, reasoning, and function/tool calling.

### **STT (Speech-to-Text)**
- **OpenAI `gpt-4o-transcribe`** — High accuracy real-time transcription.

### **TTS (Text-to-Speech)**
- **OpenAI `gpt-4o-mini-tts`** — Fast natural-sounding voice synthesis.

### **VAD (Voice Activity Detection)**
- **Silero VAD** — Detects when the user starts and stops speaking.

### **Turn Detection**
- **LiveKit Multilingual Turn Detector** — Ensures proper conversational turn-taking.

### **Validation & Data Storage**
- **Pydantic** — Strong form field validation for name, email, phone, and country.
- **pycountry** — For validating real country names.
- **JSON-based Session Storage** — Saves onboarding state and conversation logs.

---

## 📂 Project Structure

- **agent.py** — Main agent setup and LiveKit session handling  
- **prompts.py** — Prompt instructions for onboarding flow  
- **tools.py** — Onboarding logic, validation, and JSON storage  
- **requirements.txt** — Python dependencies  
- **README.md** — This file  

---

## 🔑 Environment Variables

You must create a `.env` file in the root directory with:

```env
OPENAI_API_KEY=your_openai_api_key_here
LIVEKIT_URL=wss://your_livekit_server_url
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
Explanation:

OPENAI_API_KEY — Required for LLM, STT, and TTS models.

LIVEKIT_URL — WebSocket URL of your LiveKit deployment (e.g., wss://example.livekit.cloud).

LIVEKIT_API_KEY — API key for your LiveKit server.

LIVEKIT_API_SECRET — API secret for your LiveKit server.

🛠 Tool Calling
The LLM uses LiveKit's function_tool decorators to call Python functions like:

validate_field(field, value) — Validate form input.

store_field(field, value) — Store validated input.

save_current_session() — Save the current session to JSON.

get_summary() — Return a summary of all collected onboarding data.

log_message(speaker, text) — Log conversation messages.

This means the LLM can directly call Python functions instead of just generating text.
