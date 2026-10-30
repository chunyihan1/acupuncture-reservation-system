# 针灸治疗预约与治疗记录管理系统（ART-RS）

> 软件工程课程项目 · 第 11 组
> 依据《针灸预约系统》需求文档与《可行性研究报告》实现，面向个体针灸诊所、医院针灸科及高校实训教学场景。

系统围绕“患者预约 → 医师排期 → 辨证取穴 → 治疗登记 → 审核归档 → 运营统计”构建完整业务闭环，并提供基于角色的功能权限与数据行级隔离。

---

## 1. 功能概览

| 角色 | 核心功能 |
| --- | --- |
| 就诊患者 | 自助注册、按医师/日期选择出诊时段、提交主诉、取消预约、查看预约进度、查阅本人已确认治疗档案 |
| 针灸医师 | 接诊工作台、待排期确认、状态流转、制定治疗方案（主穴/配穴）、录入治疗记录、患者历史档案、维护执业资料 |
| 门诊管理员 | 运营数据看板（4 类图表）、预约检索与 CSV 导出、账号管理、排班管理、穴位库维护、治疗记录审核 |
| 系统运维/教学管理员 | 包含管理员全部权限，并可审计操作日志 |

### 业务主流程

```
患者提交预约(pending) → 医师确认排期(scheduled) → 开始治疗(treating)
        → 治疗记录确认(completed) → 归档(archived)
异常分支：pending/scheduled → cancelled；scheduled/treating/completed → returned → 重新排期
```

状态流转集中在 `Appointment.TRANSITIONS` 中定义，任何页面操作都会经过同一套校验，避免非法状态跳跃。

---

## 2. 技术栈

- Python 3.10+ / Django 5.1
- SQLite（默认，开箱即用）/ MySQL 8（通过环境变量切换，字符集 utf8mb4）
- Django Template + Bootstrap 5 + Bootstrap Icons
- ECharts 5（管理端运营看板）
- 原生 HTML/CSS（自定义“青绿 + 宣纸”视觉体系，无前端构建步骤）

---

## 3. 快速开始

```bash
# 1. 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python manage.py migrate

# 4. 导入演示数据（账号、穴位库、排班、预约、方案、治疗记录）
python manage.py seed_demo

# 5. 启动开发服务器
python manage.py runserver
```

访问 <http://127.0.0.1:8000/>，使用以下演示账号登录（统一密码 `demo12345`）：

| 账号 | 角色 | 说明 |
| --- | --- | --- |
| `patient1` | 就诊患者 | 已有预约与治疗档案，可直接体验 |
| `doctor1` | 针灸医师 | 今日有排班与待处理预约 |
| `admin` | 门诊管理员 | 可查看运营看板与全部管理功能 |
| `sysadmin` | 系统运维管理员 | 额外可查看操作日志 |

> 重新生成演示数据：`python manage.py seed_demo --reset`

### 使用 MySQL

```bash
set MYSQL_DATABASE=art_rs
set MYSQL_USER=root
set MYSQL_PASSWORD=your_password
set MYSQL_HOST=127.0.0.1
set MYSQL_PORT=3306
pip install mysqlclient
python manage.py migrate
```

### 生产环境关键环境变量

| 变量 | 作用 |
| --- | --- |
| `DJANGO_SECRET_KEY` | 密钥，生产环境必须替换 |
| `DJANGO_DEBUG=0` | 关闭调试模式（自动启用 HTTPS Cookie、HSTS） |
| `DJANGO_ALLOWED_HOSTS` | 允许域名，逗号分隔 |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | HTTPS 域名白名单 |

生产部署可使用 Gunicorn/uWSGI + Nginx，静态文件通过 `python manage.py collectstatic` 收集到 `staticfiles/`。

---

## 4. 项目结构

```
acupuncture-reservation-system/
├── art_rs/                     # 项目配置
│   ├── settings.py             # SQLite/MySQL 切换、安全与日志配置
│   └── urls.py
├── clinic/                     # 核心业务应用
│   ├── models.py               # 用户、排班、预约、方案、记录、日志
│   ├── services.py             # 预约占号、状态流转、统计聚合
│   ├── permissions.py          # 角色权限 + 行级数据权限
│   ├── forms.py                # 表单与校验规则
│   ├── views.py                # 患者端 / 医师端 / 管理端视图
│   ├── urls.py
│   ├── tests.py                # 22 个单元测试
│   ├── management/commands/seed_demo.py
│   └── templatetags/clinic_extras.py
├── templates/
│   ├── base.html               # 角色感知导航
│   ├── auth/                   # 登录、注册（品牌化分栏页）
│   ├── patient/                # 医师列表、排班、预约、档案
│   ├── doctor/                 # 工作台、接诊、方案、记录、患者
│   ├── admin/                  # 看板、预约、账号、排班、穴位、审核、日志
│   ├── components/pagination.html
│   └── errors/                 # 403 / 404 / 500
├── static/css/app.css          # 设计系统样式
├── requirements.txt
└── manage.py
```

