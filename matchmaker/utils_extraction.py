import re
from .skills_dictionary import SKILL_DICTIONARY

# Dependencias pesadas: cargar de forma perezosa y tolerante a errores
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

_ner = None
_ner_failed = False


def _get_ner_pipeline():
    """Intenta inicializar el pipeline NER solo una vez; si falla, desactiva NER."""
    global _ner, _ner_failed
    if _ner is not None or _ner_failed:
        return _ner
    try:
        from transformers import pipeline  # import local para tolerar entornos sin transformers
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
    """Limpia, deduplica y ordena las habilidades."""
    clean = set()
    for s in skills:
        s = re.sub(r"[^a-zA-Z0-9#+\-\.\s]", "", s)
        s = s.replace("##", "").strip().lower()
        if len(s) > 1:
            clean.add(s)
    return sorted(clean)


# --- LECTURA PDF ---
def extract_text_from_pdf(file_path: str) -> str:
    if not file_path:
        return ""
    if fitz is None:
        return ""
    try:
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text("text")
        return text.strip()
    except Exception:
        return ""


# --- SKILL MATCHING ---
def extract_skills_from_text(text: str):
    found = set()

    if not text:
        return []

    # 1) buscar skills usando regex y diccionario amplio
    for category, skills in SKILL_DICTIONARY.items():
        for skill in skills:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
                found.add(skill.lower())

    # 2) NER opcional (si el pipeline está disponible y operativo)
    ner = _get_ner_pipeline()
    if ner is not None:
        try:
            preds = ner(text[:1500])  # limitar para rendimiento
            for p in preds:
                w = (p.get("word") or "").strip().lower()
                if len(w) > 2 and not w.startswith("##"):
                    found.add(w)
        except Exception:
            # si falla en runtime, continuar con lo encontrado por diccionario
            pass

    return normalize_skills(list(found))


# --- CREACIÓN PERFIL ---
def build_profile_from_text(text: str):
    skills = extract_skills_from_text(text)

    idiomas = []
    if re.search(r"ingl[eǸ]s", text or "", re.I):
        idiomas.append("InglǸs")
    if re.search(r"espa��ol", text or "", re.I):
        idiomas.append("Espa��ol")

    rol = None
    if re.search(r"\bbackend\b|django|api|fastapi|flask", text or "", re.I):
        rol = "Backend Developer"
    elif re.search(r"\bfrontend\b|react|vue|angular", text or "", re.I):
        rol = "Frontend Developer"
    elif re.search(r"\bdata\b|etl|pandas|machine learning|ml\b", text or "", re.I):
        rol = "Data Engineer / ML"

    return {
        "rol": rol or "Desarrollador",
        "skills": sorted(set(skills)),
        "idiomas": idiomas or ["Espa��ol"],
        "experiencia": "",
        "meta": {},
    }

