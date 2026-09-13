# Day 5 复盘：登录、JWT 与当前用户

## 一句话主链路

```text
POST /token
    -> OAuth2 表单取得 username 和 password
    -> authenticate_user 查询用户并验证 Argon2id 密码哈希
    -> create_access_token 写入 sub 和 exp，并使用 HS256 签名
    -> 返回 Bearer access token

GET /users/me
    -> Authorization: Bearer <token>
    -> OAuth2PasswordBearer 提取纯 JWT 字符串
    -> get_current_user 验签、检查 exp、读取 sub
    -> 根据用户 ID 查询数据库
    -> UserRead 过滤敏感字段并返回公开用户信息
```

## 1. 注册、登录与当前用户

- 注册 `POST /users` 创建用户，把明文密码哈希后保存。
- 登录 `POST /token` 不创建用户；它验证已有用户的邮箱和密码，并签发 access token。
- `GET /users/me` 不接收密码；它从 Bearer token 还原当前用户。

登录成功并不代表每个接口都自动知道用户是谁。客户端需要在后续受保护请求中携带 token，服务端再通过依赖完成验证和查询。

## 2. JWT 是签名，不是加密

JWT 由三段以句点连接的 Base64URL 文本组成：

```text
Header.Payload.Signature
```

- Header 说明签名算法，例如 HS256。
- Payload 保存声明；本项目只保存字符串 `sub` 和过期时间 `exp`。
- Signature 用服务端密钥计算，用于证明 Header 与 Payload 没有被篡改，且 token 由持有该密钥的一方签发。

Payload 可以被拿到 token 的人解码阅读，因此不能放密码、密码哈希、JWT 密钥或其他秘密。

攻击者可以伪造一个包含 `sub="999"` 的 Payload，也可以用自己的密钥把它签成格式正确的 token；但服务端只信任自己的 `jwt_secret_key`。服务端重新计算的签名与攻击者 token 中的签名不一致，因此会抛出 `InvalidSignatureError`。只改动 token 中一个字符也会破坏签名。

## 3. `sub`、`exp` 与配置

本项目的 token Payload：

```text
sub: 字符串形式的用户 ID
exp: UTC 过期时间
```

用户主键虽然是整数，`sub` 仍统一写成字符串；在 `get_current_user()` 这个边界处再用 `int(sub)` 转回数据库主键。这样 JWT 的主体声明格式稳定，数据库类型转换集中在一个位置。

`exp` 过期后，即使签名仍正确，PyJWT 也会抛出 `ExpiredSignatureError`。因此“验签通过”不等于“token 仍可使用”。

认证配置来自被 Git 忽略的 `.env`：

- `JWT_SECRET_KEY`：真实签名密钥；
- `JWT_ALGORITHM`：当前为 HS256；
- `ACCESS_TOKEN_EXPIRE_MINUTES`：当前默认 30 分钟。

`.env.example` 只保留明显的密钥占位值和非秘密配置，真实密钥绝不进入 Git、日志、截图或聊天内容。

## 4. Bearer 与 HTTP 请求头

成功登录返回：

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

`Bearer` 是 HTTP 认证方案名称，意思是“持有这枚 token 的客户端可以使用它”。JWT 本身不包含 `Bearer`；客户端发送请求时按标准把它包装在请求头中：

```http
Authorization: Bearer <access_token>
```

`Authorization` 由客户端发给服务端，携带认证信息。认证失败时服务端返回：

```http
WWW-Authenticate: Bearer
```

它告诉客户端该接口要求 Bearer 认证。Header 名称不区分大小写。

`OAuth2PasswordRequestForm` 的表单字段名固定为 `username` 和 `password`；本项目把 `username` 当作邮箱使用。因此登录请求是表单数据，不是 JSON。

## 5. `Depends` 如何还原当前用户

`OAuth2PasswordBearer(tokenUrl="token")` 只从请求头提取 token：

```text
Authorization: Bearer eyJ...
    -> 提取 eyJ...
```

