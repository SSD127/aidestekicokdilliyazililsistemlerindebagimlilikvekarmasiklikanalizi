from __future__ import annotations

import json
from typing import Any

import requests


def _build_prompt(run_summary: dict[str, Any]) -> str:
    return (
        "Sen kıdemli bir yazılım mimarısın. "
        "Asagidaki analiz verilerini inceleyerek en fazla 6 satırda Turkce bir degerlendirme yap. "
        "Ana riskleri ve 2 somut refactor onerisini belirt.\n\n"
        f"Analiz ozeti:\n{json.dumps(run_summary, ensure_ascii=False)}"
    )


def _fallback_insight(run_summary: dict[str, Any]) -> str:
    hotspots = run_summary.get("hotspots", [])
    top = hotspots[0] if hotspots else None
    if not top:
        return (
            "Bu run icin hotspot verisi bulunamadi. "
            "Oncelikle parser/metrik ciktilarinin ingest edildigini dogrulayin."
        )
    return (
        f"En riskli nokta `{top.get('function_name', 'unknown')}` "
        f"(skor: {top.get('score', 0)}). "
        "Bu fonksiyonu daha kucuk parcalara bolup kosul karmasikligini azaltmayi onceliklendirin. "
        "Ikinci adim olarak bagimli modullerin sinirlarini netlestirip dongusel bagimliliklari giderin."
    )


def generate_ai_insight(
    run_summary: dict[str, Any],
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
) -> dict[str, str]:
    prompt = _build_prompt(run_summary)

    if openai_api_key:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=20,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return {"provider": "openai", "insight": text.strip()}

    if gemini_api_key:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            params={"key": gemini_api_key},
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return {"provider": "gemini", "insight": text.strip()}

    return {"provider": "rule-based", "insight": _fallback_insight(run_summary)}
