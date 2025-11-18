import re
from .skills_dictionary import SKILL_DICTIONARY

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

_ner = None
_ner_failed = False


def _get_ner_pipeline():
    """Intenta inicializar el pipeline NER solo una vez; si falla, lo desactiva."""
    global _ner, _ner_failed
    if _ner is not None or _ner_failed:
        return _ner
    try:
        from transformers import pipeline

        _ner = pipeline(
            "token-classification",
            model="mrm8488/bert-spanish-cased-finetuned-ner",
            aggregation_strategy="simple",
        )
    except Exception:
        _ner_failed = True
        _ner = None
    return _ner


def normalize_skills(skills):
    clean = set()
    for s in skills:
        s = re.sub(r"[^a-zA-Z0-9#+\-\.\s]", "", s)
        s = s.replace("##", "").strip().lower()
        if len(s) > 1:
            clean.add(s)
    return sorted(clean)


def extract_text_from_pdf(file_path: str) -> str:
    if not file_path:
        return ""

    if fitz is not None:
        try:
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text("text")
            if text.strip():
                return text.strip()
        except Exception:
            pass

    if PdfReader is not None:
        try:
            reader = PdfReader(file_path)
            text = "".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text.strip()
        except Exception:
            pass

    return ""


def extract_skills_from_text(text: str):
    if not text:
        return []

    found = set()
    for skills in SKILL_DICTIONARY.values():
        for skill in skills:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
                found.add(skill.lower())

    ner = _get_ner_pipeline()
    if ner is not None:
        try:
            preds = ner(text[:1500])
            for p in preds:
                w = (p.get("word") or "").strip().lower()
                if len(w) > 2 and not w.startswith("##"):
                    found.add(w)
        except Exception:
            pass

    return normalize_skills(list(found))


def build_profile_from_text(text: str):
    normalized = text or ""
    skills = extract_skills_from_text(normalized)

    idiomas = []
    if re.search(r"inglés", normalized, re.I):
        idiomas.append("Inglés")
    if re.search(r"español", normalized, re.I):
        idiomas.append("Español")

    if not skills:
        possible = []
        for line in normalized.splitlines():
            low = line.lower()
            if "habilidad" in low or "skill" in low:
                tokens = re.split(r"[•·\-\u2022,;]", line)
                possible.extend(t.strip() for t in tokens if len(t.strip()) > 2)
        skills = extract_skills_from_text(" ".join(possible))

    rol = None
    if re.search(r"\bbackend\b|django|api|fastapi|flask", normalized, re.I):
        rol = "Backend Developer"
    elif re.search(r"\bfrontend\b|react|vue|angular", normalized, re.I):
        rol = "Frontend Developer"
    elif re.search(r"\bdata\b|etl|pandas|machine learning|ml\b", normalized, re.I):
        rol = "Data Engineer / ML"

    return {
        "rol": rol or "Desarrollador",
        "skills": sorted(set(skills)),
        "idiomas": idiomas or ["Español"],
        "experiencia": "",
        "meta": {},
    }
