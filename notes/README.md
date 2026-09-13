# 学习复盘索引

`learning/` 保存每天开始前使用的任务说明，`notes/` 保存完成任务后的知识复盘。

## 已完成

| 学习日 | 主题 | 复盘笔记 |
|---|---|---|
| Day 1 | Python、HTTP、FastAPI、Pydantic、内存 CRUD、pytest | [day-01.md](day-01.md) |
| Day 2 | SQLAlchemy、PostgreSQL、Docker、Session、依赖注入、测试隔离 | [day-02.md](day-02.md) |
| Day 3 | Alembic、结构迁移、revision、upgrade、downgrade、stamp | [day-03.md](day-03.md) |
| Day 4 | 用户注册、Argon2id 密码哈希、用户模型、迁移与接口测试 | [day-04.md](day-04.md) |
| Day 5 | 登录、JWT、Bearer token、当前用户依赖与认证测试 | [day-05.md](day-05.md) |

常用操作集中在[项目命令速查](commands.md)，供使用时查询，不要求逐字背诵。

## 使用方法

不要从头到尾反复抄写或背诵。每次复习按以下顺序：

1. 合上代码，用自己的话复述笔记开头的“主链路”；
2. 回答文末自测题；
3. 只查不会或答错的部分；
4. 回到真实代码寻找证据；
5. 运行测试确认项目仍然工作。

建议节奏：

- 次日：复述主链路，限时 10 分钟；
- 三天后：完成一次自测；
- 七天后：关闭笔记，独立做一个小改动；
- 简历准备阶段：按项目请求链路重新口述。

记忆目标不是背下所有 API，而是：知道组件负责什么、它们怎样连接、遇到问题去哪里检查，并能用测试验证修改。
