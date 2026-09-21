# WEB-APP-002 独立复测失败报告

## 状态

TEST_FAILED

## 环境与命令

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- Vitest：4.1.11
- `npm ci`：成功（仅有依赖树 engine warning）
- 专项命令：

  ```text
  npx vitest run tests/test_web_app_002.spec.ts --reporter=dot
  ```

## 选择器问题核查

初始独立复测为 `4 passed / 3 failed`。3 项失败均明确为 jsdom 不支持测试选择器 `:has-text()`，错误为 `Unknown pseudo-class :has-text()`，属于测试工具选择器问题。

已在 `frontend/tests/test_web_app_002.spec.ts` 中将这些定位改为标准 CSS 定位与 Vue Test Utils 的公开按钮文本查找，并补齐测试路由的 `name: "login"` 夹具。未修改 `frontend/src`。

## 修正后结果

```text
Test Files  1 failed (1)
Tests       1 failed | 6 passed (7)
Exit code   1
```

## 真实失败证据

修正选择器和测试夹具后，剩余失败为：

```text
WEB-APP-002 ApplicationsView > sends search, status/stage/time filters and ordering, then resets page on query changes
Expected request to contain: in_progress
Actual latest request: {"page":1,"pageSize":50,"search":"示例","ordering":"-updated_at"}
```

实际 mock API 请求序列为：

```text
[
  {"page":3,"pageSize":50,"search":"","ordering":"-updated_at"},
  {"page":1,"pageSize":50,"search":"示例","ordering":"-updated_at"}
]
```

在标准公开 `select[name="status"]`、`select[name="stage"]`、时间输入和 ordering 控件完成用户交互后，最终请求仍未包含 `in_progress`、`first_interview`、时间范围或 `-first_interview_time`。页码重置为 1 和搜索值传递正常，但组合筛选/排序契约未满足，因此判定为真实实现失败，不是选择器或环境问题。

## 已通过范围

修正后通过的 6 项覆盖：

- 当前 query 请求及公司、岗位、状态、六阶段时间、更新时间展示；
- URL query 初始恢复及浏览器后退恢复；
- 当前用户、退出和新增入口；
- 首次空列表、无结果、网络错误、401 状态及查询保留；
- 并发搜索只接受最新响应；
- 测试运行环境和组件加载。

WEB-AUTH-001/002/003 与 WEB-APP-001 回归因本次用户要求立即收敛，未在该失败轮次继续执行；不得将其标记为通过。

## 结论

`TEST_FAILED`。请将筛选/排序状态提交到列表 API 请求的问题回流实现 Agent。未修改 `frontend/src`。