# WEB-APP-008 RED_CONFIRMED

- 测试角色：测试 Agent
- 任务状态：`PLANNED`
- 输入：`docs/tasks/WEB-APP-008.md`、`docs/requirements/WEB-APP-008.md`、APP-011/WEB-APP-007 公开契约与验收报告
- 环境：Windows；Python 3.11.13；uv 0.7.21；按 `.nvmrc` 选择 Node.js 20.19.0；npm 10.8.2；后端 API 测试使用项目既有隔离 PostgreSQL，前端使用本地 Vite 与 Edge、公开 HTTP 夹具。
- 修改范围：只新增 `backend/tests/`、`frontend/tests/` 测试和本报告；未修改生产代码、任务单或既有断言。

## 新增测试

- `backend/tests/test_web_app_008_api.py`
  - 默认列表服务端拒绝末位排序：全拒绝公司置于所有非拒绝公司之后；多岗位只要有一个有效流程状态非拒绝，就属于非拒绝组。
  - `page=0`、负数、非整数、小数、空值和空白页码返回字段级 `400 VALIDATION_ERROR`。
- `frontend/tests/test_web_app_008.e2e.spec.ts`
  - 关键字框聚焦加载当前用户跨分页历史公司建议，去重后点击建议填入并搜索，同时保留 page_size、状态、日期和排序。
  - 页码选择器 `1..total_pages`、页码输入跳转、查询状态保留和非法输入不发请求。
- `frontend/tests/playwright.web_app_008.config.mts`
  - WEB-APP-008 独立 Playwright 配置。

## 后端 RED

命令连续运行两次：

```powershell
& .\backend\tests\run-isolated-postgres.ps1 -PytestArguments @('tests/test_web_app_008_api.py','--tb=no','-q')
```

结果稳定一致：

- 第一次：**6 passed / 1 failed / 0 errors**，9.78 秒
- 第二次：**6 passed / 1 failed / 0 errors**，8.90 秒
- 通过项：六种非法 `page` 输入均得到字段级验证错误。
- 失败项：`test_default_listing_places_only_all_rejected_companies_after_active_companies`。

公开输入包括三个当前用户公司：一个非拒绝岗位公司、一个同时含拒绝岗位和测评岗位的多岗位公司、一个全拒绝公司；请求为 `GET /api/v1/applications/?page=1&page_size=10`，未指定自定义排序。

期望顺序为：多岗位仍推进公司、早期推进公司、最近全拒绝公司。实际第一项为最近全拒绝公司，说明当前公开默认排序仍按更新时间/ID优先，未在服务端分页前应用“全拒绝末位”分组。失败来自公开响应顺序，不是认证、数据库、语法或夹具错误。

## 前端 RED

命令连续运行两次：

```powershell
nvm use 20.19.0
Set-Location frontend
npm exec -- playwright test -- --config=tests/playwright.web_app_008.config.mts --reporter=line
```

两次均为 **0 passed / 2 failed**，失败集合一致：

1. `focus loads own deduplicated company suggestions and selecting one searches with preserved query state`
   - 公开输入：聚焦关键字输入框。
   - 期望：出现可访问 `listbox`，展示当前用户跨两页的本人历史公司，大小写/首尾空白归一去重；点击建议后填入公司名、关闭建议并以 `page=1` 搜索，同时保留 `page_size=50`、`application_status=assessment`、日期和 `ordering`。
   - 实际：`getByRole('listbox')` 在 4 秒内不可见；测试失败发生在新增建议行为入口，不是登录、主列表 API 或夹具错误。

2. `page selector and numeric jump preserve page size and filters, while invalid input sends no request`
   - 公开输入：主列表返回 `total_pages=3`，URL 带 `pageSize=50`、搜索、状态和排序。
   - 期望：出现带“页码”可访问名称的选择器，选项为 `1/2/3`，选择页码或输入合法页码只改变 `page` 并保留查询状态；输入 `0` 显示错误且不发列表请求。
   - 实际：`getByRole('combobox', { name: /页码/ })` 不存在；失败发生在新增分页选择器公开 UI，不是服务启动或网络错误。

现有输入框和主列表公开 API 夹具均已运行；当前缺失行为是建议面板和页码选择/输入控件本身。前端专项没有通过项，但失败稳定且命中新需求行为。

## 覆盖的验收标准

- 当前用户历史公司建议的认证来源、跨分页读取、去重和选择搜索状态保留。
- 默认拒绝末位排序服务端先于分页，多岗位混合状态不误判为全拒绝。
- 页码选择、合法跳转、非法输入不发请求以及 page/page_size/搜索/状态/排序查询状态保留。
- API 非法页码字段级错误。

## 未覆盖风险

- 未运行全量前端套件、所有浏览器矩阵、视觉像素级/全量无障碍检查。
- 未单独验证建议网络失败、401、退出登录缓存清除、空列表/无匹配文案；新增核心公开入口已稳定 RED。
- 未运行全量 APP-009/APP-010/APP-011 相邻回归；WEB-APP-008 当前 RED 已足以进入实现阶段。
- 后端未新增建议专用接口测试，因为契约明确建议复用认证后的应用列表 API；建议来源、去重和状态保留由前端公开 HTTP 夹具验证。

## 黑盒声明

严格依据 WEB-APP-008、APP-011 和 WEB-APP-007 公开契约工作；未读取、搜索、枚举或分析 `frontend/src/`、`backend/apps/`。只观察公开 HTTP 请求/响应、认证行为和可见 DOM/可访问角色。未修改生产代码、任务单或既有断言。

## Agent 交接

- 任务编号：WEB-APP-008
- 当前状态：`RED_CONFIRMED`
- 发送角色：测试 Agent
- 接收角色：项目管理 Agent；请交功能实现 Agent 进入 `IMPLEMENTING`
- 产物：`backend/tests/test_web_app_008_api.py`、`frontend/tests/test_web_app_008.e2e.spec.ts`、`frontend/tests/playwright.web_app_008.config.mts`、本报告
- 回流依据：后端排序 RED 两次稳定为 6/1，前端建议/页码 RED 两次稳定为 0/2；失败均来自缺失 WEB-APP-008 公开行为，不是环境或测试夹具问题。
