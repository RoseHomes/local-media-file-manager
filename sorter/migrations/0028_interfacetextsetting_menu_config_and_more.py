from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sorter', '0027_character_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='interfacetextsetting',
            name='menu_config',
            field=models.JSONField(blank=True, default=list, help_text='Custom order and grouping for the sidebar navigation.'),
        ),
        migrations.AlterField(
            model_name='interfacetextsetting',
            name='language_mode',
            field=models.CharField(choices=[('en', 'English'), ('th', 'ไทย'), ('mixed', 'English title + Thai description')], default='en', help_text='Choose how menus, page titles, and page descriptions are displayed.', max_length=20),
        ),
    ]
