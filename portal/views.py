from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

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

# SIGNUP
def signup_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password1"]
        User.objects.create_user(username=username, email=email, password=password)
        return redirect("login")
    return render(request, "signup.html")

# Postulante
@login_required
def postulante_dashboard(request):
    return render(request, "postulante/dashboard.html")

@login_required
def perfil_postulante(request):
    return render(request, "postulante/perfil.html")

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

