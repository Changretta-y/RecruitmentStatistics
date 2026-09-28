# SHARE-001 实现说明

- 状态：READY_FOR_TEST
- 实现角色：share_implementation；测试角色独立。
- 修改范围：`backend/apps/sharing/`、`backend/config/settings.py`、`backend/config/urls.py`，必要相邻修复 `applications/views.py`、`applications/pagination.py`、`calendar_events/views.py`。
- 已实现行为：九类 Bearer 认证 API、随机推荐与精确 ID 搜索、安全公共用户结构、发送/接受/拒绝申请、双方只读连接列表、任何一方单独解除即双向撤销、再申请与最近100条历史、共享投递分页及公司/岗位搜索。共享输出使用只读白名单，不含 user/notes；旧 CRUD 权限不变。每次共享 GET 都重新检查活跃用户与 accepted 关系，不缓存授权。
- 数据库迁移：`sharing/0001_initial` 创建独立头像 profile 和历史申请表；`0002_assign_existing_avatars` 使用历史 User 与批量回填，给已有用户随机持久头像，新用户通过 post_save 分配，公共序列化补缺 profile。8键 `avatar-01`～`avatar-08`，不改变内置User及原auth输出。
- 并发保护：规范化 lower/higher 用户对，数据库校验成员、顺序、合法状态与响应时间；partial unique `sharing_one_live_pair` 使双向pending/accepted最多一条。新申请事务按用户ID顺序锁双方行，最终唯一约束兜底；回应/解除事务锁申请行。拒绝和解除保留旧申请，新申请不覆盖历史。
- 配置变化：`SHARING_RECOMMENDATION_COUNT` 后端环境变量，默认10，整数1～50；非整数及越界在settings导入直接报 ImproperlyConfigured，并有Django check校验override值。配置例：PowerShell `$env:SHARING_RECOMMENDATION_COUNT='10'` 后启动后端；未设使用默认。不新增依赖。
- 必要相邻兼容修复：旧详情越权404补message/details，仍404且保持隔离；共用分页超页原previous_page_number()再次验证越界而500，现空results的previous指向最后有效页；既有calendar OpenAPI参数tuple触发 `TypeError: can only concatenate list (not "tuple") to list`，改list使完整schema生成恢复。
- 环境：Windows；uv0.7.21；Python3.11.13；Django5.2.17；PostgreSQL本地127.0.0.1:5432。`uv python install`、`uv sync --frozen --group test`成功，命令经`uv run --no-sync`。
- 自检结果：专项41例首轮40通过/1失败，超页实现修复后该用例1通过；并发用例通过（pytest teardown提示线程残留连接，非用例错误，独立复测应串行）。`makemigrations --check --dry-run`无变更。完整schema `spectacular --validate`退出0，sharing全部接口与serializer生成，0 warnings；已有notifications3个APIView缺serializer产生16条已有schema提示，未扩大任务修改。
- 迁移证明：新建独立本地数据库 `job_share_acceptance_20260928`，先迁移旧app叶节点，使用迁移历史auth.User写入既有用户，再执行sharing两迁移。既有profile自动回填为有效8键，新User创建即有profile，旧用户读取保持同一头像；均通过。未连接生产数据库。
- 已知限制：头像上传、消息推送不在范围；随机推荐不承诺每次必定不同；停用用户隐藏但历史保留。服务端下一次请求检查解除状态，已完成的前端快照在下次请求时清除。
- 建议复测命令（backend目录，本地测试DATABASE_URL，测试专用SECRET）：`uv sync --frozen --group test`；`uv run --no-sync pytest tests/test_share_001.py --reuse-db --tb=no -q`；APP003～008、AUTH001～004、SEC001、DOC001及CAL001相关回归；不要并行启动后端pytest。
- 测试完整性声明：未修改测试、断言、测试选择规则或质量门槛；自检不代替独立复测。
