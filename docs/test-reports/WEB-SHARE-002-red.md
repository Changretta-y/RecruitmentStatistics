# WEB-SHARE-002 RED_CONFIRMED

- 测试角色：frontend_share_tests，原独立测试 Agent。
- 环境：Windows PowerShell；nvm Node v20.19.0、npm 10.8.2、项目 Playwright Chromium。命令 PATH 先选择 `$env:NVM_HOME\v20.19.0`。
- 修改：仅将现有共享 UI / 真实 E2E 测试中的按钮名称“申请互看”更新为“申请共享”，11 处；没有新增测试、修改其他断言或改变原超时门槛。
- 命令：`cd frontend; npm run test:sharing -- --grep 'initial centered|ID search validates|recommendation sends request'`。
- 通过 / 失败：0 / 3，退出码 1。
- 公开输入：登录后打开共享页的推荐列表，以及精确搜索用户 ID 501。
- 期望：推荐 10 个发送按钮和搜索结果发送按钮的公开名称均为“申请共享”。
- 实际：推荐新名称按钮数为 0；搜索与推荐点击定位也找不到新名称。浏览器失败快照明确显示这些按钮仍为“申请互看”，页面、登录、推荐与 ID 搜索已正常工作。因此失败来自用户要求的新文案尚未实现，非语法、环境或夹具问题。
- 稳定性：推荐数量、推荐点击、搜索点击三个原有用例均观察同一旧文案；没有为低影响文案增加镜像测试。
- 回归：本 RED 阶段不运行旧全量 / 后端；实现后将独立复测现有共享 17 项及必要真实双用户流程。
- 黑盒声明：未读取、搜索、枚举或分析生产实现目录，仅观察公开 UI / HTTP mock 和浏览器输出。

## 交接

- 当前状态：RED_CONFIRMED。
- 接收角色：PM / 原实现 Agent share_implementation。
- 输入：`docs/tasks/WEB-SHARE-002.md`、本报告和更新后的现有测试。
- 实现范围：按任务单只改推荐与 ID 搜索结果按钮文案；测试目录只读。
- 本阶段完成条件：测试先行提交后由实现改标签，READY_FOR_TEST 后交回原测试 Agent 独立复测。禁止推送。
