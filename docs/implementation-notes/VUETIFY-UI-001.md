# VUETIFY-UI-001 Vuetify 3 前端 UI 迁移实现说明

## 角色与范围

- 角色：功能实现 Agent
- 工作区：G:\job
- 修改范围：frontend/src/、frontend/package.json、frontend/package-lock.json、本说明
- 未修改测试目录、后端目录或任务/验收文档

## 实现内容

- 增加 Vuetify 3.9.0 与 @mdi/font 7.4.47，并更新 npm lockfile。
- 新增 src/plugins/vuetify.ts，配置校园招聘主题色、Material Design Icons、默认控件密度/圆角和语义色。
- App.vue 使用 VApp/VMain，main.ts 安装 Pinia、Router、Vuetify 并加载全局主题样式。
- 登录/注册页重构为 VContainer、VCard、VTextField、VAlert、VBtn，保留公开 name、autocomplete、按钮文案、校验、错误映射和路由跳转。
- ApplicationsView.vue 重构为 VAppBar、VNavigationDrawer、VContainer、VCard、VTextField、VSelect、VBtn、VTable、VChip、VAlert、VDialog 等组件；保留查询 URL 同步、分页、排序、加载/空结果/401/网络错误、删除回退和重试行为。
- ApplicationForm.vue 重构为 Vuetify 字段与卡片布局，保留字段名、ISO 时间转换、null 清空、创建/编辑 PATCH 差异提交、后端字段错误、提交 loading 和未保存关闭确认。
- ApplicationFormView.vue 增加统一的 Vuetify 加载和错误状态卡片。
- 增加响应式网格、窄屏表格横向滚动、统一校园招聘视觉主题和键盘/屏幕阅读器标签。

## 验证

环境：

- nvm Node.js：20.19.0
- npm：10.8.2

通过：

- npm run lint
- npm run build

说明：

- npm install vuetify@^3.9.0 @mdi/font@^7.4.47 --save 成功并写入 lockfile。
- npm ci 复核时被 Windows 正在占用的 @rolldown 原生 .node 文件阻塞（EPERM）；未改动源码。
- 现有 Vitest UI 测试在导入 Vuetify 组件时被当前 environment=node 配置的 .css 导入处理阻塞，未进入业务断言；未修改测试目录或测试配置。
- Vite 构建仅输出现有的 configLoader ESM warning，构建结果成功。
