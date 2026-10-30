from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from clinic import services
from clinic.models import (
    Acupoint,
    Appointment,
    DoctorProfile,
    OperationLog,
    PlanAcupoint,
    Role,
    Schedule,
    TreatmentPlan,
    TreatmentRecord,
    TreatmentRoom,
    User,
)

ACUPOINTS = [
    ("百会", "GV20", "督脉", "前发际正中直上5寸"),
    ("风池", "GB20", "足少阳胆经", "枕骨之下，胸锁乳突肌与斜方肌上端之间凹陷中"),
    ("大椎", "GV14", "督脉", "第7颈椎棘突下凹陷中"),
    ("肩井", "GB21", "足少阳胆经", "大椎与肩峰端连线的中点"),
    ("曲池", "LI11", "手阳明大肠经", "屈肘成直角，肘横纹外端与肱骨外上髁连线中点"),
    ("合谷", "LI4", "手阳明大肠经", "手背第1、2掌骨间，第2掌骨桡侧中点处"),
    ("外关", "TE5", "手少阳三焦经", "腕背横纹上2寸，尺骨与桡骨之间"),
    ("内关", "PC6", "手厥阴心包经", "腕横纹上2寸，掌长肌腱与桡侧腕屈肌腱之间"),
    ("神门", "HT7", "手少阴心经", "腕横纹尺侧端，尺侧腕屈肌腱桡侧凹陷处"),
    ("中脘", "CV12", "任脉", "脐上4寸，前正中线上"),
    ("天枢", "ST25", "足阳明胃经", "脐中旁开2寸"),
    ("气海", "CV6", "任脉", "脐下1.5寸，前正中线上"),
    ("关元", "CV4", "任脉", "脐下3寸，前正中线上"),
    ("足三里", "ST36", "足阳明胃经", "犊鼻下3寸，胫骨前嵴外一横指"),
    ("三阴交", "SP6", "足太阴脾经", "内踝尖上3寸，胫骨内侧缘后际"),
    ("阴陵泉", "SP9", "足太阴脾经", "胫骨内侧髁下缘与胫骨内侧缘之间凹陷中"),
    ("阳陵泉", "GB34", "足少阳胆经", "腓骨小头前下方凹陷中"),
    ("血海", "SP10", "足太阴脾经", "髌底内侧端上2寸，股内侧肌隆起处"),
    ("梁丘", "ST34", "足阳明胃经", "髌底外侧端上2寸"),
    ("委中", "BL40", "足太阳膀胱经", "腘横纹中点"),
    ("承山", "BL57", "足太阳膀胱经", "腓肠肌两肌腹之间凹陷顶端"),
    ("昆仑", "BL60", "足太阳膀胱经", "外踝尖与跟腱之间凹陷中"),
    ("太冲", "LR3", "足厥阴肝经", "足背第1、2跖骨间，跖骨结合部前方凹陷中"),
    ("太溪", "KI3", "足少阴肾经", "内踝尖与跟腱之间凹陷中"),
    ("肾俞", "BL23", "足太阳膀胱经", "第2腰椎棘突下，旁开1.5寸"),
    ("肝俞", "BL18", "足太阳膀胱经", "第9胸椎棘突下，旁开1.5寸"),
    ("脾俞", "BL20", "足太阳膀胱经", "第11胸椎棘突下，旁开1.5寸"),
    ("心俞", "BL15", "足太阳膀胱经", "第5胸椎棘突下，旁开1.5寸"),
    ("印堂", "EX-HN3", "经外奇穴", "两眉头连线中点"),
    ("安眠", "EX-HN22", "经外奇穴", "翳风与风池连线的中点"),
    ("太阳", "EX-HN5", "经外奇穴", "眉梢与目外眦之间，向后约一横指凹陷处"),
    ("四神聪", "EX-HN1", "经外奇穴", "百会前后左右各1寸，共4穴"),
]

DOCTORS = [
    ("doctor1", "赵明", "M", "13800000101", "针灸科", "主任医师", "颈肩腰腿痛、中风后遗症", "room1"),
    ("doctor2", "孙丽", "F", "13800000102", "针灸科", "副主任医师", "失眠调理、女性内分泌", "room2"),
    ("doctor3", "周涛", "M", "13800000103", "针灸科", "主治医师", "脾胃调理、亚健康状态", "room1"),
]

