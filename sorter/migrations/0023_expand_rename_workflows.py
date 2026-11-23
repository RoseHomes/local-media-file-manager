from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sorter", "0022_webptomp4setting"),
    ]

    operations = [
        migrations.AddField(
            model_name="renamesetting",
            name="added_text",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="delimiter_occurrence",
            field=models.CharField(choices=[("first", "First delimiter"), ("last", "Last delimiter")], default="first", max_length=20),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="include_delimiter",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="increment",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="match_occurrence",
            field=models.CharField(choices=[("all", "All matches"), ("first", "First match"), ("last", "Last match")], default="all", max_length=20),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="match_scope",
            field=models.CharField(choices=[("stem", "Filename only"), ("full_name", "Include extension")], default="stem", max_length=20),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="number_action",
            field=models.CharField(choices=[("swap_numbers", "Swap numbers"), ("add_prefix_sequence", "Add sequence prefix"), ("add_suffix_sequence", "Add sequence suffix")], default="swap_numbers", max_length=30),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="number_separator",
            field=models.CharField(blank=True, default="_", max_length=10),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="reset_per_folder",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="start_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="text_action",
            field=models.CharField(choices=[("replace", "Replace text"), ("add_prefix", "Add prefix"), ("add_suffix", "Add suffix"), ("remove", "Remove text")], default="replace", max_length=20),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="trim_action",
            field=models.CharField(choices=[("keep_before", "Keep text before delimiter"), ("keep_after", "Keep text after delimiter"), ("remove_before", "Remove text before delimiter"), ("remove_after", "Remove text after delimiter")], default="keep_before", max_length=20),
        ),
        migrations.AddField(
            model_name="renamesetting",
            name="trim_delimiter",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AlterField(
            model_name="renamesetting",
            name="workflow",
            field=models.CharField(choices=[("text_transform", "Text transform"), ("trim_delimiter", "Trim by delimiter"), ("numbering", "Numbering")], default="text_transform", max_length=20),
        ),
    ]
