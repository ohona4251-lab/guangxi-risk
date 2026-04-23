# Front

这个目录是独立前端，不依赖现有后端目录结构，也不会影响 `risk_workflow/` 下的 Python 工作流代码。

## 目录说明

- `index.html`：首页和详情弹层
- `styles.css`：页面样式
- `app.js`：页面交互
- `mock-data.js`：当前演示数据，后续可替换成真实接口返回

## 使用方式

直接用浏览器打开 `front/index.html` 即可预览。

如果你想本地起一个静态服务，也可以在仓库根目录执行：

```powershell
python -m http.server 8080
```

然后访问：

```text
http://localhost:8080/front/
```

## 后续对接后端

当前页面先使用 `mock-data.js`。

后续接入真实后端时，建议只改 `app.js` 的数据来源部分，例如：

1. 用 `fetch("/api/points")` 获取列表。
2. 用 `fetch("/api/points/{id}")` 获取详情。
3. 保持当前 DOM 结构不变，这样不会影响已经完成的页面排版。
