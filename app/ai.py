"""AI providers used to tailor resumes: Claude (Anthropic), OpenAI, and Codecraft (any OpenAI-compatible endpoint).

API keys live in the local SQLite settings table (data/jobs.db) and never leave this machine
except in requests to the provider you picked.
"""
import json
import re

from . import db

PROVIDERS = {
    "anthropic": {
        "label": "Claude",
        "default_model": "claude-3-5-sonnet-20241022",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "key_hint": "sk-ant-...",
        "needs_base_url": False,
        "help": "Create a key at console.anthropic.com. Claude Sonnet gives fast, high-quality rewrites.",
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"],
        "key_hint": "sk-...",
        "needs_base_url": False,
        "help": "Create a key at platform.openai.com. Any chat completion model works.",
    },
    "codecraft": {
        "label": "Codecraft",
        "default_model": "claude-sonnet-5",
        "models": ["claude-sonnet-5", "claude-opus-5", "claude-haiku-5", "gpt-4o", "deepseek-chat"],
        "key_hint": "API key from your Codecraft account",
        "needs_base_url": True,
        "help": "Codecraft or any OpenAI-compatible proxy. Provide base URL (e.g. ending in /v1) and your model name.",
    },
}
DEFAULT_PROVIDER = "anthropic"
JSON_ONLY = "\n\nRespond with a single JSON object only, no prose, matching this JSON schema:\n"


class AIError(Exception):
    """A user-facing error: missing key, bad model, provider rejected the request, etc."""


# ---------------------------------------------------------------- settings
def _key(provider, field):
    return f"ai.{provider}.{field}"


def get_settings():
    """Full settings including raw keys. Only for server-side fallback."""
    out = {"provider": db.get_setting("ai.provider", DEFAULT_PROVIDER), "providers": {}}
    for p, meta in PROVIDERS.items():
        out["providers"][p] = {
            "api_key": db.get_setting(_key(p, "api_key"), "") or "",
            "model": db.get_setting(_key(p, "model"), "") or meta["default_model"],
            "base_url": db.get_setting(_key(p, "base_url"), "") or "",
        }
    if out["provider"] not in PROVIDERS:
        out["provider"] = DEFAULT_PROVIDER
    return out


def public_settings():
    """Catalog and defaults safe for public clients. Never leaks secret keys."""
    return {
        "provider": db.get_setting("ai.provider", DEFAULT_PROVIDER),
        "catalog": PROVIDERS,
    }


def save_settings(data):
    """Server-side save (optional for self-hosted single users)."""
    if "provider" in data:
        if data["provider"] not in PROVIDERS:
            raise AIError("Unknown provider")
        db.set_setting("ai.provider", data["provider"])
    for p, v in (data.get("providers") or {}).items():
        if p not in PROVIDERS or not isinstance(v, dict):
            continue
        if "api_key" in v:
            if v["api_key"] is None:
                db.set_setting(_key(p, "api_key"), "")
            elif str(v["api_key"]).strip():
                db.set_setting(_key(p, "api_key"), str(v["api_key"]).strip())
        if "model" in v:
            db.set_setting(_key(p, "model"), str(v["model"] or "").strip())
        if "base_url" in v:
            db.set_setting(_key(p, "base_url"), str(v["base_url"] or "").strip().rstrip("/"))
    return public_settings()


def resolve(provider=None, client_ai=None):
    """Return (provider, api_key, model, base_url), prioritizing client-provided credentials."""
    client_ai = client_ai or {}
    provider = client_ai.get("provider") or provider or db.get_setting("ai.provider", DEFAULT_PROVIDER)
    if provider not in PROVIDERS:
        raise AIError(f"Unknown provider: {provider}")
    label = PROVIDERS[provider]["label"]
    meta = PROVIDERS[provider]

    if client_ai:
        key = (client_ai.get("api_key") or "").strip()
        model = (client_ai.get("model") or "").strip() or meta.get("default_model", "")
        base_url = (client_ai.get("base_url") or "").strip().rstrip("/")
    else:
        # Fallback to server database only when no client_ai was provided
        key = db.get_setting(_key(provider, "api_key"), "") or ""
        model = db.get_setting(_key(provider, "model"), "") or meta["default_model"]
        base_url = (db.get_setting(_key(provider, "base_url"), "") or "").rstrip("/")

    if not key:
        raise AIError(f"No API key provided for {label}. Add your API key under AI settings in the sidebar.")
    if not model:
        raise AIError(f"No model set for {label}. Enter a model name under AI settings.")
    if meta["needs_base_url"] and not base_url:
        raise AIError(f"{label} needs a base URL (for example https://api.example.com/v1).")
    return provider, key, model, base_url


def fetch_models(provider=None, client_ai=None):
    """Fetch available models dynamically from provider using the client's credentials."""
    client_ai = client_ai or {}
    provider = client_ai.get("provider") or provider or DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        raise AIError("Unknown provider")
    label = PROVIDERS[provider]["label"]
    meta = PROVIDERS[provider]

    if client_ai:
        key = (client_ai.get("api_key") or "").strip()
        base_url = (client_ai.get("base_url") or "").strip().rstrip("/")
    else:
        key = db.get_setting(_key(provider, "api_key"), "") or ""
        base_url = (db.get_setting(_key(provider, "base_url"), "") or "").rstrip("/")

    if not key:
        raise AIError(f"Enter your API key for {label} first to fetch available models.")
    if meta["needs_base_url"] and not base_url:
        raise AIError(f"{label} needs a base URL to fetch available models.")

    models = []
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=key, timeout=20)
        try:
            resp = client.models.list()
            models = [m.id for m in resp.data]
        except Exception:
            models = list(meta.get("models") or [])
    else:
        import openai
        client = openai.OpenAI(api_key=key, base_url=base_url or None, timeout=20)
        try:
            resp = client.models.list()
            models = sorted([m.id for m in resp.data])
        except openai.AuthenticationError:
            raise AIError(f"{label} rejected the API key.")
        except Exception as e:
            raise AIError(f"Could not fetch models from {label}: {e}")

    if not models:
        models = list(meta.get("models") or [])
    return {"ok": True, "provider": provider, "models": models}


