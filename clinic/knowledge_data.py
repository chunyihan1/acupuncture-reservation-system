"""可复用的针灸知识数据：穴位主治与常见病例治疗方案。

内容用于课程项目演示与临床思路参考，实际诊疗须由执业医师辨证施治。
"""

#: 穴位名称 -> 主治病症
ACUPOINT_INDICATIONS = {
    "百会": "头痛、眩晕、失眠、健忘、中风失语、脱肛、子宫脱垂。",
    "风池": "头痛、眩晕、颈项强痛、目赤肿痛、鼻塞、感冒、失眠。",
    "大椎": "颈项强痛、肩背痛、感冒发热、咳嗽、癫痫。",
    "肩井": "肩背疼痛、颈项强痛、上肢不遂、乳痈。",
    "曲池": "肘臂疼痛、上肢不遂、发热、咽喉肿痛、高血压、皮肤瘙痒。",
    "合谷": "头痛、牙痛、鼻塞、面瘫等头面五官疾患，上肢疼痛，发热，痛经（孕妇慎用）。",
    "外关": "头痛、耳鸣耳聋、胁肋疼痛、上肢痿痹、感冒。",
    "内关": "心悸、胸闷、胃痛、呕吐、失眠、晕车。",
    "神门": "失眠、健忘、心悸、焦虑、痴呆。",
    "中脘": "胃痛、腹胀、呕吐、食欲不振、脾胃虚弱。",
    "天枢": "腹泻、便秘、腹胀、痛经、月经不调。",
    "气海": "气虚乏力、腹胀、腹痛、月经不调、遗尿。",
    "关元": "腹痛、腹泻、月经不调、痛经、阳痿、遗尿、虚劳。",
    "足三里": "胃痛、腹胀、消化不良、呕吐、下肢痿痹，亦为体虚保健要穴。",
    "三阴交": "月经不调、痛经、失眠、脾胃虚弱、泌尿系统疾患（孕妇慎用）。",
    "阴陵泉": "腹胀、腹泻、水肿、小便不利、膝痛。",
    "阳陵泉": "胁肋疼痛、膝关节疼痛、下肢痿痹、胆囊疾患。",
    "血海": "月经不调、痛经、湿疹、皮肤瘙痒、膝痛。",
    "梁丘": "胃痛、膝痛、下肢不遂。",
    "委中": "腰背痛、下肢痿痹、腘窝疼痛、中暑。",
    "承山": "小腿疼痛、腰腿痛、痔疾、便秘。",
    "昆仑": "头痛、项强、腰骶痛、足跟痛、踝关节疼痛。",
    "太冲": "头痛、眩晕、月经不调、痛经、胁痛、情志不畅。",
    "太溪": "腰膝酸软、耳鸣、失眠、咽干、月经不调。",
    "肾俞": "腰痛、腰膝酸软、耳鸣、遗尿、月经不调。",
    "肝俞": "胁痛、目疾、眩晕、情志不畅。",
    "脾俞": "腹胀、腹泻、食欲不振、倦怠乏力。",
    "心俞": "心悸、失眠、健忘、胸闷。",
    "印堂": "头痛、失眠、鼻塞、眉棱骨痛。",
    "安眠": "失眠、多梦、头痛、眩晕。",
    "太阳": "偏头痛、目赤肿痛、面瘫。",
    "四神聪": "失眠、健忘、头痛、眩晕。",
}

