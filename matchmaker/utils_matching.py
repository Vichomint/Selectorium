from sentence_transformers import SentenceTransformer, util
from .skills_dictionary import SKILL_DICTIONARY
import re

# Sentence-Transformers models
_model = SentenceTransformer("anass1209/resume-job-matcher-all-MiniLM-L6-v2")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def filter_text_by_skills(text: str):
    """Return only dictionary skills found in a free text."""
    skills_flat = sum(SKILL_DICTIONARY.values(), [])
    found = set()
    for s in skills_flat:
        if re.search(rf"\b{re.escape(s)}\b", text or "", re.I):
            found.add(s.lower())
    return " ".join(sorted(found))


def expand_job_description(job_text: str):
    """Append found skills to a job description for better matching."""
    skills_flat = sum(SKILL_DICTIONARY.values(), [])
    found = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", job_text or "", re.I)]
    return f"{job_text}\n\nSkills requeridas: {' '.join(found)}"


def semantic_match(job, candidates):
    """Return ordered matches for a Job over all candidates."""
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

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def calculate_match_score(cv_skills, job_description, skills_obligatorias=None, skills_deseables=None):
    """
    Adaptive scoring that combines:
    - lexical overlap of skills (dictionary-based)
    - embedding similarity CV <-> description
    - optional embeddings for oblig/deseable lists

    Returns score in [0, 100].
    """

    cv_text = " ".join(cv_skills or [])

    # If no explicit job skill lists, infer from description
    if (not skills_obligatorias) and (not skills_deseables):
        skills_flat = sum(SKILL_DICTIONARY.values(), [])
        inferred = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", job_description or "", re.I)]
        skills_obligatorias = inferred

    oblig_list = skills_obligatorias or []
    deseab_list = skills_deseables or []
    oblig_text = " ".join(oblig_list)
    deseab_text = " ".join(deseab_list)

    # Lexical overlap between CV skills and job skills
    cv_set = {str(s).strip().lower() for s in (cv_skills or []) if str(s).strip()}
    job_set = {str(s).strip().lower() for s in (oblig_list + deseab_list) if str(s).strip()}
    overlap_ratio = 0.0
    if job_set:
        overlap_ratio = len(cv_set.intersection(job_set)) / max(1, len(job_set))

    # Embeddings
    emb_cv = model.encode(cv_text, convert_to_tensor=True)
    emb_desc = model.encode(job_description or "", convert_to_tensor=True)
    emb_oblig = model.encode(oblig_text, convert_to_tensor=True) if oblig_text else None
    emb_deseab = model.encode(deseab_text, convert_to_tensor=True) if deseab_text else None

    sim_general = util.cos_sim(emb_cv, emb_desc).item()
    sim_oblig = util.cos_sim(emb_cv, emb_oblig).item() if emb_oblig is not None else 0.0
    sim_deseab = util.cos_sim(emb_cv, emb_deseab).item() if emb_deseab is not None else 0.0

    # Adaptive weights
    if not oblig_text and not deseab_text:
        # No explicit lists: rely on general similarity and (if inferred) overlap
        peso_overlap = 0.6 if job_set else 0.0
        peso_general = 1.0 - peso_overlap
        peso_oblig = 0.0
        peso_deseab = 0.0
    else:
        # With explicit lists: prioritize lexical overlap; complement with embeddings
        peso_overlap = 0.5
        peso_oblig = 0.2
        peso_deseab = 0.1
        peso_general = 0.2

    score_final = (
        peso_overlap * overlap_ratio +
        peso_oblig * sim_oblig +
        peso_deseab * sim_deseab +
        peso_general * sim_general
    )

    # Clamp to [0, 1] and scale
    score_final = max(0.0, min(1.0, score_final))
    return round(score_final * 100, 2)

