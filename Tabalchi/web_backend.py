from __future__ import annotations

import json
import re
from typing import Any

BOL_AUDIO_MAP = {
    "ge": "Ge.m4a",
    "ga": "Ge.m4a",
    "ghet": "Ge.m4a",
    "gat": "Ge.m4a",
    "ke": "Ke.m4a",
    "ki": "Ke.m4a",
    "ka": "Ke.m4a",
    "kat": "Di.m4a",
    "ghen": "Ghen.m4a",
    "na": "Na.m4a",
    "ta": "Ta.m4a",
    "tin": "Tin.m4a",
    "thun": "Thun.m4a",
    "te": "Te.m4a",
    "ti": "Te.m4a",
    "tit": "Te.m4a",
    "tet": "Te.m4a",
    "ne": "Ne.m4a",
    "re": "Ne.m4a",
    "ra": "Ne.m4a",
    "di": "Di.m4a",
    "tere": "Tere.m4a",
    "tete": "Tete.m4a",
    "s": "S.m4a",
    "dha": "Dha.m4a",
    "dhin": "Dhin.m4a",
    "dhet": "Dhet.m4a",
    "dhe": "Dhet.m4a",
    "dhere": "Dhere.m4a",
    "dhete": "Dhete.m4a",
    "kre": "Kre.m4a",
    "kran": "Kran.m4a",
    "gran": "Dhin.m4a",
    "terekite": "Terekite.m4a",
    "gadigene": "Gadigene.m4a",
    "nagetete": "Nagetete.m4a",
    "kitetaka": "Kitetaka.m4a",
    "dheredhere": "Dheredhere.m4a",
    "teretere": "Teretere.m4a",
}

BHARI_TO_KHALI_MAP = {
    "dha": "ta",
    "ge": "ke",
    "ga": "ke",
    "ghet": "ke",
    "gat": "ke",
    "dhin": "tin",
    "dhete": "tete",
    "dheredhere": "teretere",
    "gran": "kran",
}

JATI_TO_COUNT = {
    "chatusra": 4,
    "tisra": 3,
    "khanda": 5,
    "misra": 7,
    "mishra": 7,
    "sankeerna": 9,
}

_TOKEN_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")


def _normalize_jati_count(value: Any) -> int:
    if isinstance(value, (int, float)) and value > 0:
        return int(value)

    if isinstance(value, str):
        key = value.strip().lower()
        if key in JATI_TO_COUNT:
            return JATI_TO_COUNT[key]
        try:
            number = float(key)
            if number > 0:
                return int(number)
        except ValueError:
            pass

    return 4


def infer_khali_from_bhari(text: Any) -> str:
    if not isinstance(text, str):
        return ""

    def _replace_token(match: re.Match[str]) -> str:
        token = match.group(0)
        parts = token.split("-")
        replaced_parts = [BHARI_TO_KHALI_MAP.get(part.lower(), part.lower()) for part in parts]
        merged = "-".join(replaced_parts)

        if token.isupper():
            return merged.upper()
        if token and token[0].isupper():
            return merged[0].upper() + merged[1:]
        return merged

    return _TOKEN_RE.sub(_replace_token, text)


def _push_phrase_if_present(sections: list[str], value: Any) -> None:
    if not isinstance(value, str):
        return
    trimmed = value.strip()
    if not trimmed or trimmed.lower() == "infer":
        return
    sections.append(trimmed)


def get_phrase_sections(components: Any) -> list[str]:
    sections: list[str] = []
    if not isinstance(components, dict):
        return sections

    main_theme = components.get("mainTheme")
    if isinstance(main_theme, dict):
        _push_phrase_if_present(sections, main_theme.get("bhari"))
        khali = main_theme.get("khali")
        if isinstance(khali, str) and khali.strip().lower() == "infer":
            _push_phrase_if_present(sections, infer_khali_from_bhari(main_theme.get("bhari")))
        else:
            _push_phrase_if_present(sections, khali)

    paltas = components.get("paltas")
    if isinstance(paltas, list):
        for palta in paltas:
            if not isinstance(palta, dict):
                continue
            _push_phrase_if_present(sections, palta.get("bhari"))
            khali = palta.get("khali")
            if isinstance(khali, str) and khali.strip().lower() == "infer":
                _push_phrase_if_present(sections, infer_khali_from_bhari(palta.get("bhari")))
            else:
                _push_phrase_if_present(sections, khali)

    _push_phrase_if_present(sections, components.get("tihai"))

    if not sections:
        _push_phrase_if_present(sections, components.get("content"))

    return sections


def tokenize_beat(beat_text: Any) -> list[tuple[str, str]]:
    if not isinstance(beat_text, str):
        return []

    tokens: list[tuple[str, str]] = []
    for match in _TOKEN_RE.finditer(beat_text):
        raw = match.group(0)
        normalized = raw.replace("-", "").lower()
        if normalized:
            tokens.append((raw, normalized))
    return tokens


def build_playback_plan(source_json_payload: Any) -> dict[str, Any]:
    parsed = json.loads(source_json_payload) if isinstance(source_json_payload, str) else source_json_payload
    if not isinstance(parsed, dict):
        raise ValueError("Cannot build playback plan: source is not a JSON object.")

    components = parsed.get("components")
    if not isinstance(components, dict):
        raise ValueError("Cannot build playback plan: components is missing.")

    phrase_sections = get_phrase_sections(components)
    timeline: list[dict[str, Any]] = []
    token_counter = 0

    for section in phrase_sections:
        for beat_text in section.split("|"):
            for raw_text, normalized in tokenize_beat(beat_text):
                if normalized == "infer":
                    continue

                timeline.append(
                    {
                        "kind": "token",
                        "tokenIndex": token_counter,
                        "rawText": raw_text,
                        "normalized": normalized,
                        "fileName": BOL_AUDIO_MAP.get(normalized),
                    }
                )
                token_counter += 1

            timeline.append({"kind": "divider"})

    while timeline and timeline[-1].get("kind") == "divider":
        timeline.pop()

    tokens = [item for item in timeline if item.get("kind") == "token"]
    if not tokens:
        raise ValueError("No playable bols found in components.")

    missing_audio: list[str] = []
    for item in tokens:
        if not item.get("fileName") and item["normalized"] not in missing_audio:
            missing_audio.append(item["normalized"])

    speed = parsed.get("speed")
    if not isinstance(speed, (int, float)) or speed <= 0:
        speed = 60

    jati_count = _normalize_jati_count(parsed.get("jati"))
    raw_rate = (float(speed) * jati_count) / 240.0
    playback_rate = max(0.5, min(3.0, raw_rate))

    name = parsed.get("name") if isinstance(parsed.get("name"), str) else "composition"

    return {
        "name": name,
        "speed": speed,
        "jatiCount": jati_count,
        "rawRate": raw_rate,
        "playbackRate": playback_rate,
        "timeline": timeline,
        "tokens": tokens,
        "missingAudio": missing_audio,
        "playableCount": sum(1 for item in tokens if item.get("fileName")),
    }
