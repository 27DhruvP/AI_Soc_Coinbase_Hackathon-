import json
import dotenv

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .services.finance import (
    get_history,
    get_snapshot,
    sma_crossover_backtest,
    technical_summary,
)
from .services.llm import chat as llm_chat
from .services.prompts import INVESTMENT_SYSTEM_PROMPT

dotenv.load_dotenv()

# Create your views here.
def home(request):
    return render(request, 'home.html')

@require_GET
def api_snapshot(request):
    """Return a quick stock snapshot for a given ticker."""
    ticker = (request.GET.get("ticker") or "").strip()
    if not ticker:
        return JsonResponse({"error": "Missing ?ticker="}, status=400)
    try:
        snap = get_snapshot(ticker)
        return JsonResponse({"ok": True, "snapshot": snap.__dict__})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
def api_chat(request):
    """Chat endpoint: combines user message + optional finance context + LLM."""

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}

    user_message = (payload.get("message") or "").strip()
    ticker = (payload.get("ticker") or "").strip()
    settings = payload.get("settings") or {}

    if not user_message:
        return JsonResponse({"ok": False, "error": "Missing message"}, status=400)

    include_fundamentals = bool(settings.get("fundamentals", True))
    include_technicals = bool(settings.get("technicals", True))
    include_backtest = bool(settings.get("backtest", False))
    include_guardrails = bool(settings.get("guardrails", True))

    # Assemble context for the model.
    context = {"ticker": ticker.upper() if ticker else None}
    snapshot = None
    tech = None
    backtest = None

    if ticker:
        try:
            if include_fundamentals:
                snapshot = get_snapshot(ticker)
                context["snapshot"] = snapshot.__dict__
            if include_technicals or include_backtest:
                df = get_history(ticker, period="1y", interval="1d")
                if include_technicals:
                    tech = technical_summary(df)
                    context["technicals"] = tech
                if include_backtest:
                    backtest = sma_crossover_backtest(df, fast=20, slow=50)
                    context["toy_backtest"] = backtest
        except Exception as e:
            context["data_error"] = str(e)

    system = INVESTMENT_SYSTEM_PROMPT
    if include_guardrails:
        # Small add-on reminder for safety and tone.
        system += "\n\nTone: friendly, concise, and practical. Do not overfit to short-term price moves."

    messages = [
        {
            "role": "user",
            "content": (
                "User question:\n"
                f"{user_message}\n\n"
                "Context (JSON, may be empty):\n"
                f"{json.dumps(context, ensure_ascii=False)}"
            ),
        }
    ]

    llm = llm_chat(system=system, messages=messages)

    return JsonResponse(
        {
            "ok": llm["ok"],
            "reply": llm["content"],
            "context": context,
            "snapshot": snapshot.__dict__ if snapshot else None,
            "technicals": tech,
            "backtest": backtest,
        }
    )

def farcaster_manifest_view(request):
    """Serve the Farcaster/Base mini-app manifest at /.well-known/farcaster.json"""
    # Look for the manifest in the static folder
    data = json.loads("""{
  "accountAssociation": {
    "header": "",
    "payload": "",
    "signature": ""
  },
  "miniapp": {
    "version": "1",
    "name": "summariser",
    "homeUrl": "https://thegreatestminiappofalltime.onrender.com/",
    "iconUrl": "https://static.vecteezy.com/system/resources/previews/011/995/200/non_2x/geometric-icon-logo-geometric-abstract-element-free-vector.jpg",
    "splashImageUrl": "https://static.vecteezy.com/system/resources/previews/011/995/200/non_2x/geometric-icon-logo-geometric-abstract-element-free-vector.jpg",
    "splashBackgroundColor": "#020617",
    "webhookUrl": "https://thegreatestminiappofalltime.onrender.com/api/webhook",
    "subtitle": "summarise anything",
    "description": "A mini app that can summarise any text you give it.",
    "screenshotUrls": [
      "https://static.vecteezy.com/system/resources/previews/011/995/200/non_2x/geometric-icon-logo-geometric-abstract-element-free-vector.jpg"
    ],
    "primaryCategory": "games",
    "tags": ["game", "miniapp", "base"],
    "heroImageUrl": "https://static.vecteezy.com/system/resources/previews/011/995/200/non_2x/geometric-icon-logo-geometric-abstract-element-free-vector.jpg",
    "tagline": "Summarise anything, anywhere!",
    "ogTitle": "summariser",
    "ogDescription": "This is summariser. It can summarise anything you give it, in 5 words or less.",
    "ogImageUrl": "https://static.vecteezy.com/system/resources/previews/011/995/200/non_2x/geometric-icon-logo-geometric-abstract-element-free-vector.jpg",
    "noindex": true
  }
}
""")
    return JsonResponse(data)


def webhook_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        payload = {}
    return JsonResponse({"ok": True, "received": payload})




