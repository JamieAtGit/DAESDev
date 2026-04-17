from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0010_order_special_instructions'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_address', models.TextField()),
                ('special_instructions', models.TextField(blank=True)),
                ('recurrence_day', models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday')], max_length=20)),
                ('delivery_day', models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday')], max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('next_order_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_orders', to='marketplace.customuser')),
            ],
        ),
        migrations.CreateModel(
            name='RecurringOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='marketplace.product')),
                ('recurring_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='marketplace.recurringorder')),
            ],
        ),
    ]
