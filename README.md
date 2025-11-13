# DASE  
**MS Project**  

This is project seeks to introduce dynamic incident response trainings. 
---

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
- Set it as an environment variable:

  **Windows (PowerShell):**
  ```bash
  setx GEMINI_API_KEY "your_api_key_here" 
  ```
  **MacOS/Linux**
  ```
  export GEMINI_API_KEY="your_api_key_here"
  ```

### 5. Run gui.py
  
