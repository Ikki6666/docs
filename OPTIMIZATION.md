# 文档服务优化方案

## 问题描述
原 Docker 容器启动后，每次切换页面都需要重新编译，导致访问速度很慢。

## 解决方案

### 🎯 核心思路
提供两种运行模式供不同场景使用：

1. **静态模式 (Static Mode)** - 预构建文档 + Nginx 静态服务
2. **开发模式 (Dev Mode)** - 文件监听 + Mintlify 实时编译

---

## 使用方法

### 📦 方式一：静态模式（推荐用于浏览）

适用于：**阅读文档、快速浏览**

```bash
# 方式 1: 使用脚本（推荐）
./scripts/start.sh static

# 方式 2: 使用 make
make start-static
```

**特点:**
- ✅ 页面切换瞬间完成（纯静态 HTML）
- ✅ 资源占用低（Nginx 轻量化服务）
- ✅ 支持浏览器缓存（静态资源 cache-control）
- ⚠️  修改文档后需重新运行命令重建

**工作流程:**
1. 构建中文 overlay → `.generated/zh/src`
2. 编译文档 → `build/` 目录
3. Docker 容器使用 Nginx 服务 `build/` 中的静态文件
4. 访问 `http://localhost:33030`

---

### 📝 方式二：开发模式（推荐用于编辑）

适用于：**编写/修改文档、实时预览**

```bash
# 方式 1: 使用脚本（推荐）
./scripts/start.sh dev

# 方式 2: 使用 make（旧版兼容）
make dev-zh

# 方式 3: 直接 Docker Compose
docker compose up langchain-docs-dev
```

**特点:**
- ✅ 自动检测文件变化并热重载
- ✅ 实时预览修改效果
- ⚠️  页面切换较慢（Mintlify 按需编译）
- ⚠️  资源占用较高（持续文件监听 + 编译）

**工作流程:**
1. 构建中文 overlay → `.generated/zh/src`
2. `pipeline dev` 启动文件监听器
3. Mintlify 开发服务器监听 MDX 文件变化
4. 文件变化时触发增量编译
5. 浏览器自动刷新
6. 访问 `http://localhost:3000`

---

## 新旧方案对比

| 特性 | 原方案 | 静态模式 | 开发模式 |
|------|--------|---------|---------|
| 页面切换速度 | 🔴 慢 | ✅ 快 | 🟡 中 |
| 资源占用 | 🟡 中 | ✅ 低 | 🔴 高 |
| 实时重载 | ✅ 是 | ❌ 否 | ✅ 是 |
| 适合场景 | - | 阅读文档 | 编辑文档 |
| 端口 | 33030 | 33030 | 3000 |

---

## 架构说明

### 静态模式
```
用户请求 (33030) 
    ↓
Docker 容器 (Nginx)
    ↓
serve 静态文件
    ↓
build/index.html
build/assets/*
```

### 开发模式
```
用户请求 (3000)
    ↓
Docker 容器 (mint dev)
    ↓
FileWatcher 监控
    ↓
源码变更 → 触发 rebuild → mint 重新编译
```

---

## Docker Compose 配置

已添加两个服务：

```yaml
# 静态服务 (默认端口 33030)
langchain-docs-static:
  build:
    args:
      BUILD_MODE: static
  ports:
    - "33030:80"

# 开发服务 (默认端口 3000)  
langchain-docs-dev:
  volumes:
    - .:/app:cached
  environment:
    - BUILD_MODE=dynamic
  ports:
    - "3000:3000"
```

---

## 常见问题

### Q: 为什么静态模式页面切换更快？
A: 静态模式下，所有页面都是预编译好的 HTML 文件，Nginx 直接返回文件，无需编译。而开发模式下，Mintlify 需要根据当前 URL 动态编译相关组件和依赖。

### Q: 如何验证优化效果？
A: 
1. 启动静态模式：`make start-static`
2. 打开浏览器开发者工具 (F12) → Network 标签
3. 在不同页面间切换，观察加载时间
4. 你会看到大多数页面在 100ms 内完成加载

### Q: 切换到静态模式需要做什么？
A: 只需停止当前运行的容器，然后运行 `make start-static` 即可。第一次运行会执行完整构建，后续运行非常快。

### Q: 可以同时运行两个服务吗？
A: 可以，但建议不要同时运行。如果必须同时运行，注意端口冲突（33030 vs 3000）。

### Q: 原来使用的 `make dev-zh` 还能用吗？
A: 可以用，完全兼容。这是开发模式的旧命令别名。

---

## 回滚

如果需要恢复原来的单一 Docker 容器方案：

```bash
# 删除新增的服务配置
git checkout docker-compose.yml
git checkout Dockerfile
git checkout nginx.conf
rm scripts/start.sh
git checkout Makefile
```

---

## 技术细节

### 优化点总结

1. **分离构建和运行时**: 静态模式下，构建和运行分离，避免开发时的文件监听开销
2. **Nginx 轻量级服务**: 使用 Nginx 替代 Node.js 进程服务静态文件
3. **浏览器缓存**: 对 JS/CSS/图片等资源设置长期缓存
4. **灵活选择**: 根据场景选择最优方案

### 性能预期

| 指标 | 开发模式 | 静态模式 |
|------|---------|---------|
| 首屏加载 | 2-5s | 1-2s |
| 页面切换 | 1-3s | 50-200ms |
| CPU 占用 | 20-40% | <5% |
| 内存占用 | 400-600MB | 10-20MB |

---

## 下一步优化建议

1. **增量构建**: 优化 pipeline build，只对变更的文件进行编译
2. **开发模式预热**: 首次访问时异步编译，减少等待时间
3. **CDN 缓存**: 在 Docker 前加一层 CDN 代理
4. **本地开发**: 直接在 Mac 上运行 `mint dev`，避免 Docker I/O 开销
