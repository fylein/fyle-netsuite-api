# Generated by Django
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('internal', '0003_auto_generated_sql')]

    operations = [
        migrations.RunSQL(
            sql="""
                INSERT INTO django_q_schedule (func, args, schedule_type, minutes, next_run, repeats, cluster)
                    SELECT 'apps.internal.tasks.re_export_stuck_exports', NULL, 'I', 60, NOW() + interval '1 minute', -1, 'import'
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM django_q_schedule
                        WHERE func = 'apps.internal.tasks.re_export_stuck_exports'
                        AND args IS NULL
                    );
            """,
            reverse_sql="""
                DELETE FROM django_q_schedule
                WHERE func = 'apps.internal.tasks.re_export_stuck_exports'
                AND args IS NULL;
            """
        )
    ]
