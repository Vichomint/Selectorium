from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Profile , Vacante, Postulacion,Pregunta,Respuesta
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
import logging
from matchmaker.utils_extraction import extract_text_from_pdf, build_profile_from_text
from matchmaker.skills_dictionary import SKILL_DICTIONARY
import re
import json
from django.db.models import Q, Count
from collections import Counter


def _calculate_match_score(*, cv_skills, job_description, skills_obligatorias, skills_deseables):
    """Deferred import to avoid loading heavy matching stack when not needed."""
    from matchmaker.utils_matching import calculate_match_score as _calc

    return _calc(
        cv_skills=cv_skills,
        job_description=job_description,
        skills_obligatorias=skills_obligatorias,
        skills_deseables=skills_deseables,
    )


def landing_view(request):
    plan_cards = [
        {
            "name": "Starter",
            "price": "Gratis",
            "description": "Recluta con IA desde el primer día y mide el impacto sin compromisos.",
            "cta": "Crear cuenta",
            "cta_url_name": "signup",
            "tagline": "Optimizado para equipos en fase piloto",
            "improvement": "Mejora continua del dashboard de vacantes y reportes semanales automáticos.",
            "features": [
                "Hasta 6 vacantes activas simultáneas",
                "Motor de búsqueda semántica básico",
                "Insights de mercado esenciales",
                "Soporte por correo en 48h",
            ],
        },
        {
            "name": "Growth",
            "price": "$15.000 clp/mes",
            "description": "Automatiza procesos completos y comparte analítica avanzada con tu equipo.",
            "cta": "Hablar con ventas",
            "cta_url": "mailto:contacto@selectorium.ai",
            "tagline": "Plan recomendado",
            "improvement": "Nuevas integraciones ATS trimestrales y mejoras en scorecards colaborativos.",
            "features": [
                "Vacantes ilimitadas",
                "Matching predictivo + ranking inteligente",
                "Panel colaborativo para recruiters",
                "Soporte prioritario en 4h",
            ],
        },
        {
            "name": "Enterprise",
            "price": "A medida",
            "description": "Suite completa de Talent Intelligence, seguridad corporativa y roadmap conjunto.",
            "cta": "Agenda una demo",
            "cta_url": "mailto:contacto@selectorium.ai",
            "tagline": "Innovación conjunta",
            "improvement": "Roadmap compartido con releases mensuales, APIs privadas y personalizaciones.",
            "features": [
                "Acceso multi-país y multi-marca",
                "Modelos personalizados de scoring",
                "SLAs dedicados y Customer Success",
                "Implementación y training onsite",
            ],
        },
    ]

    metrics = [
        {"value": "5x", "label": "Más rápido filtrando talento"},
        {"value": "92%", "label": "Precisión promedio del matching"},
        {"value": "-38%", "label": "Reducción en rotación del primer año"},
    ]

    pillars = [
        {
            "title": "Experiencia candidata memorable",
            "description": "Portales personalizados, recordatorios automáticos y feedback en un solo hilo.",
        },
        {
            "title": "Analítica accionable",
            "description": "Mapas de habilidades, funnels por etapa y alertas tempranas de embudos saturados.",
        },
        {
            "title": "Integración sencilla",
            "description": "API y conectores nativos con herramientas ATS y colaboración vía Slack/Teams.",
        },
    ]

    return render(
        request,
        "landing.html",
        {
            "plan_cards": plan_cards,
            "metrics": metrics,
            "pillars": pillars,
        },
    )


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
        Profile.objects.create(user=user, role=role)  # ðŸ‘ˆ se crea el perfil

        return redirect("login")

    return render(request, "signup.html")

