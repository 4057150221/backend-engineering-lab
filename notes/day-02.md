# Day 2 复盘：从内存字典到 PostgreSQL

## 一句话成果

使用 SQLAlchemy 2.0 ORM 和 Psycopg 将 Item CRUD 持久化到 Docker 中的 PostgreSQL，并使用 FastAPI 依赖注入管理请求 Session，使用 pytest 依赖覆盖和内存 SQLite 隔离测试。

## 主链路

以 `POST /items` 为例：

```text
客户端发送JSON
        ↓
ItemCreate校验请求体
        ↓
Depends(get_session)创建本次请求的Session
        ↓
main.py调用crud.create_item()
        ↓
根据ItemCreate构造Item ORM对象
        ↓
Session通过Engine和Psycopg连接PostgreSQL
        ↓
INSERT、COMMIT、REFRESH
        ↓
crud.py返回Item ORM对象
        ↓
response_model=ItemRead读取属性并校验
        ↓
FastAPI返回JSON和201
        ↓
请求结束，Session关闭
```

## 1. 项目分层

```text
app/config.py       读取和校验环境配置
app/database.py     定义Base、Engine、Session工厂和Session依赖
app/models.py       定义数据库表与ORM映射
app/schemas.py      定义API请求与响应契约
app/crud.py         执行数据库增、查、改、删
app/main.py         定义HTTP接口并协调其他模块
tests/conftest.py   准备公共测试环境和数据库清理
compose.yaml        描述Docker PostgreSQL服务
```

主要依赖关系：

```text
config.py
    ↓
database.py
    ↓
models.py

schemas.py ─────┐
models.py  ─────┼→ crud.py ─┐
database.py ────┘           ├→ main.py
schemas.py ─────────────────┘
```

分层不是 Python 强制要求，而是为了让不同变化集中在不同位置：数据库地址变更看配置层，表结构变更看 Model，请求规则变更看 Schema，SQL 操作变更看 CRUD，HTTP 行为变更看路由。

## 2. 关系数据库与 ORM

| 关系数据库 | SQLAlchemy ORM |
|---|---|
| 表 | ORM 类 |
| 一行 | ORM 类的一个实例 |
| 列 | `Mapped` 属性 |
| 主键 | `primary_key=True` 的列 |

```python
class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
```

`Item` 声明 Python ORM 对象与 `items` 表的映射，不负责界面显示。

所有 ORM 模型必须使用从 `app.database` 导入的同一个 `Base`。重复声明 Base 会产生互不相认的 `metadata`，统一建表时可能找不到模型。

`Mapped[str | None]` 表示 Python 属性允许 `None`，`nullable=True` 明确数据库列允许 SQL `NULL`。

## 3. Model 与 Schema

```text
SQLAlchemy Model
→ 数据怎样保存到数据库

Pydantic Schema
→ API允许接收和返回什么数据
```

当前三个对象：

| 变量示例 | 类型 | 作用 |
|---|---|---|
| `item_data` | `ItemCreate` | 创建或更新请求 |
| `db_item` | `Item` | 数据库 ORM 对象 |
| `response_data` | `ItemRead` | API 响应模型 |

```python
class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

`ConfigDict` 是 Pydantic 模型行为配置。`from_attributes=True` 允许从 ORM 对象的属性读取值。

```python
response_data = ItemRead.model_validate(db_item)
```

`model_validate()` 是继承自 `BaseModel` 的类方法。它读取输入、校验字段，并创建新的 `ItemRead` 实例。它不是“变成 Python 格式”，因为前后本来都是 Python 对象。

```text
Item ORM对象
→ ItemRead.model_validate()
→ ItemRead对象
→ model_dump()
→ dict
→ FastAPI序列化
→ JSON
```

## 4. 配置层

`config` 是 `configuration` 的缩写。

```python
class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
```

- `.env` 保存本机实际配置，不提交 Git；
- `.env.example` 提交安全示例；
- `Settings` 从环境变量或 `.env` 读取并校验配置；
- 数据库密码不应硬编码进 Python 源码。

数据库 URL：

```text
postgresql+psycopg://用户:密码@地址:端口/数据库名
```

其中 `postgresql` 是 SQLAlchemy 方言，`psycopg` 是 Python 与 PostgreSQL 通信的驱动。

## 5. Engine、`sessionmaker` 与 Session

```python
engine = create_engine(settings.database_url, echo=True)
SessionLocal = sessionmaker(bind=engine)
```

- Engine 保存数据库地址、方言和连接池等配置，负责提供连接资源。
- `create_engine()` 通常是惰性的；第一次执行 SQL 时才真正建立连接。
- `sessionmaker(bind=engine)` 创建记住 Engine 和 Session 配置的工厂。
- `SessionLocal()` 每次调用都产生一个新的具体 Session。

```text
Engine
  ↑
