# APP-012 TEST_PASSED

- 测试角色：独立测试 Agent
- 实现交接状态：`READY_FOR_TEST`
- 环境：Windows；Python `3.11.13`；uv `0.7.21`；Node.js `20.19.0`（按 `.nvmrc`）；npm `10.8.2`；隔离 PostgreSQL。
- 测试数据库：由 `backend/tests/run-isolated-postgres.ps1` 创建/复用隔离数据库；未连接开发或生产数据库。
- 黑盒边界：仅通过公开 HTTP API、公开 DOM/HTTP 行为和迁移命令验证；未读取或分析 `backend/apps/`、`frontend/src/`，未修改测试或生产代码。

## APP-012 后端专项

命令：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_app_012.py','--tb=no','-q')
```

结果：**5 passed / 0 failed / 0 errors**，约 10.48 秒，exit 0。

覆盖的公开行为：

- 未认证公司目录返回 `401`；公司名称按首尾空白和大小写规范化，全局重复创建返回 `409 COMPANY_EXISTS`，不产生第二个公司；目录只返回公开公司字段。
- 用户 A/B 可复用同一公司并看到共享招聘网站，但应用、岗位、备注、状态、面试及越权详情/子资源保持用户隔离，越权统一 `404`。
- 同一用户以 `company_id` 新增岗位复用原公司投递聚合；岗位级 `application_url` 被 `400 VALIDATION_ERROR` 拒绝，岗位响应不复制公司网站。
- 公司招聘网站 PATCH 对双方可见；岗位状态更新不改动公司招聘网站。
- 旧 flat `company_name`/`application_url` 请求仍可创建并返回 `company_id`、公司招聘网站兼容投影，APP-011 八值状态保持有效。

## APP-012 前端专项

命令：

```powershell
nvm use 20.19.0
Set-Location frontend
& .\node_modules\.bin\playwright.cmd test --config=tests/playwright.web_app_012.config.mts --reporter=line
```

结果：**3 passed / 0 failed / 0 errors**，约 8.5 秒，exit 0。

覆盖的公开行为：

- 新增表单使用全局公司选择器和创建入口；选择已有公司后只提交 `company_id`，不提交公司名或招聘网站作为岗位字段。
- 同一公司新增多个岗位时招聘网站只展示一次，岗位表单不提交岗位级网站字段。
- 公司行可折叠展开当前用户的多个岗位；展开后可见岗位独立编辑入口，不显示其他用户岗位。
- 公司网站编辑明确为共享信息，并通过 `/api/v1/companies/{id}/` PATCH 保存。

## 迁移与兼容公开证据

- 命令 `& .\backend\tests\run-isolated-postgres.ps1 -MigrateOnly` 成功，结果为所有迁移已应用且 `No migrations to apply`。
- APP-009/APP-011 后端相邻公开回归合计 **49 passed / 0 failed / 0 errors**，其中包含既有旧数据迁移后的 API 兼容、岗位/流程保留和权限隔离验证。
- `docs/implementation-notes/APP-012.md` 记录了 APP-012 迁移文件、真实 PostgreSQL 存量合并/URL 冲突统计及非空关系逆迁移保护；本轮未改动该说明。

## 相邻回归观察（不改变 APP-012 专项结论）

- APP-011 前端旧回归：`1 passed / 2 failed`。失败测试仍按 APP-012 之前的自由文本“公司名称”和旧的首个 combobox 定位，属于相邻测试与 APP-012 新公司选择器契约未同步，不是 APP-012 两个专项断言失败。
- WEB-APP-009 前端回归：`2 passed / 2 failed`，失败为既有 favicon/sidebar 用户图片字节哈希断言；与 APP-012 无关。按用户指示未继续无关长回归。

## 覆盖的验收标准

- [x] 全局公司目录规范化唯一、重复创建冲突和公开字段隔离。
- [x] A/B 公司复用但用户投递、岗位、备注、状态、面试和流程隔离。
- [x] 同用户追加岗位复用聚合，公司 URL 单一写入来源及岗位 URL 禁写。
- [x] 旧 flat 兼容投影及 APP-011 状态字段保持。
- [x] 前端公司选择/创建、公司网站单次展示、折叠岗位列表和独立编辑入口。
- [x] 隔离 PostgreSQL 迁移可应用，迁移/兼容说明的公开证据已核对。

## 结论

- 状态：`TEST_PASSED`
- 是否实现回流：否。APP-012 指定后端和前端专项均稳定通过；已观察到的相邻前端失败已明确归因，不作为 APP-012 实现回流依据。
- 后续：交项目管理 Agent 进入公开验收；相邻 APP-011 UI 测试契约同步和 WEB-APP-009 favicon 失败另行处理。
