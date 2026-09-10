# Day 4：用户注册与密码哈希

## 今日目标

完成一条可测试的用户注册链路：

```text
POST /users
    ↓
UserCreate校验邮箱和密码
    ↓
检查邮箱是否已注册
    ↓
使用Argon2计算密码哈希
    ↓
User ORM对象写入PostgreSQL
    ↓
UserRead只返回id和email
```

完成后应当能解释：

- 哈希与加密有什么不同；
- 为什么不能保存或返回明文密码；
- 为什么同一密码两次生成的哈希通常不同；
- `UserCreate`、`User` ORM模型和`UserRead`为什么必须分开；
- 应用层重复检查与数据库`UNIQUE`约束分别解决什么问题；
- 新增ORM模型后怎样生成、检查和执行第二份migration。

## 今日边界

- 只实现注册，不实现登录和JWT；
- 不把密码或哈希写进日志和API响应；
- 不自己发明密码哈希算法；
- 使用`pwdlib`推荐配置，目前对应Argon2；
- 不创建Item与User的外键关系，资源归属留到后续；
- migration先在独立迁移数据库验证，再升级开发数据库。

## 检查点A：观察密码哈希

安装今日依赖：

```powershell
python -m pip install -r requirements-day4.txt
```

验证：

```powershell
python -c "from pwdlib import PasswordHash; from pydantic import EmailStr; print(PasswordHash.recommended()); print(EmailStr)"
```

在被Git忽略的`scratch/day_04_password_hashing.py`中：

1. 创建`PasswordHash.recommended()`实例；
2. 对同一个明文密码调用两次`hash(...)`；
3. 打印两个哈希是否相等；
4. 分别用正确密码、错误密码调用`verify(...)`；
5. 只打印哈希和布尔结果，不打印真实个人密码。

运行前先预测三个布尔值。理解随机salt的作用后再进入正式代码。

## 检查点B：安全工具与Pydantic模型

新增`app/security.py`：

- 模块级创建一个推荐的`PasswordHash`实例；
- `hash_password(password: str) -> str`返回密码哈希；
- `verify_password(plain_password: str, hashed_password: str) -> bool`验证密码。

在`app/schemas.py`新增：

- `UserCreate`：`email`使用`EmailStr`，`password`长度8到128；
- `UserRead`：允许从ORM属性读取，只包含`id`和`email`。

新增`tests/test_security.py`，至少验证：

- 哈希不等于明文；
- 正确密码验证成功；
- 错误密码验证失败。

## 检查点C：User ORM模型与第二份迁移

在`app/models.py`新增`User`：

- 表名`users`；
- 整数主键`id`；
- `email`为最长255的非空唯一字符串；
- `hashed_password`为最长255的非空字符串。

随后：

1. 确认当前数据库是`backend_lab`；
2. 生成`create users table` migration；
3. 人工检查`revision`、`down_revision`、列、主键和唯一约束；
4. 切换到`backend_lab_migration`执行并验证；
5. 切回`backend_lab`执行并验证。

第二份迁移的`down_revision`必须等于第一份迁移ID：

```text
e5f21096bb73
```

## 检查点D：注册CRUD与接口

在`app/crud.py`增加：

- 按email查询用户；
- 创建用户，写入`hashed_password`而不是明文密码。

在`app/main.py`增加`POST /users`：

- 成功返回201和`UserRead`；
- 已存在的email返回409；
- 响应中不得出现`password`或`hashed_password`。

## 检查点E：注册测试

更新测试数据库清理fixture，并至少覆盖：

- 注册成功；
- 响应不泄露密码与哈希；
- 数据库保存哈希而不是明文；
- 保存的哈希可以验证原密码；
- 重复email返回409；
- 非法email返回422；
- 少于8个字符的密码返回422。

## 今日完成标准

- PostgreSQL存在由第二份migration创建的`users`表；
- `email`唯一性同时由接口行为和数据库约束保护；
- 数据库与响应中都没有明文密码；
- 安全工具与注册接口均有自动化测试；
- 原有Item测试继续通过；
- 能从请求模型、哈希、ORM、事务一路解释到响应模型。

## 建议提交

全部检查通过后：

```text
feat: add user registration with password hashing
```
