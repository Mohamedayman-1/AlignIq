# Generated by Django 5.2.1 on 2025-06-21 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project_excel_comparison', '0009_database_comparison'),
    ]

    operations = [
        migrations.AddField(
            model_name='comparison',
            name='range1',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='comparison',
            name='range2',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
