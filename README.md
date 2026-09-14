# Job Application Tracker API

一个用 FastAPI 构建的求职投递追踪后端：登录用户可以创建、查看、更新、删除自己的投递记录（公司、岗位、状态、投递日期、备注），所有数据按用户隔离。项目源自三周 Python 后端工程训练（Day 1-5 用通用 `User / Item` 场景搭建工程闭环），Day 6 起改造为这个真实业务题材。

## 技术栈

- **Web 框架**：FastAPI、Pydantic v2（请求校验、响应模型）
- **数据库**：PostgreSQL、SQLAlchemy 2.0（ORM）、Alembic（结构化迁移，支持 upgrade/downgrade）
- **认证**：JWT（PyJWT）+ OAuth2 Password Flow、Argon2id 密码哈希（pwdlib）
- **测试**：pytest + httpx（`TestClient`），44 个测试覆盖鉴权、CRUD、跨用户隔离、边界校验
- **运行环境**：Docker Compose（PostgreSQL）

## 功能范围

- 用户注册（邮箱 + 密码，Argon2id 哈希存储）、登录签发 JWT、`/users/me` 查询当前用户。
- 投递记录 `Application`：`company`、`position`、`status`（`saved` / `applied` / `interviewing` / `offer` / `rejected`）、`applied_at`（可空）、`notes`（可空）。
- `/applications` 全部端点要求 `Authorization: Bearer <token>`；`owner_id` 一律从当前登录用户获取，客户端无法传入或伪造。
- 所有读取、更新、删除按 `owner_id` 过滤；访问不存在或不属于自己的记录统一返回 `404`，不通过状态码区分"不存在"与"无权限"，避免泄露资源存在性。

不包含：前端、投递爬虫/自动投递、统计面板、标签系统、CI（明确排除在当前范围外，见下方"学习约定"）。

## 快速开始

### 1. 环境变量

复制 `.env.example` 为 `.env` 并按需修改（`JWT_SECRET_KEY` 生产环境务必换成随机值）：

```bash
cp .env.example .env
```

### 2. 启动 PostgreSQL

```bash
docker compose up -d
```

### 3. 安装依赖并执行迁移

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-day5.txt
alembic upgrade head
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/docs` 查看交互式 API 文档（Swagger UI 的 Authorize 按钮会自动附加 Bearer token）。

## 测试

```bash
pytest
```

测试使用内存 SQLite，不依赖本地 PostgreSQL。

## API 使用示例

```bash
# 注册
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "a-strong-password"}'

# 登录，拿 access token
TOKEN=$(curl -X POST http://127.0.0.1:8000/token \
  -d "username=you@example.com&password=a-strong-password" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 创建一条投递记录
curl -X POST http://127.0.0.1:8000/applications \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company": "Acme", "position": "Backend Engineer", "status": "applied"}'

# 查看自己的所有投递记录
curl http://127.0.0.1:8000/applications -H "Authorization: Bearer $TOKEN"
```

## 架构

```text
app/
  main.py       FastAPI 应用、路由、认证依赖（get_current_user）
  crud.py       数据库读写函数，按 owner_id 过滤
  models.py     SQLAlchemy ORM 模型（User、Application）
  schemas.py    Pydantic 请求/响应模型
  security.py   密码哈希、JWT 编解码
  database.py   引擎、Session 依赖
  config.py     环境变量配置（pydantic-settings）
alembic/        数据库迁移脚本
tests/          pytest 测试套件
```

请求链路：`Authorization: Bearer <token>` → `OAuth2PasswordBearer` 提取 token → `get_current_user` 验签并查库确认用户仍存在 → 路由函数用 `current_user.id` 作为 `owner_id` 调用 `crud` 层 → `crud` 层的每条查询都在 SQL 层面同时过滤 `id` 和 `owner_id`。

## 安全说明

- 密码使用 Argon2id 哈希存储，不落库明文或可逆密文。
- JWT 短期有效（默认 30 分钟），`sub` 为用户 ID，`get_current_user` 在验签通过后仍会查库确认该用户存在（token 未过期但用户已被删除时会被拒绝）。
- 所有 `/applications` 端点要求认证；`owner_id` 只能来自服务端解析出的当前用户，任何请求体/路径参数都无法覆盖它。
- 跨用户访问他人记录统一返回 `404 Application not found`，不使用 `403`，避免暴露资源是否存在。

## 学习约定

- 核心功能先由学习者独立实现，AI 负责概念讲解、代码审查、测试建议和排错提示。
- 每个功能以"能运行、能测试、能解释、能独立重写"为完成标准。
- 不复制完整项目模板，不提前加入 Redis、消息队列、微服务或额外 AI 功能。
- 每个学习日产生一个清楚、真实的 Git 提交。

## 学习进度

- Day 1：解释器、虚拟环境、包与模块、HTTP API、内存 CRUD 和自动化测试。
- Day 2：SQLAlchemy ORM、PostgreSQL、Docker Compose、数据库 CRUD、FastAPI Session 依赖与隔离测试。
- Day 3：Alembic 初始化迁移、空库升级与回退验证、已有数据库版本基线。
- Day 4：用户注册、邮箱与密码校验、Argon2id 密码哈希、用户表迁移和接口测试。
- Day 5：登录、JWT access token、Bearer 认证、当前用户依赖与认证接口测试。
- Day 6：把通用 `Item` 重构为业务真实的 `Application`（求职投递记录），按登录用户隔离数据，`items` 表迁移为 `applications` 表并补齐字段，旧的 7 条无归属实验数据已备份后清空，全部端点要求鉴权，新增 21 个测试覆盖鉴权与跨用户隔离，测试总数 44 全部通过。

- 任务说明：[learning/day-01.md](learning/day-01.md)、[learning/day-02.md](learning/day-02.md)、[learning/day-03.md](learning/day-03.md)、[learning/day-04.md](learning/day-04.md)、[learning/day-05.md](learning/day-05.md)
- 复盘索引：[notes/README.md](notes/README.md)
- 每日笔记：[notes/day-01.md](notes/day-01.md)、[notes/day-02.md](notes/day-02.md)、[notes/day-03.md](notes/day-03.md)、[notes/day-04.md](notes/day-04.md)、[notes/day-05.md](notes/day-05.md)
- 常用命令：[notes/commands.md](notes/commands.md)

## 完成定义

1. 从空数据库执行迁移并启动服务；
2. 通过 Docker Compose 重复运行；
3. 自动测试认证、CRUD、权限、异常流程；
4. 由学习者脱离教程与 AI 重写一条完整业务链路；
5. 为简历中的每项技术声明提供代码、测试或提交记录证据。