# Postulante
def _build_postulante_dashboard_context(user):
    perfil = Profile.objects.filter(user=user).first()

    postulaciones_qs = (
        user.postulaciones.select_related("vacante").order_by("-fecha_postulacion")
    )

    total_postulaciones = postulaciones_qs.count()
    activas = postulaciones_qs.exclude(estado__in=["rechazado"]).count()

    estado_resumen = {code: 0 for code, _ in Postulacion.ESTADOS}
    for item in postulaciones_qs.values("estado").annotate(total=Count("id")):
        estado_resumen[item["estado"]] = item["total"]

    conversion_rate = 0
    if total_postulaciones:
        conversion_rate = round(
            (estado_resumen["aceptado"] / total_postulaciones) * 100, 1
        )
    aceptadas = estado_resumen["aceptado"]

    recent_postulaciones = list(postulaciones_qs[:3])

    skills_actuales = []
    if perfil and (perfil.habilidades_tecnicas or "").strip():
        skills_actuales = [
            skill.strip()
            for skill in perfil.habilidades_tecnicas.split(",")
            if skill.strip()
        ]

    skills_actuales_lower = {s.lower() for s in skills_actuales}

    all_skills = []
    for skills in SKILL_DICTIONARY.values():
        all_skills.extend(skills)

    faltantes_counter = Counter()
    for postulacion in postulaciones_qs:
        descripcion = (postulacion.vacante.descripcion or "").lower()
        for skill in all_skills:
            if re.search(rf"\b{re.escape(skill)}\b", descripcion, flags=re.I):
                if skill.lower() not in skills_actuales_lower:
                    faltantes_counter[skill] += 1

    skills_recomendadas = [skill for skill, _ in faltantes_counter.most_common(6)]

    estado_cards = [
        {
            "codigo": code,
            "label": label,
            "total": estado_resumen[code],
            "percent": round(
                (estado_resumen[code] / total_postulaciones) * 100, 1
            )
            if total_postulaciones
            else 0,
        }
        for code, label in Postulacion.ESTADOS
    ]

    metric_cards = [
        {
            "label": "Postulaciones totales",
            "value": total_postulaciones,
            "color": "text-gray-900",
        },
        {
            "label": "Postulaciones activas",
            "value": activas,
            "color": "text-gray-900",
        },
        {
            "label": "Aceptadas",
            "value": aceptadas,
            "color": "text-emerald-600",
        },
        {
            "label": "Tasa de exito",
            "value": conversion_rate,
            "suffix": "%",
            "color": "text-primary-600",
        },
    ]

    return {
        "perfil": perfil,
        "total_postulaciones": total_postulaciones,
        "activas": activas,
        "conversion_rate": conversion_rate,
        "aceptadas": aceptadas,
        "estado_cards": estado_cards,
        "recientes": recent_postulaciones,
        "skills_actuales": skills_actuales,
        "skills_recomendadas": skills_recomendadas,
        "metric_cards": metric_cards,
    }


