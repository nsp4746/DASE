import utils, os
import json
from google import genai
from google.genai import types

conversation_history = []

def generate(user_input, company_profile):

    conversation_history.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)]
    ))
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash"
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]

    # Combine the base prompt with the company profile
    base_prompt = utils.read_from_file("prompt.txt")
        
    final_prompt = company_profile + "\n" + base_prompt

    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
        tools=tools,
        system_instruction=[types.Part.from_text(text=final_prompt)]
    )
    full_response = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=conversation_history,
        config=generate_content_config,
    ):
       # print(chunk.text, end="", flush=True)
        yield chunk.text
        full_response += chunk.text
    
    conversation_history.append(
        types.Content(
            role="model",
            parts=[types.Part.from_text(text=full_response)]
        )
    )

if __name__ == "__main__":
    print("=========DASE Gemini Interface============")
    difficulty = input("Select difficulty (low, medium, high): ").strip().lower()
    reactions = input("Select number of reactions (1, 2, 3): ").strip()
    
    company_map = {
        "1": "well_connect.json",
        "2": "aeropay.json",
        "3": "metrogrid.json"
    }

    company_choice = input("Enter company name to perform exercise on:" \
    "\n Company 1: Well Connect \n" \
    "\n Company 2: AeroPay \n" \
    "\n Company 3: MetroGrid Manufacturing \n" \
    "Please select one: ").strip()

    company_file = company_map.get(company_choice)

    if not company_file:
        print("Invalid company selection.")
    else:
        with open(company_file, 'r') as f:
            company_profile = json.load(f)
        
        # Convert the json into a string format that is readable by the model
        company_profile_str = json.dumps(company_profile, indent=2)


        step = 0
        while True:
            user_prompt = input("User: ")
            
            if user_prompt.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break
            if step == 0:
                user_prompt = user_prompt + "\n The user desires this level of techincal difficulty: " + difficulty + " and this number of reactions " + reactions + ". The company to perform the exercise on is " + company_profile["company_name"] + "."
                step += 1
                generate(user_prompt, company_profile_str)

            else: 
                generate(user_prompt, company_profile_str)