SessionLocal工厂
  ├── Session A
  ├── Session B
  └── Session C
```

`with Session(engine)` 是现场创建 Session 并传入 Engine。`with SessionLocal()` 是调用已经保存 Engine 配置的工厂，所以不需要再传一次。

`SessionLocal` 保存的是创建配置，不保存多次数据库操作的上下文。具体事务和 ORM 对象状态属于每个独立 Session。

## 6. `with`、`yield` 与 `Depends`

```python
def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
```

- `with` 确保正常结束或抛出异常时都关闭 Session、归还连接资源；
- `yield` 暂停函数，把 Session 交给 FastAPI；
- 请求结束后函数继续，离开 `with` 完成清理。

```python
session: Session = Depends(get_session)
```

表示 Session 参数由 FastAPI 提供。写 `Depends(get_session)`，而不是 `Depends(get_session())`，因为要把函数交给框架，让框架在每次请求时调用。

每个请求不能共享一个全局 Session，因为 Session 内含事务状态、正在跟踪的 ORM 对象和连接资源，共享会造成请求相互干扰。

当前使用同步 SQLAlchemy Session，所以数据库接口使用普通 `def`。

## 7. ORM 对象状态与事务

```text
Item(...)
→ transient：只有Python对象

session.add(item)
→ pending：等待写入

flush或commit
→ persistent：数据库已有对应行，Session正在管理

Session关闭
→ detached：对象仍在Python中，但已脱离原Session
```

主要方法：

| 方法 | 作用 |
|---|---|
| `add()` | 加入 Session 管理，准备写入 |
| `flush()` | 把修改发送给数据库，但不正式提交事务 |
| `commit()` | 完成必要的 flush，并正式提交事务 |
| `refresh()` | 根据主键重新查询，更新同一个 ORM 对象 |
| `rollback()` | 撤销当前尚未提交的事务修改 |

PostgreSQL 的 `INSERT ... RETURNING items.id` 已能返回数据库生成的主键；`refresh()` 再查询当前整行，明确加载数据库默认值或触发器可能产生的值。

`return db_item` 不会把对象转换成 ORM 对象。对象从调用 `Item(...)` 时就是 ORM 对象；`return` 只把同一个引用交给调用者，`-> Item` 只是类型标注。

日志中查询后出现 `ROLLBACK`，可能只是 Session 关闭只读事务，不会撤销之前已经成功 `COMMIT` 的修改。

## 8. 查询 API

```text
scalar(statement)
→ 第一行的第一列，一个结果或None

scalars(statement).all()
→ 每一行的第一列组成的多个结果
```

查询 `select(Item)` 时，第一列就是 `Item` ORM 对象：

```python
session.scalar(select(Item))
# 一个Item或None

