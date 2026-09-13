# Day 5：登录、JWT 与当前用户

## 今日目标

完成认证最小闭环：

```text
POST /token（邮箱和密码）
    -> 查询用户
    -> 验证密码哈希
    -> 生成有签名、有过期时间的JWT
    -> 返回access_token

GET /users/me（Authorization: Bearer <token>）
    -> 提取Bearer token
    -> 验证签名和过期时间
    -> 从sub取得用户ID
    -> 查询用户
    -> 返回UserRead
```

完成后应当能解释：

- 注册和登录的区别；
- JWT为什么是“签名”而不是“加密”；
- JWT的Header、Payload、Signature分别做什么；
- `sub`和`exp`声明的含义；
- Bearer token如何放进HTTP请求；
- 为什么错误邮箱和错误密码应该返回相同提示；
- `Depends(oauth2_scheme)`如何取得token；
- 当前用户依赖如何把token还原成数据库用户。

## 今日边界

- 只实现access token，不实现refresh token；
- 使用HS256完成当前单体项目，不引入RSA密钥；
- token中只放字符串形式的用户ID和过期时间；
- token中不放密码、密码哈希或其他秘密；
- JWT密钥只保存在被Git忽略的`.env`中；
- 不实现注销、黑名单、角色、权限或第三方OAuth登录；
- Item资源归属留到Day 6。

## 检查点A：观察JWT，而不是先接FastAPI

安装今日依赖：

```powershell
python -m pip install -r requirements-day5.txt
```

在被Git忽略的`scratch/day_05_jwt_basics.py`中完成一个最小实验：

1. `import jwt`；
2. 准备一个只用于scratch实验的临时密钥；
3. payload包含字符串`sub`和UTC时间的`exp`；
4. 使用`jwt.encode(..., algorithm="HS256")`生成token；
5. 使用`jwt.decode(..., algorithms=["HS256"])`解码；
6. 打印token和解码后的payload；
7. 修改token中的任意一个字符，再观察解码失败。

实验前先预测：

1. JWT能否被任何拿到它的人读取payload？
2. 不知道密钥的人修改payload后，服务端能否发现？
3. token超过`exp`后，`decode()`会成功还是失败？

注意：JWT通常只做Base64URL编码和签名，并不加密payload。

## 检查点B：认证配置

在`Settings`中增加：

- JWT签名密钥；
- JWT算法，默认HS256；
- access token有效分钟数，默认30分钟。

使用Python标准库生成开发密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

把真实生成值写入`.env`，只把明显的占位值和非秘密配置写入`.env.example`。不要在聊天、截图、测试输出或Git diff中展示真实密钥。

## 检查点C：令牌Schema与安全函数

在`app/schemas.py`新增响应模型：

- `Token`：包含`access_token: str`和`token_type: str`。

在`app/security.py`增加两个职责明确的函数：

- 根据用户ID创建带`sub`、`exp`的JWT；
- 验证并解码JWT，取得`sub`。

建议令牌中的`sub`始终是字符串，即使用户主键是整数。把它转换回整数的动作放在读取当前用户的边界处。

新增安全单元测试，至少验证：

- 新token可以被正确解码；
- `sub`与原用户ID一致；
- 使用错误密钥签名或被篡改的token无法通过；
- 已过期token无法通过。

## 检查点D：验证登录凭据

在CRUD层增加认证函数：

```text
输入：session、email、明文密码
输出：匹配的User，或None
```

流程：

1. 按email查询用户；
2. 用户不存在时认证失败；
3. 用户存在但密码验证失败时认证失败；
4. 两者都正确时返回用户对象。

不要区分“邮箱不存在”和“密码错误”的对外错误信息，否则攻击者更容易枚举已注册邮箱。

## 检查点E：`POST /token`

使用`OAuth2PasswordRequestForm`接收表单数据。因为OAuth2表单字段名固定为`username`和`password`，本项目暂时把`username`当作email使用。

成功时返回：

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

邮箱或密码错误时统一返回401，并附带：

```text
WWW-Authenticate: Bearer
```

理解请求的`Content-Type`是表单格式，而不是注册接口使用的JSON。

## 检查点F：当前用户依赖与`GET /users/me`

创建`OAuth2PasswordBearer(tokenUrl="token")`。它负责从请求头提取Bearer token，但不负责验证JWT。

当前用户依赖负责：

1. 接收`oauth2_scheme`提取的token；
2. 解码并验证token；
3. 确认`sub`存在且能转换为用户ID；
4. 从数据库查询用户；
5. 任一步失败都统一返回401；
6. 成功则返回`User` ORM对象。

随后实现：

```text
GET /users/me -> UserRead
```

接口本身只需要依赖“当前用户”，不需要重复编写解析token和查询数据库的逻辑。

## 检查点G：接口测试

至少覆盖：

- 正确邮箱和密码能够登录；
- 返回`token_type=bearer`；
- token可以访问`/users/me`；
- `/users/me`返回对应用户且不泄露哈希；
- 错误密码返回401；
- 不存在的邮箱返回同样的401提示；
- 缺少Authorization头返回401；
- 伪造或损坏token返回401；
- token对应的用户已不存在时返回401；
- 原有注册和Item测试继续通过。

测试不要依赖固定用户ID，也不要断言JWT完整字符串，因为token中的时间和签名可能变化。

## 今日完成标准

- 能通过注册、登录、携带token访问当前用户接口；
- token有签名并带过期时间；
- JWT密钥没有进入Git；
- 所有认证失败使用一致的401响应；
- 自动化测试覆盖正常和异常认证链路；
- 能解释HTTP请求头、Bearer token、JWT验证和数据库查询如何连接。

## 建议提交

全部检查通过后：

```text
feat: add JWT authentication and current user
```
