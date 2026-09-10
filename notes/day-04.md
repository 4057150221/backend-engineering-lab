# Day 4 复盘：用户注册与密码哈希

## 一句话主链路

```text
POST /users
    -> UserCreate 校验邮箱和密码
    -> 查询邮箱是否已存在
    -> Argon2id 哈希明文密码
    -> User ORM 写入 PostgreSQL
    -> UserRead 过滤响应字段
    -> 返回 201、id 和 email
```

这一天完成的是“注册”，还不是“登录”。注册负责创建用户；登录将在后续验证密码并签发访问令牌。

## 1. 哈希不是加密

加密通常可以用密钥还原原文；密码哈希的设计目标是单向计算，服务端不需要、也不应该把哈希还原成密码。

项目使用：

```python
password_hash = PasswordHash.recommended()
hashed_password = password_hash.hash(plain_password)
is_valid = password_hash.verify(plain_password, hashed_password)
```

验证密码时不是“解密哈希”，而是读取哈希中记录的算法参数和 salt，再校验输入密码是否匹配。

同一个密码连续哈希两次通常会得到不同结果，因为每次会使用随机 salt。这可以避免相同密码在数据库中呈现完全相同的哈希值。虽然哈希字符串不同，两者都能通过正确密码的 `verify()`。

数据库中的 `$argon2id$` 前缀说明当前推荐配置生成的是 Argon2id 哈希。

## 2. 三种用户模型为什么分开

### `UserCreate`：请求模型

它描述客户端注册时允许提交的内容：

```text
email
password
```

Pydantic 在接口函数执行前检查邮箱格式和密码长度。校验失败时，FastAPI 直接返回 422，注册函数不会开始执行。

### `User`：数据库 ORM 模型

它描述 `users` 表，以及一行数据库记录在 Python 中如何表示：

```text
id
email
hashed_password
```

这里没有 `password` 字段，因此业务代码不会把明文密码误存进数据库。

### `UserRead`：响应模型

它描述允许发送给客户端的字段：

```text
id
email
```

接口内部返回的 ORM 对象虽然含有 `hashed_password`，但 `response_model=UserRead` 只读取并序列化公开字段。密码和哈希都不会进入 JSON 响应。

因此三个模型不是重复代码，而是三道边界：输入边界、存储边界和输出边界。

## 3. 注册请求的执行过程

```python
@app.post("/users", response_model=UserRead, status_code=201)
def create_user(user_data: UserCreate, session: Session = Depends(get_session)):
    ...
```

一次请求大致经历：

1. FastAPI 读取 JSON 请求体；
2. Pydantic 用 `UserCreate` 校验并创建 `user_data`；
3. 依赖注入为接口提供数据库 `Session`；
4. CRUD 层查询邮箱是否已存在；
5. 已存在时抛出 409，函数立即结束；
6. 不存在时对密码进行哈希，创建 `User` ORM 对象；
7. `add()`、`commit()`、`refresh()` 完成数据库写入并取得数据库生成的 `id`；
8. `UserRead` 校验并过滤返回值；
9. FastAPI 序列化 JSON，并返回 201。

## 4. 201、409 和 422

- `201 Created`：服务器成功创建了新用户资源。
- `409 Conflict`：请求格式本身正确，但邮箱与已有资源发生冲突。
- `422 Unprocessable Entity`：请求体不符合 `UserCreate` 的数据约束，例如邮箱格式错误或密码过短。

422 通常发生在接口函数执行前；409 是接口函数查询数据库后主动返回的业务错误。

## 5. 为什么既查询重复邮箱，又设置 UNIQUE

应用层预先查询可以返回清楚的业务提示：

```json
{"detail": "Email already registered"}
```

数据库的 `UNIQUE` 约束是最终的数据一致性防线。即使其他脚本绕过 API 写数据库，数据库也不允许出现完全相同的邮箱。

当前版本还有一个后续加固点：两个并发请求可能同时通过“邮箱不存在”的预查，其中一个会触发数据库唯一约束错误。工程化阶段可以捕获 `IntegrityError`、回滚事务并统一返回 409。

邮箱大小写规范化也尚未实现。后续可以在查询和保存前统一处理，避免是否把 `User@example.com` 与 `user@example.com` 视为不同账号的规则含糊。

## 6. 第二份迁移说明了什么

迁移链现在是：

```text
base
  -> e5f21096bb73：创建 items 表
  -> ba7612f262f6：创建 users 表（head）
```

- `head` 是代码中迁移链的最新版本；
- `current` 是当前数据库已经执行到的版本；
- `upgrade head` 把当前数据库升级到最新迁移；
- `downgrade -1` 回退一份迁移。

先在 `backend_lab_migration` 中升级、回退和再次升级，是为了验证迁移脚本不会伤害已有开发数据。确认后才升级 `backend_lab`，其中原有 7 条 Item 数据仍然存在。

## 7. 测试覆盖了哪些风险

安全工具测试验证：

- 哈希不等于明文；
- 正确密码可以验证；
- 错误密码不能验证。

注册接口测试验证：

- 成功响应是 201；
- 响应包含公开的用户数据；
- 响应不包含密码和哈希；
- 数据库保存的是可验证的哈希；
- 重复邮箱返回 409；
- 非法邮箱和过短密码返回 422。

测试使用隔离的 SQLite 数据库。`conftest.py` 中的自动 fixture 会在每个测试前清理 `Item` 和 `User`，避免测试之间相互污染。手工使用 Swagger 和 PostgreSQL 查询则补充验证了真实开发数据库链路。

## 8. 为什么关闭 SQLAlchemy `echo`

`echo=True` 会打印 SQL 语句及绑定参数。注册时绑定参数可能包含 `hashed_password`。哈希虽然不是明文密码，仍属于敏感认证数据，不应该随意出现在终端或日志中。因此正式应用的 engine 不再默认开启 SQL 输出；需要排错时应谨慎、临时地启用日志。

## 自测题

1. 为什么同一个密码的两个哈希不同，却都能验证成功？
2. `UserCreate`、`User` 和 `UserRead` 分别负责什么？
3. 为什么接口函数返回完整 `User` ORM 对象，客户端却看不到 `hashed_password`？
4. 非法邮箱为什么返回 422，而且注册函数不会执行？
5. 重复邮箱为什么返回 409，而不是 422？
6. 应用层重复查询和数据库 `UNIQUE` 约束各自有什么作用？
7. `head` 与 `current` 有什么区别？
8. 为什么生产性质的日志不应输出密码哈希？

## 今天真正需要记住的内容

不需要背诵每个库函数。需要能够复述：

```text
请求模型只接收注册所需数据
    -> 明文密码只在请求处理期间短暂存在
    -> 密码经成熟算法哈希后写入数据库
    -> 数据库模型只保存 hashed_password
    -> 响应模型只允许公开字段离开服务端
```

这条链路是后续登录、JWT 和资源归属的基础。
