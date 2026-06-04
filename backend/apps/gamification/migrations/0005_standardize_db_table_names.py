from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gamification', '0004_remove_badge_badge_type_badge_category_badge_code_and_more'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='badge',
            table='gamification_badge',
        ),
        migrations.AlterModelTable(
            name='dailyquest',
            table='gamification_daily_quest',
        ),
        migrations.AlterModelTable(
            name='storeitem',
            table='gamification_store_item',
        ),
        migrations.AlterModelTable(
            name='userbadge',
            table='gamification_user_badge',
        ),
        migrations.AlterModelTable(
            name='userinventory',
            table='gamification_user_inventory',
        ),
        migrations.DeleteModel(
            name='UserStat',
        ),
    ]
