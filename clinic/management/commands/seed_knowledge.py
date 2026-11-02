from django.core.management.base import BaseCommand

from clinic.knowledge_data import sync_knowledge


class Command(BaseCommand):
    help = "导入或更新穴位主治与常见病例治疗方案（可重复执行）"

    def handle(self, *args, **options):
        updated_points, created, updated, missing = sync_knowledge()
        if missing:
            self.stdout.write(
                self.style.WARNING(f"以下穴位未在库中，已跳过：{'、'.join(missing)}")
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"知识库同步完成：更新 {updated_points} 个穴位主治，"
                f"新建 {created} 个病例方案，更新 {updated} 个病例方案"
            )
        )
