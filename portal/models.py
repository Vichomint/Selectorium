from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('postulante', 'Postulante'),
        ('reclutador', 'Reclutador'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='postulante')

    fecha_nacimiento = models.DateField(null=True, blank=True)
    estudios = models.TextField(blank=True, null=True)
    experiencia = models.TextField(blank=True, null=True)
    cv = models.FileField(upload_to="cvs/", blank=True, null=True)
    foto = models.ImageField(upload_to="fotos_postulantes/", blank=True, null=True)

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
    postulante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="postulaciones")
    vacante = models.ForeignKey(Vacante, on_delete=models.CASCADE, related_name="postulaciones")
    fecha_postulacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=(("pendiente", "Pendiente"), ("en_revision", "En revisión"), ("rechazado", "Rechazado"), ("aceptado", "Aceptado")),
        default="pendiente"
    )

    def __str__(self):
        return f"{self.postulante.username} → {self.vacante.titulo}"
    
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