session.scalars(select(Item)).all()
# 多个Item
```

`session.get(Item, item_id)` 适合按主键查询，找到返回 ORM 对象，找不到返回 `None`。

分页查询应明确排序：

```python
select(Item).order_by(Item.id).offset(offset).limit(limit)
```

没有明确 `order_by` 时，数据库不保证每次返回顺序一致。

日志中的 `[cached since ...]` 通常是 SQL 编译缓存，不是旧查询结果缓存；更换参数后仍会访问数据库。

## 9. CRUD 层与 HTTP 层

`crud.py` 集中数据库增查改删，`main.py` 处理路径、参数、状态码和 HTTP 异常。

```text
crud.get_item()找不到
→ 返回None
→ main.py转换为HTTP 404
```

这样 CRUD 层不需要认识 HTTP。

更新已由同一个 Session 管理的持久化对象时，直接修改属性后 `commit()` 即可，不需要再次 `add()`。SQLAlchemy 会跟踪变化并生成 `UPDATE`。

```python
session.delete(db_item)
```

会删除数据库行；`del db_item` 只会删除 Python 变量引用。

删除函数设计为返回 `None`，与 `204 No Content` 接口语义一致。

接口中的：

```python
def create_item(...) -> Item:
```

描述函数实际返回 ORM `Item`；装饰器中的：

```python
response_model=ItemRead
```

规定对外响应必须符合 `ItemRead`，并执行运行时响应处理。

## 10. `create_all()` 与迁移

```python
Base.metadata.create_all(engine)
```

会检查并创建缺失表。已有表存在时，日志可能只有查询系统表而没有 `CREATE TABLE`。

它不能可靠管理已有表的结构演进。例如 ORM 增加一列后，`create_all()` 不等于自动修改旧表。后续将使用 Alembic 记录并执行数据库迁移。

## 11. Docker 在本项目中的作用

Docker 当前负责运行开发 PostgreSQL；FastAPI 仍在 Windows `.venv` 中运行。

```text
浏览器
→ 127.0.0.1:9000
→ Windows中的Uvicorn/FastAPI
→ SQLAlchemy和Psycopg
→ 127.0.0.1:5432
→ Docker中的PostgreSQL
→ postgres_data命名卷
```

| Docker 对象 | 当前作用 |
|---|---|
| 镜像 `postgres:17` | 创建 PostgreSQL 容器的模板 |
| `db` 容器 | 运行 PostgreSQL 进程 |
| 端口映射 | Windows 5432 转发到容器 5432 |
| `postgres_data` 卷 | 持久化数据库文件 |
| 健康检查 | `pg_isready` 判断数据库是否可连接 |

普通 `docker compose down` 删除容器和网络，但保留命名卷。`docker compose down -v` 会删除命名卷和数据，不应随意执行。

容器重建前后数据量一致，证明数据保存在命名卷，而不是只存在容器临时文件系统。

`.venv`、Docker、PostgreSQL 的区别：

```text
.venv       隔离Python解释器和包
Docker      管理隔离的服务运行环境
PostgreSQL  真正保存和查询业务数据
```

## 12. SQLite 与 PostgreSQL

| 对比 | SQLite | PostgreSQL |
|---|---|---|
| 运行方式 | 嵌入应用 | 独立数据库服务器 |
| 存储 | 文件或内存 | 数据目录/命名卷 |
| 连接 | 本地访问 | 通过客户端协议连接 |
| 并发和权限 | 相对简单 | 完整的并发、事务、角色和权限能力 |
| 当前用途 | 快速隔离测试 | 开发环境真实数据库 |

SQLite 与 PostgreSQL 在类型、SQL 方言、并发和事务等方面并不完全相同。SQLite 测试通过不能完全替代 PostgreSQL 集成验证。

Python `None` 对应 SQL `NULL`。`psql` 默认可能把 `NULL` 显示为空白，它与空字符串 `''` 不同。

## 13. `conftest.py` 与测试隔离

`conf` 可以理解为 `configuration`。`conftest.py` 是 pytest 约定自动发现的公共测试配置文件，不需要测试代码手动导入。

```text
pytest启动
→ 导入tests/conftest.py
→ 创建内存SQLite Engine和表
→ 注册fixture
→ 收集测试函数
→ 每条测试前运行autouse fixture
→ 执行测试
```

```python
app.dependency_overrides[get_session] = override_get_session
```

测试期间，FastAPI 遇到 `Depends(get_session)` 时，改为调用返回 SQLite Session 的测试依赖，不污染开发 PostgreSQL。

```python
@pytest.fixture(autouse=True)
def clean_items() -> None:
    ...
```

`autouse=True` 表示每条测试前自动执行。清空测试表保证测试相互独立、不依赖顺序。

`StaticPool` 让内存 SQLite 复用同一个连接；`check_same_thread=False` 允许 TestClient 所在线程使用该连接。

文件必须准确命名为 `conftest.py`。误写为 `test_conftest.py` 时会被当成普通测试模块，公共清理 fixture 不会服务相邻测试，数据会跨测试累积。

## 14. 常用命令

启动与测试：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 9000
.\.venv\Scripts\python.exe -m pytest -q
```

Docker 与 PostgreSQL：

```powershell
docker compose up -d db
docker compose ps
docker compose logs db --tail 30
docker compose exec db psql -P pager=off -U backend_user -d backend_lab
docker compose down
```

`psql` 底部显示 `(END)` 是分页器，按小写 `q` 退出。`-P pager=off` 可以关闭分页。

WSL 更新：

```powershell
wsl --update
```

Git 检查：

```powershell
git status --short
git diff --check
git diff --cached --check
git log --oneline -5
```

`.env`、`.venv/`、`scratch/` 和缓存文件不应提交。

## Day 2 踩坑记录

