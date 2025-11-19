from openai import OpenAI
from dotenv import load_dotenv
import json
import os
'''

Not updated file, please gui.py for most up to data version of DASE client. 

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
           


def main():
    prompt_id = "pmpt_68ed9669d8f88195ab599ab84c53870f0ec675ea9d29fd46"
    
    print("--------DASE Client Interface--------")
    print("Be sure to describe the type of scenario you want to practice.")
    print("Type 'exit' to quit the session.")
    
    difficulty = input("Select difficulty (low, medium, high): ").strip().lower()
    reactions = input("Select number of reactions (1, 2, 3): ").strip()
    
    base_json_dir = os.path.join(os.path.dirname(__file__), "json")
    company_map = {
        "1": os.path.join(base_json_dir, "well_connect.json"),
        "2": os.path.join(base_json_dir, "aeropay.json"),
        "3": os.path.join(base_json_dir, "metrogrid.json")
    }

    company_choice = input(
        "Enter company name to perform exercise on:"
        "\n Company 1: Well Connect \n"
        "\n Company 2: AeroPay \n"
        "\n Company 3: MetroGrid Manufacturing \n"
        "Please select one: "
    ).strip()

    company_file = company_map.get(company_choice)
    if not company_file:
        print("Invalid company selection.")
        return

    with open(company_file, "r") as f:
        company_profile = json.load(f)

    company_profile_str = json.dumps(company_profile, indent=2)
    company_name = company_profile.get("company_name", "Unknown Company")

    dase = DASEClient(prompt_id, difficulty, reactions, company_profile_str, company_name)

    
    user_input = input("Start scenario: ")
    print()
    
    while True:
        if user_input.lower() == "exit" or user_input.lower() == "quit" or user_input.lower() == "q" or user_input.lower() == "stop" or user_input.lower() == "end":
            print("Session ended.")
            dase.save_history()
            break

   
        model_output = dase.send_message(user_input)
        print("\nDASE:\n", model_output, "\n")

  
        user_input = input("Your next action: ")
        print()


if __name__ == "__main__":
    main()  


# client = OpenAI()

# response = client.responses.create(
#   prompt={
#     "id": "pmpt_68ed9669d8f88195ab599ab84c53870f0ec675ea9d29fd46",
#     "version": "4",
#     "variables": {
#       "reactions": "example reactions",
#       "difficulty": "example difficulty"
#     }
#   }
# )
