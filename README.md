# Backend Engineering Lab

这是三周 Python 后端工程训练的独立仓库。第一周使用通用 `User / Item` 场景建立最小工程闭环；第七天完成独立验收后，再确定最终业务题材。

## 学习约定

- 核心功能先由学习者独立实现，AI负责概念讲解、代码审查、测试建议和排错提示。
- 每个功能以“能运行、能测试、能解释、能独立重写”为完成标准。
- 不复制完整项目模板，不提前加入 Redis、消息队列、微服务或 AI 功能。
- 每个学习日产生一个清楚、真实的 Git 提交。

## 当前阶段

Day 1 已完成：解释器、虚拟环境、包与模块、HTTP API、内存 CRUD 和自动化测试。

Day 2 已完成：SQLAlchemy ORM、PostgreSQL、Docker Compose、数据库 CRUD、FastAPI Session 依赖与隔离测试。

Day 3 已完成：Alembic 初始化迁移、空库升级与回退验证、已有数据库版本基线。

- 任务说明：[learning/day-01.md](learning/day-01.md)、[learning/day-02.md](learning/day-02.md)、[learning/day-03.md](learning/day-03.md)
- 复盘索引：[notes/README.md](notes/README.md)
- 每日笔记：[notes/day-01.md](notes/day-01.md)、[notes/day-02.md](notes/day-02.md)、[notes/day-03.md](notes/day-03.md)
- 常用命令：[notes/commands.md](notes/commands.md)

## 计划中的目录

以下目录由学习者在完成练习时亲自创建：

```text
app/
  __init__.py
  main.py
tests/
  test_health.py
```

## 完成定义

三周后，本仓库应当能够：

1. 从空数据库执行迁移并启动服务；
2. 通过 Docker Compose 重复运行；
3. 自动测试认证、CRUD、权限、搜索和异常流程；
4. 由学习者脱离教程与 AI 重写一条完整业务链路；
5. 为简历中的每项技术声明提供代码、测试或提交记录证据。
