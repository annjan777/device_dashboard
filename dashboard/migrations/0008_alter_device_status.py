# Generated by Django 3.2.25 on 2025-06-28 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0007_auto_20250615_1216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='status',
            field=models.CharField(choices=[('online', 'Online'), ('idle', 'Idle'), ('offline', 'Offline')], default='offline', max_length=10),
        ),
    ]
