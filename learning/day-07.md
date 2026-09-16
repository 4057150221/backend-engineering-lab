# Day 7：列表分页、筛选与排序

## 今日目标

把 `GET /applications` 从"只能翻页"升级成"能按条件查、能排序"：

```text
GET /applications?status=applied&company=acme&sort=-applied_at&offset=0&limit=10
    -> 按当前用户过滤（已有）
    -> 再按 status 精确匹配（新增，可选）
    -> 再按 company 模糊匹配（新增，可选）
    -> 再按 sort 指定的字段和方向排序（新增，默认按 id 升序保持兼容）
    -> 最后 offset/limit 分页（已有）
```

完成后应当能解释：

- 为什么筛选/排序用 query 参数而不是塞进请求体（GET 的语义、可以被收藏成一个链接、可以被浏览器/代理缓存）；
- 为什么排序字段要用白名单限制，而不是直接把用户传的字符串拼进 `ORDER BY`；
- `ilike` 和 `like` 的区别，以及这次为什么选 `ilike`；
- 为什么"筛选/排序"和"按 owner_id 隔离"两件事不能互相覆盖——加了新的 `where` 条件之后，原来的隔离条件还必须在。

## 今日边界

- 只做单字段排序，不做多字段组合排序（如 `sort=status,-applied_at`）；
- `company` 只做包含匹配，不做全文搜索、不接入搜索引擎；
- 不新增筛选字段以外的能力（不做日期范围筛选、不做"我最近浏览"之类的功能）；
- 响应体结构不变，仍然是 `list[ApplicationRead]`，不额外返回 `total` 总数（如果面试时被问"要不要返回总数方便前端做分页控件"，可以口头讨论，但这次不实现）；
- 不引入 Elasticsearch/全文索引之类的重型方案，PostgreSQL 的 `ILIKE` 对这个数据量完全够用。

## 检查点A：设计 `sort` 参数的语法与白名单

先在纸上/注释里想清楚，再写代码：

1. `sort` 是一个字符串 query 参数，格式为 `field` 或 `-field`（前缀 `-` 表示降序）。
2. 允许排序的字段只有 `id` 和 `applied_at`——写一个显式的白名单（比如 `{"id", "applied_at"}` 或者一个 dict 映射到 ORM 列），不允许的字段应该被拒绝，而不是被静默忽略或者报 500。
3. 想清楚：如果直接做 `getattr(Application, user_input)` 会有什么风险？（提示：不是 SQL 注入，SQLAlchemy 的 `order_by` 不会拼字符串到 SQL 里，但 `getattr` 在没有白名单时可能让用户探测到模型上任意属性/方法的存在，也可能因为传入错误属性名导致 500 而不是可控的 4xx。）
4. 非法的 `sort` 值应该返回什么状态码？参考项目里已有的错误处理风格（`_get_application_or_404` 用的是显式 `raise HTTPException`），这次可以用同样的方式，选一个合适的 4xx（`400` 还是 `422`，想清楚两者的语义区别再选，写在你的复盘笔记里）。

## 检查点B：`app/schemas.py` 加校验

给筛选/排序参数加一层 schema 校验，而不是散落在路由函数签名里裸写字符串比较。可以考虑：

- 复用已有的 `ApplicationStatus` 枚举给 `status` 筛选参数做类型约束（非法值会被 FastAPI 自动转成 422，不用你手写）；
- `sort` 是否需要专门的类型（比如一个小的校验函数或 `Literal`/`Enum`）取决于你觉得放在 schema 里还是路由函数里更清楚——两种都能接受，选一种并能说明为什么。

## 检查点C：`app/crud.py::get_applications` 扩展查询

现在的实现：

```python
def get_applications(session, owner_id, offset, limit):
    statement = (
        select(Application)
        .where(Application.owner_id == owner_id)
        .order_by(Application.id)
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())
```

改造方向（不是标准答案，自己组织代码结构）：

- 新增 `status: ApplicationStatus | None` 和 `company: str | None` 参数，为 `None` 时不加对应的 `where` 条件；
- `company` 用 `Application.company.ilike(f"%{company}%")`；
- `sort` 用白名单映射到 ORM 列，再判断方向调用 `.asc()` / `.desc()`，替换掉写死的 `.order_by(Application.id)`；
- 注意 `Application.owner_id == owner_id` 这个条件必须保留且始终生效，不能因为加了新的筛选逻辑而被误删或被新条件覆盖。

## 检查点D：`app/main.py::read_applications` 接入新参数

路由函数签名里用 `Query(...)` 声明新增的 `status`、`company`、`sort` 参数（都设为可选，默认 `None`），透传给 `crud.get_applications`。想一下参数校验失败时（比如非法 `sort`）应该在路由层拦截还是让 crud 层抛异常——保持现有代码风格中"路由层负责 HTTP 语义，crud 层负责数据库操作"的分工。

## 检查点E：接口测试

在 `tests/test_applications.py` 里新增测试，至少覆盖：

- 按 `status` 筛选，只返回匹配状态的记录；
- 按 `company` 模糊搜索（大小写不敏感），能匹配部分包含的关键字；
- 按 `applied_at` 升序/降序排序，顺序正确；
- 不传 `sort` 时保持原来按 `id` 升序的默认行为（老测试不应该因为这次改动而失败）；
- 传入白名单之外的 `sort` 字段，返回你选定的 4xx 状态码，而不是 500；
- 筛选/排序结果依然遵守 `owner_id` 隔离——用两个用户各自创建数据，确认筛选条件不会让 A 看到 B 的记录（这是最容易在重构时不小心破坏的地方，务必单独测）。

跑一遍现有测试，确认 44 个老测试全部还在通过：

```powershell
python -m pytest
```

## 今日完成标准

- `GET /applications` 支持 `status`、`company`、`sort` 三个可选 query 参数，互相独立、可以任意组合使用，也可以都不传（保持向后兼容）；
- 排序字段有白名单限制，非法值返回明确的 4xx 而不是 500 或被静默忽略；
- 新增测试全部通过，且原有 44 个测试不受影响；
- 能解释白名单排序的必要性、`ilike` 的作用、为什么筛选条件不能削弱 `owner_id` 隔离。

## 建议提交

全部检查通过后：

```text
feat: add filtering and sorting to applications list
```
