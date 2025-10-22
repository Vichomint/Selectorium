import fitz
import re
from transformers import pipeline
from .skills_dictionary import SKILL_DICTIONARY



def normalize_skills(skills):
    """Limpia, deduplica y ordena las habilidades."""
    clean = set()
    for s in skills:
        s = re.sub(r"[^a-zA-Z0-9#+\-\.\s]", "", s)  # quita símbolos raros
        s = s.replace("##", "").strip().lower()
        if len(s) > 1:
            clean.add(s)
    return sorted(clean)


# Modelo NER de Hugging Face (detecta entidades útiles en español)
_ner = pipeline(
    "token-classification",
    model="mrm8488/bert-spanish-cased-finetuned-ner",
    aggregation_strategy="simple",
)

# --- LECTURA PDF ---
def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text")
    return text.strip()


# --- SKILL MATCHING ---
def extract_skills_from_text(text: str):
    found = set()

    # 1) buscar skills usando regex y diccionario amplio
    for category, skills in SKILL_DICTIONARY.items():
        for skill in skills:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
                found.add(skill.lower())

    # 2) detección NER adicional (palabras técnicas)
    preds = _ner(text[:1500])  # solo los primeros 1500 caracteres (512 tokens aprox)
    for p in preds:
        w = p["word"].strip().lower()
        if len(w) > 2 and not w.startswith("##"):
            found.add(w)

    return normalize_skills(list(found))


# --- CREACIÓN PERFIL ---
def build_profile_from_text(text: str):
    skills = extract_skills_from_text(text)

    idiomas = []
    if re.search(r"ingl[eé]s", text, re.I):
        idiomas.append("Inglés")
    if re.search(r"español", text, re.I):
        idiomas.append("Español")

    rol = None
    if re.search(r"\bbackend\b|django|api|fastapi|flask", text, re.I):
        rol = "Backend Developer"
    elif re.search(r"\bfrontend\b|react|vue|angular", text, re.I):
        rol = "Frontend Developer"
    elif re.search(r"\bdata\b|etl|pandas|machine learning|ml\b", text, re.I):
        rol = "Data Engineer / ML"

    return {
        "rol": rol or "Desarrollador",
        "skills": sorted(set(skills)),
        "idiomas": idiomas or ["Español"],
        "experiencia": "",
        "meta": {},
    }
