"""
Token Takip Modülü
Bir çalışma boyunca tüm Gemini API token kullanımını toplar.
"""

# Gemini 2.5 Flash fiyatları ($/1M token, Mayıs 2026)
INPUT_PRICE_PER_M  = 0.15   # $0.15 / 1M input token
OUTPUT_PRICE_PER_M = 0.60   # $0.60 / 1M output token

_input_tokens  = 0
_output_tokens = 0
_extra_cost    = 0.0  # token dışı maliyetler (örn. Veo video, saniye başı ücret)
_api_errors    = []


def reset():
    global _input_tokens, _output_tokens, _extra_cost, _api_errors
    _input_tokens  = 0
    _output_tokens = 0
    _extra_cost    = 0.0
    _api_errors    = []


def add_cost(usd: float):
    """Token bazlı olmayan maliyet ekler (örn. video üretimi)."""
    global _extra_cost
    _extra_cost += usd


def track(response):
    """Gemini response'undan token kullanımını okur."""
    global _input_tokens, _output_tokens
    try:
        usage = response.usage_metadata
        _input_tokens  += usage.prompt_token_count or 0
        _output_tokens += usage.candidates_token_count or 0
    except Exception:
        pass


def track_error(error: str):
    """API hatasını kaydeder."""
    _api_errors.append(error)


def summary() -> dict:
    """Toplam kullanım özetini döner."""
    cost = (
        (_input_tokens  / 1_000_000) * INPUT_PRICE_PER_M +
        (_output_tokens / 1_000_000) * OUTPUT_PRICE_PER_M +
        _extra_cost
    )
    return {
        "input_tokens":  _input_tokens,
        "output_tokens": _output_tokens,
        "total_tokens":  _input_tokens + _output_tokens,
        "cost_usd":      round(cost, 6),
        "api_errors":    "; ".join(_api_errors) if _api_errors else ""
    }
