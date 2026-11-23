from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sorter", "0030_filemanageoperationjob_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="FixJpgSetting",
        ),
    ]
