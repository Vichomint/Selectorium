from django.db import models
from django.utils import timezone

class Job(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField(default=timezone.now)

class Candidate(models.Model):
    nombre = models.CharField(max_length=255)
    cv_text = models.TextField()
    fecha_carga = models.DateTimeField(default=timezone.now)

class MatchResult(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    score = models.FloatField()
    explicacion = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(default=timezone.now)
