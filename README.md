<!-- 记录项目学习过程 -->

# my-agent 学习笔记

`my-agent` 是一个从零开始学习并构建 AI Agent 的项目。当前学习重点包括：

- Python 后端基础
- FastAPI 接口开发
- SQLite / SQLAlchemy 数据库存储
- RAG 文档检索流程
- LangChain / Chroma / PyTorch 基础概念
- 前端聊天与调试界面

## 1. 项目结构

当前项目分为前端和后端：

```text
my-agent/
├── backend/   # Python 后端
├── frontend/  # 前端界面
└── README.md  # 项目学习笔记
```

前端初始化方式：

```bash
pnpm create vite ./ --template react-ts
```

后端主要使用 Python 生态。

## 2. Python 基础

Python 是动态类型语言，变量本身不会强制绑定类型。但推荐写类型提示，因为它可以提升代码可读性、可维护性和编辑器提示效果。

### 2.1 类型提示

```python
from typing import List

nums: List[int] = [1, 2, 3]
```

含义：

- `List[int]` 表示这是一个整数列表
- 类型提示不一定会在运行时强制校验
- 主要用于代码提示、静态检查和团队协作

### 2.2 range()

`range()` 会生成一个整数序列的可迭代对象，常用于 `for` 循环。它不会一次性创建完整列表，因此比较省内存。

```python
for i in range(10):
    print(i)
```

输出从 `0` 到 `9`。

### 2.3 列表推导式

列表推导式可以用更短的写法生成列表。

```python
documents = [chunk.page_content for chunk in chunks]
```

等价于：

```python
documents = []
for chunk in chunks:
    content = chunk.page_content
    documents.append(content)
```

## 3. uv 项目管理

`uv` 是 Python 包、环境、版本管理工具，可以用来管理依赖和虚拟环境。

### 3.1 初始化项目

```bash
uv init project-name
```

生成结构示例：

```text
my-project/
├── .python-version   # uv 管理的 Python 版本文件
├── pyproject.toml    # 项目依赖和元数据
├── README.md         # 项目说明
└── main.py           # 主程序入口
```

### 3.2 创建虚拟环境

```bash
uv venv
```

虚拟环境用于隔离项目依赖，避免不同项目之间的包版本冲突。

### 3.3 激活虚拟环境

```bash
source .venv/bin/activate
```

激活后，当前终端会使用该项目虚拟环境里的 Python 和依赖。

## 4. 后端技术栈

| 技术 | 类型 | 作用 |
| --- | --- | --- |
| uv | Python 项目管理 | 管理 Python 环境、依赖和虚拟环境 |
| FastAPI | Web 框架 | 提供 AI Agent HTTP 接口 |
| Uvicorn | Web 服务器 | 启动 FastAPI 服务 |
| Pydantic | 数据模型 | 校验请求参数和结构化输出 |
| python-dotenv | 环境变量 | 加载 `.env` 配置 |
| httpx | HTTP 客户端 | 调用外部 API |
| OpenAI SDK | 大模型 SDK | 调用 LLM |
| loguru | 日志 | 统一日志输出 |
| LangChain | Agent / RAG 框架 | 封装 Prompt、Tool、RAG 等能力 |
| ChromaDB | 向量数据库 | 存储文档 embedding |
| SQLAlchemy | ORM | 通过对象方式操作数据库 |
| SQLite | 数据库 | 本地轻量数据库 |
| pytest | 测试 | 单元测试 |
| Ruff | 代码规范 | lint 和 format |
| SSE / WebSocket | 实时通信 | AI 流式输出 |
| React | 前端 | Agent 聊天界面 |

## 5. Python 包与配置

### 5.1 `__init__.py`

`__init__.py` 是 Python 包里的特殊文件。它的作用是告诉 Python：这个目录可以作为一个包来导入。

示例：

```python
from app.api import routes
```

Python 3.3 以后即使没有 `__init__.py` 也可能工作，但实际项目中仍然建议保留，避免导入问题。

### 5.2 dotenv 环境变量

`.env` 用来保存本地配置，例如 API Key、模型名、服务地址。

```python
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("LLM_API_KEY")
```

流程：

1. `load_dotenv()` 把 `.env` 文件加载到当前 Python 进程。
2. `os.getenv("变量名")` 从环境变量中读取配置。

