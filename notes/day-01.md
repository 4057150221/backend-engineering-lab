# Day 1 复盘：从 Python 函数到 HTTP CRUD

## 一句话成果

使用 FastAPI、Pydantic 和内存字典实现了 Item REST CRUD，并用 pytest 自动验证正常和异常流程。

## 主链路

```text
客户端发送HTTP请求
        ↓
FastAPI根据方法和路径匹配路由
        ↓
解析路径参数、查询参数和JSON请求体
        ↓
Pydantic执行类型转换与字段校验
        ↓
路由函数执行业务操作
        ↓
Python对象被序列化为JSON响应
        ↓
pytest检查状态码和响应内容
```

## 1. Python 运行环境

- Python 解释器负责执行 Python 代码。
- `.venv` 是项目独立的 Python 环境，用来隔离解释器和第三方包版本。
- 一个 `.py` 文件通常是一个模块。
- 包是可包含多个模块的目录；`app/__init__.py` 明确了 `app` 的包身份。
- `import` 会寻找并加载模块，使当前代码可以使用其中定义的名称。

常用命令：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pip install -r requirements-day1.txt
```

虚拟环境只隔离 Python 相关内容。`rg` 是独立的 ripgrep 程序，不属于虚拟环境；未安装时可使用：

```powershell
Get-ChildItem tests -Recurse -File
```

## 2. 类、对象与类型标注

```python
class Book:
    def __init__(self, title: str) -> None:
        self.title = title


book = Book("Python")
```

- `Book` 是类，描述一类对象的属性和行为。
- `book` 是根据类创建的实例。
- `self.title` 是对象属性，右侧 `title` 是传入参数。
- `-> None`、`-> Item` 是返回类型标注，不会转换返回值。
- 真正返回什么由 `return` 后面的表达式决定。

Pydantic 类与普通类不同：Pydantic 会在运行时读取类型标注并校验数据。它也可能执行允许的转换，例如将字符串 `"123"` 解析为整数 123。

## 3. HTTP 基础

一次 HTTP 交互需要关注：

- 方法：希望执行什么操作；
- 路径：操作哪个资源；
- 查询参数：补充读取条件；
- 请求体：客户端发给服务器的数据；
- 状态码：服务器处理结果；
- 响应体：服务器返回给客户端的数据。

当前接口：

| HTTP | 路径 | CRUD | 作用 | 成功状态码 |
|---|---|---|---|---:|
| `POST` | `/items` | Create | 创建资源 | 201 |
| `GET` | `/items/{item_id}` | Read | 查询单个资源 | 200 |
| `GET` | `/items` | Read | 分页查询资源 | 200 |
| `PUT` | `/items/{item_id}` | Update | 替换可修改字段 | 200 |
| `DELETE` | `/items/{item_id}` | Delete | 删除资源 | 204 |

CRUD 是 Create、Read、Update、Delete 的缩写。

相同 `POST` 连续发送通常会创建多个资源，因此通常不幂等。相同 `PUT` 连续执行后，资源最终状态通常不再变化，因此通常幂等。

## 4. FastAPI 路由

```python
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- `@app.get` 决定 HTTP 方法；
- `"/health"` 决定访问路径；
- 函数名不决定 URL；
- Python 字典会被 FastAPI 序列化为 JSON。

开发服务器：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 9000
```

本机 8000 端口位于 Windows 排除范围，因此使用 9000。`WinError 10013` 当时属于端口绑定问题，不是 FastAPI 代码错误。

Swagger UI：

```text
http://127.0.0.1:9000/docs
```

## 5. 路径参数与查询参数

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    ...
```

`item_id` 出现在路径模板中，因此是路径参数。FastAPI 会把 URL 文本转换为 `int`；`/items/abc` 无法转换，在进入函数前返回 422。

```python
def read_items(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    ...
```

`offset`、`limit` 没有出现在路径模板中，因此是查询参数：

```text
GET /items?offset=10&limit=5
```

- `offset`：跳过多少条；
- `limit`：最多读取多少条。

## 6. Pydantic 与 `Field`

```python
class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=300)
```

Pydantic Schema 是运行时数据契约，负责：

- 声明允许的字段；
- 检查字段类型；
- 执行长度等约束；
- 必要时执行允许的类型转换；
- 数据不合法时产生结构化错误。

`str | None` 表示值可以是字符串或 `None`；`default=None` 表示未提供时使用 `None`。Python `None` 序列化到 JSON 后是 `null`。

## 7. 404、422 与 204

- 404：请求格式正确，但指定资源不存在，需要业务代码主动抛出 `HTTPException`。
- 422：输入数据或参数不符合类型和约束，通常由 FastAPI/Pydantic 自动返回。
- 204：操作成功但没有响应体，适合删除成功。

```python
if item is None:
    raise HTTPException(status_code=404, detail="Item not found")
```

`raise` 会中断当前函数，不会继续执行后续语句。

## 8. Day 1 的内存存储

```python
items: dict[int, ItemRead] = {}
```

这个字典只是数据库替身：

- 程序关闭后数据消失；
- 无法提供真正的事务；
- 不适合可靠并发；
- 主要用于先学 HTTP CRUD，再替换存储实现。

Day 1 的请求和响应对象生命周期：

```text
JSON
→ ItemCreate
→ 路由函数
→ ItemRead
→ 内存字典
→ JSON响应
```

## 9. 自动化测试

```python
response = client.get("/health")
assert response.status_code == 200
assert response.json() == {"status": "ok"}
```

测试可以自动重复检查正常和异常流程，防止后续重构破坏已有行为。

Day 1 使用 `setup_function()` 在每条测试前清空内存字典，保证测试不依赖执行顺序。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Day 1 踩坑记录

1. 8000 端口无法绑定，改用 9000。
2. 返回字典后，客户端实际收到 JSON。
3. 路径类型错误由 FastAPI 返回 422，函数不会执行。
4. 404 与 422 不同：一个是资源不存在，一个是输入不合法。
5. 调用函数但不接收返回值时，返回结果会被丢弃。
6. 代码中的空白行可以保留，但空白行内不应含隐藏空格。

## Day 1 自测

1. 哪段代码决定 `/health` 的方法和路径？
2. 请求体和响应体分别是谁发给谁？
3. `ItemCreate` 为什么不仅是类型提示？
4. 缺少 `title` 为什么在进入路由函数前返回 422？
5. 404 与 422 有什么区别？
6. 路径参数和查询参数在 URL 中的位置有什么区别？
7. 为什么删除成功使用 204 时不能返回 JSON？
8. 为什么每条内存 CRUD 测试前要清空字典？
9. `-> ItemRead` 会自动把返回值转换成 `ItemRead` 吗？
10. `POST` 与 `PUT` 的幂等性通常有什么区别？

### 简短答案

1. `@app.get("/health")`。
2. 请求体由客户端发给服务器，响应体由服务器发给客户端。
3. 它继承 `BaseModel`，Pydantic 会在运行时执行解析和校验。
4. FastAPI 在调用函数前已经让 Pydantic 完成验证。
5. 404 是资源不存在，422 是输入不符合契约。
6. 路径参数位于路径段，查询参数位于 `?` 后。
7. 204 的语义就是成功但无响应内容。
8. 保证测试相互独立、不依赖执行顺序。
9. 不会，箭头只是类型标注。
10. `POST` 常创建多个资源，`PUT` 重复执行后最终状态通常相同。
