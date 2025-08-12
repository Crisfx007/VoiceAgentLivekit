import json
import os
from typing import Optional, List, Annotated, Dict
from pydantic import BaseModel, EmailStr, field_validator, Field
import pycountry
from livekit.agents import function_tool

# -------------------
#  Pydantic Validation Model
# -------------------

class UserOnboarding(BaseModel):
    """
    Pydantic model to validate onboarding form fields.
    """
    name: Optional[Annotated[str, Field(
        strip_whitespace=True,
        min_length=2,
        max_length=100
    )]] = None

    email: Optional[EmailStr] = None

    phone: Optional[Annotated[str, Field(
        strip_whitespace=True,
        pattern=r"^\+?[1-9]\d{1,14}$"
    )]] = None

    country: Optional[str] = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v):
        if v is None:
            return v
        countries = {c.name.lower() for c in pycountry.countries}
        if v.lower() not in countries:
            raise ValueError("Invalid country name")
        return v


# -------------------
#  Session-Specific State Management
# -------------------

# Dictionary to hold session-specific data
sessions_data: Dict[str, Dict] = {}

def _get_session_data(session_id: str) -> Dict:
    """Get or create session data for the given session_id"""
    if session_id not in sessions_data:
        sessions_data[session_id] = {
            "onboarding_state": {
                "name": None,
                "email": None,
                "phone": None,
                "country": None
            },
            "conversation_log": []
        }
    return sessions_data[session_id]

def _get_onboarding_state(session_id: str) -> Dict[str, Optional[str]]:
    """Get onboarding state for specific session"""
    return _get_session_data(session_id)["onboarding_state"]

def _get_conversation_log(session_id: str) -> List[Dict[str, str]]:
    """Get conversation log for specific session"""
    return _get_session_data(session_id)["conversation_log"]


# -------------------
#  File Helpers
# -------------------

def _get_session_file(session_id: str) -> str:
    """
    Build the file path for a given session's JSON file.
    """
    return f"session_{session_id}.json"

