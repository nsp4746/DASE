# DASE  
**MS Project**  

This project examines the potential for large language models (LLMs) to improve cybersecurity incident response training through the introduction of dynamic and adaptive adversary behavior. Traditional tabletop exercises, while widely used, are often limited by static structure, predictable outcomes, and the significant effort required to create them, which reduces their effectiveness for preparing defenders against modern and fast-evolving cyber threats. To address these limitations, a proof-of-concept system known as the Dynamic Adversary Simulation Engine (DASE) was developed, in which an LLM is used to simulate a live adversary whose behavior is shaped by user decisions in real time. The system is supported by structured fictional company profiles, a state-aware prompting loop, and a lightweight graphical interface that together enable the generation of unique and contextually grounded scenarios without reliance on predefined scripts. Through these mechanisms, DASE demonstrates that LLM-driven simulations can maintain coherence, adapt responses to defender actions, and produce technically plausible adversary behavior. The final implementation includes session exporting and support for multiple LLM backends within the GUI, allowing improved usability and reproducibility. Qualitative user testing indicated that scenario realism and usability were generally perceived as strong, while also identifying areas for improvement such as interface clarity and constraints on model behavior. Overall, DASE is positioned as an early contribution toward more flexible, realistic, and scalable incident response training that reflects the complexity of real-world cyber incidents.

## 🚀 How to Run

### 1. **Install Python (3.12 - 3.13)**  
   You can download it from [python.org/downloads](https://www.python.org/downloads/).

### 2. Setup a virtual environment
   In VS Code ```ctrl+shift+p``` will bring up developer actions. Type ```Python Create Virtual Environment``` to create an environment specific to this installation.  

   
### 3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
### 4. Set up the Gemini API key

- Obtain a free API key from [Google AI Studio](https://aistudio.google.com).  
- Create a ```.env``` file in the root directory, examine .env.example to understand the structure of this file.

### 5. Run gui.py  


## Appendix
- [File Dir](./images/directory_setup.png)
- Utils.py can be used to query for information about the JSON files. 

