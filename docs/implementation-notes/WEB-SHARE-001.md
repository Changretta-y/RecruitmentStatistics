# WEB-SHARE-001 实现说明

- 状态：READY_FOR_TEST
- 实现角色：share_implementation；测试由frontend_share_tests独立负责。
- 修改范围：`frontend/src/api/sharing.ts`、`types/sharing.ts`、`views/SharingView.vue`、`components/SharingAvatar.vue`、`SharingUserRow.vue`，既有 `AppShell.vue` 和 `router/index.ts`。
- 已实现行为：认证守卫内`/sharing`路由和主侧栏“投递共享”入口，直接打开/刷新/导航统一复用AppShell；我的ID、默认头像、推荐/换一批、数字ID搜索、发送申请、显式同意/拒绝、双方申请历史、共享用户选择、只读分页记录与公司/岗位搜索、单方解除确认及双向失效提示。
- 浮窗：主内容区初始居中宽面板760px，选人后420ms平滑移动到右上并缩为330px，记录预留右侧空间。面板自身可滚动、选人后持续处理申请及切换用户。1100px以下改为正常文流上方布局，390px不溢出/不盖记录，尊重prefers-reduced-motion取消动画。
- 可访问语义：共享用户面板/共享投递记录region、语义ul/li、connected用户名选择button、用户ID与记录搜索label、每页原生select及确认dialog。键盘焦点可见。
- 安全与异步：仅connected用户触发共享API；只读卡片含公司岗位状态当前阶段投递链接/时间、六阶段时间/分钟、创建更新时间，不呈现notes或CRUD控件；链接只允许http/https。切人/搜索/页码刷新先清旧内容，请求序号丢弃迟到响应，404立即清选人及记录；共享名单刷新不含selected时也清理。变更按钮发送中禁用，冲突刷新服务端状态。用户ID搜索失败保留输入、非法输入不发请求并使旧响应失效。
- 默认头像：8组本地内联SVG图形/颜色对应avatar-01～08，role=img及用户名可访问说明，无远端服务，持久键决定稳定视觉。
- 数据库迁移：依赖SHARE-001两步迁移，无前端额外迁移。
- 配置变化：无需新运行时依赖；继续统一Axios Bearer/refresh客户端。真实验收Vite配置 `VITE_API_PROXY_TARGET=http://127.0.0.1:8000`。
- 环境：Windows；nvm use20.19.0并将nvm版本目录置PATH首位；实测Node v20.19.0、npm10.8.2。前端依赖此前已由测试Agent从锁npm ci同步，本实现不改依赖/锁/测试配置。
- 自检结果：14专项初轮12通过，2搜索控件角色超时（native searchbox），改公开textbox后两失败项重跑2通过。`npm run lint`通过；`npm run build`通过。早期CSS拼写在build自检中定位并修复。既有Vite configLoader native警告不影响构建。自检不能替代独立复测。
- 本地真实验收服务：frontend `http://127.0.0.1:5173`（session6116）代理backend `127.0.0.1:8000`（session45850/PID30532）。严格隔离DB `job_share_acceptance_20260928`及测试SECRET，只本地监听，无部署、推送或生产数据库连接。
- 已知限制：没有推送或轮询；对方解除在下次记录请求或刷新共享名单时清除现有快照。头像上传、聊天、替他人编辑不在范围。
- 建议复测命令：frontend `npm run test:sharing`；既有导航/日历专项、`npm run test`、`npm run lint`、`npm run build`。本地前后端已启动，可根目录`npm run e2e -- web_share_001.spec.ts`验证真实两用户链路。
- 测试完整性声明：未修改测试、断言、配置、质量门槛或选择规则。所有测试为只读；READY_FOR_TEST后由原独立测试Agent复测。
