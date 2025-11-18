from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0010_remove_postulacion_fecha_visto"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="portada",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="portadas_postulantes/",
            ),
        ),
    ]