1. Docker Desktop 首次启动因 WSL 更新失败，正确执行 `wsl --update` 后恢复。
2. `psql` 显示 `(END)` 不是卡死，按 `q` 退出。
3. `models.py` 重复声明 Base，导致两套 metadata 不同。
4. 多次运行插入练习会产生多行记录，这是预期行为。
5. SQL `NULL` 在 `psql` 中显示为空白，但不是空字符串。
6. 查询后的 `ROLLBACK` 可能只是关闭只读事务。
7. `[cached since ...]` 是 SQL 编译缓存，不是结果缓存。
8. `test_conftest.py` 不是 pytest 公共配置；正确名称是 `conftest.py`。
9. 测试资源必须与开发资源隔离，不能为了断言 ID 而清空开发数据库。
10. 容器可以删除重建，重要数据必须放在命名卷中。

## Day 2 自测

1. `config.py`、`database.py`、`models.py`、`schemas.py`、`crud.py`、`main.py` 分别负责什么？
2. `ItemCreate`、`Item`、`ItemRead` 有什么区别？
3. `ConfigDict(from_attributes=True)` 为什么存在？
4. `ItemRead.model_validate(db_item)` 做了什么？
5. Engine、`SessionLocal` 和具体 Session 有什么区别？
6. 为什么 `with SessionLocal()` 不需要再次传 Engine？
7. `add`、`flush`、`commit`、`refresh`、`rollback` 分别做什么？
8. `scalar()` 与 `scalars().all()` 有什么区别？
9. 为什么每个请求要使用独立 Session？
10. `Depends(get_session)` 如何保证 Session 最终被关闭？
11. `response_model=ItemRead` 与 `-> Item` 有什么区别？
12. 为什么更新已查询的 ORM 对象不需要再次 `add()`？
13. Docker、PostgreSQL 和 `.venv` 分别负责什么？
14. 容器删除重建后数据为什么仍存在？
15. pytest 为什么会自动使用 `conftest.py`？
16. 为什么测试使用 SQLite，而开发使用 PostgreSQL？
17. SQLite 测试通过为什么仍不能完全替代 PostgreSQL 验证？
18. `create_all()` 为什么不能代替 Alembic？

### 简短答案

1. 分别负责配置、数据库基础设施、ORM映射、API契约、数据库操作和HTTP协调。
2. 请求模型、数据库ORM模型、响应模型。
3. 让 Pydantic 可以从 ORM 对象属性读取响应字段。
4. 校验输入并创建新的 `ItemRead` 实例。
5. Engine 管连接资源，`SessionLocal` 是工厂，Session 是具体工作单元。
6. `sessionmaker(bind=engine)` 已经保存了 Engine 配置。
7. 加入管理、发送但不提交、正式提交、重新读取、撤销未提交修改。
8. 一个第一列结果，与多个第一列结果。
9. 避免事务和 ORM 状态在请求之间互相干扰。
10. `yield` 后请求执行，结束后依赖函数继续并离开 `with`。
11. 前者是运行时响应契约，后者是函数返回类型提示。
12. 对象已由当前 Session 管理，属性变化会被跟踪。
13. Python包隔离、服务环境管理、数据保存与查询。
14. 数据保存在独立的 `postgres_data` 命名卷中。
15. 它是 pytest 约定自动发现和导入的特殊文件。
16. SQLite 快速、易清理，适合大量隔离测试；PostgreSQL 是当前真实开发数据库。
17. 两种数据库的类型、方言、并发和事务行为存在差异。
18. `create_all` 主要创建缺失表，不能版本化管理已有表的结构变化。

## 当前还没有学习

- Alembic 数据库迁移；
- User、密码哈希和 JWT；
- 外键、多对多关系和 JOIN；
- 搜索、状态过滤与更复杂分页；
- 日志与统一错误响应；
- FastAPI 容器化和 GitHub Actions；
- Redis、消息队列、微服务和高并发。

看到这些名词时不需要提前扩大学习范围，后续按项目需求逐个加入。

## 当前可口述的项目成果

> 使用 FastAPI 和 Pydantic 实现 Item REST CRUD 与参数校验，通过 SQLAlchemy 2.0 ORM 和 Psycopg 访问 PostgreSQL；使用 Docker Compose 管理带健康检查和命名卷持久化的 PostgreSQL 开发环境；通过 FastAPI 依赖注入为每个请求提供独立 Session，并利用 pytest、依赖覆盖和内存 SQLite 实现接口测试隔离。

这段描述中的每项技术都能在当前代码、测试或 Git 提交中找到证据。后续加入认证、关系、迁移和工程化后，再整理为正式简历项目描述。
