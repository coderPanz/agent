---
name: 提交信息规范
description: 提交代码时的信息格式规范（中文 + 结构化）
metadata:
  type: feedback
  updated: 2026-05-16
---

## 规范要求

**所有 git commit 信息必须使用中文**，结构化格式如下：

```
feat: 功能描述

**分类标题1:**
- 具体改动点1
- 具体改动点2

**分类标题2:**
- 具体改动点1

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>
```

## 提交类型前缀（中文）

| 前缀 | 含义 | 示例 |
|------|------|------|
| `feat:` | 新功能、新工具、新模块 | `feat: 新增天气查询工具` |
| `fix:` | Bug 修复 | `fix: 修复 vite 代理端口错误` |
| `refactor:` | 代码重构、优化 | `refactor: 优化 Agent 执行流程` |
| `docs:` | 文档更新、方案文档 | `docs: 补充天气查询实现文档` |
| `chore:` | 配置、依赖更新 | `chore: 更新依赖版本` |

## 示例

### 示例 1：多文件改动

```
feat: 完善前端显示和天气查询功能

**前端改进:**
- 修复 vite proxy 指向后端正确端口 8000
- 添加 react-markdown 渲染 Markdown 内容
- 优化消息显示样式（标题、代码块、列表、表格等格式支持）

**后端功能:**
- 新增天气查询工具技术实现文档
- 包含 WeatherService、tool 注册、测试方案、常见问题

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>
```

### 示例 2：单一功能

```
fix: 修复后端 context_builder 中的消息类型错误

使用 state.messages 而非 state.message，确保正确获取对话历史。

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>
```

## 何时使用

- **每次提交代码**时，都使用规范的中文提交信息
- 中文提交信息帮助项目保持一致性，便于日后 git log 查阅
- Co-Author 行是与 Claude 协作的标志，保留即可

## 如何执行

使用 `git commit` 时，通过 HEREDOC 传入中文信息：

```bash
git commit -m "$(cat <<'EOF'
feat: 功能描述

**分类:**
- 改动1
- 改动2

Co-Authored-By: Claude Sonnet 4 <noreply@anthropic.com>
EOF
)"
```

> 为什么不在 git 配置中设置默认提交信息？因为配置应该保留在项目级别（`.claude/settings.json` 或项目 README），不在全局 git 配置中修改。