## 6. SQLite 和 SQLAlchemy

### 6.1 SQLite 是什么

SQLite 是轻量级关系型数据库。它不需要单独启动数据库服务，而是把数据直接存储在一个本地文件中。

适合：

- 本地开发
- 小型项目
- Demo 项目
- 轻量数据存储

### 6.2 ORM 是什么

ORM 全称是 Object-Relational Mapping，对象关系映射。

简单理解：

- 数据库表 -> Python 类
- 表字段 -> 类属性
- 一行数据 -> 一个对象

使用 ORM 后，可以少写 SQL，更多通过对象方式操作数据库。

### 6.3 SQLAlchemy 基本流程

```python
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()
```

核心步骤：

1. 创建数据库引擎：`engine = create_engine(...)`
2. 创建 Session 工厂：`SessionLocal = sessionmaker(bind=engine)`
3. 创建真正的 Session：`db = SessionLocal()`
4. 操作数据库：`db.query(...)`、`db.add(...)`、`db.commit()`

### 6.4 `check_same_thread=False`

SQLite 默认要求：数据库连接只能在创建它的线程中使用。

FastAPI 是异步 Web 框架，可能涉及多线程处理请求。因此通常会配置：

```python
connect_args={"check_same_thread": False}
```

意思是允许 SQLite 连接跨线程使用。

### 6.5 `sessionmaker` 参数

```python
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
```

参数说明：

- `autocommit=False`：不自动提交事务，需要手动 `db.commit()`
- `autoflush=False`：不自动把临时修改同步到数据库
- `bind=engine`：绑定数据库引擎

`autoflush=True` 时，只要执行查询，SQLAlchemy 可能会先自动 `flush` 一次：

```python
user = User(name="test")
session.add(user)

users = session.query(User).all()
```

好处是查询能看到刚刚 `add` 的对象；坏处是自动执行 SQL，行为不够可控。

## 7. pathlib Path

`Path` 是 Python 标准库 `pathlib` 提供的路径对象，比字符串路径更清晰、跨平台。

```python
from pathlib import Path

p = Path("xxx")
```

### 7.1 常用属性

```python
p.name        # 文件名或最后一级目录名
p.stem        # 不带后缀的文件名
p.suffix      # 文件后缀，例如 .md、.txt、.py
p.suffixes    # 多后缀列表，例如 ['.tar', '.gz']
p.parent      # 上一级目录
p.parents     # 所有上级目录
p.resolve()   # 转为绝对路径
p.absolute()  # 绝对路径
```

### 7.2 路径拼接

推荐使用 `/` 拼接路径：

```python
p2 = p / "subdir" / "test.md"
```

### 7.3 路径重命名

```python
p.with_name("new.txt")   # 替换完整文件名
p.with_stem("new_name")  # 替换文件名主体，保留后缀
p.with_suffix(".pdf")    # 替换文件后缀
```

### 7.4 判断文件或目录

```python
p.exists()       # 是否存在
p.is_file()      # 是否是文件
p.is_dir()       # 是否是目录
p.is_absolute()  # 是否是绝对路径
```

### 7.5 创建和删除

```python
p.mkdir(exist_ok=True, parents=True)
p.unlink(missing_ok=True)
p.rmdir()
```

说明：

- `parents=True`：递归创建多级目录
- `exist_ok=True`：目录已存在时不报错
- `missing_ok=True`：文件不存在时不报错

### 7.6 遍历目录

```python
# 当前目录下所有 md 文件
p.glob("*.md")

# 递归查找所有 md 文件
p.glob("**/*.md")

# 遍历当前目录下所有子文件和子目录
for item in p.iterdir():
    print(item)
```

### 7.7 文件读写

```python
text = p.read_text(encoding="utf-8")
data = p.read_bytes()

p.write_text("内容", encoding="utf-8")
p.write_bytes(b"xxx")
```

## 8. PyTorch 基础

PyTorch 是 AI 和深度学习领域常用框架，Python 包名通常是 `torch`。

```python
import torch
```

一句话理解：PyTorch 用 Python 构建和运行神经网络。

### 8.1 PyTorch 核心能力

