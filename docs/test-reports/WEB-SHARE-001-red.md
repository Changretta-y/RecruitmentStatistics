# WEB-SHARE-001 RED_CONFIRMED

- 测试角色：frontend_share_tests，独立前端测试 Agent。
- 环境：Windows PowerShell；先执行 `nvm use 20.19.0`，再将 nvm 的 `v20.19.0` 目录置于当前命令 PATH 首位（机器 node 软链仍指向其他版本）；实际 Node v20.19.0、npm 10.8.2、项目 Playwright 1.63.0、Chromium。依赖通过 `npm ci --ignore-scripts` 从现有锁同步；没有修改运行时依赖或锁。锁内 abbrev/nopt 的 engine 警告不影响本次 Playwright 启动。
- 命令：`cd frontend`，`$env:Path = "$env:NVM_HOME\v20.19.0;$env:Path"`，`npm run test:sharing`。
- 通过 / 失败：0 / 14；确认失败均为缺少 `/sharing` 页面标题或侧栏“投递共享”入口；既有登录和浏览器启动成功，无生产组件 import、语法、夹具或环境 RED。
- 稳定复现：以 `npm run test:sharing -- --grep 'entry, direct|initial centered'` 重复两个代表项，仍为 0 / 2。
- 公开输入：模拟既有认证与 SHARE-001 HTTP 契约；含我的 ID、10 名推荐、两个待处理申请、两个 connected 用户、分页共享记录，以及网络失败、迟到响应、解除授权和空记录响应。
- 期望行为：保留共享侧栏且新页面通过所有专项观察；需同意后才能读，解除立即清除可见内容并拒绝后续读取。
- 实际行为：现有应用能登录并进入个人投递列表，但 `/sharing` 无匹配路由，缺少标题/面板；侧栏缺少新入口。14 项测试均止于缺失行为，后续断言待实现复测验证。
- 回归命令：`npm run test:sharing -- --config=tests/playwright.web_nav_002.config.mts`；4 / 0 通过（桌面侧栏收起恢复、直接新增、侧栏返回、窄屏导航）。
- 黑盒声明：未读取、搜索、枚举或分析生产实现目录；仅阅读任务/需求/设计、测试和测试配置，通过真实浏览器与 HTTP mock 观察公开输入输出；没有未知生产文件 import。

## 覆盖的验收标准

1. 从个人投递入口、直接访问和刷新保留侧栏；桌面收起恢复、返回个人列表/日历与窄屏抽屉。
2. 居中宽面板：推荐、换一批、我的 ID、明确双向同意/不共享备注说明、数字 ID 搜索；无效输入不请求、404、搜索失败保留输入并重试。
3. 发出申请成功/失败、禁止重复；收到申请显式接受或拒绝，发出历史分别显示 pending/accepted/rejected/revoked，未通过不读取。
4. 公开面板边界几何：居中位置，选 connected 用户后右上并变窄，返回用户选择恢复宽面板；不检查 CSS 类或实现结构。
5. 只读公司、岗位、六阶段、投递链接、搜索、每页 10/20/50/100 与翻页；不显示编辑/删除/备注；只调用共享 API。
6. 快速用户切换的迟到旧响应不覆盖；切换先清理旧内容；加载、失败重试和空记录反馈。
7. 单方解除经明确确认后移除连接并清空当前记录；收到他方解除导致的 404 清空旧数据并提示“共享已失效”。
8. 8 种本地 avatar 图像呈现且刷新稳定；390px 手机无横向溢出、面板与记录不重叠、减少动画媒体设置。

## 未覆盖风险与后续复测

- `tests/e2e/web_share_001.spec.ts` 已编写真实双用户链路：两个真实注册账户、本人创建记录、无权限 404、UI 发申请/接受、双方互看、备注隔离/原 CRUD 仍拒绝跨用户修改、单方 UI 解除、双方下一次 GET 404、对方 UI 清空及重新申请。依赖后端实现/迁移/本地服务，当前未执行，不纳入以上 RED 数量。
- 独立复测还需重跑专项、导航/日历相关回归、前端完整相关套件、lint/build，以及真实双用户链路；不能用 mock 通过替代服务端授权验证。
- 动画检查目前验证最终公开几何和 reduced-motion 时动画持续时间，不约束内部动画实现方式。

## Agent 交接

- 任务编号：WEB-SHARE-001。
- 当前状态：RED_CONFIRMED。
- 发送角色：前端测试 Agent。
- 接收角色：项目管理 / 原实现 Agent share_implementation。
- 产物：`frontend/tests/test_web_share_001.e2e.spec.ts`、专用 Playwright 配置、`frontend/package.json` 测试 script、真实双用户 e2e 测试及本报告。
- 接收方工作范围：按任务单实现生产页面/导航；测试文件只读。
- 建议命令：`npm run test:sharing`；真实链路 `npm run e2e -- web_share_001.spec.ts`（先运行本地前后端）。
- 本阶段完成条件：测试独立提交早于生产实现；实现完成后交回本测试 Agent 独立复测，不提前设置 TEST_PASSED。
