# WEB-SHARE-001 TEST_PASSED

- 状态：TEST_PASSED（本任务范围）；完整前端 Vitest 未全绿，详见下方已知风险。
- 测试角色：frontend_share_tests，原独立前端测试 Agent。
- 生产交接：`a151234`；原测试先行 / RED 提交：`6e3ae06`。
- 环境：Windows PowerShell、nvm Node v20.19.0、npm 10.8.2、项目 Playwright Chromium / Vitest 4.1.11。每条 Node 命令先设置 `$env:Path = "$env:NVM_HOME\v20.19.0;$env:Path"`，不使用系统当前其他 Node 版本。
- 黑盒声明：未读取、搜索、枚举或分析 `frontend/src/`、`backend/apps/` 或生产配置；仅观察浏览器公开语义、几何、HTTP mock 和真实 API 输入输出。生产报错调用栈未用于源码调查。
- 测试完整性：未修改原断言、超时或质量门槛。增加 3 项契约边界验证；当前实现直接满足，未虚构额外 RED。

## 独立复测结果

| 范围 | 命令 | 通过 / 失败 |
|---|---|---:|
| 共享专项，最终完整集 | `cd frontend; npm run test:sharing` | 17 / 0 |
| 真实双用户端到端 | 根目录 `npm run e2e -- web_share_001.spec.ts` | 1 / 0 |
| 既有共享侧栏 / 日历入口 | `npm run test:sharing -- --config=tests/playwright.web_nav_001.config.mts` | 2 / 0 |
| 收起 / 新增页 / 窄屏侧栏 | `npm run test:sharing -- --config=tests/playwright.web_nav_002.config.mts` | 4 / 0 |
| 日历组件 | `npm run test -- tests/test_web_cal_001.spec.ts` | 11 / 0 |
| 类型检查 | `npm run lint` | 退出码 0 |
| 生产构建 | `npm run build` | 退出码 0 |

本任务专项、真实链路及规定相邻回归合计 **35 / 0**。原 14 项专项首轮独立运行也全部通过；新增的 3 项单独运行 3 / 0，最终将 17 项一起重跑 17 / 0（38.6 秒）。真实双用户流程 1 / 0（16.9 秒）。构建成功转换 371 modules；Vite / Vue Router 的配置、弃用 warning 未导致这些任务检查失败。

## 公开输入与验收证据

1. 从个人列表侧栏进入、直接 `/sharing` 和刷新均保留主侧栏；桌面收起 / 展开有效，可返回“我的投递进度”及“日历”；390px 窄屏抽屉有效。
2. 未选用户时宽面板居中；展示我的 ID、头像、10 位推荐、“换一批”、ID 搜索、收到 / 发出申请及已共享用户；明确双方同意后互看和个人备注不共享。
3. 非法 ID 不请求，搜索 404 显示“未找到用户”，搜索失败保留输入并可重试；发申请失败可重试，成功待处理；收到申请显式同意或拒绝；历史显示 pending / accepted / rejected / revoked。
4. 选择 connected 用户后，面板公开边界移至主内容区右上方且宽度缩小；返回用户选择恢复较宽居中面板。未通过申请不读取对方记录。
5. 只读记录显示公司、岗位、六阶段及投递链接；每页 10 / 20 / 50 / 100、翻页和公司 / 岗位搜索使用共享接口；没有编辑、删除或备注内容。
6. 快速切换用户先清理旧数据，旧用户迟到响应无法覆盖当前用户；新增同一用户连续搜索的迟到响应测试，也不能覆盖新搜索结果。加载、空列表和网络重试反馈通过。
7. 单方解除有明确确认，成功移除连接并清空当前记录；他方解除后下一次记录查询 404，显示“共享已失效”并清空旧内容。
8. 8 种本地图形头像均呈现且刷新稳定，无远程头像依赖；手机面板与记录不重叠、无横向溢出；减少动画媒体偏好下动画时长符合紧凑要求。
9. 补充关系 / 冲突边界：pending / connected 搜索结果没有再次申请按钮；409 冲突重新 GET 申请状态并禁止再申请；提交中按钮禁用，实际仅一次 POST。

## 真实双用户授权链路