PATIENTS = [
    ("patient1", "张伟", "M", "13800000201", "颈肩酸痛，久坐后加重"),
    ("patient2", "李娜", "F", "13800000202", "入睡困难，易醒多梦"),
    ("patient3", "王芳", "F", "13800000203", "胃脘不适，食欲欠佳"),
    ("patient4", "陈晨", "M", "13800000204", "腰部酸胀，活动受限"),
    ("patient5", "刘洋", "M", "13800000205", "偏头痛反复发作"),
]

PLAN_MAIN = {
    "颈肩": ["风池", "肩井", "大椎", "合谷"],
    "失眠": ["百会", "四神聪", "神门", "内关"],
    "脾胃": ["中脘", "天枢", "足三里"],
    "腰痛": ["肾俞", "委中", "太溪"],
}
PLAN_ADJUNCT = {
    "颈肩": ["外关", "曲池"],
    "失眠": ["安眠", "三阴交"],
    "脾胃": ["阴陵泉", "气海"],
    "腰痛": ["血海", "昆仑"],
}


class Command(BaseCommand):
    help = "初始化演示数据：角色账号、穴位库、排班、预约、方案与治疗记录"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="清空现有业务数据后重新生成（谨慎使用）",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("正在清空现有业务数据..."))
            TreatmentRecord.all_objects.all().delete()
            TreatmentPlan.all_objects.all().delete()
            Acupoint.all_objects.all().delete()
            Schedule.objects.all().delete()
            Appointment.all_objects.all().delete()
            DoctorProfile.objects.all().delete()
            OperationLog.objects.all().delete()
            User.all_objects.all().delete()
            TreatmentRoom.all_objects.all().delete()

        if User.objects.filter(username="admin").exists():
            self.stdout.write(
                self.style.WARNING("演示数据已存在，如需重建请执行 seed_demo --reset")
            )
            return

        rooms = {
            "room1": TreatmentRoom.objects.create(
                name="针灸一诊室", location="门诊楼二层东侧", equipment="治疗床 4 张、电针仪 2 台、艾灸仪 1 台"
            ),
            "room2": TreatmentRoom.objects.create(
                name="针灸二诊室", location="门诊楼二层西侧", equipment="治疗床 3 张、电针仪 1 台、TDP 灯 2 台"
            ),
        }

        points = {}
        for name, code, meridian, location in ACUPOINTS:
            point, _ = Acupoint.objects.get_or_create(
                name=name,
                defaults={"code": code, "meridian": meridian, "location": location},
            )
            points[name] = point

        admin = User.objects.create_user(
            username="admin",
            password="demo12345",
            name="王敏",
            phone="13800000001",
            role=Role.ADMIN,
            is_staff=True,
        )
        sysadmin = User.objects.create_user(
            username="sysadmin",
            password="demo12345",
            name="系统管理员",
            phone="13800000002",
            role=Role.SYSADMIN,
            is_staff=True,
            is_superuser=True,
        )

        doctors = []
        for username, name, gender, phone, dept, title, specialty, room_key in DOCTORS:
            doctor = User.objects.create_user(
                username=username,
                password="demo12345",
                name=name,
                gender=gender,
                phone=phone,
                role=Role.DOCTOR,
            )
            DoctorProfile.objects.create(
                user=doctor,
                department=dept,
                title=title,
                specialty=specialty,
                room=rooms[room_key],
            )
            doctors.append(doctor)

        patients = []
        for username, name, gender, phone, complaint in PATIENTS:
            patient = User.objects.create_user(
                username=username,
                password="demo12345",
                name=name,
                gender=gender,
                phone=phone,
                role=Role.PATIENT,
            )
            patients.append((patient, complaint))

        today = timezone.localdate()
        schedules = {}
        for doctor_index, doctor in enumerate(doctors):
            for offset in range(10):
                day = today + timedelta(days=offset)
                if day.weekday() == 6:
                    continue
                for key, start, end, capacity in (
                    ("am", time(9, 0), time(10, 30), 4),
                    ("pm", time(14, 0), time(15, 30), 4),
                ):
                    schedule, _ = Schedule.objects.get_or_create(
                        doctor=doctor,
                        date=day,
                        start_time=start,
                        defaults={"end_time": end, "capacity": capacity},
                    )
                    schedules[(doctor_index, offset, key)] = schedule

        def make_appointment(patient, doctor, schedule, status, complaint):
            return Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                schedule=schedule,
                appoint_time=services.slot_datetime(schedule),
                status=status,
                chief_complaint=complaint,
            )

        def make_plan(appointment, key, syndrome, technique):
            plan = TreatmentPlan.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                doctor=appointment.doctor,
                syndrome=syndrome,
                technique=technique,
                course_cycle=14,
                frequency_per_week=3,
                notes="配合起居调护，注意保暖，避免过度劳累。",
            )
            for index, point_name in enumerate(PLAN_MAIN[key]):
                PlanAcupoint.objects.create(
                    plan=plan, acupoint=points[point_name], type=PlanAcupoint.Type.MAIN, order=index
                )
            for index, point_name in enumerate(PLAN_ADJUNCT[key]):
                PlanAcupoint.objects.create(
                    plan=plan, acupoint=points[point_name], type=PlanAcupoint.Type.ADJUNCT, order=index
                )
            return plan

        p1, c1 = patients[0]
        p2, c2 = patients[1]
        p3, c3 = patients[2]
        p4, c4 = patients[3]
        p5, c5 = patients[4]

        # 今日待排期
        make_appointment(p1, doctors[0], schedules[(0, 0, "am")], Appointment.Status.PENDING, c1)
        # 今日已排期，待接诊
        a2 = make_appointment(p2, doctors[1], schedules[(1, 0, "am")], Appointment.Status.SCHEDULED, c2)
        make_plan(a2, "失眠", "心脾两虚证", "提插捻转补法")
        # 明日已排期，已有待审核记录
        a3 = make_appointment(p3, doctors[2], schedules[(2, 1, "am")], Appointment.Status.SCHEDULED, c3)
        plan3 = make_plan(a3, "脾胃", "脾胃虚弱证", "平补平泻")
        TreatmentRecord.objects.create(
            plan=plan3,
            doctor=doctors[2],
            treat_time=timezone.now() - timedelta(hours=2),
            needling_duration=30,
            advice="规律饮食，忌生冷油腻。",
            status=TreatmentRecord.Status.REGISTERED,
        )
        # 已完成并归档的治疗记录
        a4 = make_appointment(p4, doctors[0], schedules[(0, 0, "pm")], Appointment.Status.COMPLETED, c4)
        plan4 = make_plan(a4, "腰痛", "肾气不足证", "捻转补法")
        TreatmentRecord.objects.create(
            plan=plan4,
            doctor=doctors[0],
            treat_time=timezone.now() - timedelta(hours=1),
            needling_duration=25,
            advice="注意腰部保暖，可配合八段锦锻炼。",
            status=TreatmentRecord.Status.CONFIRMED,
            audit_remark="记录完整，审核通过",
        )
        # 取消预约
        make_appointment(p5, doctors[0], schedules[(0, 0, "am")], Appointment.Status.CANCELLED, c5)
        # 历史完成单
        a6 = make_appointment(p2, doctors[1], schedules[(1, 1, "pm")], Appointment.Status.COMPLETED, c2)
        plan6 = make_plan(a6, "失眠", "心脾两虚证", "提插捻转补法")
        TreatmentRecord.objects.create(
            plan=plan6,
            doctor=doctors[1],
            treat_time=timezone.now() - timedelta(days=3),
            needling_duration=30,
            advice="睡前温水泡脚，减少浓茶咖啡摄入。",
            status=TreatmentRecord.Status.CONFIRMED,
        )

        OperationLog.objects.create(user=admin, action="系统初始化", detail="导入演示数据")
        OperationLog.objects.create(user=sysadmin, action="系统初始化", detail="创建演示账号与穴位库")

        self.stdout.write(self.style.SUCCESS("演示数据初始化完成"))
        self.stdout.write(
            "账号：patient1 / doctor1 / admin / sysadmin，统一密码 demo12345"
        )
