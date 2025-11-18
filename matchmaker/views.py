from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from .models import Candidate, CandidateProfile, Job
from .utils_extraction import extract_text_from_pdf, build_profile_from_text
from django.shortcuts import render, get_object_or_404, redirect
from .forms import JobForm


def _semantic_match(job, candidates):
    from .utils_matching import semantic_match as _semantic_match_impl

    return _semantic_match_impl(job, candidates)

@require_POST
def upload_cv_view(request):
    file = request.FILES.get("cv")
    nombre = request.POST.get("nombre", "Postulante")

    if not file:
        return HttpResponseBadRequest("Debe adjuntar un archivo PDF")

    # Guardar candidato
    cand = Candidate.objects.create(nombre=nombre, cv_file=file)

    # Extraer texto
    text = extract_text_from_pdf(cand.cv_file.path)
    cand.cv_text = text
    cand.save()

    # Generar perfil
    profile_data = build_profile_from_text(text)
    profile, _ = CandidateProfile.objects.update_or_create(
        candidate=cand,
        defaults={
            "rol": profile_data["rol"],
            "skills": profile_data["skills"],
            "idiomas": profile_data["idiomas"],
            "experiencia": profile_data["experiencia"],
            "meta": profile_data["meta"],
        },
    )

    return JsonResponse({
        "ok": True,
        "id": cand.id,
        "nombre": cand.nombre,
        "rol": profile.rol,
        "skills": profile.skills,
        "idiomas": profile.idiomas,
    })

def upload_form_view(request):
    return render(request, "matchmaker/upload.html")

def recruiter_dashboard(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    candidates = Candidate.objects.all().distinct('nombre')
    matches = _semantic_match(job, candidates)
    return render(request, "matchmaker/recruiter_dashboard.html", {
        "job": job,
        "matches": matches,
    })


def create_job_view(request):
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        descripcion = request.POST.get("descripcion")
        skills_obligatorias = [s.strip() for s in request.POST.get("skills_obligatorias", "").split(",") if s.strip()]
        skills_deseables = [s.strip() for s in request.POST.get("skills_deseables", "").split(",") if s.strip()]

        Job.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            skills_obligatorias=skills_obligatorias,
            skills_deseables=skills_deseables
        )

        return redirect("upload_form")

    return render(request, "matchmaker/create_job.html")