- 使用已交接的本地前端 `http://127.0.0.1:5173` → 后端 `http://127.0.0.1:8000`；专用数据库 `job_share_acceptance_20260928`，不是生产数据库。
- 通过公开注册 / 登录创建 A、B 两个独立账户；各自通过本人 API 创建带秘密备注的投递记录。浏览器使用两个独立 context。
- 同意前双方共享 GET 均为 404；A 用 UI 按 B 的 ID 搜索并申请，待处理仍 404；B 在 UI 显式同意后，双方各自可在 UI 选择对方，显示对方公司 / 岗位记录。
- 双方只读 UI 均无编辑 / 删除，秘密备注未出现；A 使用原本人 CRUD PATCH B 的记录仍得到 404，原权限隔离没有扩大。
- A 在 UI 单方确认解除后自身面板清空；双方下一次真实共享 GET 均为 404；B 再次 UI 搜索触发失效提示并清空旧记录，不需 B 同意解除；A 重新 POST 申请得到 201。
- 测试在 `finally` 关闭两套浏览器 context，Playwright 进程已结束。测试账户 / 记录仅保留于专用本地验收库以供 PM 后续验收；没有向生产写入账户、记录或浏览器会话。服务和数据库的最终回收由启动它们的角色 / PM 协调。

## 全量前端测试与未覆盖风险

测试配置已添加 `exclude: [...configDefaults.exclude, "**/*.e2e.spec.ts"]`：仅将本来属于 Playwright 的浏览器用例从 Vitest 错误收集里分离。NAV-001 / NAV-002 / WEB-SHARE-001 的对应 Playwright 套件全部独立通过；没有排除任何失败单元测试。

保留 5 秒原超时门槛，以 `npm run test -- --maxWorkers=1 --reporter=json --outputFile=../test-results/web-share-vitest.json` 执行全量，再重复一次（输出到 `web-share-vitest-rerun.json`）。两次均 **86 / 90，通过 8 个文件、失败 3 个文件**，并非全量通过：

- WEB-APP-002 后退 / 前进后搜索框仍“新查询”，预期“示例”；退出后路由仍 `/applications`，预期 `/login`。
- WEB-APP-004 重置筛选后 URL `query.search` 仍“无结果”，预期删除搜索参数。
- WEB-AUTH-002 第一次恢复用户 / 初始化案例在完整集约 5,015～5,019ms 失败。认证定向一次 **9 / 9**，再次定向 **8 / 9**（同首项约 5,014ms），因此不能宣称该项稳定通过。

前三个列表行为此前已记录于 `docs/test-reports/WEB-APP-005-passed.md` 和 `docs/acceptance/WEB-MAIL-001.md`；WEB-MAIL-001 验收也记录过相同认证初始化案例在全量中超时、定向通过。本次实际认证定向结果已精确保留，未把过往的定向通过替代当前结果。初次完整输出明确报告默认 5,000ms 超时，JSON 后续仅显示 `STACK_TRACE_ERROR` 与约 5 秒时长；这属于已观察到的测试不稳定风险，**未进行生产因果或性能归因**。

这些全量问题提交 PM 按既有任务 / 测试稳定性跟进；本次不扩大生产实现范围，也不延长原超时、删除失败用例或降低断言。跨浏览器 Firefox / WebKit、真实多人并发 UI 与更大字体未覆盖；后端完整授权 / 并发约束证据由 SHARE-001 独立测试报告负责。动画验证使用最终位置 / 尺寸和 reduced-motion 持续时间，不绑定内部动画结构。

## Agent 交接

- 任务编号：WEB-SHARE-001。
- 当前状态：TEST_PASSED（范围内）。
- 发送角色：原前端测试 Agent。
- 接收角色：项目管理 Agent。
- 已完成产物：原 RED、17 项公开 UI 测试、真实双用户 E2E、浏览器 / 单元运行器分离配置与本独立通过报告。
- 验收建议：按任务单复核宽面板 / 右上窄面板视觉、侧栏保持及真实解除行为；验收记录明确保留全量 86 / 90 与认证不稳定风险。
- 完成门禁：仅项目管理 Agent 可在验收及交付物齐全后设置 DONE。

## 交付截图补充

- 复用原已通过的几何测试保存两张公开 UI PNG：`docs/test-reports/WEB-SHARE-001-centered.png`（未选用户居中宽面板）、`docs/test-reports/WEB-SHARE-001-selected.png`（已选用户、右上窄面板、只读记录）。两张均由既有 HTTP mock 数据生成，不含密码或 Token；已打开图片视觉检查。
- 截图时发现测试夹具时长键缺少 `_minutes`，与 APP-008 公开 `*_duration_minutes` 契约不一致；仅修正六个自有夹具键并添加 30 / 45 / 60 分钟可见断言。生产实现未改动，PM 真实 75 分钟记录验收已通过，未将夹具错误归因为生产问题或伪造 RED。
- 仅复跑 `npm run test:sharing -- --grep 'selecting user animates|record display is read only'`，**2 / 0** 通过；重新生成的选中截图正确显示三个阶段时长。未重复全量或改变任何既有失败 / 超时门槛，原任务验收状态保持。
