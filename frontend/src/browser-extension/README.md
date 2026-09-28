# 我的投递采集助手

Chrome / Microsoft Edge Manifest V3 扩展。用户主动打开扩展后，它会从当前普通 HTTP(S) 网申页面提取公司、岗位和页面 URL，允许人工修正或从页面点选文字，并在明确确认后写入当前登录的平台账号。

## 本地加载

1. 打开 Chrome 的 `chrome://extensions/` 或 Edge 的 `edge://extensions/`。
2. 开启“开发者模式”。
3. 选择“加载已解压的扩展”，目录选择 `frontend/src/browser-extension/`。
4. 打开一个网申页面，点击工具栏中的“我的投递采集助手”。

扩展默认连接平台入口 `http://115.190.240.84:5173`，认证与投递记录请求均通过该 origin 下的 `/api/v1/` 反向代理。开发时也可选择 `http://127.0.0.1:5173` 或 `http://localhost:5173`。

从仓库根目录执行 `npm run build:extension`，可从 `frontend/src/browser-extension/` 生成 `artifacts/recruitment-capture-extension-v0.1.0.zip`。ZIP 仅包含浏览器加载所需文件。

## 权限说明

- `activeTab`：只在用户点击扩展时访问当前标签页。
- `scripting`：按需执行页面提取或单字段点选，不常驻网页。
- `storage`：保存扩展自己的 JWT、账号最少信息和同页点选草稿。

扩展不申请浏览历史权限，不注册覆盖所有网页的常驻 content script，也不会把 JWT 发送给网页脚本。