它不验证签名、不检查过期时间，也不查询数据库。

依赖链由 FastAPI 自动解析：

```text
GET /users/me
    -> Depends(get_current_user)
        -> Depends(oauth2_scheme) 取得纯 JWT
        -> Depends(get_session) 取得本次请求的 Session
    -> decode_access_token 验签并检查 exp、sub
    -> session.get(User, user_id)
    -> 返回 User ORM 对象
```

缺少 `Authorization` 请求头时，`oauth2_scheme` 会先自动返回 401；此时 `get_current_user()` 不会执行。token 损坏、伪造、过期、`sub` 无法转为整数，或 token 对应的用户已删除时，`get_current_user()` 统一返回 401。

## 6. 为什么认证失败要统一处理

`authenticate_user()` 对以下两种情况都返回 `None`：

- 邮箱不存在；
- 邮箱存在但密码错误。

`POST /token` 对外把两者统一成相同的 401、错误消息和 `WWW-Authenticate: Bearer`，避免攻击者根据不同提示枚举哪些邮箱已注册。

认证依赖只捕获预期的 `InvalidTokenError` 与 `ValueError`，而不捕获所有 `Exception`。这样 JWT 或 `sub` 的认证失败会变成 401；数据库故障或编程错误仍会作为真正的服务端错误暴露出来，便于排查。

## 7. 测试与手工验收

安全单元测试覆盖：

- 新 token 可被正确解码，`sub` 为字符串且含有 `exp`；
- 使用错误密钥签名的 token 被拒绝；
- 已过期 token 被拒绝。

接口与 CRUD 测试覆盖：

- 正确凭据登录并返回 Bearer token；
- 错误密码与未知邮箱返回相同 401；
- token 可以访问 `/users/me`，且响应不含密码或密码哈希；
- 缺少 Authorization 请求头、损坏 token、token 对应用户已删除均返回 401；
- 原有注册与 Item 测试继续通过。

自动化验收结果：`36 passed`。

真实 PostgreSQL 与 Swagger 手工验收结果：

```text
POST /users      -> 201
POST /token      -> 200
Swagger Authorize -> 授权成功
GET /users/me    -> 200
```

Swagger 的 Authorize 会调用 `/token`、暂时保存得到的 token，并在后续受保护请求中自动附加 `Authorization: Bearer <token>`。它不实现角色或权限管理。

## 8. 当前未实现的内容

- refresh token；
- 注销和 token 黑名单；
- 角色与权限；
- 第三方 OAuth 登录；
- Item 的用户归属关系。

这些内容超出当前最小认证闭环，留到后续按项目需求逐步增加。

## 自测题

1. 注册、登录和读取当前用户分别做什么？
2. JWT 为什么不是加密？为什么不能把密码放进 Payload？
3. Header、Payload、Signature 分别负责什么？
4. 攻击者为什么可以读 Payload，却无法伪造可被服务端接受的 token？
5. `sub` 为什么写成字符串，在哪里转回整数？
6. 签名正确但 `exp` 过期时，为什么仍要拒绝 token？
7. `Authorization: Bearer <token>` 与 `WWW-Authenticate: Bearer` 分别由谁发送？
8. `OAuth2PasswordBearer` 与 `get_current_user` 分别负责什么？
9. 为什么未知邮箱和错误密码必须返回相同的对外提示？
10. 为什么 token 对应用户被删除后仍要查询数据库，而不是只信任 JWT？

## 今天真正需要记住的内容

```text
用户名和密码只用于登录
    -> 服务端验证密码哈希
    -> 签发带 sub、exp 和签名的短期 JWT
    -> 客户端在 Authorization 请求头中携带 Bearer token
    -> 服务端验签、检查过期时间、查询当前用户
    -> 响应模型只返回允许公开的数据
```

JWT 证明 token 由受信任的服务端签发且未被篡改；数据库查询确认该用户当前仍存在。两者共同构成当前项目的最小认证闭环。