# ---------------------------------------------------------------- JSON completion
def _parse_json(text):
    """Parse model output as JSON, tolerating code fences and stray prose around the object."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.M).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            pass
    raise AIError("The AI returned something that is not valid JSON. Try again or pick another model.")


def complete_json(system, user, schema, provider=None, client_ai=None, max_tokens=16000):
    """Send one prompt and get back a JSON object matching `schema`. Returns (data, provider, model)."""
    provider, key, model, base_url = resolve(provider, client_ai=client_ai)
    if provider == "anthropic":
        data = _anthropic_json(key, model, system, user, schema, max_tokens)
    else:
        data = _openai_json(key, model, base_url, system, user, schema, provider)
    return data, provider, model


def _anthropic_json(key, model, system, user, schema, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=key, timeout=600, max_retries=2)
    kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user}],
                  output_config={"format": {"type": "json_schema", "schema": schema}})
    try:
        try:
            # Server-side refusal fallback keeps a rare safety decline from failing the request outright.
            resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except TypeError:
            resp = client.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        raise AIError("Claude rejected the API key. Check it under AI settings.")
    except anthropic.NotFoundError:
        raise AIError(f"Claude model '{model}' was not found. Check the model name.")
    except anthropic.RateLimitError:
        raise AIError("Claude rate limit reached. Wait a minute and try again.")
    except anthropic.BadRequestError as e:
        msg = str(getattr(e, "message", e))
        if "output_config" in msg or "json_schema" in msg or "fallbacks" in msg or "beta" in msg.lower():
            # Older models or SDKs: ask for JSON in the prompt instead of enforcing a schema.
            kwargs.pop("output_config", None)
            kwargs["system"] = system + JSON_ONLY + json.dumps(schema)
            try:
                resp = client.messages.create(**kwargs)
            except anthropic.APIStatusError as e2:
                raise AIError(f"Claude error: {getattr(e2, 'message', e2)}")
        else:
            raise AIError(f"Claude error: {msg}")
    except anthropic.APIStatusError as e:
        raise AIError(f"Claude error ({e.status_code}): {getattr(e, 'message', e)}")
    except anthropic.APIConnectionError:
        raise AIError("Could not reach api.anthropic.com. Check your internet connection or proxy.")
    if resp.stop_reason == "refusal":
        raise AIError("Claude declined this request.")
    if resp.stop_reason == "max_tokens":
        raise AIError("The response was cut off. Try a shorter resume or job description.")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return _parse_json(text)


def _openai_json(key, model, base_url, system, user, schema, provider):
    import openai
    label = PROVIDERS[provider]["label"]
    client = openai.OpenAI(api_key=key, base_url=base_url or None, timeout=600, max_retries=2)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if provider == "openai":
        fmt = {"type": "json_schema", "json_schema": {"name": "tailored_resume", "schema": schema, "strict": True}}
    else:
        fmt = {"type": "json_object"}
        messages[0]["content"] += JSON_ONLY + json.dumps(schema)
    try:
        try:
            resp = client.chat.completions.create(model=model, messages=messages, response_format=fmt)
        except openai.BadRequestError as e:
            # Some endpoints and models do not support response_format; ask for JSON in the prompt instead.
            msg = str(getattr(e, "message", e))
            if "response_format" in msg or "json_schema" in msg or "json_object" in msg or "strict" in msg:
                if provider == "openai":
                    messages[0]["content"] += JSON_ONLY + json.dumps(schema)
                resp = client.chat.completions.create(model=model, messages=messages)
            else:
                raise
    except openai.AuthenticationError:
        raise AIError(f"{label} rejected the API key. Check it under AI settings.")
    except openai.NotFoundError:
        where = f" at {base_url}" if base_url else ""
        raise AIError(f"{label} model '{model}' was not found{where}. Check the model name.")
    except openai.RateLimitError:
        raise AIError(f"{label} rate limit or quota reached. Check your account and try again.")
    except openai.APIStatusError as e:
        raise AIError(f"{label} error ({e.status_code}): {getattr(e, 'message', e)}")
    except openai.APIConnectionError:
        where = f" at {base_url}" if base_url else ""
        raise AIError(f"Could not reach {label}{where}. Check the URL and your connection.")
    choice = resp.choices[0] if resp.choices else None
    if not choice or not choice.message or not choice.message.content:
        raise AIError(f"{label} returned an empty response.")
    if choice.finish_reason == "length":
        raise AIError("The response was cut off. Try a shorter resume or job description.")
    return _parse_json(choice.message.content)


def test_connection(provider=None, client_ai=None):
    """Make the smallest possible request to confirm the key, model and URL work."""
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
              "additionalProperties": False}
    data, provider, model = complete_json("You answer with JSON only.", 'Reply with {"ok": true}', schema,
                                          provider=provider, client_ai=client_ai, max_tokens=64)
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise AIError("The provider answered, but not with the expected JSON.")
    return {"ok": True, "provider": provider, "model": model,
            "message": f"{PROVIDERS[provider]['label']} connected successfully with model {model}."}
