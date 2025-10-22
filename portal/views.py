from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Profile , Vacante, Postulacion,Pregunta,Respuesta
from django.utils import timezone
from django.contrib import messages
import logging
from matchmaker.utils_extraction import extract_text_from_pdf, build_profile_from_text
from matchmaker.utils_matching import calculate_match_score
from matchmaker.skills_dictionary import SKILL_DICTIONARY
import re
import json
from matchmaker.skills_dictionary import SKILL_DICTIONARY
import re

# LOGIN
def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("postulante_dashboard")
        return render(request, "login.html", {"form": {"errors": True}})
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")

def signup_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password1"]
        role = request.POST["role"]

        user = User.objects.create_user(username=username, email=email, password=password)
        Profile.objects.create(user=user, role=role)  # 👈 se crea el perfil

        return redirect("login")

    return render(request, "signup.html")

# Postulante
@login_required
def postulante_dashboard(request):
    return render(request, "postulante/dashboard.html")

@login_required
def perfil_postulante(request):
    # Crea el perfil si no existe
    perfil, created = Profile.objects.get_or_create(user=request.user)
    errores = []

    if request.method == "POST":
        # Datos generales
        perfil.fecha_nacimiento = request.POST.get("fecha_nacimiento")
        perfil.nivel_educacion = request.POST.get("nivel_educacion")
        perfil.area_profesional = request.POST.get("area_profesional")
        perfil.anios_experiencia = request.POST.get("anios_experiencia")
        perfil.tipo_jornada = request.POST.get("tipo_jornada")
        perfil.pretension_renta = request.POST.get("pretension_renta")
        perfil.disponibilidad = request.POST.get("disponibilidad")
        perfil.movilidad = request.POST.get("movilidad") == "on"

        # Chips (habilidades blandas y técnicas)
        perfil.habilidades_blandas = request.POST.get("habilidades_blandas", "").strip()
        perfil.habilidades_tecnicas = request.POST.get("habilidades_tecnicas", "").strip()

        # Archivos
        if "foto" in request.FILES:
            perfil.foto = request.FILES["foto"]
        if "cv" in request.FILES:
            perfil.cv = request.FILES["cv"]
            # Guardamos primero para asegurar el archivo en disco
            try:
                perfil.save()
                # Extraer texto del CV y generar perfil automático
                text = extract_text_from_pdf(perfil.cv.path)
                profile_data = build_profile_from_text(text)
                # Persistir habilidades técnicas y rol sugerido
                perfil.habilidades_tecnicas = ", ".join(profile_data.get("skills", []))
                if not perfil.area_profesional:
                    perfil.area_profesional = profile_data.get("rol")
                perfil.save()
            except Exception as e:
                logging.getLogger(__name__).exception("Error extrayendo skills del CV")
                errores.append("No se pudo procesar el CV para extraer habilidades.")

        # Validaciones obligatorias
        if not perfil.cv:
            errores.append("Debe subir su currículum antes de continuar.")
        if not perfil.area_profesional or not perfil.nivel_educacion:
            errores.append("Debe completar su formación y área profesional.")
        if not perfil.pretension_renta:
            errores.append("Debe indicar su pretensión de renta.")

        # Guardar si no hay errores
        if not errores:
            perfil.save()
            messages.success(request," ")
            return redirect("perfil_postulante")

    # Separar chips para mostrar como listas
    habilidades_blandas = [
        c.strip() for c in (perfil.habilidades_blandas or "").split(",") if c.strip()
    ]
    habilidades_tecnicas = [
        c.strip() for c in (perfil.habilidades_tecnicas or "").split(",") if c.strip()
    ]

    context = {
        "perfil": perfil,
        "errores": errores,
        "habilidades_blandas": habilidades_blandas,
        "habilidades_tecnicas": habilidades_tecnicas,
    }

    return render(request, "postulante/perfil_postulante.html", context)



