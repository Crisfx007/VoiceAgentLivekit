import uuid
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from prompts1 import AGENT_INSTRUCTION, SESSION_INSTRUCTION
import tools1  # our onboarding tools

load_dotenv()

class Assistant(Agent):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        
        # Set the current session ID for tools to use
        tools1.set_current_session_id(session_id)
        
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            stt=openai.STT(model="gpt-4o-transcribe"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tools=[
                tools1.validate_field,
                tools1.store_field,
                tools1.save_current_session,
                tools1.log_message,
                tools1.log_conversation_turn,
                tools1.force_save_session,
                tools1.get_conversation_history,
                tools1.is_onboarding_complete,
                tools1.get_summary,
                tools1.get_current_state,
                tools1.reset_current_session,
                tools1.load_session,
            ],
            tts=openai.TTS(model="gpt-4o-mini-tts", voice="ash"),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel()
        )

    async def on_message(self, message, participant, is_final):
        """
        Intercepts all messages in the conversation for logging.
        """
        if not is_final or not message.strip():
            return  # only log final, non-empty messages

        try:
            # More robust participant detection
            # In LiveKit, the agent itself is usually identified by participant.identity
            participant_identity = getattr(participant, 'identity', '')
            participant_name = getattr(participant, 'name', '')
            
            print(f"🔍 [{self.session_id}] Message from participant - Identity: '{participant_identity}', Name: '{participant_name}', is_local: {participant.is_local}")
            
            # Determine speaker based on multiple criteria
            if participant.is_local or 'agent' in participant_identity.lower() or 'assistant' in participant_identity.lower():
                speaker = "assistant"
                print(f"🤖 [{self.session_id}] ASSISTANT MESSAGE: '{message}'")
            else:
                speaker = "user"
                print(f"👤 [{self.session_id}] USER MESSAGE: '{message}'")

            # Log the message with session ID
            result = await tools1.log_message_with_session(self.session_id, speaker, message)
            print(f"📝 [{self.session_id}] Log result: {result}")
            
            # Save session after logging message
            save_result = await tools1.save_session(self.session_id)
            print(f"💾 [{self.session_id}] Session save result: {save_result}")
                
        except Exception as e:
            print(f"❌ [{self.session_id}] Error in on_message: {e}")
            import traceback
            traceback.print_exc()

    async def on_participant_speech_end(self, participant, text: str):
        """
        Called when any participant finishes speaking.
        """
        try:
            participant_identity = getattr(participant, 'identity', '')
            participant_name = getattr(participant, 'name', '')
            
            print(f"🗣️ [{self.session_id}] Speech ended - Participant: '{participant_identity}', Text: '{text}'")
            
            # Determine speaker
            if participant.is_local or 'agent' in participant_identity.lower():
                speaker = "assistant"
            else:
                speaker = "user"
                
            # Log the speech
            result = await tools1.log_message_with_session(self.session_id, speaker, text)
            print(f"📝 [{self.session_id}] Speech log result: {result}")
            
            # Save session after logging
            save_result = await tools1.save_session(self.session_id)
            print(f"💾 [{self.session_id}] Session save after speech: {save_result}")
            
        except Exception as e:
            print(f"❌ [{self.session_id}] Error in on_participant_speech_end: {e}")
            import traceback
            traceback.print_exc()

    async def on_agent_speech_end(self, text: str):
        """
        Called when the agent finishes speaking.
        """
        try:
            print(f"🗣️ [{self.session_id}] Agent speech ended: '{text}'")
            # Log assistant message
            result = await tools1.log_message_with_session(self.session_id, "assistant", text)
            print(f"📝 [{self.session_id}] Agent speech log result: {result}")
            
            # Save session after logging
            save_result = await tools1.save_session(self.session_id)
            print(f"💾 [{self.session_id}] Session save after agent speech: {save_result}")
            
        except Exception as e:
            print(f"❌ [{self.session_id}] Error in on_agent_speech_end: {e}")
            import traceback
            traceback.print_exc()

    async def on_user_speech_end(self, text: str):
        """
        Called when user finishes speaking.
        """
        try:
            print(f"🗣️ [{self.session_id}] User speech ended: '{text}'")
            # Log user message
            result = await tools1.log_message_with_session(self.session_id, "user", text)
            print(f"📝 [{self.session_id}] User speech log result: {result}")
            
            # Save session after logging
            save_result = await tools1.save_session(self.session_id)
            print(f"💾 [{self.session_id}] Session save after user speech: {save_result}")
            
        except Exception as e:
            print(f"❌ [{self.session_id}] Error in on_user_speech_end: {e}")
            import traceback
            traceback.print_exc()


async def entrypoint(ctx: agents.JobContext):
    # Create unique session ID for this onboarding call
    session_id = str(uuid.uuid4())
    print(f"🚀 Starting new session with ID: {session_id}")
    
    # Reset session state
    reset_result = await tools1.reset_session(session_id)
    print(f"🔄 Session reset: {reset_result}")

    session = AgentSession()

    # Create assistant instance
    assistant = Assistant(session_id=session_id)

    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Initial onboarding intro
    try:
        initial_message = "Starting onboarding session..."
        log_result = await tools1.log_message_with_session(session_id, "assistant", initial_message)
        save_result = await tools1.save_session(session_id)
        print(f"📝 Initial log: {log_result}")
        print(f"💾 Initial save: {save_result}")
    except Exception as e:
        print(f"❌ Error logging initial message: {e}")

    # Generate initial reply with session instructions
    await session.generate_reply(
        instructions=f"{SESSION_INSTRUCTION}\n\nSession ID: {session_id}"
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))