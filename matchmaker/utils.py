from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("anass1209/resume-job-matcher-all-MiniLM-L6-v2")

def calcular_match(job_text, cv_text):
    """Devuelve un puntaje de similitud entre oferta y CV."""
    emb_job = model.encode(job_text, convert_to_tensor=True)
    emb_cv = model.encode(cv_text, convert_to_tensor=True)
    sim = util.cos_sim(emb_job, emb_cv).item()
    score = round(sim * 100, 2)
    return score

def explicar_match(job_text, cv_text):
    """Devuelve una explicación simple del match."""
    job_keywords = set(job_text.lower().split())
    cv_keywords = set(cv_text.lower().split())
    common_keywords = job_keywords.intersection(cv_keywords)
    if not common_keywords:
        return "No se encontraron palabras clave comunes."
    explanation = f"Palabras clave comunes: {', '.join(common_keywords)}"
    return explanation
# Ejemplo de uso:
# job_desc = "Se busca desarrollador Python con experiencia en Django y REST."