@function_tool()
async def save_session(session_id: str) -> str:
    """
    Save the current onboarding state and conversation log to a JSON file.

    Args:
        session_id: Unique identifier for the session.

    Returns:
        Confirmation message as string.
    """
    session_data = _get_session_data(session_id)
    data = {
        "session_id": session_id,
        "onboarding_data": session_data["onboarding_state"],
        "conversation": session_data["conversation_log"]
    }
    try:
        with open(_get_session_file(session_id), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Session {session_id} saved with {len(session_data['conversation_log'])} messages")
        return f"Session {session_id} saved successfully"
    except Exception as e:
        print(f"❌ Failed to save session {session_id}: {str(e)}")
        return f"Failed to save session: {str(e)}"


@function_tool()
async def load_session(session_id: str) -> str:
    """
    Load an existing session's data from its JSON file.

    Args:
        session_id: Unique identifier for the session.

    Returns:
        Confirmation message as string.
    """
    file_path = _get_session_file(session_id)
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Load into session-specific storage
                sessions_data[session_id] = {
                    "onboarding_state": data.get("onboarding_data", {
                        "name": None, "email": None, "phone": None, "country": None
                    }),
                    "conversation_log": data.get("conversation", [])
                }
            print(f"📂 Session {session_id} loaded with {len(sessions_data[session_id]['conversation_log'])} messages")
            return f"Session {session_id} loaded successfully"
        else:
            print(f"📂 Session file for {session_id} not found, creating new session")
            return f"Session file not found for {session_id}"
    except Exception as e:
        print(f"❌ Failed to load session {session_id}: {str(e)}")
        return f"Failed to load session: {str(e)}"


@function_tool()
async def reset_session(session_id: str) -> str:
    """
    Reset the current onboarding state and conversation log for a new session.

    Args:
        session_id: Unique identifier for the session.

    Returns:
        Confirmation message as string.
    """
    # Reset session-specific data
    sessions_data[session_id] = {
        "onboarding_state": {
            "name": None,
            "email": None, 
            "phone": None,
            "country": None
        },
        "conversation_log": []
    }
    
    try:
        await save_session(session_id)
        print(f"🔄 Session {session_id} reset successfully")
        return f"Session {session_id} reset successfully"
    except Exception as e:
        print(f"❌ Failed to reset session {session_id}: {str(e)}")
        return f"Failed to reset session: {str(e)}"


# -------------------
#  Session Context Management
# -------------------

# Global variable to store current session ID for tool calls
current_session_id: str = ""

def set_current_session_id(session_id: str):
    """Set the current session ID for tool calls"""
    global current_session_id
    current_session_id = session_id

# -------------------
#  Conversation Logging
# -------------------
@function_tool()
async def log_message(speaker: str, text: str) -> str:
    """
    Log a message in the conversation history for the current session.

    Args:
        speaker: Either 'user' or 'assistant'.
        text: Message text to log.

    Returns:
        Confirmation message as string.
    """
    session_id = current_session_id
    try:
        conversation_log = _get_conversation_log(session_id)
        message_entry = {
            "speaker": speaker,
            "text": text,
            "timestamp": str(__import__('datetime').datetime.now())
        }
        conversation_log.append(message_entry)
        print(f"📝 [{session_id}] Logged {speaker} message: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        return f"Message logged successfully for session {session_id}"
    except Exception as e:
        print(f"❌ Failed to log message for session {session_id}: {str(e)}")
        return f"Failed to log message: {str(e)}"

@function_tool()
async def log_message_with_session(session_id: str, speaker: str, text: str) -> str:
    """
    Log a message in the conversation history for a specific session (direct call).

    Args:
        session_id: Unique identifier for the session.
        speaker: Either 'user' or 'assistant'.
        text: Message text to log.

    Returns:
        Confirmation message as string.
    """
    try:
        conversation_log = _get_conversation_log(session_id)
        message_entry = {
            "speaker": speaker,
            "text": text,
            "timestamp": str(__import__('datetime').datetime.now())
        }
        conversation_log.append(message_entry)
        print(f"📝 [{session_id}] Logged {speaker} message: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        return f"Message logged successfully for session {session_id}"
    except Exception as e:
        print(f"❌ Failed to log message for session {session_id}: {str(e)}")
        return f"Failed to log message: {str(e)}"


# -------------------
#  Validation & Storage Functions (Updated for current session)
# -------------------
@function_tool()
async def validate_field(field: str, value: str) -> str:
    """
    Validate a user-provided onboarding field using Pydantic.

    Args:
        field: One of "name", "email", "phone", "country".
        value: The user's provided value to validate.

    Returns:
        Validation result as string.
    """
    session_id = current_session_id
    print(f"🔧 [{session_id}] VALIDATE_FIELD CALLED: field='{field}', value='{value}'")
    
    onboarding_state = _get_onboarding_state(session_id)
    
    if field not in onboarding_state:
        result = f"Invalid field: {field}. Must be one of: name, email, phone, country"
        print(f"🔧 [{session_id}] VALIDATE_FIELD RESULT: {result}")
        return result
    
    temp_data = onboarding_state.copy()
    temp_data[field] = value

    try:
        UserOnboarding(**temp_data)
        result = f"Valid {field}: {value}"
        print(f"🔧 [{session_id}] VALIDATE_FIELD RESULT: {result}")
        return result
    except Exception as e:
        result = f"Invalid {field}: {str(e)}"
        print(f"🔧 [{session_id}] VALIDATE_FIELD RESULT: {result}")
        return result

@function_tool()
async def store_field(field: str, value: str) -> str:
    """
    Store a validated onboarding field in the state.

    Args:
        field: One of "name", "email", "phone", "country".
        value: The validated value to store.

    Returns:
        Confirmation message as string.
    """
    session_id = current_session_id
    print(f"🔧 [{session_id}] STORE_FIELD CALLED: field='{field}', value='{value}'")
    
    onboarding_state = _get_onboarding_state(session_id)
    
    if field not in onboarding_state:
        result = f"Invalid field: {field}. Must be one of: name, email, phone, country"
        print(f"🔧 [{session_id}] STORE_FIELD RESULT: {result}")
        return result
    
    # Validate before storing
    validation_result = await validate_field(field, value)
    if not validation_result.startswith("Valid"):
        result = f"Cannot store invalid value: {validation_result}"
        print(f"🔧 [{session_id}] STORE_FIELD RESULT: {result}")
        return result
    
    onboarding_state[field] = value
    result = f"{field.capitalize()} stored successfully: {value}"
    print(f"🔧 [{session_id}] STORE_FIELD RESULT: {result}")
    return result


@function_tool()
async def is_onboarding_complete() -> str:
    """
    Check if all onboarding fields have been filled for the current session.

    Returns:
        Status message as string.
    """
    session_id = current_session_id
    onboarding_state = _get_onboarding_state(session_id)
    missing_fields = [k for k, v in onboarding_state.items() if not v]
    if missing_fields:
        return f"Onboarding incomplete. Missing: {', '.join(missing_fields)}"
    else:
        return "Onboarding complete - all fields filled"


@function_tool()
async def get_summary() -> str:
    """
    Get a summary of all collected onboarding data for the current session.

    Returns:
        Summary of collected data as string.
    """
    session_id = current_session_id
    onboarding_state = _get_onboarding_state(session_id)
    filled_fields = {k: v for k, v in onboarding_state.items() if v}
    if not filled_fields:
        return "No onboarding data collected yet"
    
    summary_parts = [f"{k.capitalize()}: {v}" for k, v in filled_fields.items()]
    return "Collected data: " + ", ".join(summary_parts)

@function_tool()
async def get_current_state() -> str:
    """
    Get the current state of all onboarding fields for the current session.

    Returns:
        Current state as string.
    """
    session_id = current_session_id
    onboarding_state = _get_onboarding_state(session_id)
    state_parts = []
    for field, value in onboarding_state.items():
        status = value if value else "not provided"
        state_parts.append(f"{field.capitalize()}: {status}")
    
    return "Current onboarding state: " + ", ".join(state_parts)

@function_tool()
async def save_current_session() -> str:
    """
    Save the current session data.

    Returns:
        Confirmation message as string.
    """
    return await save_session(current_session_id)

@function_tool()
async def reset_current_session() -> str:
    """
    Reset the current session data.

    Returns:
        Confirmation message as string.
    """
    return await reset_session(current_session_id)

@function_tool()
async def log_conversation_turn(user_message: str, assistant_response: str) -> str:
    """
    Log both user message and assistant response in one function call.
    This ensures the LLM can explicitly log conversation turns.

    Args:
        user_message: The user's message
        assistant_response: The assistant's response

    Returns:
        Confirmation message as string.
    """
    session_id = current_session_id
    try:
        conversation_log = _get_conversation_log(session_id)
        
        # Log user message
        if user_message.strip():
            user_entry = {
                "speaker": "user",
                "text": user_message.strip(),
                "timestamp": str(__import__('datetime').datetime.now())
            }
            conversation_log.append(user_entry)
            print(f"📝 [{session_id}] Logged user message: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
        
        # Log assistant response
        if assistant_response.strip():
            assistant_entry = {
                "speaker": "assistant", 
                "text": assistant_response.strip(),
                "timestamp": str(__import__('datetime').datetime.now())
            }
            conversation_log.append(assistant_entry)
            print(f"📝 [{session_id}] Logged assistant response: '{assistant_response[:50]}{'...' if len(assistant_response) > 50 else ''}'")
        
        # Auto-save after logging
        await save_session(session_id)
        
        return f"Conversation turn logged successfully for session {session_id}"
    except Exception as e:
        print(f"❌ Failed to log conversation turn for session {session_id}: {str(e)}")
        return f"Failed to log conversation turn: {str(e)}"

@function_tool()
async def force_save_session() -> str:
    """
    Force save the current session data immediately.

    Returns:
        Confirmation message as string.
    """
    session_id = current_session_id
    try:
        result = await save_session(session_id)
        print(f"🔄 [{session_id}] Force saved session")
        return f"Session {session_id} force saved successfully"
    except Exception as e:
        print(f"❌ Failed to force save session {session_id}: {str(e)}")
        return f"Failed to force save session: {str(e)}"

@function_tool()
async def get_conversation_history() -> str:
    """
    Get the current conversation history for debugging.

    Returns:
        Conversation history as string.
    """
    session_id = current_session_id
    try:
        conversation_log = _get_conversation_log(session_id)
        if not conversation_log:
            return "No conversation history yet"
        
        history_parts = []
        for i, entry in enumerate(conversation_log):
            speaker = entry.get("speaker", "unknown")
            text = entry.get("text", "")
            timestamp = entry.get("timestamp", "")
            history_parts.append(f"{i+1}. [{speaker}] {text} (at {timestamp})")
        
        return f"Conversation history ({len(conversation_log)} messages):\n" + "\n".join(history_parts)
    except Exception as e:
        return f"Failed to get conversation history: {str(e)}"