# Reclutador
@login_required
def reclutador_dashboard(request):
    # Resumen
    vacantes_activas = Vacante.objects.filter(reclutador=request.user, activa=True).order_by("-fecha_publicacion")
    total_activas = vacantes_activas.count()

    postulaciones_no_vistas = Postulacion.objects.select_related("vacante", "postulante").filter(
        vacante__reclutador=request.user, estado="enviado"
    ).order_by("-fecha_postulacion")
    total_no_vistas = postulaciones_no_vistas.count()

    # Últimas 3 vacantes abiertas con métricas
    ultimas_vacantes = []
    for v in vacantes_activas[:3]:
        qs = Postulacion.objects.filter(vacante=v)
        total = qs.count()
        aptos = 0
        for p in qs.select_related("postulante"):
            perfil_post = getattr(p.postulante, "profile", None)
            if not perfil_post:
                continue
            cv_text = (perfil_post.habilidades_tecnicas or "")
            cv_skills = [s.strip() for s in cv_text.split(",") if s.strip()]
            if not cv_skills:
                continue
            try:
                score = calculate_match_score(cv_skills=cv_skills, job_description=v.descripcion or "", skills_obligatorias=[], skills_deseables=[])
                if score is not None and float(score) >= 40.0:
                    aptos += 1
            except Exception:
                pass
        ultimas_vacantes.append({
            "obj": v,
            "postulaciones": total,
            "aptos": aptos,
        })

    # Skills más demandadas en las vacantes activas (diccionario)
    skill_counts = {}
    skills_flat = sum(SKILL_DICTIONARY.values(), [])
    for v in vacantes_activas:
        desc = v.descripcion or ""
        for s in skills_flat:
            if re.search(rf"\b{re.escape(s)}\b", desc, re.I):
                skill_counts[s] = skill_counts.get(s, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    context = {
        "total_activas": total_activas,
        "total_no_vistas": total_no_vistas,
        "postulaciones_no_vistas": postulaciones_no_vistas[:5],
        "ultimas_vacantes": ultimas_vacantes,
        "top_skills": [k for k, _ in top_skills],
    }
    return render(request, "reclutador/dashboard.html", context)

@login_required
def reclutador_estadisticas(request):
    # Vacantes del reclutador
    vacantes = Vacante.objects.filter(reclutador=request.user).order_by("-fecha_publicacion")

    labels = []
    postulaciones_counts = []
    aptos_counts = []

    for v in vacantes:
        labels.append(v.titulo)
        qs = Postulacion.objects.filter(vacante=v)
        postulaciones_counts.append(qs.count())

        # Contar aptos (Apto o Muy apto => score >= 40)
        aptos = 0
        for p in qs.select_related("postulante"):
            perfil_post = getattr(p.postulante, "profile", None)
            if not perfil_post:
                continue
            cv_text = (perfil_post.habilidades_tecnicas or "").strip()
            if not cv_text:
                continue
            cv_skills = [s.strip() for s in cv_text.split(",") if s.strip()]
            if not cv_skills:
                continue
            try:
                score = calculate_match_score(
                    cv_skills=cv_skills,
                    job_description=v.descripcion or "",
                    skills_obligatorias=[],
                    skills_deseables=[],
                )
                if score is not None and float(score) >= 40.0:
                    aptos += 1
            except Exception:
                pass
        aptos_counts.append(aptos)

    context = {
        "chart_labels": json.dumps(labels, ensure_ascii=False),
        "chart_postulaciones": json.dumps(postulaciones_counts),
        "chart_aptos": json.dumps(aptos_counts),
    }
    return render(request, "reclutador/estadisticas.html", context)

# Postulación a vacante
@login_required
def formulario_postulacion(request):
    return render(request, "postulacion/formulario.html")

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Dashboard postulante (ya lo tienes)
@login_required
def postulante_dashboard(request):
    return render(request, "postulante/dashboard.html")

# Mis Postulaciones
@login_required
def mis_postulaciones(request):
    postulaciones = Postulacion.objects.filter(postulante=request.user).select_related("vacante")
    # Obtener habilidades procesadas desde el perfil
    perfil = Profile.objects.filter(user=request.user).first()
    cv_skills = []
    if perfil and (perfil.habilidades_tecnicas or "").strip():
        cv_skills = [s.strip() for s in perfil.habilidades_tecnicas.split(",") if s.strip()]

    # Calcular score de match para cada postulación
    for p in postulaciones:
        try:
            p.match_score = calculate_match_score(
                cv_skills=cv_skills,
                job_description=p.vacante.descripcion or "",
                skills_obligatorias=[],
                skills_deseables=[],
            ) if cv_skills else None
        except Exception:
            p.match_score = None

        # Mapear a etiqueta cualitativa
        def _to_label(score):
            if score is None:
                return None
            # Normalizar negativas a 0 para evitar "-x%"
            s = max(0.0, float(score))
            if s >= 70:
                return "Muy apto"
            if s >= 40:
                return "Apto"
            if s >= 15:
                return "Poco apto"
            return "No apto"

        p.match_label = _to_label(p.match_score)

    return render(request, "postulante/mis_postulaciones.html", {"postulaciones": postulaciones})


# Configuración
@login_required
def configuracion_postulante(request):
    if request.method == "POST":
        # Aquí podrías actualizar el email o contraseña
        # O redirigir a Django's PasswordChangeView
        pass
    return render(request, "postulante/configuracion.html")

 

@login_required
def reclutador_vacantes(request):
    vacantes = Vacante.objects.filter(reclutador=request.user).order_by("-fecha_publicacion")
    return render(request, "reclutador/vacantes.html", {"vacantes": vacantes})


@login_required
def reclutador_postulantes(request):
    postulaciones = Postulacion.objects.select_related(
        'postulante',
        'vacante'
    ).filter(vacante__reclutador=request.user)
    
    print("DEBUG - Número de postulaciones:", postulaciones.count())  # Debug
    for p in postulaciones:
        print(f"DEBUG - Postulante: {p.postulante.first_name}")  # Debug
    
    return render(request, "reclutador/postulantes.html", {
        'postulaciones': postulaciones
    })


@login_required
def reclutador_configuracion(request):
    return render(request, "reclutador/configuracion.html")


def role_redirect_view(request):
    if request.user.is_authenticated:
        if request.user.profile.role == "postulante":
            return redirect("postulante_dashboard")
        elif request.user.profile.role == "reclutador":
            return redirect("reclutador_dashboard")
    return redirect("login")

def home_redirect(request):
    return redirect("login")

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Redirección según rol
            if hasattr(user, "profile"):
                if user.profile.role == "postulante":
                    return redirect("postulante_dashboard")
                elif user.profile.role == "reclutador":
                    return redirect("reclutador_dashboard")

            # fallback (por si no tiene perfil)
            return redirect("login")

        return render(request, "login.html", {"form": {"errors": True}})

    return render(request, "login.html")

@login_required
def crear_vacante(request):
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        descripcion = request.POST.get("descripcion")
        ubicacion = request.POST.get("ubicacion")
        preguntas = request.POST.getlist("preguntas")  # lista de preguntas

        vacante = Vacante.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            ubicacion=ubicacion,
            reclutador=request.user
        )

        # Guardar preguntas
        for p in preguntas:
            if p.strip() != "":
                Pregunta.objects.create(vacante=vacante, texto=p.strip())

        return redirect("reclutador_vacantes")

    return render(request, "reclutador/crear_vacante.html")



