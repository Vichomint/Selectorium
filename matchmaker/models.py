from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class Job(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    skills_obligatorias = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    skills_deseables = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)  # ✅ NUEVO CAMPO CORRECTO

    def __str__(self):
        return self.titulo


class Candidate(models.Model):
    nombre = models.CharField(max_length=255, blank=True)
    cv_file = models.FileField(upload_to="cvs/")
    cv_text = models.TextField(blank=True)
    fecha_carga = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre or f"Candidato {self.id}"



class CandidateProfile(models.Model):
    candidate = models.OneToOneField("matchmaker.Candidate", on_delete=models.CASCADE, related_name="profile")
    rol = models.CharField(max_length=255, blank=True)
    skills = models.JSONField(default=list, blank=True)
    idiomas = models.JSONField(default=list, blank=True)
    experiencia = models.CharField(max_length=100, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)


class MatchResult(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    score = models.FloatField()
    explicacion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.candidate} → {self.job} ({self.score}%)"
