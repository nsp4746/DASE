from openai import OpenAI
import json 

class DASEClient:
    def __init__(self, prompt_id, difficulty="low", reactions="2"):
        self.client = OpenAI()
        self.prompt_id = prompt_id
        self.difficulty = difficulty
        self.reactions = reactions
        self.history = []

    def send_message(self, user_input):
        try:
            response = self.client.responses.stream(
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
           
    def save_history(self, file_path="session_log.json"):
      
        with open(file_path, "w") as f:
            json.dump(self.history, f, indent=2)

def main():
    prompt_id = "pmpt_68ed9669d8f88195ab599ab84c53870f0ec675ea9d29fd46"
    
    print("--------DASE Client Interface--------")
    print("Be sure to describe the type of scenario you want to practice.")
    print("Type 'exit' to quit the session.")
    
    difficulty = input("Select difficulty (low, medium, high): ").strip().lower()
    reactions = input("Select number of reactions (1, 2, 3): ").strip()
    
    dase = DASEClient(prompt_id, difficulty, reactions)

    
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
