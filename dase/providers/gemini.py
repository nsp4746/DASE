import os
from dase import utils
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from dase.paths import ENV_PATH, PROMPT_PATH
"""
DASE Client for interacting with OpenAI's API using a predefined prompt. 
"""
conversation_history = []
session_log = utils.SessionLog()
load_dotenv(ENV_PATH)

def _sanitize_chunk(chunk_dict):
    """Keep only relevant fields to avoid bloating session logs."""
    if not isinstance(chunk_dict, dict):
        return {}
    allowed_keys = {"candidates", "text"}
    sanitized = {key: chunk_dict[key] for key in allowed_keys if key in chunk_dict}
    return sanitized

def generate(user_input, company_profile, log: utils.SessionLog, *, history=None, system_prompt=None):

    # Session callers supply their own history. The CLI retains its legacy list.
    contents = list(conversation_history) if history is None else [
        types.Content(role="model" if turn["role"] == "assistant" else "user",
                      parts=[types.Part.from_text(text=turn["content"])])
        for turn in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=120_000),
    )

    model = "gemini-2.5-pro" # or "gemini-2.5-flash/pro", flash for faster responses
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]

    # Combine the base prompt with the company profile
    base_prompt = utils.read_from_file(PROMPT_PATH)
        
    final_prompt = system_prompt or company_profile + "\n" + base_prompt

    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
        tools=tools if system_prompt is None else None,
        system_instruction=[types.Part.from_text(text=final_prompt)]
    )
    full_response = ""
    raw_chunks = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        chunk_dict = chunk.to_dict() if hasattr(chunk, "to_dict") else {}
        if not chunk_dict and hasattr(chunk, "model_dump"):
            chunk_dict = chunk.model_dump()
        sanitized = _sanitize_chunk(chunk_dict)
        if sanitized:
            raw_chunks.append(sanitized)
        chunk_text = getattr(chunk, "text", "")
        if chunk_text:
            full_response += chunk_text
    
    if not full_response.strip():
        raise RuntimeError("Gemini returned no text.")
    if history is None:
        conversation_history[:] = contents + [
            types.Content(role="model", parts=[types.Part.from_text(text=full_response)])
        ]
    log.add_turn("user", user_input)
    log.add_turn("model", full_response, raw_chunks)
    return full_response, raw_chunks

if __name__ == "__main__":
    print("=========DASE Gemini Interface============")
    difficulty = input("Select difficulty (low, medium, high): ").strip().lower()
    reactions = input("Select number of reactions (1, 2, 3): ").strip()
    
    company_profile, company_profile_str = utils.select_company_from_cli()
    
    if not company_profile:
        # Error message is handled in the utility function
        exit()
    else:
        session_log.add_metadata("company_name", company_profile.get("company_name"))
        session_log.add_metadata("difficulty", difficulty)
        session_log.add_metadata("reactions", reactions)

        step = 0
        while True:
            user_prompt = input("User: ")
            
            if user_prompt.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                print("Would you like to save session history?")
                save_choice = input("Type 'yes' to save, or anything else to exit without saving: ").strip().lower()
                if save_choice == "yes":
                    file_path = utils.save_session(session_log)
                    print(f"Session history saved to {file_path}")
                break

            final_prompt = user_prompt
            if step == 0:
                final_prompt = (
                    f"{user_prompt}\nThe user desires this level of technical difficulty: {difficulty} "
                    f"and this number of reactions {reactions}. The company to perform the exercise on is "
                    f"{company_profile['company_name']}."
                )
                step += 1
            
            with utils.loading_indicator():
                response_text, _ = generate(final_prompt, company_profile_str, session_log)

            print("\nGemini:\n" + response_text)