| 能力 | 说明 |
| --- | --- |
| 张量计算 | 类似 NumPy 的增强数组计算 |
| GPU 加速 | 使用显卡加速计算 |
| 深度学习 | 构建神经网络 |
| 自动求导 | 自动计算梯度 |
| 模型训练 | 训练 AI 模型 |
| 模型推理 | 运行 AI 模型 |

### 8.2 Tensor

Tensor 是 PyTorch 最核心的数据结构。

可以理解为：支持 GPU 和自动求导的数组。

```python
import torch

x = torch.tensor([1, 2, 3])
print(x)
```

输出：

```text
tensor([1, 2, 3])
```

### 8.3 Tensor 运算

```python
import torch

a = torch.tensor([1, 2])
b = torch.tensor([3, 4])

print(a + b)
```

输出：

```text
tensor([4, 6])
```

### 8.4 GPU 加速

CPU 计算：

```python
x = torch.tensor([1, 2, 3])
```

GPU 计算：

```python
x = torch.tensor([1, 2, 3]).cuda()
```

检查 GPU 是否可用：

```python
import torch

print(torch.cuda.is_available())
```

### 8.5 神经网络

```python
import torch.nn as nn

model = nn.Linear(10, 1)
```

含义：创建一个线性神经网络层。

### 8.6 自动求导

```python
import torch

x = torch.tensor(2.0, requires_grad=True)
y = x ** 2
y.backward()

print(x.grad)
```

输出：

```text
tensor(4.)
```

自动求导是反向传播、模型训练、梯度下降的基础。

### 8.7 常见模块

| 模块 | 作用 |
| --- | --- |
| `torch` | 核心模块 |
| `torch.nn` | 神经网络 |
| `torch.optim` | 优化器 |
| `torch.cuda` | GPU |
| `torch.autograd` | 自动求导 |
| `torch.utils.data` | 数据集处理 |

### 8.8 PyTorch 在 AI Agent 中的作用

在当前 Agent / RAG / LLM 项目中，通常不会直接训练模型，更多是调用现成模型：

- OpenAI API
- DeepSeek API
- LangChain
- Transformers
- 本地 embedding 模型

Transformers 底层大量依赖 PyTorch：

```python
from transformers import AutoModel

model = AutoModel.from_pretrained("bert-base-uncased")
```

这个 `model` 底层就是 PyTorch 模型。

### 8.9 学习顺序建议

1. Tensor、CUDA、基础运算
2. `nn.Module`、`forward`、Dataset
3. 反向传播、训练流程、优化器
4. Transformers、本地模型、Embedding、微调

当前项目建议优先学习：

- FastAPI
- LangChain
- RAG
- Tool Calling

之后再深入：

- Transformers
- PyTorch
- 本地模型
- 模型微调

## 9. LangChain 基础

LangChain 是构建 Agent / RAG 应用的框架，常用于封装：

- Prompt
- Tool
- Document
- Retriever
- Chain
- Agent

### 9.1 Document 对象

LangChain 的 `Document` 表示一段文档内容，包含正文和元数据。

```python
from langchain_core.documents import Document

doc = Document(
    page_content="xx",
    metadata={"source": "tweet"},
    id=1,
)
```

字段说明：

- `page_content`：正文内容
- `metadata`：元数据，例如来源文件、页码、分片序号
- `id`：唯一标识，可选

### 9.2 文档分片后的结构

RAG 中通常会先把长文档切成多个分片：

```python
chunks = splitter.split_documents(documents)
```

结果类似：

```python
chunks = [
    Document(
        page_content="xx",
        metadata={"source": "xx"},
        id=1,
    ),
]
```

这些分片会被向量化，然后写入 ChromaDB，后续根据用户问题召回相关内容。

## 10. AI 技术栈关系

当前项目的大致技术链路：

```text
Python
  ↓
FastAPI
  ↓
LangChain
  ↓
RAG / Tool Calling
  ↓
Agent
```

模型相关底层链路：

```text
PyTorch
  ↓
Transformers
  ↓
Embedding / LLM
  ↓
Agent / RAG
```

前端类比帮助理解：

| AI 概念 | 前端类比 |
| --- | --- |
| `torch` | React Runtime |
| `tensor` | state |
| `nn.Module` | component |
| `forward` | render |
| `backward` | diff / update |
| CUDA | GPU 渲染 |