@login_required
def postulante_dashboard(request):
    contexto = _build_postulante_dashboard_context(request.user)
    return render(request, "postulante/dashboard.html", contexto)

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

        # Chips (habilidades blandas y tÃ©cnicas)
        perfil.habilidades_blandas = request.POST.get("habilidades_blandas", "").strip()
        perfil.habilidades_tecnicas = request.POST.get("habilidades_tecnicas", "").strip()

        # Archivos
        if "foto" in request.FILES:
            perfil.foto = request.FILES["foto"]
        if "portada" in request.FILES:
            perfil.portada = request.FILES["portada"]
        if "cv" in request.FILES:
            perfil.cv = request.FILES["cv"]
            # Guardamos primero para asegurar el archivo en disco
            try:
                perfil.save()
                # Extraer texto del CV y generar perfil automÃ¡tico
                text = extract_text_from_pdf(perfil.cv.path)
                profile_data = build_profile_from_text(text)
                # Persistir habilidades tÃ©cnicas y rol sugerido
                perfil.habilidades_tecnicas = ", ".join(profile_data.get("skills", []))
                if not perfil.area_profesional:
                    perfil.area_profesional = profile_data.get("rol")
                perfil.save()
            except Exception as e:
                logging.getLogger(__name__).exception("Error extrayendo skills del CV")
                errores.append("No se pudo procesar el CV para extraer habilidades.")
    elif created and not perfil.habilidades_tecnicas:
        habilidades_tecnicas = []

        # Validaciones obligatorias
        if not perfil.cv:
            errores.append("Debe subir su currÃ­culum antes de continuar.")
        if not perfil.area_profesional or not perfil.nivel_educacion:
            errores.append("Debe completar su formaciÃ³n y Ã¡rea profesional.")
        if not perfil.pretension_renta:
            errores.append("Debe indicar su pretensiÃ³n de renta.")

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
    if not habilidades_tecnicas:
        text = ""
        if perfil.cv:
            try:
                text = extract_text_from_pdf(perfil.cv.path)
            except Exception:
                text = ""
        if text:
            profile_data = build_profile_from_text(text)
            perfil.habilidades_tecnicas = ", ".join(profile_data.get("skills", []))
            if not perfil.area_profesional:
                perfil.area_profesional = profile_data.get("rol")
            perfil.save()
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

    # Ãšltimas 3 vacantes abiertas con mÃ©tricas
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
                score = _calculate_match_score(
                    cv_skills=cv_skills,
                    job_description=v.descripcion or "",
                    skills_obligatorias=[],
                    skills_deseables=[],
                )
                if score is not None and float(score) >= 40.0:
                    aptos += 1
            except Exception:
                pass
        ultimas_vacantes.append({
            "obj": v,
            "postulaciones": total,
            "aptos": aptos,
        })

    # Skills mÃ¡s demandadas en las vacantes activas (diccionario)
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
                score = _calculate_match_score(
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

# PostulaciÃ³n a vacante
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
    return render(request, "postulante/mis_postulaciones.html", {"postulaciones": postulaciones})


# ConfiguraciÃ³n
@login_required
def configuracion_postulante(request):
    if request.method == "POST":
        # AquÃ­ podrÃ­as actualizar el email o contraseÃ±a
        # O redirigir a Django's PasswordChangeView
        pass
    return render(request, "postulante/configuracion.html")

 

@login_required
def reclutador_vacantes(request):
    vacantes = Vacante.objects.filter(reclutador=request.user)

    q = request.GET.get("q", "").strip()
    ubicacion = request.GET.get("ubicacion", "").strip()
    days = request.GET.get("days", "").strip()

    if q:
        vacantes = vacantes.filter(
            Q(titulo__icontains=q) | Q(descripcion__icontains=q)
        )
    if ubicacion:
        vacantes = vacantes.filter(ubicacion__icontains=ubicacion)
    if days:
        try:
            days_int = int(days)
            if days_int >= 0:
                vacantes = vacantes.filter(
                    fecha_publicacion__gte=timezone.now() - timedelta(days=days_int)
                )
        except ValueError:
            pass

    vacantes = vacantes.order_by("-fecha_publicacion")

    now = timezone.now()
    vacantes_info = []
    for vacante in vacantes:
        delta = now - vacante.fecha_publicacion
        days_since = max(delta.days, 0)
        vacantes_info.append(
            {
                "obj": vacante,
                "days_since": days_since,
            }
        )

    context = {
        "vacantes": vacantes_info,
        "filters": {
            "q": q,
            "ubicacion": ubicacion,
            "days": days,
        },
    }
    return render(request, "reclutador/vacantes.html", context)


@login_required
def reclutador_postulantes(request):
    postulaciones = (
        Postulacion.objects
        .select_related("postulante", "postulante__profile", "vacante")
        .filter(vacante__reclutador=request.user)
        .order_by("-fecha_postulacion")
    )

    candidatos = {}
    for post in postulaciones:
        user = post.postulante
        perfil = getattr(user, "profile", None)
        data = candidatos.get(user.id)

        if not data:
            skills = []
            if perfil and (perfil.habilidades_tecnicas or "").strip():
                skills = [s.strip() for s in perfil.habilidades_tecnicas.split(",") if s.strip()][:8]

            data = {
                "user": user,
                "perfil": perfil,
                "count": 0,
                "last_date": None,
                "last_vacante": None,
                "skills": skills,
            }
            candidatos[user.id] = data

        data["count"] += 1
        if data["last_date"] is None or post.fecha_postulacion > data["last_date"]:
            data["last_date"] = post.fecha_postulacion
            data["last_vacante"] = post.vacante

    fallback_date = timezone.now()
    candidatos_list = sorted(
        candidatos.values(),
        key=lambda c: c["last_date"] or fallback_date,
        reverse=True,
    )

    return render(request, "reclutador/postulantes.html", {
        "candidatos": candidatos_list,
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
            
            # RedirecciÃ³n segÃºn rol
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
    vacantes = Vacante.objects.filter(activa=True)

    q = request.GET.get("q", "").strip()
    ubicacion = request.GET.get("ubicacion", "").strip()
    days = request.GET.get("days", "").strip()

    if q:
        vacantes = vacantes.filter(
            Q(titulo__icontains=q) | Q(descripcion__icontains=q)
        )
    if ubicacion:
        vacantes = vacantes.filter(ubicacion__icontains=ubicacion)
    if days:
        try:
            days_int = int(days)
            if days_int >= 0:
                vacantes = vacantes.filter(
                    fecha_publicacion__gte=timezone.now() - timedelta(days=days_int)
                )
        except ValueError:
            pass

    vacantes = vacantes.order_by("-fecha_publicacion")

    now = timezone.now()
    vacantes_info = []
    for vacante in vacantes:
        delta = now - vacante.fecha_publicacion
        days_since = max(delta.days, 0)
        vacantes_info.append(
            {
                "obj": vacante,
                "days_since": days_since,
            }
        )

    context = {
        "vacantes": vacantes_info,
        "filters": {
            "q": q,
            "ubicacion": ubicacion,
            "days": days,
        },
    }
    return render(request, "postulante/listar_vacantes.html", context)

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
        messages.success(request, "Tu postulaciÃ³n ha sido enviada con Ã©xito.")

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
                score = _calculate_match_score(
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

            # Skills que coinciden (segÃºn diccionario y descripciÃ³n)
            try:
                desc = (vacante.descripcion or "")
                found_job = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", desc, re.I)]
                # Detectar skills en el texto del CV (cadena completa), no solo por split
                cv_text = perfil_post.habilidades_tecnicas or ""
                found_cv = [s for s in skills_flat if re.search(rf"\b{re.escape(s)}\b", cv_text, re.I)]
                # IntersecciÃ³n
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

        p.etapa_display = p.get_etapa_proceso_display()

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
    # Verificar si ya existe una postulaciÃ³n del usuario
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
    skills_list = []
    if (perfil.habilidades_tecnicas or "").strip():
        skills_list = [s.strip() for s in perfil.habilidades_tecnicas.split(",") if s.strip()]
    return render(request, "reclutador/perfil_postulante.html", {"perfil": perfil, "skills_list": skills_list})

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
    postulacion = get_object_or_404(
        Postulacion,
        id=postulacion_id,
        vacante__id=vacante_id,
        vacante__reclutador=request.user,
    )

    if request.method == "POST":
        nueva_etapa = request.POST.get("etapa_proceso", "").strip()
        etapas_validas = {code for code, _ in Postulacion.ETAPAS_PROCESO}
        if nueva_etapa in etapas_validas:
            postulacion.etapa_proceso = nueva_etapa
            postulacion.save(update_fields=["etapa_proceso"])
            messages.success(request, "Etapa del proceso actualizada.")
        return redirect("detalle_postulante", vacante_id=vacante_id, postulacion_id=postulacion.id)

    if postulacion.estado == "enviado":
        postulacion.estado = "visto"
        postulacion.fecha_visto = timezone.now()
        postulacion.save()

    perfil = getattr(postulacion.postulante, "profile", None)
    respuestas = postulacion.respuestas.select_related("pregunta").all() if hasattr(postulacion, "respuestas") else []

    match_score = None
    match_label = None
    top_skills = []
    if perfil and (perfil.habilidades_tecnicas or "").strip():
        cv_skills = [s.strip() for s in perfil.habilidades_tecnicas.split(",") if s.strip()]
        try:
            match_score = _calculate_match_score(
                cv_skills=cv_skills,
                job_description=postulacion.vacante.descripcion or "",
                skills_obligatorias=[],
                skills_deseables=[],
            )
        except Exception:
            match_score = None
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

    return render(
        request,
        "reclutador/detalle_postulante.html",
        {
            "postulacion": postulacion,
            "perfil": perfil,
            "respuestas": respuestas,
            "match_score": match_score,
            "match_label": match_label,
            "top_skills": top_skills,
            "etapas_proceso": Postulacion.ETAPAS_PROCESO,
        },
    )
