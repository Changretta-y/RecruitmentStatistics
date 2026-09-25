# WEB-APP-005 RED 确认报告

- 测试角色：测试 Agent
- 状态：`RED_CONFIRMED`
- 环境：Windows；Node.js 20.19.0（`.nvmrc`）；npm 10.8.2；Vitest 4.1.11
- 依赖同步：按环境规范执行 `nvm install 20.19.0`、`nvm use 20.19.0`、`npm ci`；安装成功。npm 对 `abbrev`、`nopt` 的 engine 范围给出 warning，测试在项目要求的 Node.js 20.19.0 下正常运行。
- 新增测试：`frontend/tests/test_web_app_005.spec.ts`
- 黑盒声明：仅依据任务单、CAL-001 第 2 节、APP-008 和 WEB-APP-003 的公开契约编写并运行 UI/API mock 交互测试；未读取或分析 `frontend/src/`。

## RED 复现

执行前均运行 `nvm use 20.19.0`，并确认 `nvm current` 与 `node --version` 均为 `v20.19.0`。

```text
npm run test -- tests/test_web_app_005.spec.ts --reporter=dot
```

连续两次结果一致：`Test Files 1 failed (1)`、`Tests 10 failed (10)`。Vitest 启动、加载组件和执行用例正常；无语法、夹具或环境错误。失败断言均为公开 UI 缺少按阶段命名的分钟时长输入，例如 `aiInterviewDurationMinutes input: expected false to be true`；同一用例通过软断言确认 AI 面、笔试、一面、二面、三面、HR 面六个时长控件均不存在。其他用例同样在请求这些公开控件时失败，未出现对空 DOM 控件操作的异常。

## 覆盖的公开契约

- 六阶段各自有独立时长输入；无开始时间时为空且禁用，设置新开始时间后默认 60 分钟。
- 新增时六阶段时长随阶段时间独立提交；未手工指定的新增时长提交 60。
- 编辑回填六阶段真实自定义值，仅修改开始时间不覆盖已有值。
- 清空阶段时间时同步清空并提交该阶段时长 `null`。
- 非法分钟值（0、负数、1441、小数、非数字）阻止提交并定位错误；服务端字段错误映射及网络失败保留输入。
- 复用既有新增、编辑和未保存更改回归用例。

时长场景测试已写好；由于六个输入控件均未提供，相关用例无法继续到默认值、提交载荷、回填、联动和错误映射断言。这些断言会在控件可交互后直接验证相应行为。

## 既有表单回归

```text
npm run test -- tests/test_web_app_003.spec.ts --reporter=dot
```

结果：`Test Files 1 passed (1)`、`Tests 9 passed (9)`。新增/编辑、阶段时间传输、重复提交保护、字段错误保留和未保存确认的原有公开流程工作正常。

## 结论与交接

确认 RED 原因是 WEB-APP-005 需求行为尚未出现在公开表单中。将任务状态更新为 `RED_CONFIRMED` 后，可交给实现 Agent；实现后建议先运行本报告中的专项命令，再运行 WEB-APP-003 回归命令。

- 通过 / 失败：新专项 `0 / 10`；既有表单回归 `9 / 0`
- 是否稳定复现：是，连续两次专项运行产生相同的缺少时长输入失败
- 未覆盖风险：RED 阶段无法观察尚未存在的时长值提交、回填和字段错误细节；专项用例已对此编写可执行断言。
