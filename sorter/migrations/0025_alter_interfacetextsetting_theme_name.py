from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sorter", "0024_update_number_action_choices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="interfacetextsetting",
            name="theme_name",
            field=models.CharField(
                choices=[
                    ("cocoa-brown", "Cocoa Brown"),
                    ("mystic-violet", "Mystic Violet"),
                    ("cotton-candy-cloud", "Cotton Candy Cloud"),
                    ("lunar-cloud", "Lunar Cloud"),
                    ("electric-violet", "Electric Violet"),
                ],
                default="cocoa-brown",
                help_text="Choose the global interface theme.",
                max_length=40,
            ),
        ),
    ]
