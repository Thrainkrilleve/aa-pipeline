from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("pipeline", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checkfilter",
            name="content_type",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pipeline_checkfilter_set",
                to="contenttypes.contenttype",
            ),
        ),
    ]
