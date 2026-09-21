# WEB-APP-001 RED 测试报告

## 状态

RED_CONFIRMED

## 环境与命令

- 工作目录：`G:\job\frontend`
- Node：20.19.0
- npm：10.8.2
- 测试框架：Vitest 4.1.11
- 依赖安装：`npm ci` 成功
- 执行命令：

  ```text
  npx vitest run tests/test_web_app_001.spec.ts --reporter=dot
  ```

## 结果

```text
Test Files  1 failed (1)
Tests       12 failed (12)
```

Vitest 正常启动、收集并执行测试，未发生依赖安装、运行时或语法错误。

失败证据：

- API 测试无法加载公开 applications API 模块：`Cannot find module '/src/api/applications'`。
- query 状态测试未发现公开的 application query parse/serialize 模块：`No public application query parse/serialize module was found`。

因此失败来自 WEB-APP-001 所要求的公开 API/query 行为模块缺失，而非测试夹具、命令或环境故障。

## 覆盖范围

新增 `frontend/tests/test_web_app_001.spec.ts`，覆盖：

- JobApplication 分页响应的 snake_case 到 camelCase 转换；
- null 与 ISO 时间值无损保留；
- API 错误类型/details 可观察；
- query 默认值、pageSize 白名单及非法值回退；
- query 对象与 URL 参数双向转换；
- 空筛选不发送；
- ordering 的 `-` 保留；
- PATCH 字段转换及 null 传递；
- API 通过统一 HTTP 层调用。

本阶段未修改 `frontend/src` 生产实现。
