# WEB-APP-009 项目 Logo 与网页图标

- 状态：`TEST_WRITING`
- 角色：项目管理=主 Agent；独立测试=release_tests；独立实现=company_implementation。
- 用户价值：项目在浏览器标签页、侧栏和内部品牌区域使用统一的项目 Logo，形成一致识别。
- 资源来源：用户本次附件 `codex-clipboard-4ff5e87c-fa2d-4382-83b7-c83163af7ef5.png`；SHA-256 `9C0420FD9643705BD36A1C9E8E5C4D80B5FE100EA5B22492BB1301ABBA610403`。实现角色可从 `C:\Users\Yinchengyu\AppData\Local\Temp\codex-clipboard-4ff5e87c-fa2d-4382-83b7-c83163af7ef5.png` 读取后复制到项目资源目录。
- 范围：Logo 静态资源、网页 favicon、AppShell 品牌区域和前端构建产物。
- 非范围：重新绘制图片、后端接口、手机端专门适配、浏览器扩展品牌重构。
- 允许修改范围：项目管理仅 `docs/requirements/`、`docs/tasks/`、`docs/acceptance/`；测试仅 `frontend/tests/`、`docs/test-reports/`；实现仅 `frontend/src/`、`frontend/public/`、`frontend/index.html`（如存在）和 `docs/implementation-notes/`。

## UI 契约

- 用户提供的图片保存为项目 Logo 静态资源，前端构建后可通过公开 URL 加载。
- `frontend/index.html` 的 favicon 指向该 Logo 资源；浏览器标签页不再使用缺省图标。
- AppShell 侧栏品牌区域显示该 Logo 图片，并提供可访问的替代文本/名称；项目名称继续显示。
- 内部主品牌标识使用 Logo 图片，不以单独的 briefcase 图标代替；导航功能图标可以继续保留。
- Logo 资源在开发服务器和生产构建产物中均可访问；不新增运行时依赖。

## 验收标准

- [ ] Logo 资源存在、格式可被浏览器加载，构建后路径稳定。
- [ ] favicon 链接存在并指向 Logo 资源。
- [ ] AppShell 品牌区显示 Logo 和项目名称，Logo 有可访问替代文本。
- [ ] 现有登录、导航、列表和构建回归不受影响。

## Agent 交接

- 测试角色先通过公开文件、DOM 和构建行为确认 RED，再交实现角色。
- 实现角色不得修改测试；测试角色不得读取生产实现目录。
- 不覆盖工作区中与本任务无关的 WEB-APP-008 未提交改动。
