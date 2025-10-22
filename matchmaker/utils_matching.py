from sentence_transformers import SentenceTransformer, util
from .skills_dictionary import SKILL_DICTIONARY
import torch, re

_model = SentenceTransformer("anass1209/resume-job-matcher-all-MiniLM-L6-v2")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def filter_text_by_skills(text: str):
    """Filtra el texto del CV dejando solo skills del diccionario."""
    skills_flat = sum(SKILL_DICTIONARY.values(), [])
    found = set()
    for s in skills_flat:
        if re.search(rf"\b{re.escape(s)}\b", text, re.I):
            found.add(s.lower())
    return " ".join(sorted(found))

def expand_job_description(job_text: str):
    """Agrega skills relevantes del diccionario a la descripción del trabajo."""
    from .skills_dictionary import SKILL_DICTIONARY
    skills_flat = sum(SKILL_DICTIONARY.values(), [])
    found = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", job_text, re.I)]
    return f"{job_text}\n\nSkills requeridas: {' '.join(found)}"



def semantic_match(job, candidates):
    """
    Genera una lista de coincidencias (matches) entre un Job y todos los candidatos.
    Retorna una lista con nombre, rol, idiomas, skills y score.
    """
    matches = []

    for cand in candidates:
        profile = getattr(cand, "candidateprofile", None)
        if not profile or not profile.skills:
            continue

        score = calculate_match_score(
            cv_skills=profile.skills,
            job_description=job.descripcion,
            skills_obligatorias=job.skills_obligatorias,
            skills_deseables=job.skills_deseables,
        )

        matches.append({
            "candidate": cand.nombre,
            "rol": profile.rol,
            "idiomas": profile.idiomas,
            "skills": profile.skills,
            "score": score,
            "cv_url": cand.cv_file.url if cand.cv_file else "#",
        })

    # Ordenar de mayor a menor puntaje
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches



def calculate_match_score(cv_skills, job_description, skills_obligatorias=None, skills_deseables=None):
    """
    Calcula un puntaje ponderado considerando:
    - skills obligatorias: peso alto
    - skills deseables: peso medio
    - similitud general CV ↔ descripción: peso bajo
    """

    cv_text = " ".join(cv_skills)
    oblig_text = " ".join(skills_obligatorias or [])
    deseab_text = " ".join(skills_deseables or [])

    emb_cv = model.encode(cv_text, convert_to_tensor=True)
    emb_desc = model.encode(job_description, convert_to_tensor=True)
    emb_oblig = model.encode(oblig_text, convert_to_tensor=True) if oblig_text else None
    emb_deseab = model.encode(deseab_text, convert_to_tensor=True) if deseab_text else None

    sim_general = util.cos_sim(emb_cv, emb_desc).item()
    sim_oblig = util.cos_sim(emb_cv, emb_oblig).item() if emb_oblig is not None else 0
    sim_deseab = util.cos_sim(emb_cv, emb_deseab).item() if emb_deseab is not None else 0

    # Ponderación: obligatorias pesan más
    peso_oblig = 0.5
    peso_deseab = 0.3
    peso_general = 0.2

    score_final = (
        peso_oblig * sim_oblig +
        peso_deseab * sim_deseab +
        peso_general * sim_general
    )

    return round(score_final * 100, 2)