# WEB-AUTH-004 实现说明

- 状态：`READY_FOR_TEST`
- 修改范围：`frontend/src/views/LoginView.vue`、`frontend/src/views/RegisterView.vue`
- 已实现行为：登录与注册页统一使用 `width: 100%`、`max-width: 560px` 的认证卡片；页面根容器显式保留左右各 `16px` 间距，使认证卡片在窄屏随可用宽度收缩；注册页新增可聚焦的“返回登录”路由链接，激活后导航至 `/login`，且链接位于注册表单外，不会提交表单或调用注册 API；既有注册成功后跳转登录页的逻辑保持不变。
- 数据库迁移：无。
- 配置变化：无。
- 已知限制：当前环境未提供 `nvm` 命令，但实际 Node.js `v20.19.0` 与 `.nvmrc`、`package.json` 一致，npm 为 `10.8.2`。`npm ci` 对传递依赖 `abbrev@5.0.0`、`nopt@10.0.1` 给出 Node 引擎警告，但依赖同步成功。Vitest 通过公开 DOM 样式契约验证窄屏布局，真实浏览器像素测量仍由独立复测按需补充。生产构建成功，但 Vite 提示当前 CommonJS 上下文加载含 ESM 语法的配置文件在未来原生配置加载器中可能不受支持；该既有警告不属于本任务范围。
- 自检结果：`npm ci` 成功；`npm run test -- tests/test_web_auth_004.spec.ts tests/test_web_auth_003.spec.ts --reporter=verbose` 通过（2 个测试文件，10 项测试全部通过）；`npm run lint` 通过；`npm run build` 通过（344 个模块完成转换）。测试输出中的空路径 Vue Router 警告为既有测试路由提示，不影响通过结果。
- 建议复测命令：`npm run test -- tests/test_web_auth_004.spec.ts tests/test_web_auth_003.spec.ts --reporter=verbose`；`npm run lint`；`npm run build`。
- 测试完整性声明：未修改测试、断言或质量门槛。

