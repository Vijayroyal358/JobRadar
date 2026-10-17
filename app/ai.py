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
        "default_model": "claude-opus-5-5",
        "models": ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"],
        "key_hint": "sk-ant-...",
        "needs_base_url": False,
        "help": "Create a key at console.anthropic.com. Claude Opus 5.5 gives the best rewrites.",
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4.1",
        "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-5"],
        "key_hint": "sk-...",
        "needs_base_url": False,
        "help": "Create a key at platform.openai.com. Any chat model works.",
    },
    "codecraft": {
        "label": "Codecraft",
        "default_model": "",
        "models": [],
        "key_hint": "API key from your Codecraft account",
        "needs_base_url": True,
        "help": "Codecraft or any other OpenAI-compatible endpoint. Enter the base URL (ending in /v1) and the model name.",
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
    """Full settings including raw keys. Only for server-side use."""
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


def _is_ready(s, provider):
    v = s["providers"].get(provider) or {}
    if not v.get("api_key") or not v.get("model"):
        return False
    if PROVIDERS[provider]["needs_base_url"] and not v.get("base_url"):
        return False
    return True


def public_settings():
    """Settings safe to send to the browser: keys are masked to their last four characters."""
    s = get_settings()
    out = {"provider": s["provider"], "providers": {}, "catalog": PROVIDERS}
    for p, v in s["providers"].items():
        k = v["api_key"]
        out["providers"][p] = {
            "has_key": bool(k),
            "key_mask": ("••••" + k[-4:]) if len(k) >= 8 else ("••••" if k else ""),
            "model": v["model"],
            "base_url": v["base_url"],
            "ready": _is_ready(s, p),
        }
    out["ready"] = _is_ready(s, s["provider"])
    return out


def save_settings(data):
    """data: {provider?, providers?: {name: {api_key?, model?, base_url?}}}.

    An empty api_key string means "keep the saved key"; null means "remove it".
    """
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


def resolve(provider=None):
    """Return (provider, api_key, model, base_url) for the chosen or default provider, or raise AIError."""
    s = get_settings()
    provider = provider or s["provider"]
    if provider not in PROVIDERS:
        raise AIError("Unknown provider")
    v = s["providers"][provider]
    label = PROVIDERS[provider]["label"]
    if not v["api_key"]:
        raise AIError(f"No API key saved for {label}. Add one under AI settings in the sidebar.")
    if not v["model"]:
        raise AIError(f"No model set for {label}. Enter a model name under AI settings.")
    if PROVIDERS[provider]["needs_base_url"] and not v["base_url"]:
        raise AIError(f"{label} needs a base URL (for example https://api.example.com/v1).")
    return provider, v["api_key"], v["model"], v["base_url"]


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


def complete_json(system, user, schema, provider=None, max_tokens=16000):
    """Send one prompt and get back a JSON object matching `schema`. Returns (data, provider, model)."""
    provider, key, model, base_url = resolve(provider)
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


def test_connection(provider=None):
    """Make the smallest possible request to confirm the key, model and URL work."""
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
              "additionalProperties": False}
    data, provider, model = complete_json("You answer with JSON only.", 'Reply with {"ok": true}', schema, provider,
                                          max_tokens=64)
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise AIError("The provider answered, but not with the expected JSON.")
    return {"ok": True, "provider": provider, "model": model,
            "message": f"{PROVIDERS[provider]['label']} works with model {model}."}
