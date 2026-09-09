# Day 3：用 Alembic 管理数据库结构版本

## 今日目标

Day 2 中，Python ORM 模型与数据库表已经能够正常工作，但表是通过
`Base.metadata.create_all(...)` 直接创建的。今天要把数据库结构交给
Alembic 管理：

```text
修改 ORM 模型
    ↓
生成或编写迁移脚本
    ↓
检查迁移内容
    ↓
执行 upgrade
    ↓
PostgreSQL 表结构发生可追踪的变化
```

完成后应当能解释：

- 数据库迁移解决什么问题；
- `create_all` 与 Alembic migration 有什么区别；
- revision、`upgrade()`、`downgrade()` 和 head 分别是什么；
- Alembic 为什么必须导入 `Base.metadata` 和 ORM 模型；
- `alembic_version` 表用于保存什么；
- 为什么不能只修改 `models.py`，却不迁移数据库。

## 今日边界

- 只建立 Alembic 环境和第一份 `items` 表迁移；
- 不创建 `User`；
- 不做 JWT 登录；
- 不删除现有 PostgreSQL 练习数据；
- 不把 `.env` 中的数据库密码写进 `alembic.ini`；
- 迁移脚本必须人工检查，不能看见 autogenerate 成功就直接执行。

## 检查点 A：初始化迁移环境

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m alembic init alembic
```

预期新增：

```text
alembic.ini
alembic/
  env.py
  script.py.mako
  README
  versions/
```

这一命令只生成 Alembic 的项目结构，不会修改数据库。

初始化后先观察文件，不立即生成 revision。找到并回答：

1. `alembic.ini` 中的 `script_location` 指向哪里？
2. `alembic/env.py` 中当前的 `target_metadata` 是什么？
3. `alembic/versions/` 当前是否为空？

## 检查点 B：让 Alembic 认识项目模型

修改 `alembic/env.py`，使它：

1. 从 `app.config` 读取 `settings.database_url`；
2. 从 `app.database` 导入 `Base`；
3. 导入 `app.models`，保证 `Item` 已注册进 `Base.metadata`；
4. 将 Alembic 配置中的数据库 URL 设置为项目的数据库 URL；
5. 将 `target_metadata` 设置为 `Base.metadata`。

完成后先验证 metadata：

```powershell
.\.venv\Scripts\python.exe -c "from app.database import Base; import app.models; print(list(Base.metadata.tables.keys()))"
```

预期输出包含：

```text
['items']
```

## 检查点 C：创建第一份迁移

当前开发数据库已经存在 `items` 表。如果直接对它执行
`revision --autogenerate`，Alembic 会认为模型和数据库没有差异，从而生成空迁移。

因此第一份迁移必须在不破坏现有数据的前提下，使用空数据库生成并验证。具体命令在
检查点 B 通过后再执行，避免同时排查配置和数据库状态。

第一份 revision 应表达：

- 创建 `items` 表；
- `id` 为整数主键；
- `title` 为最长 100 的非空字符串；
- `description` 为最长 300、允许 NULL 的字符串；
- `downgrade()` 能删除 `items` 表。

## 检查点 D：在空 PostgreSQL 数据库验证

验证顺序：

1. 空数据库中确认不存在 `items`（执行 autogenerate 后，Alembic 自己的
   `alembic_version` 表可能已经存在，但此时表中没有版本记录）；
2. 执行 `alembic upgrade head`；
3. 确认 `items` 和 `alembic_version` 两张表出现；
4. 使用 `alembic current` 确认当前 revision；
5. 查看 PostgreSQL 中的实际列类型、NULL 约束和主键；
6. 执行现有 pytest，确认 14 个测试仍通过。

现有开发数据库已有相同结构，最终通过 `stamp` 纳入版本记录，而不是重复执行建表迁移。
在执行 `stamp` 前，必须先确认现有表结构与 migration 一致。

## 今日完成标准

- Alembic 配置不包含明文密码；
- 初始 migration 不是空文件；
- `upgrade()` 与 `downgrade()` 内容能够逐行解释；
- 一个空 PostgreSQL 数据库能通过 `upgrade head` 得到正确表结构；
- 现有开发数据库的数据没有被删除；
- 现有自动化测试继续通过；
- 能说明修改 ORM 模型之后为什么数据库不会自动改变。

## 建议提交

所有检查点通过后再提交：

```text
feat: add initial database migration
```
