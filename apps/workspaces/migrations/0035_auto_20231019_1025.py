# Generated by Django 3.1.14 on 2023-10-19 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0034_auto_20231012_0750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuration',
            name='reimbursable_expenses_object',
            field=models.CharField(choices=[('EXPENSE REPORT', 'EXPENSE REPORT'), ('JOURNAL ENTRY', 'JOURNAL ENTRY'), ('BILL', 'BILL')], help_text='Reimbursable Expenses type', max_length=50, null=True),
        ),
    ]
