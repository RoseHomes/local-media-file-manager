from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sorter', '0025_alter_interfacetextsetting_theme_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='use_folder_name_as_filename',
            field=models.BooleanField(
                default=False,
                help_text="When enabled, Fanart File uses this game's folder name as the filename prefix instead of a character name.",
            ),
        ),
    ]
