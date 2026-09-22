# Glacior 计划同步接口文档

## 1. 文档组织

### 1.1 文档目的

本文档用于指导其他系统读取 `Glacior 计划.json`，并将其中的公司投递进度同步到校招进度管理平台。

平台提供标准 REST API。对接方负责解析 Glacior JSON、完成字段映射，并调用平台接口；平台只负责认证、投递记录的增删改查和用户数据隔离。

### 1.2 基础约定

| 项目 | 约定 |
| --- | --- |
| Base URL | `${API_BASE_URL}`，由部署环境提供，不在代码中写死 |
| 数据格式 | `application/json` |
| 字符编码 | UTF-8 |
| 认证方式 | JWT Bearer Token |
| 认证请求头 | `Authorization: Bearer <access>` |
| 时间格式 | ISO 8601，建议使用 `2026-09-08T00:00:00+08:00` |
| 用户范围 | Token 对应用户，只能读写该用户自己的投递记录 |

当前 API 的投递创建接口接收“单条标准化投递记录”，不直接接收整个 Glacior 项目根 JSON。对接方应遍历 `folders`，将每个 folder 转换为一条投递记录。`application_url` 是投递链接功能字段，需要部署包含对应数据库迁移的版本后才能使用。

### 1.3 Glacior 数据映射规则

每个 `folders[]` 对应一条投递记录：

| Glacior 字段 | 平台字段 | 映射规则 |
| --- | --- | --- |
| `folder.title` | `company_name`、`position_name` | 按第一个 `-` 分割；左侧为公司，右侧为岗位 |
| `folder.status=completed` | `application_status=rejected` | 表示已挂/已结束 |
| `folder.status=active` | `application_status=in_progress` | 表示仍在流程中 |
| `folder.collapsed` | 不参与状态判断 | 不能使用该字段判断是否挂 |
| task.title=`笔试` | `written_test_time` | 使用 `task.start` |
| task.title=`AI面试` | `ai_interview_time` | 使用 `task.start` |
| task.title=`一面` | `first_interview_time` | 使用 `task.start` |
| task.title=`二面` | `second_interview_time` | 使用 `task.start` |
| task.title=`三面` | `third_interview_time` | 使用 `task.start` |
| task.title=`HR面` | `hr_interview_time` | 使用 `task.start` |
| task.title=`测评` | `notes` | 当前模型没有独立测评字段，建议保留为备注 |
| 无投递日期 | `application_time=null` | 不要用任务日期代替投递日期 |

`folder.id`、`task.id` 仅用于对接方定位和去重，当前平台接口不会保存这两个来源 ID。重复同步前，对接方应先查询当前用户记录，并按 `company_name + position_name` 匹配后执行新增或修改。

## 2. 接口列表

