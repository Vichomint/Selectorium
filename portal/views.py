from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Profile , Vacante, Postulacion,Pregunta,Respuesta
from django.utils import timezone
from django.contrib import messages

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

    return render(request, "reclutador/administrar_vacante.html", {
        "vacante": vacante,
        "postulaciones": postulaciones,
    })



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
def mis_postulaciones(request):
    postulaciones = Postulacion.objects.filter(postulante=request.user).select_related("vacante")
    return render(request, "postulante/mis_postulaciones.html", {"postulaciones": postulaciones})

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

    return render(request, "reclutador/detalle_postulante.html", {
        "postulacion": postulacion,
        "perfil": perfil,
        "respuestas": respuestas,
    })