#: 常见病例治疗方案
CASE_PROTOCOLS = [
    {
        "name": "颈椎病",
        "category": "骨伤科",
        "syndrome": "风寒阻络、气滞血瘀",
        "symptoms": "颈项僵硬酸痛、活动受限，可牵涉肩背或出现上肢麻木。",
        "main_points": ["风池", "大椎", "肩井", "合谷"],
        "adjunct_points": ["外关", "曲池", "太阳"],
        "technique": "平补平泻，得气后留针 20–30 分钟，可配合电针",
        "course_cycle": 14,
        "frequency_per_week": 3,
        "notes": "避免久坐低头，注意颈部保暖，配合颈椎功能锻炼。",
    },
    {
        "name": "肩周炎",
        "category": "骨伤科",
        "syndrome": "风寒湿痹、气血瘀阻",
        "symptoms": "肩部疼痛、夜间加重、抬举与外展受限，久则肩周肌肉萎缩。",
        "main_points": ["肩井", "曲池", "合谷"],
        "adjunct_points": ["外关", "大椎", "血海"],
        "technique": "平补平泻，留针时配合肩关节被动活动",
        "course_cycle": 21,
        "frequency_per_week": 3,
        "notes": "坚持爬墙、钟摆等功能锻炼，避免肩部受凉。",
    },
    {
        "name": "腰椎间盘突出症",
        "category": "骨伤科",
        "syndrome": "肾气不足、瘀血阻络",
        "symptoms": "腰部酸胀疼痛，活动受限，可沿下肢后侧放射并伴麻木。",
        "main_points": ["肾俞", "委中", "承山"],
        "adjunct_points": ["昆仑", "太溪", "血海"],
        "technique": "平补平泻，腰部穴位可加温针或电针",
        "course_cycle": 21,
        "frequency_per_week": 3,
        "notes": "急性期卧硬板床休息，缓解期加强腰背肌训练，避免弯腰负重。",
    },
    {
        "name": "膝骨关节炎",
        "category": "骨伤科",
        "syndrome": "肝肾亏虚、寒湿痹阻",
        "symptoms": "膝关节疼痛、晨起僵硬、上下楼加重，局部可有肿胀。",
        "main_points": ["阳陵泉", "阴陵泉", "血海", "梁丘"],
        "adjunct_points": ["足三里", "太溪", "昆仑"],
        "technique": "平补平泻，可配合温针灸",
        "course_cycle": 14,
        "frequency_per_week": 3,
        "notes": "控制体重，减少爬坡与深蹲，注意膝部保暖。",
    },
    {
        "name": "面瘫（周围性面神经麻痹）",
        "category": "神经科",
        "syndrome": "风邪入中、气血不足",
        "symptoms": "一侧面部肌肉弛缓，口角歪斜、闭目不全、额纹消失。",
        "main_points": ["合谷", "风池", "太阳", "印堂"],
        "adjunct_points": ["太冲", "外关"],
        "technique": "初期浅刺轻刺激，恢复期平补平泻",
        "course_cycle": 28,
        "frequency_per_week": 3,
        "notes": "避免面部直吹冷风，配合表情肌训练，注意眼部保护。",
    },
    {
        "name": "失眠",
        "category": "内科",
        "syndrome": "心脾两虚、肝郁化火",
        "symptoms": "入睡困难、易醒多梦、醒后疲乏，可伴心悸与情绪烦躁。",
        "main_points": ["百会", "四神聪", "神门", "内关"],
        "adjunct_points": ["安眠", "三阴交", "太冲", "心俞"],
        "technique": "以补法为主，留针 30 分钟",
        "course_cycle": 14,
        "frequency_per_week": 3,
        "notes": "规律作息，睡前避免浓茶、咖啡与长时间使用电子产品。",
    },
    {
        "name": "偏头痛",
        "category": "神经科",
        "syndrome": "肝阳上亢、瘀血阻络",
        "symptoms": "一侧颞部搏动性疼痛，反复发作，可伴恶心、畏光。",
        "main_points": ["风池", "太阳", "合谷", "太冲"],
        "adjunct_points": ["外关", "百会", "印堂"],
        "technique": "以泻法为主，疼痛剧烈时加强捻转",
        "course_cycle": 14,
        "frequency_per_week": 3,
        "notes": "记录头痛日记，规避劳累、情绪波动与饮食诱因。",
    },
    {
        "name": "中风后遗症",
        "category": "神经科",
        "syndrome": "气虚血瘀、经脉失养",
        "symptoms": "半身不遂、口眼歪斜、语言不利、肢体麻木无力。",
        "main_points": ["肩井", "曲池", "合谷", "足三里", "阳陵泉"],
        "adjunct_points": ["外关", "血海", "太溪", "昆仑"],
        "technique": "平补平泻，配合康复训练与电针",
        "course_cycle": 28,
        "frequency_per_week": 3,
        "notes": "尽早介入康复，防跌倒、防压疮，控制血压与血糖。",
    },
    {
        "name": "胃脘痛（功能性消化不良）",
        "category": "内科",
        "syndrome": "脾胃虚弱、肝胃不和",
        "symptoms": "上腹隐痛或胀满、餐后加重，伴嗳气、食欲不振。",
        "main_points": ["中脘", "天枢", "足三里"],
        "adjunct_points": ["内关", "气海", "阴陵泉", "脾俞"],
        "technique": "平补平泻，留针 20–30 分钟",
        "course_cycle": 14,
        "frequency_per_week": 3,
        "notes": "规律饮食，忌生冷油腻与暴饮暴食，保持情绪舒畅。",
    },
    {
        "name": "功能性便秘",
        "category": "内科",
        "syndrome": "气虚便秘、肠燥津亏",
        "symptoms": "排便困难、排便次数减少、便质干硬，腹胀不适。",
        "main_points": ["天枢", "足三里", "关元"],
        "adjunct_points": ["内关", "气海", "承山"],
        "technique": "平补平泻，腹部穴位可配合温和灸",
        "course_cycle": 14,
        "frequency_per_week": 3,
        "notes": "增加膳食纤维与饮水量，养成定时排便习惯，适度运动。",
    },
    {
        "name": "原发性痛经",
        "category": "妇科",
        "syndrome": "寒凝血瘀、气滞血瘀",
        "symptoms": "经前或经期小腹冷痛或坠痛，可伴腰酸、畏寒、经色暗有块。",
        "main_points": ["关元", "三阴交", "血海"],
        "adjunct_points": ["气海", "太冲", "天枢"],
        "technique": "经前 3–5 天开始，平补平泻，关元可加温针或艾灸",
        "course_cycle": 90,
        "frequency_per_week": 3,
        "notes": "连续调理 3 个月经周期，经期注意保暖，忌生冷。",
    },
    {
        "name": "过敏性鼻炎",
        "category": "五官科",
        "syndrome": "肺脾气虚、风寒犯肺",
        "symptoms": "阵发性喷嚏、清水样鼻涕、鼻塞鼻痒，遇冷或接触过敏原加重。",
        "main_points": ["印堂", "风池", "合谷", "足三里"],
        "adjunct_points": ["太阳", "大椎", "肾俞"],
        "technique": "平补平泻，背部穴位可加灸",
        "course_cycle": 21,
        "frequency_per_week": 3,
        "notes": "避免接触过敏原，注意防寒保暖，必要时配合耳鼻喉科诊治。",
    },
]