| 方法 | 路径 | 认证 | 用途 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/login/` | 否 | 登录并获取 JWT |
| `POST` | `/api/v1/auth/refresh/` | 否 | 刷新 access token |
| `GET` | `/api/v1/auth/me/` | 是 | 获取当前用户 |
| `GET` | `/api/v1/applications/` | 是 | 查询当前用户投递记录 |
| `POST` | `/api/v1/applications/` | 是 | 创建一条投递记录 |
| `GET` | `/api/v1/applications/{id}/` | 是 | 查询一条投递记录 |
| `PATCH` | `/api/v1/applications/{id}/` | 是 | 修改一条投递记录 |
| `DELETE` | `/api/v1/applications/{id}/` | 是 | 删除一条投递记录 |
| `POST` | `/api/v1/auth/logout/` | 是 | 注销并使 refresh token 失效 |

## 3. 具体接口

### 3.1 登录

**请求**

```http
POST ${API_BASE_URL}/api/v1/auth/login/
Content-Type: application/json
```

```json
{
  "username": "李心宇",
  "password": "用户密码"
}
```

**成功响应：`200 OK`**

```json
{
  "access": "<jwt-access-token>",
  "refresh": "<jwt-refresh-token>",
  "access_expires_in": 3600,
  "refresh_expires_in": 604800,
  "user": {
    "id": 1,
    "username": "李心宇",
    "email": "user@example.com"
  }
}
```

后续请求使用 `access`：

```http
Authorization: Bearer <jwt-access-token>
```

### 3.2 查询当前用户投递记录

```http
GET ${API_BASE_URL}/api/v1/applications/?page=1&page_size=100
Authorization: Bearer <jwt-access-token>
```

**成功响应：`200 OK`**

```json
{
  "count": 1,
  "page": 1,
  "page_size": 100,
  "total_pages": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 21,
      "user": 1,
      "company_name": "多益网络",
      "position_name": "前端开发",
      "application_url": "https://example.com/jobs/123",
      "application_status": "in_progress",
      "current_stage": "first_interview",
      "application_time": null,
      "ai_interview_time": null,
      "written_test_time": "2026-08-27T00:00:00+08:00",
      "first_interview_time": "2026-09-08T00:00:00+08:00",
      "second_interview_time": null,
      "third_interview_time": null,
      "hr_interview_time": null,
      "notes": "测评：2026-08-22",
      "created_at": "2026-09-22T10:00:00+08:00",
      "updated_at": "2026-09-22T10:00:00+08:00"
    }
  ]
}
```

支持的筛选参数：

| 参数 | 示例 | 说明 |
| --- | --- | --- |
| `search` | `search=多益` | 公司名或岗位名模糊搜索 |
| `application_status` | `application_status=in_progress` | 平台状态值，支持逗号分隔多个状态，例如 `in_progress,rejected` |
| `stage` | `stage=first_interview` | 筛选已填写的阶段时间 |
| `application_time_after` | `application_time_after=2026-09-01T00:00:00+08:00` | 投递时间起点 |
| `application_time_before` | `application_time_before=2026-09-30T23:59:59+08:00` | 投递时间终点 |
| `page` | `page=1` | 页码 |
| `page_size` | `page_size=100` | 每页数量，最大 100 |

### 3.3 创建投递记录

对接方在查询结果中找不到同一 `company_name + position_name` 时调用创建接口。

```http
POST ${API_BASE_URL}/api/v1/applications/
Authorization: Bearer <jwt-access-token>
Content-Type: application/json
```

```json
{
  "company_name": "多益网络",
  "position_name": "前端开发",
  "application_url": "https://example.com/jobs/123",
  "application_status": "in_progress",
  "application_time": null,
  "ai_interview_time": null,
  "written_test_time": "2026-08-27T00:00:00+08:00",
  "first_interview_time": "2026-09-08T00:00:00+08:00",
  "second_interview_time": null,
  "third_interview_time": null,
  "hr_interview_time": null,
  "notes": "来源：Glacior 计划；测评：2026-08-22"
}
```

**成功响应：`201 Created`**，返回完整投递记录，结构与查询接口 `results[]` 相同。

### 3.4 修改投递记录

对接方查询到同一条记录后，使用返回的 `id` 修改。推荐使用 `PATCH`，只提交发生变化的字段。

```http
PATCH ${API_BASE_URL}/api/v1/applications/21/
Authorization: Bearer <jwt-access-token>
Content-Type: application/json
```

```json
{
  "application_status": "rejected",
  "notes": "来源：Glacior 计划；状态字段=completed"
}
```

**成功响应：`200 OK`**，返回修改后的完整投递记录。

### 3.5 删除投递记录

```http
DELETE ${API_BASE_URL}/api/v1/applications/21/
Authorization: Bearer <jwt-access-token>
```

**成功响应：`204 No Content`**。

对接同步不建议主动删除平台已有记录；如果源数据中不再存在某个 folder，默认只是不更新，不应直接删除。

### 3.6 刷新 Token

```http
POST ${API_BASE_URL}/api/v1/auth/refresh/
Content-Type: application/json
```

```json
{
  "refresh": "<jwt-refresh-token>"
}
```

**成功响应：`200 OK`**，返回新的 `access` 和 `refresh`。

## 4. Glacior JSON 对接流程

推荐流程如下：

1. 调用登录接口获取 `access` 和 `refresh`。
2. 遍历 JSON 的 `folders[]`。
3. 按字段映射规则生成标准化投递对象。
4. 调用列表接口获取当前用户已有记录。
5. 按 `company_name + position_name` 匹配：不存在则 `POST`，存在则 `PATCH`。
6. 对每个 folder 处理完成后记录成功、失败和跳过数量。
7. access token 过期时使用 refresh token 换取新 token 后重试一次。

伪代码：

```text
access = login(username, password).access
existing = list_all_applications(access)

for folder in glacior.folders:
    application = convert_folder(folder)
    old = find(existing, application.company_name, application.position_name)

    if old is None:
        post_application(access, application)
    else:
        patch_application(access, old.id, application)
```

## 5. 状态和错误处理

### 5.1 平台状态值

| 平台值 | 含义 |
| --- | --- |
| `applied` | 已投递，尚未进入明确流程 |
| `in_progress` | 仍在流程中，对应 Glacior `status=active` |
| `offer` | 已录用 |
| `rejected` | 已拒绝/挂，对应 Glacior `status=completed` |
| `withdrawn` | 已放弃 |

### 5.2 错误响应

统一错误结构：

```json
{
  "code": "VALIDATION_ERROR",
  "details": {
    "application_status": ["application_status is not a supported status."]
  }
}
```

常见状态码：

| HTTP 状态码 | 含义 | 对接处理 |
| --- | --- | --- |
| `400` | 请求字段或时间格式错误 | 修正当前记录，不要重复重试 |
| `401` | access token 无效或过期 | refresh 后重试一次 |
| `404` | 记录不存在或不属于当前用户 | 重新查询后按新增处理 |
| `409` | 资源冲突 | 记录冲突信息并人工确认 |
| `500` | 服务端异常 | 记录失败，稍后重试 |

## 6. 在线文档入口

部署环境提供以下 OpenAPI 文档：

- JSON Schema：`${API_BASE_URL}/api/schema/`
- Swagger UI：`${API_BASE_URL}/api/schema/swagger/`

以上地址中的 `${API_BASE_URL}` 由部署方替换为实际平台地址。不要在代码仓库中提交账号密码、JWT、数据库密码或固定生产地址。
