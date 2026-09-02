# Day 2：从内存字典到关系数据库

## 今日目标

今天完成两次递进：

```text
纯Python对象
    ↓ SQLAlchemy ORM映射
SQLite表与事务
    ↓ 更换数据库连接
Docker中的PostgreSQL
    ↓
为FastAPI数据库CRUD做准备
```

完成后应当能解释：

- 表、行、列、主键分别是什么；
- ORM类和Pydantic模型为什么不是同一种模型；
- Engine、连接、Session和事务分别负责什么；
- `add`、`flush`、`commit`、`rollback`、`refresh`的区别；
- 为什么测试和每次Web请求不能共享同一个Session；
- SQLite与PostgreSQL在本项目中分别扮演什么角色。

## 阅读范围

只阅读SQLAlchemy 2.0官方文档的以下部分：

1. [Declare Models](https://docs.sqlalchemy.org/en/20/orm/quickstart.html#declare-models)
2. [Create an Engine](https://docs.sqlalchemy.org/en/20/orm/quickstart.html#create-an-engine)
3. [Emit CREATE TABLE DDL](https://docs.sqlalchemy.org/en/20/orm/quickstart.html#emit-create-table-ddl)
4. [Create Objects and Persist](https://docs.sqlalchemy.org/en/20/orm/quickstart.html#create-objects-and-persist)
5. [Simple SELECT](https://docs.sqlalchemy.org/en/20/orm/quickstart.html#simple-select)

不要继续阅读关系、JOIN、异步Session或高级查询。

## 第一部分：安装依赖

在仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-day2.txt
```

验证：

```powershell
.\.venv\Scripts\python.exe -c "import sqlalchemy, psycopg, alembic; print(sqlalchemy.__version__)"
```

## 第二部分：SQLite ORM热身

先在已被Git忽略的`scratch/day_02_sqlalchemy_basics.py`中练习，不修改FastAPI业务代码。

### 数据库与对象的对应关系

| 关系数据库 | SQLAlchemy ORM |
|---|---|
| 表 | ORM类 |
| 一行数据 | ORM类的一个实例 |
| 列 | `Mapped`属性 |
| 主键 | `primary_key=True`的列 |

### 检查点A：声明模型并建表

创建：

- 一个继承`DeclarativeBase`的`Base`类；
- 一个继承`Base`的`BookRecord`类；
- 表名为`books`；
- `id`为整数主键；
- `title`为最长100的非空字符串；
- `pages`为非空整数。

创建SQLite Engine：

```text
sqlite:///./scratch/day_02.db
```

暂时设置`echo=True`，观察SQLAlchemy实际发出的SQL。调用metadata的建表操作后运行脚本，确认输出中出现`CREATE TABLE books`，并且`scratch/day_02.db`文件被创建。

### 检查点B：插入与事务

使用`with Session(engine) as session:`：

1. 创建两个`BookRecord`对象；
2. 使用`session.add_all(...)`加入Session；
3. 调用`session.commit()`提交事务；
4. 观察输出中的`INSERT`和`COMMIT`。

再次运行脚本会重复插入，这是当前脚本的预期行为。不要先实现去重。

### 检查点C：查询

使用SQLAlchemy 2.x的`select(BookRecord)`构造查询，通过`session.scalars(...)`获取ORM对象列表，逐项打印`id`、`title`和`pages`。

不要使用旧版教程中的`session.query(...)`。

## 第三部分：切换PostgreSQL

SQLite三个检查点通过后再开始：

1. 验证Docker Desktop和Compose可用；
2. 启动独立PostgreSQL容器和持久化卷；
3. 使用`postgresql+psycopg://`数据库URL创建Engine；
4. 用同一套ORM模型建表、插入和查询；
5. 重启容器后验证数据仍存在。

具体容器配置在SQLite阶段通过后生成，避免同时排查Python代码和Docker环境。

### Compose配置

仓库根目录的`compose.yaml`声明一个`db`服务：

- 使用PostgreSQL 17官方镜像；
- 只将数据库端口绑定到本机`127.0.0.1`；
- 使用命名卷`postgres_data`保存数据库文件；
- 使用`pg_isready`健康检查等待数据库真正可用；
- 用户名、密码、库名和宿主机端口来自不提交的`.env`。

从公开示例创建本地配置：

```powershell
Copy-Item .env.example .env
```

验证Compose展开后的配置：

```powershell
docker compose config
```

启动并检查：

```powershell
docker compose up -d db
docker compose ps
docker compose logs db --tail 30
```

首次启动需要下载PostgreSQL镜像。`docker compose ps`中的状态最终应为`healthy`。

在容器内部执行SQL验证：

```powershell
docker compose exec db psql -U backend_user -d backend_lab -c "SELECT version();"
```

### 正式项目结构：配置、连接和模型

PostgreSQL验证成功后，增加三个模块：

```text
app/config.py      读取并校验环境配置
app/database.py    创建Base、Engine和Session工厂
app/models.py      声明Item ORM模型
```

`.env`除Compose所需的四个`POSTGRES_*`变量外，还要包含：

```text
DATABASE_URL=postgresql+psycopg://backend_user:backend_password@127.0.0.1:5432/backend_lab
```

这里的`postgresql+psycopg`分别指定SQLAlchemy方言和数据库驱动。`127.0.0.1:5432`是从宿主机Python程序访问Compose容器时使用的地址。

完成后创建一个位于`scratch/`的验证脚本，依次完成：

1. 导入`Item`后调用`Base.metadata.create_all(engine)`；
2. 创建并提交一个`Item`对象；
3. `refresh`后打印数据库生成的主键；
4. 使用`select(Item)`重新查询并打印记录。

这一步仍然不修改`app/main.py`，确认连接层和模型层可独立工作后再迁移接口。

停止容器但保留数据：

```powershell
docker compose down
```

不要使用`docker compose down -v`，因为`-v`会删除保存数据库数据的命名卷。

## 禁止项

- 暂不修改`app/main.py`中的CRUD；
- 暂不创建User或Tag表；
- 暂不学习关系、外键和JOIN；
- 暂不使用AsyncSession；
- 暂不配置Alembic迁移；
- 不复制旧版`session.query()`教程。

## 今日提交策略

SQLite练习位于被忽略的`scratch/`，不提交。PostgreSQL连接成功后，再把正式的数据库配置、ORM模型和依赖清单作为Day 2提交。
