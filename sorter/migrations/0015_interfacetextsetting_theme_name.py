from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sorter', '0014_interfacetextsetting'),
    ]

    operations = [
        migrations.AddField(
            model_name='interfacetextsetting',
            name='theme_name',
            field=models.CharField(
                choices=[
                    ('warm-sand', 'Warm Sand'),
                    ('mystic-violet', 'Mystic Violet'),
                    ('cotton-candy-cloud', 'Cotton Candy Cloud'),
                ],
                default='warm-sand',
                help_text='Choose the global interface theme.',
                max_length=40,
            ),
        ),
    ]