---

## 5. 数据模型

| 实体 | 关键字段 | 说明 |
| --- | --- | --- |
| `User` | role、name、phone、id_card、is_deleted | 继承 `AbstractUser`，一个账号一种角色 |
| `DoctorProfile` | department、title、specialty、room | 医师执业档案，与账号一对一 |
| `TreatmentRoom` | name、location、equipment | 治疗室与设备配置 |
| `Schedule` | doctor、date、start_time、end_time、capacity | 出诊排班，`(doctor,date,start_time)` 唯一 |
| `Appointment` | patient、doctor、schedule、appoint_time、status | 预约单，状态机核心 |
| `Acupoint` | name、code、meridian、location | 穴位基础库 |
| `TreatmentPlan` | appointment、syndrome、technique、course_cycle | 与预约一对一 |
| `PlanAcupoint` | plan、acupoint、type(主穴/配穴)、order | 方案与穴位多对多关联 |
| `TreatmentRecord` | plan、doctor、treat_time、needling_duration、status | 治疗记录，支持审核退回 |
| `OperationLog` | user、action、target、detail、ip | 关键操作审计 |

设计要点：

- **软删除**：`User`、`Appointment`、`TreatmentPlan`、`TreatmentRecord`、`Acupoint` 等使用 `is_deleted` 逻辑删除，保留历史诊疗数据；`Patient`/`Appointment` 对外键使用 `PROTECT`，避免级联删除破坏记录。
- **号源一致性**：`services.create_appointment` 在事务中对排班行 `select_for_update()`，叠加 `(doctor,date,start_time)` 唯一约束，防止并发超约。
- **敏感数据**：手机号在列表 / 日志中通过 `mask_phone` 模板过滤器脱敏（`138****0123`）。

---

## 6. 权限与安全设计

1. **功能级权限**：`role_required(*roles)` 装饰器按角色拦截患者端 / 医师端 / 管理端路由。
2. **数据级权限**：
   - 患者只能查看本人的预约、记录；
   - 医师只能查看“本人接诊过”的患者档案，跨医师访问返回 403；
   - 管理员可查看全量业务数据，但系统运维账号仅系统管理员可管理。
3. **状态机约束**：所有状态变更经 `Appointment.transition_to()` 校验，非法流转抛出 `ValidationError`。
4. **登录防护**：同一会话连续失败 5 次锁定 5 分钟；失败与成功均写入操作日志（含 IP）。
5. **其他**：CSRF 全站启用、`X-Frame-Options=DENY`、生产模式启用 Secure Cookie / HSTS；删除账号采用逻辑删除并保留历史数据。

---

## 7. 测试

```bash
python manage.py test clinic -v 2
```

覆盖 22 个用例，包含：

- 预约创建、重复预约拦截、号源上限、过期排班拒绝、取消释放号源；
- 状态机合法 / 非法流转；
- 治疗方案主穴必选、配穴互斥、记录确认后主流程推进；
- 管理员记录审核确认 / 退回；
- 跨患者、跨医师、跨角色越权访问（403 / 404）；
- 敏感字段脱敏。

---

## 8. 页面速览

| 端 | 页面 |
| --- | --- |
| 公共 | 登录、患者注册、403/404/500 |
| 患者 | 医师列表、医师排班、提交预约、我的预约、预约详情、治疗档案、记录详情 |
| 医师 | 工作台、预约接诊列表、接诊详情、治疗方案制定、治疗记录录入、患者档案、个人资料 |
| 管理 | 运营看板（趋势/状态/医师负载/月度治疗）、预约管理、CSV 导出、账号管理、排班管理、穴位维护、记录审核、操作日志 |

---

## 9. 后续可扩展方向

- 短信 / 企业微信预约提醒与取消通知；
- 医师端排班自助申请与管理员审批；
- 疗程自动排期（按 `course_cycle` 与 `frequency_per_week` 生成后续预约）；
- 治疗前后对比照片、量表评分（VAS 疼痛评分）与疗效统计；
- 对接医院 HIS / 电子病历系统。

---

## 10. 说明

本项目为课程作业实现，演示数据均为虚构；系统不构成任何医疗建议。若用于真实诊疗场景，需补充等保合规、数据加密存储、审计留存周期与医疗行业相关资质要求。
