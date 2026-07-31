#!/bin/bash

# LangChain Docs - 快速启动脚本
# 功能：根据用户需求选择静态或动态模式

set -e

MODE="${1:-static}"

echo "======================================"
echo "LangChain 中文文档服务"
echo "======================================"
echo ""

if [ "$MODE" = "static" ]; then
    echo "📦 模式：静态 (预构建 + Nginx 服务)"
    echo "   ✅ 页面切换快"
    echo "   ✅ 资源占用低"
    echo "   ⚠️  需要手动重建才能看到修改"
    echo ""
    echo "步骤:"
    echo "  1. 构建中文 overlay"
    echo "  2. 编译文档到 build/"
    echo "  3. 启动 Docker 容器 (Nginx 服务静态文件)"
    echo ""
    
    # 构建中文 overlay
    echo "🔧 步骤 1: 构建中文 overlay..."
    uv run python -m scripts.zh.overlay build
    
    # 编译文档
    echo "🔧 步骤 2: 编译文档..."
    PYTHONPATH=$(pwd) uv run pipeline build --src-dir .generated/zh/src --build-dir build
    
    # 重启容器
    echo "🔧 步骤 3: 启动/重启 Docker 容器..."
    docker compose down langchain-docs-static 2>/dev/null || true
    docker compose up -d --build langchain-docs-static
    
    echo ""
    echo "✅ 服务已启动！访问 http://localhost:33030"
    echo "💡 提示：修改文档后需要重新运行此脚本"
    
elif [ "$MODE" = "dev" ]; then
    echo "📝 模式：开发 (文件监听 + 实时重载)"
    echo "   ✅ 自动检测文件变化"
    echo "   ✅ 实时预览修改"
    echo "   ⚠️  页面切换较慢（每次编译）"
    echo ""
    echo "启动 Docker 开发容器..."
    
    # 使用现有的动态模式
    docker compose down langchain-docs-dev 2>/dev/null || true
    docker compose up langchain-docs-dev
    
else
    echo "用法：$0 [static|dev]"
    echo ""
    echo "参数:"
    echo "  static  - 静态模式（推荐用于浏览）"
    echo "  dev     - 开发模式（推荐用于编辑）"
    echo ""
    echo "示例:"
    echo "  $0 static   # 启动静态服务"
    echo "  $0 dev      # 启动开发服务"
    exit 1
fi
