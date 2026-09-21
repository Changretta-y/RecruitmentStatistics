# WEB-APP-003 独立复测报告

## 状态

TEST_PASSED

## 环境

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- Vitest：4.1.11
- `npm ci`：成功（仅有依赖树 engine warning）

## 执行命令

```text
nvm use 20.19.0
npm ci
npx vitest run tests/test_web_app_003.spec.ts tests/test_web_app_002.spec.ts tests/test_web_app_001.spec.ts tests/test_token_storage.spec.ts tests/test_web_auth_002.spec.ts tests/test_web_auth_003.spec.ts --reporter=dot
```

## 结果

```text
Test Files  6 passed (6)
Tests       51 passed (51)
Exit code   0
```

WEB-APP-003 专项及 WEB-APP-001/002、WEB-AUTH-001/002/003 回归全部通过。

## WEB-APP-003 覆盖证据

- 新增模式默认字段和完整字段展示；
- 编辑模式回填副本，原始列表行保持不变；
- 六阶段时间设置、修改、清空，ISO 与 `null` 传输；
- 公司/岗位、状态和时间格式校验；
- 提交 loading 与重复提交阻止；
- 新增 POST 语义；
- 编辑 PATCH 只提交变化字段；
- 成功后的关闭、清理和刷新第 1 页事件；
- 失败保留输入并映射后端字段错误；
- 未保存关闭确认。

## 回归说明

WEB-AUTH-003 输出 Vue Router 空路径 warning，但无测试失败、未处理错误或环境阻塞。

本轮未修改 `frontend/src`，仅执行测试并写入本报告。
