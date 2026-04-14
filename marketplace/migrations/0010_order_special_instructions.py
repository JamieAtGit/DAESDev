from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0009_customuser_phone_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='special_instructions',
            field=models.TextField(blank=True),
        ),
    ]
