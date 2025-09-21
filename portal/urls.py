from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),

    # Postulante
    # Postulante
    path("postulante/dashboard/", views.postulante_dashboard, name="postulante_dashboard"),
    path("postulante/mis-postulaciones/", views.mis_postulaciones, name="mis_postulaciones"),
    path("postulante/perfil/", views.perfil_postulante, name="perfil_postulante"),
    path("postulante/configuracion/", views.configuracion_postulante, name="configuracion_postulante"),

    # Reclutador
    path("reclutador/dashboard/", views.reclutador_dashboard)

]