@login_required
def listar_vacantes(request):
    vacantes = Vacante.objects.filter(activa=True).order_by("-fecha_publicacion")
    return render(request, "postulante/listar_vacantes.html", {"vacantes": vacantes})

from django.contrib import messages
from .models import Vacante, Postulacion

@login_required
def postular_vacante(request, vacante_id):
    vacante = Vacante.objects.get(id=vacante_id)

    # evitar postulaciones duplicadas
    if Postulacion.objects.filter(postulante=request.user, vacante=vacante).exists():
        messages.warning(request, "Ya te has postulado a esta vacante.")
    else:
        Postulacion.objects.create(postulante=request.user, vacante=vacante)
        messages.success(request, "Tu postulación ha sido enviada con éxito.")

    return redirect("listar_vacantes")

@login_required
def detalle_vacante(request, vacante_id):
    vacante = Vacante.objects.get(id=vacante_id)
    return render(request, "postulante/detalle_vacante.html", {"vacante": vacante})



@login_required
def administrar_vacante(request, vacante_id):
    vacante = get_object_or_404(Vacante, id=vacante_id, reclutador=request.user)
    postulaciones = Postulacion.objects.filter(vacante=vacante).select_related("postulante")

    # Marcar como visto (cuando reclutador hace clic)
    if request.method == "POST":
        postulacion_id = request.POST.get("postulacion_id")
        postulacion = get_object_or_404(Postulacion, id=postulacion_id, vacante=vacante)
        if postulacion.estado == "enviado":
            postulacion.estado = "visto"
            postulacion.save()
        return redirect("administrar_vacante", vacante_id=vacante.id)

    # Calcular etiqueta de match y chips de skills para previsualizar en la lista
    skills_flat = sum(SKILL_DICTIONARY.values(), [])
    for p in postulaciones:
        perfil_post = getattr(p.postulante, "profile", None)
        cv_skills = []
        if perfil_post and (perfil_post.habilidades_tecnicas or "").strip():
            cv_skills = [s.strip() for s in perfil_post.habilidades_tecnicas.split(",") if s.strip()]
        p.match_label = None
        p.matched_skills = []
        if cv_skills:
            try:
                score = calculate_match_score(
                    cv_skills=cv_skills,
                    job_description=vacante.descripcion or "",
                    skills_obligatorias=[],
                    skills_deseables=[],
                )
                s = max(0.0, float(score))
                if s >= 70:
                    p.match_label = "Muy apto"
                elif s >= 40:
                    p.match_label = "Apto"
                elif s >= 15:
                    p.match_label = "Poco apto"
                else:
                    p.match_label = "No apto"
            except Exception:
                p.match_label = None

            # Skills que coinciden (según diccionario y descripción)
            try:
                desc = (vacante.descripcion or "")
                found_job = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", desc, re.I)]
                # Detectar skills en el texto del CV (cadena completa), no solo por split
                cv_text = perfil_post.habilidades_tecnicas or ""
                found_cv = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", cv_text, re.I)]
                # Intersección
                cv_set = {s.lower() for s in found_cv}
                overlap = [s for s in found_job if s.lower() in cv_set]
                if overlap:
                    p.matched_skills = overlap[:6]
                elif found_cv:
                    p.matched_skills = found_cv[:6]
                else:
                    p.matched_skills = found_job[:6]
            except Exception:
                p.matched_skills = []

    return render(request, "reclutador/administrar_vacante.html", {
        "vacante": vacante,
        "postulaciones": postulaciones,
    })

