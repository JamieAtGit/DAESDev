from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0011_recurringorder'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='low_stock_threshold',
            field=models.PositiveIntegerField(default=10),
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField()),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='marketplace.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='marketplace.product')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='review',
            unique_together={('customer', 'product')},
        ),
    ]
