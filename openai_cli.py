from openai import OpenAI
from dotenv import load_dotenv
import json
import os, utils
'''
DASE Client for interacting with OpenAI's API using a predefined prompt. 
'''
load_dotenv()

class DASEClient:
    def __init__(self, prompt_id, difficulty="low", reactions="2", company_profile="", company_name=""):
        self.client = OpenAI()
        self.prompt_id = prompt_id
        self.difficulty = difficulty
        self.reactions = reactions
        self.company_profile = company_profile
        self.company_name = company_name
        self.history = []
        self._first_message = True

    def send_message(self, user_input):
        if self._first_message:
            context = (
                f"\nThe user desires this level of technical difficulty: {self.difficulty}. "
                f"The number of requested reactions is {self.reactions}. "
                f"The company to perform the exercise on is {self.company_name}.\n"
                f"Company profile:\n{self.company_profile}\n"
            )
            user_input = f"{user_input} {context}"
            self._first_message = False

        try:
            response = self.client.responses.create(
                model="gpt-5.1",
                prompt={
                    "id": self.prompt_id,
                    "version": "4",
                    "variables": {
                        "reactions": self.reactions,
                        "difficulty": self.difficulty,
                    },
                },
                input=user_input
            )
        except Exception as e:
            error_msg = f"API call failed: {e}"
            self.history.append({"user": user_input, "dase": error_msg})
            return error_msg

        output_text = getattr(response, "output_text", None)
        if output_text:
            output_text = output_text.strip()
        else:
            try:
                output_text = response.output[0].content[0].text.strip()
            except Exception:
                output_text = "[No text output returned]"

        self.history.append({
            "user": user_input,
            "dase": output_text
        })

        return output_text
           
def save_history_and_exit(dase_client):
    """Handles saving session history and exiting the application."""
    print("Session ended.")
    print("Would you like to save session history?")
    save_choice = input("Type 'yes' to save, or anything else to exit without saving: ").strip().lower()
    if save_choice == "yes" and hasattr(dase_client, 'history'):
        log = utils.SessionLog()
        log.turns = [utils.Turn(role="user", text=t["user"]) for t in dase_client.history] # Simplified conversion
        file_path = utils.save_session(log)
        print(f"History saved to {file_path}")

def main():
    prompt_id = "pmpt_68ed9669d8f88195ab599ab84c53870f0ec675ea9d29fd46"
    
    print("--------DASE Client Interface--------")
    print("Be sure to describe the type of scenario you want to practice.")
    print("Type 'exit' to quit the session.")
    
    difficulty = input("Select difficulty (low, medium, high): ").strip().lower()
    reactions = input("Select number of reactions (1, 2, 3): ").strip()
    
    company_profile, company_profile_str = utils.select_company_from_cli()
    if not company_profile:
        return
    
    company_name = company_profile.get("company_name", "Unknown Company")

    dase = DASEClient(prompt_id, difficulty, reactions, company_profile_str, company_name)
    
    user_input = input("Start scenario: ")
    print()
    
    while True:
        try:
            if user_input.lower() in ("exit", "quit", "q", "stop", "end"):
                save_history_and_exit(dase)
                break
    
            with utils.loading_indicator():
                model_output = dase.send_message(user_input)
            
            print("\nDASE:\n", model_output, "\n")

            user_input = input("Your next action: ")
            print()
        except (KeyboardInterrupt, EOFError):
            save_history_and_exit(dase)
            break

if __name__ == "__main__":
    main()  

