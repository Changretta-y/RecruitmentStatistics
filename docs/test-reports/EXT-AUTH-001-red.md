# EXT-AUTH-001 RED_CONFIRMED

- 测试角色：share_tests，EXT-AUTH-001唯一测试 Agent。
- 当前阶段：TEST_WRITING → RED_CONFIRMED，交实现角色；本报告不表示认证链路已通过。
- 可写范围：backend/tests、frontend/tests、tests/e2e、docs/test-reports；经PM明确允许本任务测试npm脚本，未改依赖声明/锁文件。
- 环境：Windows PowerShell；nvm Node20.19.0；npm10.8.2；项目Playwright1.63.0；uv0.7.21/Python3.11.13仅用于公开ZIP解包和内容指纹。
- 输入：任务单、设计公开认证/API契约、公开交付归档 `artifacts/recruitment-capture-extension-v0.1.0.zip`。未读取/搜索/枚举 `frontend/src/` 或生产实现目录。
- 新测试：`tests/e2e/ext_auth_001.spec.ts`、`tests/e2e/playwright.ext_auth_001.config.ts`；7项契约测试。
- 合成凭据策略：只在内存生成，隔离HTTP代理stub绝不转发任何请求；拒绝HTTPS CONNECT，浏览器DNS映射至本机。未使用对话真实用户名/密码，未向生产登录/刷新/写记录。

## 有效RED命令与稳定证据

根目录，使用nvm选定20.19.0（执行时将其目录置于Path前）：

```text
npm ci
npm run test:ext-auth -- --grep 'delivery manifest|delivery popup initial|documented repository'
```

两次相同子集均 **0 passed / 3 failed，0环境错误**：

1. 公开Manifest host permission预期 `http://115.190.240.84:5173/*`；实际只有生产8000、127.0.0.1:8000与localhost:8000。
2. 对交付popup.html进行headless浏览器渲染，仅观察其公开初始服务器配置（不模拟MV3接口）：默认select值预期5173，实际8000。Headless Shell正常启动、DOM和选择器正常，稳定断言错误来自缺失目标配置。
3. README公开源码/构建交付说明缺少 `frontend/src/browser-extension/`。测试后续要求归档名、经PM确认的 `npm run build:extension` 入口，以及该入口两次构建ZIP文件集合/每文件内容SHA一致（忽略ZIP时间戳），均不读取生产源码。

Manifest单独额外复现两次，均仅相同host权限失败。三个有效RED没有语法、夹具或环境错误，不依赖内部JavaScript结构或静态源码关键字断言。

## 公网无凭据基线

仅GET `http://115.190.240.84:5173/api/v1/health/`：**200 application/json**。没有请求生产auth/login、refresh、me或applications，不使用真实账户。健康接口正常不能替代插件认证验证。

## 完整MV3认证测试与环境阻塞（不计RED）

`npm run test:ext-auth` 的真实MV3部分计划验证：

- 插件默认origin；有效/无效合成登录成功与失败UI。
- 触发失效Access → refresh → me与applications，所有API观察均为同一5173 origin，受保护请求使用认证头，最终仅写隔离stub。
- 网络503不能显示成功；密码与两个Token不出现在页面或console。

隔离服务按公开平台响应字段实现本机HTTP契约stub。它可以验证请求形状、origin、Token刷新调用和UI行为，**不替代真实Django认证集成**；没有将stub Token当成平台真实JWT有效性证据。

当前4项真实MV3测试在浏览器启动前阻塞：完整Chrome for Testing153.0.8010.12（Playwright chromium1243）Windows报“并行配置不正确”，Playwright `spawn UNKNOWN`。已通过获准的测试脚本 `npm run test:install:chromium`（`playwright install chromium --force`）重新下载完整官方browser/FFmpeg/Headless Shell；首次网络超时后自动重试下载成功，完整浏览器仍同样无法启动。独立headless shell启动成功，因此上方公开popup初始配置RED有效。

完整MV3初次运行5项显示5 failed，其中1项为有效Manifest RED、4项是此环境启动错误；不计为5个需求RED。后续新增公开渲染/构建测试形成最终7项集，未把未执行的认证流程或环境错误宣称通过。测试没有skip/降低断言/延长质量门槛。参考官方扩展运行条件：[Playwright Chromium extension测试](https://playwright.dev/docs/chrome-extensions)，真正MV3需persistent Chromium context，已按该方式配置。

## 验收标准映射与剩余边界

- 默认API/Manifest：公开归档权限与初始服务器配置已有效RED；真实插件请求origin测试已写但受full Chromium环境阻塞。
- Health：仅公开无凭据GET200基线通过。
- 合成登录、刷新、me、applications：隔离proxy测试已写，未真实执行到UI；不能据此宣布认证链路通过。
- 源码恢复/README/重复打包：公开文档和构建出口已有有效RED；后续仅执行公开build命令比较ZIP，不读取src。实际源码目录恢复由有权限的PM/实现角色确认，测试不跨越源码门禁。
- 扩展可加载：真实MV3启动环境待解决；公开Manifest能解析不等同浏览器真实加载通过。
- 机密：测试仅内存生成随机合成凭据，trace/screenshot/video关闭，打印的网络观察仅origin/path/method/认证头存在布尔值，不输出密码/Token；当前尚未进入合成登录UI，最终仍需执行隐私断言。

## Agent交接

- 当前状态：RED_CONFIRMED，依据3项真实公开配置/交付缺失；full Chromium环境缺陷单列风险，未作为RED理由。
- 接收角色：实现 Agent，仅PM指定生产目录及明确授权README/构建/ZIP范围。测试文件只读。
- 输入：本报告、任务单、7项契约测试；PM已确认公开构建入口 `npm run build:extension`。
- 实现完成条件：恢复可维护源码、统一5173 API与权限、补README/build入口并可重复生成指定ZIP，产出实现说明READY_FOR_TEST，随后原测试独立复测。
- 独立复测门槛：必须如实区分公开配置/打包通过与尚未执行的MV3认证；应先排除完整Chromium运行环境阻塞后执行全部7项，不以本报告或stub替代真实加载/认证证据，不能称全绿。
- 未修改生产/真实用户数据；未push；保留无关变更。后端/前端既有全量测试未重跑，不把已有通过替代本次插件行为。
