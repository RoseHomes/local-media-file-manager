from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sorter", "0026_game_use_folder_name_as_filename"),
    ]

    operations = [
        migrations.AddField(
            model_name="character",
            name="description",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]