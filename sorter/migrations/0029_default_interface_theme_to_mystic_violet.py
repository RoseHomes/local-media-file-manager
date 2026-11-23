from django.db import migrations, models


def migrate_existing_theme_names(apps, schema_editor):
    InterfaceTextSetting = apps.get_model("sorter", "InterfaceTextSetting")
    InterfaceTextSetting.objects.filter(theme_name__in=["warm-sand", "cocoa-brown"]).update(
        theme_name="mystic-violet"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("sorter", "0028_interfacetextsetting_menu_config_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_existing_theme_names, migrations.RunPython.noop),
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
                default="mystic-violet",
                help_text="Choose the global interface theme.",
                max_length=40,
            ),
        ),
    ]
