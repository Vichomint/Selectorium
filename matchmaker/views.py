from django.shortcuts import render
from django.http import JsonResponse
from .models import Job, Candidate, MatchResult
from .utils import calcular_match

def match_view(request, job_id):
    job = Job.objects.get(id=job_id)
    candidates = Candidate.objects.all()

    results = []
    for cand in candidates:
        score = calcular_match(job.descripcion, cand.cv_text)
        MatchResult.objects.create(job=job, candidate=cand, score=score)
        results.append({
            "candidate": cand.nombre,
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return JsonResponse({"job": job.titulo, "matches": results})
