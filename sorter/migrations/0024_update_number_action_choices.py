from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sorter", "0023_expand_rename_workflows"),
    ]

    operations = [
        migrations.AlterField(
            model_name="renamesetting",
            name="number_action",
            field=models.CharField(choices=[("swap_numbers", "Swap numbers"), ("add_prefix_sequence", "Add sequence prefix"), ("add_suffix_sequence", "Add sequence suffix"), ("replace_with_sequence", "Replace with sequence")], default="swap_numbers", max_length=30),
        ),
    ]
