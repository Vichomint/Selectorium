from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('postulante', 'Postulante'),
        ('reclutador', 'Reclutador'),
    )

    NIVEL_EDUCACION = (
        ('basica', 'Educación básica'),
        ('media', 'Educación media'),
        ('tecnico', 'Técnico'),
        ('profesional', 'Profesional'),
        ('postgrado', 'Postgrado / Magíster / Doctorado'),
    )

    DISPONIBILIDAD = (
        ('inmediata', 'Inmediata'),
        ('15_dias', 'Dentro de 15 días'),
        ('30_dias', 'Dentro de 30 días'),
        ('otros', 'Otros'),
    )

    TIPO_JORNADA = (
        ('completa', 'Jornada completa'),
        ('media', 'Media jornada'),
        ('por_proyecto', 'Por proyecto / freelance'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='postulante')

    # Datos personales
    fecha_nacimiento = models.DateField(null=True, blank=True)
    foto = models.ImageField(upload_to="fotos_postulantes/", blank=True, null=True)
    portada = models.ImageField(upload_to="portadas_postulantes/", blank=True, null=True)
    cv = models.FileField(upload_to="cvs/", blank=True, null=True)

    # Perfil profesional
    nivel_educacion = models.CharField(max_length=20, choices=NIVEL_EDUCACION, blank=True, null=True)
    area_profesional = models.CharField(max_length=255, blank=True, null=True)
    anios_experiencia = models.PositiveIntegerField(blank=True, null=True)
    tipo_jornada = models.CharField(max_length=20, choices=TIPO_JORNADA, blank=True, null=True)
    pretension_renta = models.CharField(max_length=100, blank=True, null=True)
    disponibilidad = models.CharField(max_length=20, choices=DISPONIBILIDAD, blank=True, null=True)
    movilidad = models.BooleanField(default=False)
    habilidades_blandas = models.TextField(blank=True, null=True)
    habilidades_tecnicas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Vacante(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    ubicacion = models.CharField(max_length=200, blank=True, null=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    # Relación con el reclutador que la creó
    reclutador = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vacantes")

    def __str__(self):
        return f"{self.titulo} - {self.reclutador.username}"

class Postulacion(models.Model):
    ESTADOS = (
        ("enviado", "Enviado"),
        ("visto", "Visto"),
        ("aceptado", "Aceptado"),
        ("rechazado", "Rechazado"),
    )

    ETAPAS_PROCESO = (
        ("sin_avance", "Sin avance"),
        ("descartado", "Descartado"),
        ("entrevista_rrhh", "Entrevista con RRHH"),
        ("entrevista_area", "Entrevista con jefe de area"),
        ("oferta", "Oferta extendida"),
        ("contratado", "Contratado"),
    )

    postulante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="postulaciones")
    vacante = models.ForeignKey(Vacante, on_delete=models.CASCADE, related_name="postulaciones")
    fecha_postulacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="enviado")
    etapa_proceso = models.CharField(max_length=30, choices=ETAPAS_PROCESO, default="sin_avance")

    def __str__(self):
        return f"{self.postulante.username} → {self.vacante.titulo} ({self.estado})"

    
class Pregunta(models.Model):
    vacante = models.ForeignKey("Vacante", on_delete=models.CASCADE, related_name="preguntas")
    texto = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.vacante.titulo} - {self.texto}"


class Respuesta(models.Model):
    postulacion = models.ForeignKey("Postulacion", on_delete=models.CASCADE, related_name="respuestas")
    pregunta = models.ForeignKey("Pregunta", on_delete=models.CASCADE)
    texto = models.TextField()

    def __str__(self):
        return f"{self.postulacion.postulante.username} → {self.pregunta.texto}"
