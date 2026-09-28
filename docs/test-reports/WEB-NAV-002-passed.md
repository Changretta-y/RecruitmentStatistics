# WEB-NAV-002 TEST_PASSED

- 测试角色：测试 Agent（独立复测）
- 状态：`TEST_PASSED`
- 工作目录：`G:\job\frontend`
- 环境：Windows；Node.js `20.19.0`（`.nvmrc`）；npm `10.8.2`；Playwright UI tests 使用项目依赖；Vitest `4.1.11`。
- 黑盒声明：根据任务单通过浏览器可访问控件、URL、表单内容和模拟公开 API 验证；未读取、搜索或枚举 `frontend/src/`。

## WEB-NAV-002 专项

命令：

```text
npx playwright test --config=tests/playwright.web_nav_002.config.mts
```

最终结果：`4 passed / 0 failed`，退出码 `0`，命令墙钟 `9.990` 秒。

覆盖证据：

- 投递列表显示“收起侧边栏”；收起后侧栏入口隐藏而投递标题仍可见；激活“展开侧边栏”后导航恢复。
- 直接打开 `/applications/new` 时路由、表单与共享侧栏导航均可见；从侧栏投递入口返回 `/applications`。
- 从投递列表的新增入口进入 `/applications/new` 时表单与共享侧栏导航均可见；侧栏投递入口返回投递列表。
- 将浏览器视口设为窄屏尺寸后，“打开导航”按钮可打开导航抽屉；日历入口可以打开日历页，日历内容正常显示。

## 相邻回归

| 测试范围 | 命令 | 结果 | 墙钟 |
|---|---|---:|---:|
| WEB-NAV-001 导航回归 | `npx playwright test --config=tests/playwright.web_nav_001.config.mts` | 2 passed / 0 failed | 7.668 秒 |
| WEB-CAL-001 日历回归 | `npm run test -- tests/test_web_cal_001.spec.ts --reporter=dot --maxWorkers=1` | 11 passed / 0 failed | 8.862 秒 |

## 时间账本（UTC）

| 阶段 / 命令 | 开始 | 结束 | 墙钟 | 显式等待 | 主动处理 |
|---|---|---|---:|---:|---:|
| 独立复测总计 | 2026-09-28 02:41:14 | 2026-09-28 02:45:04 | 3分50秒 | 0秒 | 3分50秒（总墙钟减显式等待；含命令执行和报告整理，不代表内部思考时长） |
| `nvm use 20.19.0` 及版本确认 | — | — | 2.410秒 | 0秒 | — |
| WEB-NAV-002 首轮 3 项专项 | — | — | 8.602秒 | 0秒 | — |
| WEB-NAV-001 导航回归 | — | — | 7.668秒 | 0秒 | — |
| WEB-CAL-001 日历回归 | — | — | 8.862秒 | 0秒 | — |
| WEB-NAV-002 最终 4 项专项（含窄屏抽屉） | — | — | 9.990秒 | 0秒 | — |

- 命令墙钟合计 `37.532` 秒；命令串行运行，没有并行重叠。
- 本阶段未使用 sleep 或人工轮询。最后一次进程输出检查即时返回，计入 `0` 秒显式等待。
- 其余时间用于按要求重读任务/测试/环境规范、核对运行时、补充窄屏公开行为覆盖和整理报告。阶段实际处理子区间无法精确计量；报告按总墙钟减显式等待列示，不宣称为内部思考时长。
- Playwright/Vite 和 Vue Router 输出了已有配置或弃用 warning；所有测试进程正常结束，warning 未导致失败。

## 结论

WEB-NAV-002 专项、WEB-NAV-001 导航回归及 WEB-CAL-001 日历回归全部通过，共 `17 passed / 0 failed`。独立复测状态为 `TEST_PASSED`，提交项目管理 Agent 验收。
