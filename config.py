import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    MODEL_RESPONDEDOR: str = "claude-sonnet-4-6"

    # Mercado Livre
    ML_CLIENT_ID: str = os.getenv("ML_CLIENT_ID", "")
    ML_CLIENT_SECRET: str = os.getenv("ML_CLIENT_SECRET", "")
    ML_REFRESH_TOKEN: str = os.getenv("ML_REFRESH_TOKEN", "")   # opcional
    ML_ACCESS_TOKEN: str = os.getenv("ML_ACCESS_TOKEN", "")     # usado se nao tiver refresh
    ML_SELLER_ID: str = os.getenv("ML_SELLER_ID", "")
    ML_BASE_URL: str = "https://api.mercadolibre.com"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Sistema
    CONFIANCA_MINIMA: float = float(os.getenv("CONFIANCA_MINIMA", "0.75"))
    POLLING_INTERVAL: int = int(os.getenv("POLLING_INTERVAL_SEGUNDOS", "60"))

    def validar(self) -> None:
        """Valida credenciais obrigatorias — chamar no main.py antes de rodar."""
        obrigatorias = [
            "ANTHROPIC_API_KEY", "ML_CLIENT_ID", "ML_CLIENT_SECRET",
            "ML_SELLER_ID", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        ]
        faltando = [k for k in obrigatorias if not getattr(self, k)]
        if faltando:
            raise EnvironmentError(f"Variaveis de ambiente faltando: {', '.join(faltando)}")

        if not self.ML_REFRESH_TOKEN and not self.ML_ACCESS_TOKEN:
            raise EnvironmentError(
                "Configure ML_REFRESH_TOKEN ou ML_ACCESS_TOKEN no .env. "
                "Rode: uv run python auth_ml.py"
            )


config = Config()
