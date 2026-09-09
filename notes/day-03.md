# Day 3 复盘：数据库迁移与 Alembic

## 今天建立的主链路

```text
app/models.py
定义应用期望的表结构
    ↓
Base.metadata
汇总已经导入的ORM模型
    ↓
alembic revision --autogenerate
比较metadata与真实数据库，生成迁移文件
    ↓
人工检查upgrade()与downgrade()
    ↓
alembic upgrade head
执行迁移并更新alembic_version
    ↓
PostgreSQL真实结构发生变化
```

## 为什么需要迁移

修改 ORM 模型只会修改 Python 中的设计图，不会自动修改已经存在的数据库。
迁移文件明确记录数据库怎样从旧结构变成新结构，使开发、测试和部署环境能够以同样的
顺序演进。

`Base.metadata.create_all()` 适合快速创建缺失的表，但不会保存结构版本历史，也不适合
表达给已有表增加列、约束或索引等连续变化。正式项目因此使用 Alembic 管理结构。

## Alembic 文件的职责

- `alembic.ini`：Alembic 的总体配置和日志配置；
- `alembic/env.py`：连接通用 Alembic 与当前应用；
- `alembic/versions/`：保存按 revision 串联的迁移历史；
- `alembic/script.py.mako`：新迁移文件的生成模板。

`env.py` 从应用配置读取数据库 URL，把 `Base.metadata` 交给 Alembic，并导入
`app.models` 以确保模型已经注册到 metadata。数据库密码在运行时从 `.env` 读取，
不写进提交的配置文件。

## revision、base 与 head

每份迁移都有自己的 `revision`，并通过 `down_revision` 指向上一个版本：

```text
base
  ↓
e5f21096bb73  create items table  (head)
```

- `base`：尚未执行任何迁移的起点；
- `head`：当前迁移历史中的最新版本；
- `upgrade()`：向该版本前进；
- `downgrade()`：撤销该版本并回到父版本。

初始迁移的 `down_revision` 为 `None`，因为它没有父迁移。

## autogenerate 做了什么

`revision --autogenerate` 比较两份结构：

```text
Base.metadata中的期望结构
                ↕
目标数据库中的真实结构
```

本次目标数据库为空，因此 Alembic 检测到新增的 `items` 表，生成了
`op.create_table(...)`。自动生成只是候选变更，执行前仍需检查列类型、NULL 约束、
主键、外键、索引以及 downgrade 是否合理。

在当前版本和默认迁移环境下，autogenerate 过程中可能先创建空的
`alembic_version` 管理表，但不会执行新生成 migration 中的业务表变更。

## alembic_version 表

迁移文件记录“项目拥有哪些结构版本”，数据库中的 `alembic_version` 表记录“这个
数据库已经执行到哪个版本”。

执行 `upgrade head` 后，本次验证数据库记录：

```text
e5f21096bb73
```

执行 `downgrade base` 后，`items` 被删除，`alembic_version` 表可以继续存在，但版本
记录被清空。

## upgrade 与 stamp 的区别

```text
alembic upgrade head
执行尚未执行的upgrade()，真实修改数据库结构

alembic stamp head
不执行upgrade()，只登记数据库当前处于head
```

原开发数据库早已通过 `create_all()` 建好 `items`。确认其结构与初始 migration 一致
后，使用 `stamp head` 纳入版本管理，避免重复建表，同时保留了原来的 7 条数据。

## 本次安全验证

1. 新建独立的空 PostgreSQL 数据库；
2. 在其中生成初始 migration；
3. 执行 `upgrade head`，确认 `items` 被创建；
4. 执行 `downgrade base`，确认 `items` 被删除；
5. 再次升级，确认迁移可重复执行；
6. 切回原开发数据库并核对表结构；
7. 使用 `stamp head` 登记版本；
8. 确认原来的 7 条数据仍然存在；
9. 运行原有测试，结果为 14 passed。

## 面试表达

可以这样简要说明：

> ORM 模型只描述应用期望的数据库结构。项目使用 Alembic 保存结构版本，通过
> autogenerate 比较 SQLAlchemy metadata 与真实数据库，人工检查 migration 后再执行
> upgrade。数据库使用 alembic_version 记录当前 revision。对于已有且结构一致的表，
> 可以核对后通过 stamp 建立版本基线，而不是重复执行建表迁移。

## 自测题

1. 只在 `models.py` 增加一列，PostgreSQL 为什么不会自动出现该列？
2. `Base.metadata` 在 autogenerate 中扮演什么角色？
3. 为什么必须导入 `app.models`？
4. `revision` 与 `down_revision` 怎样组成迁移历史？
5. `base` 和 `head` 分别表示什么？
6. `upgrade head` 与 `stamp head` 的区别是什么？
7. 为什么 autogenerate 之后仍需人工检查迁移文件？
8. 为什么我们用独立空数据库测试初始迁移？
9. `downgrade` 在真实生产数据上可能有什么风险？