def sync_knowledge():
    """把穴位主治与病例方案写入数据库，可重复执行（幂等）。

    返回 (更新穴位数, 新建病例数, 更新病例数, 缺失穴位名列表)。
    """
    from clinic.models import Acupoint, CaseProtocol

    points = {point.name: point for point in Acupoint.all_objects.all()}
    updated_points = 0
    missing = []
    for name, indications in ACUPOINT_INDICATIONS.items():
        point = points.get(name)
        if point is None:
            missing.append(name)
            continue
        if point.indications != indications:
            point.indications = indications
            point.save(update_fields=["indications", "updated_at"])
            updated_points += 1

    created = updated = 0
    for item in CASE_PROTOCOLS:
        defaults = {
            key: value
            for key, value in item.items()
            if key not in ("name", "main_points", "adjunct_points")
        }
        defaults["is_deleted"] = False
        case, is_created = CaseProtocol.all_objects.update_or_create(
            name=item["name"], defaults=defaults
        )
        case.main_points.set([points[name] for name in item["main_points"] if name in points])
        case.adjunct_points.set(
            [points[name] for name in item["adjunct_points"] if name in points]
        )
        if is_created:
            created += 1
        else:
            updated += 1
    return updated_points, created, updated, missing


#: 常见病症食疗参考（面向患者的日常调养建议）
DIETARY_GUIDES = [
    {
        "name": "颈椎病",
        "category": "骨伤科",
        "principle": "祛风散寒、补益肝肾",
        "recommended": ["葛根", "黑豆", "山药", "核桃", "黑木耳"],
        "avoid": ["冰饮生冷", "过咸腌制食品", "长期饮酒"],
        "recipes": [
            "葛根黑豆排骨汤：葛根 30g、黑豆 50g 与排骨同炖，适合颈肩僵硬、受凉加重者。",
            "山药核桃粥：山药、核桃仁与粳米煮粥，早晚温服。",
        ],
    },
    {
        "name": "失眠",
        "category": "内科",
        "principle": "养心安神、健脾益气",
        "recommended": ["小米", "百合", "莲子", "龙眼肉", "酸枣仁"],
        "avoid": ["咖啡浓茶", "辛辣刺激", "睡前饱食或夜宵"],
        "recipes": [
            "酸枣仁百合莲子粥：酸枣仁 15g 捣碎，与百合、莲子、小米同煮，睡前 1 小时温服。",
            "桂圆红枣茶：桂圆肉 5 枚、红枣 3 枚泡水，适合心脾两虚者，易上火者少量饮用。",
        ],
    },
    {
        "name": "胃脘痛",
        "category": "内科",
        "principle": "健脾和胃、温中理气",
        "recommended": ["小米", "山药", "南瓜", "白扁豆", "生姜"],
        "avoid": ["生冷瓜果", "油炸油腻", "辛辣与酒"],
        "recipes": [
            "山药小米粥：山药去皮切块与小米同煮至软烂，少量多餐。",
            "南瓜小米粥：南瓜与小米煮粥，适合胃部隐痛、食欲不振者。",
        ],
    },
    {
        "name": "功能性便秘",
        "category": "内科",
        "principle": "润肠通便、益气养阴",
        "recommended": ["燕麦", "红薯", "火龙果", "黑芝麻", "蜂蜜"],
        "avoid": ["辛辣煎炸", "精细加工食品", "长期久坐少饮水"],
        "recipes": [
            "黑芝麻核桃糊：黑芝麻、核桃仁炒香研末，温水冲调，每日一小碗。",
            "红薯燕麦粥：红薯切块与燕麦同煮，搭配足量饮水。",
        ],
    },
    {
        "name": "原发性痛经",
        "category": "妇科",
        "principle": "温经散寒、活血调经",
        "recommended": ["生姜", "红枣", "桂圆", "羊肉", "红糖"],
        "avoid": ["冰饮冷食", "经期生冷瓜果", "过度节食"],
        "recipes": [
            "生姜红枣茶：生姜 3 片、红枣 5 枚煮水，经前一周开始温服。",
            "桂圆红枣小米粥：适合经后气血偏虚者调养。",
        ],
    },
    {
        "name": "过敏性鼻炎",
        "category": "五官科",
        "principle": "补益肺脾、散寒通窍",
        "recommended": ["山药", "大枣", "鸡肉", "胡萝卜", "生姜"],
        "avoid": ["冰饮生冷", "海鲜发物", "明确过敏的食物"],
        "recipes": [
            "山药大枣粥：山药、大枣与粳米煮粥，适合平素易感冒、鼻塞者。",
            "葱白生姜汤：受凉后鼻塞流清涕时可少量饮用，热证者不宜。",
        ],
    },
    {
        "name": "偏头痛",
        "category": "神经科",
        "principle": "平肝潜阳、养血通络",
        "recommended": ["深绿色蔬菜", "坚果", "小米", "菊花", "枸杞"],
        "avoid": ["奶酪", "红酒", "巧克力", "腌制与加工肉类"],
        "recipes": [
            "菊花枸杞茶：菊花 5 朵、枸杞 10 粒泡水，肝阳偏亢、目胀者适宜。",
            "小米核桃粥：小米与核桃仁煮粥，作为日常主食调养。",
        ],
    },
    {
        "name": "膝骨关节炎",
        "category": "骨伤科",
        "principle": "补益肝肾、强筋健骨",
        "recommended": ["黑豆", "牛奶", "虾皮", "山药", "黑木耳"],
        "avoid": ["过咸", "高糖零食", "油炸食品", "饮酒"],
        "recipes": [
            "黑豆山药排骨汤：黑豆提前浸泡，与山药、排骨同炖。",
            "木耳炒山药：木耳泡发后与山药清炒，少油少盐。",
        ],
    },
    {
        "name": "面瘫",
        "category": "神经科",
        "principle": "祛风通络、益气养血",
        "recommended": ["鳝鱼", "山药", "红枣", "鸡蛋", "温软主食"],
        "avoid": ["生冷", "辛辣刺激", "坚硬难嚼食物"],
        "recipes": [
            "山药鳝鱼粥：鳝鱼去骨切丝，与山药、粳米煮粥，注意少盐。",
            "红枣生姜汤：红枣与生姜煮水，适合恢复期畏风者。",
        ],
    },
    {
        "name": "中风后遗症",
        "category": "神经科",
        "principle": "益气活血、低盐低脂",
        "recommended": ["全谷物", "深海鱼", "芹菜", "黑木耳", "豆制品"],
        "avoid": ["高盐腌制", "油炸食品", "动物内脏", "含糖饮料"],
        "recipes": [
            "山药燕麦粥：山药与燕麦煮粥，适合吞咽功能尚可者。",
            "芹菜木耳炒：芹菜与木耳清炒，少油少盐，辅助控制血压血脂。",
        ],
    },
]
