from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("redirect/", views.role_redirect_view, name="role_redirect"),
    

    # Postulante
    path("postulante/dashboard/", views.postulante_dashboard, name="postulante_dashboard"),
    path("postulante/mis-postulaciones/", views.mis_postulaciones, name="mis_postulaciones"),
    path("postulante/perfil/", views.perfil_postulante, name="perfil_postulante"),
    path("postulante/configuracion/", views.configuracion_postulante, name="configuracion_postulante"),
    path("postulante/vacantes/", views.listar_vacantes, name="listar_vacantes"),
    path("postulante/vacantes/postular/<int:vacante_id>/", views.postular_vacante, name="postular_vacante"),
    path("postulante/vacantes/<int:vacante_id>/", views.detalle_vacante, name="detalle_vacante"),
    path("postulante/perfil/borrar-foto/", views.perfil_borrar_foto, name="perfil_borrar_foto"),


    # Reclutador
    path("reclutador/dashboard/", views.reclutador_dashboard),
    path("reclutador/dashboard/", views.reclutador_dashboard, name="reclutador_dashboard"),
    path("reclutador/postulantes/", views.reclutador_postulantes, name="reclutador_postulantes"),
    path("reclutador/estadisticas/", views.reclutador_estadisticas, name="reclutador_estadisticas"),
    path("reclutador/configuracion/", views.reclutador_configuracion, name="reclutador_configuracion"),
    path("", views.role_redirect_view, name="home"),
    path("reclutador/vacantes/", views.reclutador_vacantes, name="reclutador_vacantes"),
    path("reclutador/vacantes/crear/", views.crear_vacante, name="crear_vacante"),
    path("reclutador/vacantes/<int:vacante_id>/", views.administrar_vacante, name="administrar_vacante"),
    path("reclutador/postulante/<int:postulante_id>/", views.perfil_postulante_detalle, name="perfil_postulante_detalle"),
    path(
    "reclutador/vacantes/<int:vacante_id>/postulante/<int:postulacion_id>/",
    views.detalle_postulante,
    name="detalle_postulante",
),
    

]