@login_required
def cerrar_vacante(request, vacante_id):
    vacante = get_object_or_404(Vacante, id=vacante_id, reclutador=request.user)
    if request.method == "POST":
        vacante.activa = False
        vacante.save()
        messages.success(request, "Vacante cerrada correctamente.")
        return redirect("reclutador_dashboard")
    return redirect("administrar_vacante", vacante_id=vacante.id)



@login_required
def detalle_vacante(request, vacante_id):
    vacante = Vacante.objects.get(id=vacante_id)
    # Verificar si ya existe una postulación del usuario
    ya_postulado = Postulacion.objects.filter(postulante=request.user, vacante=vacante).exists()

    if request.method == "POST" and not ya_postulado:
        Postulacion.objects.create(postulante=request.user, vacante=vacante, estado="enviado")
        return redirect("mis_postulaciones")

    return render(request, "postulante/detalle_vacante.html", {
        "vacante": vacante,
        "ya_postulado": ya_postulado,
    })

@login_required
def perfil_postulante_detalle(request, postulante_id):
    perfil = Profile.objects.get(user_id=postulante_id, role="postulante")
    return render(request, "reclutador/perfil_postulante.html", {"perfil": perfil})

#borrar foto
@login_required
def perfil_borrar_foto(request):
    perfil = get_object_or_404(Profile, user=request.user)
    if perfil.foto:
        perfil.foto.delete(save=False)  # borrar archivo
        perfil.foto = None
        perfil.save()
    return redirect("perfil_postulante")


 
@login_required
def detalle_postulante(request, vacante_id, postulacion_id):
    postulacion = get_object_or_404(Postulacion, id=postulacion_id, vacante__id=vacante_id, vacante__reclutador=request.user)

    # Si aún no se ha marcado como visto → lo marcamos
    if postulacion.estado == "enviado":
        postulacion.estado = "visto"
        postulacion.fecha_visto = timezone.now()
        postulacion.save()

    # Aquí puedes traer también el perfil del postulante y sus respuestas
    perfil = getattr(postulacion.postulante, "profile", None)
    respuestas = postulacion.respuestas.select_related("pregunta").all() if hasattr(postulacion, "respuestas") else []

    # Calcular match del postulante con la vacante (usando skills del perfil)
    match_score = None
    match_label = None
    top_skills = []
    if perfil and (perfil.habilidades_tecnicas or "").strip():
        cv_skills = [s.strip() for s in perfil.habilidades_tecnicas.split(",") if s.strip()]
        try:
            match_score = calculate_match_score(
                cv_skills=cv_skills,
                job_description=postulacion.vacante.descripcion or "",
                skills_obligatorias=[],
                skills_deseables=[],
            )
        except Exception:
            match_score = None
        # Etiqueta cualitativa
        if match_score is not None:
            s = max(0.0, float(match_score))
            if s >= 70:
                match_label = "Muy apto"
            elif s >= 40:
                match_label = "Apto"
            elif s >= 15:
                match_label = "Poco apto"
            else:
                match_label = "No apto"
        top_skills = cv_skills[:10]

    return render(request, "reclutador/detalle_postulante.html", {
        "postulacion": postulacion,
        "perfil": perfil,
        "respuestas": respuestas,
        "match_score": match_score,
        "match_label": match_label,
        "top_skills": top_skills,
    })
