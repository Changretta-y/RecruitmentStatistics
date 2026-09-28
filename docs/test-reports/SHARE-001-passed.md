# SHARE-001 TEST_PASSED（任务范围）

- 测试角色：share_tests（原独立测试 Agent），只负责后端。
- 实现：`4238383`；测试先行提交 `eb99d7e`；实现说明 `docs/implementation-notes/SHARE-001.md`。
- 环境：Windows PowerShell；Python 3.11.13；uv 0.7.21；本地 PostgreSQL 127.0.0.1:5432；依赖 `uv sync --frozen --group test`；执行均 `uv run --no-sync`，测试专属至少32字符SECRET及本地测试DATABASE_URL；数据库测试串行且使用 `--reuse-db`。
- 黑盒声明：未读取、搜索、枚举或分析生产实现。观察公开HTTP、公开schema、管理命令、公开文档和公开User测试夹具；未修改生产或降低测试断言。

## 结论与准确边界

共享专项 **41/41通过**；必要联合回归 **186通过、1个任务前已存在的公共文档占位文本误报**。任务相关行为、认证、权限、隔离、分页、日历与schema契约均通过。按照项目管理对既有占位误报的核对裁决，设置任务范围 `TEST_PASSED`；联合测试命令的实际退出码仍为1，本报告不声称全量全绿，不修改或跳过该既有安全断言。

## 命令与结果

工作目录 `G:/job/backend`：

```text
uv run --no-sync pytest tests/test_share_001.py --reuse-db --tb=no -q
```

**41 passed / 0 failed / 0 errors**，85.61秒，无warnings。

```text
uv run --no-sync pytest tests/test_app_003.py tests/test_app_004.py tests/test_app_005.py tests/test_app_006.py tests/test_app_007.py tests/test_app_008.py tests/test_auth_001.py tests/test_auth_002.py tests/test_auth_003.py tests/test_auth_004.py tests/test_sec_001.py tests/docs/test_doc_001.py tests/test_cal_002.py --reuse-db --tb=no -q
```

**186 passed / 1 failed / 0 errors**，225.12秒。唯一失败 `test_public_docs_do_not_contain_real_credentials_or_production_addresses`；所有APP003～008、AUTH001～004、SEC001、CAL002及DOC001其他用例通过。

## 唯一既有误报的证据

- 失败单独稳定复现：DOC001该用例 **1 failed**，0.08秒；保留原始诊断于 `SHARE-001-test-failed.md`。
- 规则2命中 `README.md:95` 和 `docs/requirements/CAL-001.md:56`；PM确认前者为数据库密码占位提示，后者为验证URL的 `token=...` 占位示例及说明，无真实凭据。
- 独立 `git show 4ee597a:README.md` 与 `git show 4ee597a:docs/requirements/CAL-001.md` 同规则检查，任务前版本分别在95/56行命中；匹配位置与数量和当前一致。
- `git diff --name-only 4ee597a -- README.md docs/requirements/CAL-001.md` 无输出；这两个文档本任务完全未变。
- 另两条数据库连接URL和生产地址规则无命中。未向报告复制任何潜在凭据，未放宽既有断言；后续独立文档/测试修复由项目管理另行处理。

## 覆盖验收标准

- 九类接口Bearer边界、非法ID/输入校验、安全公共用户字段、自身/停用/不存在隐藏、第三方隔离。
- 8种有效头像、新注册及既有用户、重复访问稳定、me/搜索/申请一致；原注册输出安全字段不变。
- 默认10人与1/3/50配置、非法环境配置拒绝启动、去重、本人/停用/双向待处理/共享排除、不足与空推荐。
- 显式申请/接收方通过或拒绝、双方历史、伪造字段不授权、重复/反向/真实双线程并发冲突、最近100条历史倒序、拒绝再申请。
- 接受后双方只读，投递链接、六阶段时间/时长、公司/岗位/状态及时间字段符合既有输出去掉user/notes；备注不泄漏。第三方无关系/读取/解除权限。
- 共享后原本人CRUD的GET/PATCH/DELETE和user查询继续隔离，共享端点非GET拒绝修改。
- 发起人和接收人分别单方解除，立即双方下一次请求404、关系清空、历史revoked、再次申请合法但未自动授权。
- 停用已共享用户不可见/不可读；20默认与10/20/50/100分页、公司/岗位搜索、稳定倒序、超页200空、非法分页400；原分页和日历相邻兼容修复回归通过。

## 公共schema与已知局限

独立公共 `uv run --no-sync python manage.py spectacular --format openapi-json --file <临时文件> --validate` 退出 **0**；解析确认共享8条路径9种操作完整。DOC001 schema行为测试通过；完整schema仍报告 **Warnings0，Errors16（3 unique）**，实现说明归因既有通知三个接口缺serializer。生成退出0不表示全项目schema没有这些已有不足。

- 新旧用户迁移的隔离数据库证据来自实现说明；专项验证通过公开User fixture模拟旧用户，不读取内部迁移。
- 随机行为不要求换一批必然变化，不做小样本概率分布断言。
- 页面与真实浏览器端整体流程由前端原测试 Agent独立提供，后端报告不代替WEB-SHARE-001验收。
- 未运行生产部署；完整项目所有测试未宣称全部通过。

## Agent 交接

- 任务编号：SHARE-001；任务范围状态：TEST_PASSED。
- 接收角色：项目管理，按任务单逐项验收后才可设置DONE。
- 交付物：RED报告、测试提交、实现说明、独立本报告与既有误报诊断证据齐全。
- PM验收应明确记录既有DOC001占位误报及notification schema局限，不混淆为本次共享行为失败或全量全绿。
