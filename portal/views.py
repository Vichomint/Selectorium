from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Profile , Vacante, Postulacion,Pregunta,Respuesta

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
    # Aseguramos que exista el profile
    perfil, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        # Campos simples
        fecha = request.POST.get("fecha_nacimiento") or None
        estudios = request.POST.get("estudios", "").strip()
        experiencia = request.POST.get("experiencia", "").strip()

        perfil.fecha_nacimiento = fecha
        perfil.estudios = estudios
        perfil.experiencia = experiencia

        # Archivos: CV y foto
        if request.FILES.get("cv"):
            perfil.cv = request.FILES["cv"]
        if request.FILES.get("foto"):
            perfil.foto = request.FILES["foto"]

        perfil.save()
        # Redirigir para evitar reenvío al refrescar y para que se vea lo guardado
        return redirect("perfil_postulante")

    # GET: render con datos actuales (si los hay)
    return render(request, "postulante/perfil_postulante.html", {"perfil": perfil})

# Reclutador
@login_required
def reclutador_dashboard(request):
    return render(request, "reclutador/dashboard.html")

@login_required
def reclutador_estadisticas(request):
    return render(request, "reclutador/estadisticas.html")

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
    return render(request, "postulante/mis_postulaciones.html")

# Mi Perfil
@login_required
def perfil_postulante(request):
    if request.method == "POST":
        # Aquí podrías guardar la información del perfil
        # ej: fecha_nacimiento, estudios, experiencia, cv
        pass
    return render(request, "postulante/perfil_postulante.html")

# Configuración
@login_required
def configuracion_postulante(request):
    if request.method == "POST":
        # Aquí podrías actualizar el email o contraseña
        # O redirigir a Django's PasswordChangeView
        pass
    return render(request, "postulante/configuracion.html")

@login_required
def reclutador_dashboard(request):
    return render(request, "reclutador/dashboard.html")

@login_required
def reclutador_vacantes(request):
    vacantes = Vacante.objects.filter(reclutador=request.user).order_by("-fecha_publicacion")
    return render(request, "reclutador/vacantes.html", {"vacantes": vacantes})


@login_required
def reclutador_postulantes(request):
    return render(request, "reclutador/postulantes.html")

@login_required
def reclutador_estadisticas(request):
    return render(request, "reclutador/estadisticas.html")

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
    vacante = Vacante.objects.get(id=vacante_id, reclutador=request.user)
    postulaciones = Postulacion.objects.filter(vacante=vacante).select_related("postulante").prefetch_related("respuestas__pregunta")

    return render(request, "reclutador/administrar_vacante.html", {
        "vacante": vacante,
        "postulaciones": postulaciones,
    })



@login_required
def detalle_vacante(request, vacante_id):
    vacante = Vacante.objects.get(id=vacante_id)
    preguntas = vacante.preguntas.all()

    if request.method == "POST":
        postulacion = Postulacion.objects.create(postulante=request.user, vacante=vacante)
        for p in preguntas:
            respuesta = request.POST.get(f"respuesta_{p.id}")
            Respuesta.objects.create(postulacion=postulacion, pregunta=p, texto=respuesta)
        messages.success(request, "Tu postulación ha sido enviada con éxito.")
        return redirect("listar_vacantes")

    return render(request, "postulante/detalle_vacante.html", {"vacante": vacante, "preguntas": preguntas})

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
