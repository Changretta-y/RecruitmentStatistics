# EXT-AUTH-001 TEST_PASSED

- 测试角色：share_tests，原独立测试 Agent；实现提交 `5003606`，RED测试提交 `ff24b87`。
- 输入：任务单、实现说明、RED报告与原7项测试；复测全过程未读取、搜索、枚举 `frontend/src/` 或其他生产实现目录。
- 环境：Windows PowerShell；nvm Node20.19.0、npm10.8.2、项目Playwright1.63.0；已安装Microsoft Edge **154.0.4258.37**；uv0.7.21/Python3.11.13用于公开ZIP处理。
- 结论：原7项契约测试在现有Edge真MV3持久化context中 **7 passed / 0 failed**，11.7秒；公开构建与平台无凭据健康基线通过。**本机HTTP契约stub验证客户端行为，不等同真实Django认证集成或真实生产账号登录成功。**

## 可重复命令

根目录，先按根 `.nvmrc` 使用nvm选20.19.0，并将选定Node目录置于PATH前：

```powershell
nvm use 20.19.0
$env:Path = "$env:NVM_HOME\v20.19.0;$env:Path"
$env:EXT_AUTH_BROWSER_CHANNEL = 'msedge'
npm run test:ext-auth
npm run build:extension
```

Edge执行完整集 **7/7 PASS**，没有skip、更改业务断言或放宽原8000毫秒期望门槛。测试代码新增仅测试用浏览器渠道选择（chromium/chrome/msedge）、去掉默认禁止扩展启动参数，以及异常路径关闭context/清理临时目录的修复。

## 原Chrome for Testing环境与备选浏览器证据

- 原默认CfT运行原7项：**3 passed / 4 failed**；4项在浏览器启动前报 `spawn UNKNOWN`，没有进入合成认证。
- 仅过滤本次CfT路径的本地Windows SideBySide诊断提示153.0.8010.12程序集激活失败。官方完整browser已在RED阶段重新下载成功，缓存中的同版本manifest存在；未修改browser二进制、缓存manifest、Windows运行时或安装其他浏览器。
- PM允许尝试已安装浏览器后：Google Chrome能够启动，但在10秒原worker等待门槛内没有MV3 serviceworker（单项1 failed，属于加载能力限制，不代表认证失败）。初次Chrome失败清理出现资源锁，已修复异常关闭context和仅临时目录重试清理；重跑后准确暴露worker timeout。
- 现成Edge真MV3专项先 **1/1 PASS**，随后原完整7项 **7/7 PASS**。默认CfT问题仍存在，不声称所有浏览器环境可运行。

## 7项公开行为证据

1. 公开ZIP Manifest V3包含精确生产 `http://115.190.240.84:5173/*` 权限。
2. 真MV3扩展成功加载、worker存在，实际popup默认服务器为5173。
3. 对公开popup初始配置单独浏览器渲染，初始server selector也是5173。
4. README公开源码位置/归档名称/`npm run build:extension`入口正确；执行两次公开构建后，ZIP文件集合与各文件SHA均与交付ZIP一致，重复内容无漂移。
5. 无效合成凭据经扩展登录请求到本机stub返回401，保持退出状态并显示失败；请求origin为目标5173。
6. 有效合成凭据登录进入capture视图；使stub拒绝旧Access后reload，扩展实际调用refresh及me，并使用轮换Token继续访问；手动输入合成公司/岗位，经preview/confirm发出应用GET与POST成功。观察到 `/api/v1/auth/login/`、`/api/v1/auth/refresh/`、`/api/v1/auth/me/`、`/api/v1/applications/`，所有API origin均5173，无旧8000请求。页面可见文字/console没有输出合成密码、Access或Refresh Token。
7. stub模拟503，扩展显示错误且不误报登录成功。

这些是实际执行公开交付扩展的UI、MV3 worker与网络观察，未依据源码内部函数或静态JavaScript字符串塑造断言。

## 构建与归档

单独 `npm run build:extension` 再执行退出0，报告生成6个运行文件。公开ZIP reader可打开，文件集合：

```text
core.js
manifest.json
popup.css
popup.html
popup.js
service-worker.js
```

归档SHA256：`88253F0ED5AD02B81906AE3A66FA5035C66D4C82C55A9824A4037758BC4B9A9E`，与实现交付相同；无README/缓存/测试目录。Manifest permissions三个origin分别为生产5173、127.0.0.1:5173、localhost:5173。

测试直接执行公开构建入口而不读取源目录；源码恢复位置和归档逐项源文件对应关系由PM/实现角色证据确认，不假称测试越过源码门禁。

## 生产边界与未覆盖风险

- 线上只执行无凭据 `GET http://115.190.240.84:5173/api/v1/health/`：**200 application/json**；没有请求生产login/refresh/me/apps，不使用用户在对话给出的真实凭据。
- 认证测试所有HTTP在本机代理stub结束，完全不转发，HTTPS CONNECT关闭，DNS映射至本机；只生成合成凭据。Token为符合响应形状的合成值，stub只证明扩展请求/Token轮换使用/UI状态，不证明Django密码验证/JWT签名/生产CORS或用户授权。
- 合成状态仅在测试服务内存和隔离浏览器临时profile中使用，成功与异常context均关闭；每个临时目录校验路径后清理。trace/screenshot/video关闭，网络日志只含origin/path/method/认证头存在布尔值，不打印秘密，不写交付源码或ZIP。
- 未运行真实平台Django与扩展联调；未测试真实页面采集功能或生产发布，本任务未修改采集业务。既有认证API公开契约作为stub依据，未将健康200替代认证集成证据。
- 默认CfT153和已安装Google Chrome的环境/扩展加载限制如上；Edge覆盖已实际执行，但不宣称Chrome/所有系统均通过。
- 未改生产实现、依赖版本/锁或用户数据；无关未提交变更保留；测试修复/本报告定点本地提交，不push、不部署。

## Agent交接

- 当前状态：TEST_PASSED（上述客户端公开契约与构建范围）。
- 接收角色：项目管理，按任务单验收源码交付与公开扩展行为，再决定DONE。
- 已交付：RED报告、7项先行测试、实现说明、可重复ZIP、原测试独立7/7报告。默认CfT与Django集成未覆盖边界必须在验收中保留。
