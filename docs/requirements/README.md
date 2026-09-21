# 校招进度管理系统需求索引

## 需求基线

本索引对应《校招进度管理系统-详细设计方案.md》V1.0。已完成的工程任务不重复拆分：

- `TASK-001`：工程基线与健康检查接口，`DONE`。
- `BASE-ENV-001`：uv 与 nvm 环境基线，`DONE`。

其余需求均通过短 TDD 循环拆分为独立任务。所有新任务初始状态为 `PLANNED`，必须经过 `RED_CONFIRMED`、实现、独立复测和项目管理验收后才能进入 `DONE`。

## 冻结的公开决策

- API 前缀为 `/api/v1/`，JSON 错误使用 `code`、`message`、`details` 结构。
- Django 使用内置 User；注册保存用户名、可选邮箱和 Django 加盐密码哈希。
- Access Token 有效期 30 分钟，Refresh Token 绝对有效期 7 天；刷新轮换并黑名单旧 Refresh Token。
- 投递记录按当前 Token 用户隔离；越权详情、修改和删除统一返回 `404`。
- 投递阶段为 AI 面、笔试、一面、二面、三面、HR 面六个可空时间字段；当前阶段由最新阶段派生。
- 列表默认 `updated_at DESC, id DESC`，默认每页 20，允许 10/20/50/100。
- 时间使用带时区 ISO 8601，数据库保存 UTC，清空时间使用 JSON `null`。
- 前端 Token 只能由统一存储模块读写；认证请求需要自动刷新、并发去重和失败清理。

## 任务顺序

```text
TASK-001 → BASE-ENV-001
              ↓
DB-001 → AUTH-001 → AUTH-002 → AUTH-003 → AUTH-004
   │         │          │          │          │
   └─────────┴──────────┴──────────┴──────────┴─────┐
                                                    ↓
APP-001 → APP-002 → APP-003 → APP-004 → APP-005
                         │        ├──────→ APP-006
                         │        └──────→ APP-007
                         ↓
WEB-AUTH-001 → WEB-AUTH-002 → WEB-AUTH-003
                         ↓
WEB-APP-001 → WEB-APP-002 → WEB-APP-003 → WEB-APP-004
                         ↓                 ↓
                  SEC-001 / DOC-001 → E2E-001 → REL-001
```

其中 `APP-006`、`APP-007` 可在 `APP-003` 后并行；每个任务单均列出精确依赖，执行时以任务单为准。

## 新任务目录

| 顺序 | 任务 | 内容 | 状态 |
|---:|---|---|---|
| 1 | `DB-001` | Django/DRF/PostgreSQL 数据与迁移基线 | PLANNED |
| 2 | `AUTH-001` | 注册持久化与密码校验 | PLANNED |
| 3 | `AUTH-002` | 登录签发与当前用户 | PLANNED |
| 4 | `AUTH-003` | Refresh Token 轮换与 7 天登录态 | PLANNED |
| 5 | `AUTH-004` | 退出失效与认证边界 | PLANNED |
| 6 | `APP-001` | 投递模型、迁移与当前阶段派生 | PLANNED |
| 7 | `APP-002` | 创建投递记录 API | PLANNED |
| 8 | `APP-003` | 本人列表/详情与数据隔离 | PLANNED |
| 9 | `APP-004` | 分页与每页数量 | PLANNED |
| 10 | `APP-005` | 搜索、筛选与排序 | PLANNED |
| 11 | `APP-006` | 修改与阶段时间清空 | PLANNED |
| 12 | `APP-007` | 删除投递记录 | PLANNED |
| 13 | `WEB-AUTH-001` | Token 存储与 Axios 自动刷新 | PLANNED |
| 14 | `WEB-AUTH-002` | Pinia 认证状态与路由保护 | PLANNED |
| 15 | `WEB-AUTH-003` | 登录与注册页面 | PLANNED |
| 16 | `WEB-APP-001` | 投递 API 类型与查询状态 | PLANNED |
| 17 | `WEB-APP-002` | 投递列表、搜索筛选与分页页面 | PLANNED |
| 18 | `WEB-APP-003` | 新增、编辑与阶段时间表单 | PLANNED |
| 19 | `WEB-APP-004` | 删除确认、空状态与异常状态 | PLANNED |
| 20 | `SEC-001` | 安全配置、错误处理与日志脱敏 | PLANNED |
| 21 | `DOC-001` | OpenAPI、运行和部署文档 | PLANNED |
| 22 | `E2E-001` | 核心端到端流程 | PLANNED |
| 23 | `REL-001` | 全量质量门禁与发布演练 | PLANNED |

