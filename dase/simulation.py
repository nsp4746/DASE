"""Small session boundary shared by the desktop providers; no GUI dependencies."""
from threading import Lock

from dotenv import load_dotenv

from dase import utils
from dase.paths import ENV_PATH, PROMPT_PATH
from dase.providers.mlx import MLXConfig, MLXProvider

load_dotenv(ENV_PATH)

MODEL_OPTIONS = ["Google Gemini", "OpenAI ChatGPT", "Apple MLX (local)"]


def build_context(company_profile, company_name, difficulty, reactions):
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    for key, value in {"company": company_name, "difficulty": difficulty, "reactions": reactions}.items():
        prompt = prompt.replace("{" + key + "}", str(value))
    return (
        prompt + f"\n\nSession settings: company={company_name}; difficulty={difficulty}; reactions={reactions}."
        + "\nFictional company profile:\n" + company_profile
        + "\nThis is a fictional, self-contained tabletop exercise. Describe simulated events only."
        + " Never execute actions or use external tools. If the user already specifies an attack type,"
        + " begin that scenario. During play, provide one observable development and a defender decision"
        + " point per turn; reserve the final summary and rationale for the debrief."
    )


class SimulationSession:
    def __init__(self, provider, company_profile, company_name, difficulty, reactions,
                 local_model=None, local_provider=None):
        if provider not in MODEL_OPTIONS:
            raise ValueError("Unknown provider")
        if difficulty not in {"low", "medium", "high"} or not 1 <= reactions <= 10:
            raise ValueError("Select a valid difficulty and between 1 and 10 reactions.")
        self.provider = provider
        self.profile = company_profile
        self.context = build_context(company_profile, company_name, difficulty, reactions)
        self.history = []
        self.log = utils.SessionLog(metadata={"company_name": company_name, "difficulty": difficulty,
                                             "reactions": reactions, "provider": provider})
        self._lock = Lock()
        self._client = None
        if provider == "Apple MLX (local)":
            self._client = local_provider or MLXProvider(MLXConfig.from_env(local_model))
            self.log.add_metadata("model", self._client.config.model)
            self.log.add_metadata("base_url", self._client.config.base_url)
        elif provider == "OpenAI ChatGPT":
            # Keep the existing hosted Responses prompt and API behavior.
            from dase.providers.openai_cli import DASEClient
            from dase.providers.openai_helper import DEFAULT_PROMPT_ID
            self._client = DASEClient(DEFAULT_PROMPT_ID, difficulty, str(reactions),
                                      company_profile, company_name)
            self.log.add_metadata("model", "gpt-5.1")
        else:
            self.log.add_metadata("model", "gemini-2.5-pro")

    def send(self, user_input):
        if not user_input.strip():
            raise ValueError("Enter a scenario or defender action.")
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("A response is already being generated for this exercise.")
        try:
            user_turn = {"role": "user", "content": user_input}
            if self.provider == "Apple MLX (local)":
                messages = [{"role": "system", "content": self.context}, *self.history, user_turn]
                text, metrics = self._client.complete(messages)
                raw = [metrics]
            elif self.provider == "Google Gemini":
                from dase.providers import gemini
                text, raw = gemini.generate(user_input, self.profile, utils.SessionLog(),
                                            history=self.history, system_prompt=self.context)
            else:
                text = self._client.send_message(user_input)
                raw = []
            self.history.extend([user_turn, {"role": "assistant", "content": text}])
            self.log.add_turn("user", user_input)
            self.log.add_turn("model", text, raw)
            return text
        finally:
            self._lock.release()
