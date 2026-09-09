# 项目命令速查

这是一张使用时查询的速查表，不要求逐字背诵。执行命令前先说清它将作用于哪个环境、
可能改变什么，再运行并检查输出。

## Python 与服务

```powershell
# 使用当前虚拟环境运行测试
python -m pytest

# 启动开发服务器（本机8000端口被系统保留，因此使用9000）
python -m uvicorn app.main:app --reload --port 9000
```

未激活虚拟环境时，可以显式使用：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Git

```powershell
git status
git diff
git diff --check
git add <path>
git diff --cached
git commit -m "<message>"
git log --oneline -5
```

## Docker Compose

```powershell
docker compose up -d db
docker compose ps
docker compose logs db --tail 30
docker compose down
```

`docker compose down` 停止并移除容器但保留命名卷。不要在不确认数据可删除时使用
`docker compose down -v`。

## PostgreSQL

通用结构：

```powershell
docker compose exec db psql -P pager=off -U <用户> -d <数据库> -c "<SQL或psql命令>"
```

常用检查：

```text
\dt                             列出表
\d items                        查看items表结构
SELECT COUNT(*) FROM items;      统计数据
```

## Alembic

```powershell
# 只在第一次初始化迁移目录
python -m alembic init alembic

# 比较metadata与数据库，生成候选迁移
python -m alembic revision --autogenerate -m "<message>"

# 升级到最新迁移
python -m alembic upgrade head

# 查看当前数据库版本
python -m alembic current

# 查看迁移历史
python -m alembic history --verbose

# 回退到所有迁移之前；可能删除结构和数据，只能确认目标后使用
python -m alembic downgrade base

# 不执行迁移，只登记当前版本；必须先人工确认结构一致
python -m alembic stamp head
```

## 临时环境变量

```powershell
# 查看当前数据库名但不打印含密码的完整URL
python -c "from app.config import settings; print(settings.database_url.rsplit('/', 1)[-1])"

# 清除当前PowerShell中的临时数据库URL覆盖
Remove-Item Env:DATABASE_URL
```
