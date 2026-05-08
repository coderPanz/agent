<!-- 记录项目学习过程 -->
# 2026-05-06
my-agent 项目从零到一学习并构建ai智能体项目。

# python
Python 本身是动态类型语言，友好的类型提示：可以提高代码的可读性、可维护性、可扩展性。不强制约束类型，但是推荐使用。

range() 生成整数序列的可迭代对象，常用于for 循环、生成连续数字，不占大内存（不是直接生成列表）。

**列表推导式**
```python
# 列表推导式
documents = [chunk.page_content for chunk in chunks]

# 等价 普通 for 循环
documents = []
for chunk in chunks:
    content = chunk.page_content
    documents.append(content)
```

```python
for i in range(10):
    print(i)
```


```python
from typing import List
nums: List[int] = [1, 2, 3]
```

## 项目结构
前端：pnpm create vite ./ --template react-ts
后端：python 生态

### uv 项目管理
uv： Python 包 / 环境 / 版本三合一管理器

1. uv初始化项目cmd： uv init project-name
生成如下项目结构：
my-project/
├── .python-version   # uv 管理的 Python 版本文件
├── pyproject.toml    # uv 项目核心配置文件（依赖+元数据）
├── README.md         # 项目说明文档
└── main.py           # 你的主程序代码


2. uv 创建虚拟环境
cmd: uv venv, 创建虚拟环境的目的：隔离项目依赖，避免冲突。

3. 激活虚拟环境
cmd: source .venv/bin/activate, 激活虚拟环境的目的：在当前终端使用虚拟环境中的 Python 解释器。


### 后端技术栈汇总
| 技术            | 类型          | 一句话作用                |
| ------------- | ----------- | -------------------- |
| uv            | Python项目管理  | 管理 Python 环境、依赖、虚拟环境 |
| FastAPI       | Web框架       | 提供 AI Agent HTTP 接口  |
| Uvicorn       | Web服务器      | 启动 FastAPI 服务        |
| Pydantic      | 数据模型        | 校验请求参数和结构化输出         |
| python-dotenv | 环境变量        | 加载 `.env` 配置         |
| httpx         | HTTP客户端     | Agent 调用外部 API       |
| OpenAI SDK    | 大模型SDK      | 调用 LLM               |
| loguru        | 日志          | 统一日志输出               |
| LangChain     | Agent/RAG框架 | 封装 Prompt、Tool、RAG   |
| chromadb      | 向量数据库       | 存储文档 embedding       |
| tiktoken      | Token工具     | 计算上下文 token          |
| sqlalchemy    | ORM         | 数据库存储                |
| sqlite        | 数据库         | 本地轻量数据库              |
| pytest        | 测试          | 单元测试                 |
| Ruff          | 代码规范        | lint + format        |
| SSE/WebSocket | 实时通信        | AI 流式输出              |
| React/Vue     | 前端          | Agent 聊天界面           |


__init__.py 的作用：__init__.py 是 Python 包（package）中的一个特殊文件，它最核心的作用是：告诉 Python：这个目录是一个“包”,
cmd: from app.api import chat
tips: Python 3.3+ 后, 理论上不是必须，存在 Namespace Package 机制，但仍然建议添加，避免潜在问题。


dotenv 加载环境变量
```python
from dotenv import load_dotenv
# 将 .env 加载到当前 py 环境
load_dotenv()
# 从当前 py 环境读取
os.getenv("DEEPSEEK_API_KEY")
```

Path.home()：获取用户主目录：例如：/Users/yourname
Path(__file__).resolve().parents[n]：获取当前文件的父目录的第 n 级目录
parents[0]: 获取当前文件的父目录
parents[1]: 获取当前文件的父目录的父目录
parents[2]: 获取当前文件的父目录的父目录的父目录



## SQLite 数据库
SQLite 是一个轻量级的关系型数据库管理系统，它不需要单独的服务器进程或系统配置，而是直接把所有内容存储在单一的文件中。

什么是 ORM？
ORM（Object-Relational Mapping）是对象关系映射，它是一种将对象模型与关系模型进行映射的技术。
不需要直接使用 SQL 语句，而是通过对象的方式来操作数据库。

**check_same_thread=False的特殊机制**  
默认情况下：SQLite 连接只能在创建它的线程中使用，例如：在一个线程中创建一个 SQLite 连接，在另一个线程中无法使用该连接。
为了支持多线程，SQLite 提供了 check_same_thread=False 参数，使得 SQLite 连接可以在多个线程中使用。因为使用的的 FastAPI 框架是异步 + 多线程 Web 框架

**核心流程**
1. 创建数据库引擎: engine = create_engine(...)
2. 创建 Session 工厂: SessionLocal = sessionmaker(bind=engine)
3. 创建真正 Session: db = SessionLocal()
4. 操作数据库: db.query(...)


**sessionmaker 参数解释**
```python
# 创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

- autocommit=False: 不自动提交事务，确保事务可控，例如：db.add(user), 之后必须 db.commit() 才能将数据写入数据库
- autoflush=False: 关闭自动刷新，只有你手动调用 session.flush() 或 session.commit() 时，才会把数据同步到数据库。
- autoflush=True: 代码里的 新增 / 修改 / 删除 临时发送到数据库，数据只是暂存，其他的会话（另一个db = SessionLocal()拿不到，必须 commit 才能拿到）看不到，所以开启后默认行为是你只要执行查询，SQLAlchemy 就会自动先 flush 一次，
```python
user = User(name="test")
session.add(user)  # 还没 flush，也没 commit

# 只要你一查询 → 自动触发 flush
# 好处：能查到刚 add 的数据
# 坏处：频繁自动执行 SQL，性能差、不可控、容易出意外
users = session.query(User).all()
```

- bind=engine: 绑定数据库引擎


### Path
```python
from pathlib import Path
p = Path("xxx")   # 转为 Path 对象
```

p.name       # 文件名/最后一级目录名
p.stem       # 不带后缀的文件名
p.suffix     # 文件后缀  .md .txt .py
p.suffixes   # 多后缀列表  ['.tar', '.gz']
p.parent     # 上一级目录 Path对象
p.parents    # 所有上级目录迭代器
p.resolve()  # 转为**绝对路径**，自动补全、解析相对路径
p.absolute() # 绝对路径

#### 路径拼接 / 重构
```python
# 推荐用 / 拼接，跨平台兼容
p2 = p / "subdir" / "test.md"

# 替换文件名/后缀
p.with_name("new.txt")    # 替换整个文件名
p.with_stem("new_name")   # 替换纯文件名，保留后缀
p.with_suffix(".pdf")     # 替换文件后缀
```

#### 判断文件 / 目录类型
```python
p.exists()      # 是否存在
p.is_file()     # 是否是文件
p.is_dir()      # 是否是文件夹
p.is_absolute() # 是否是绝对路径
```

#### 目录创建 / 删除
```python
# 创建文件夹，存在不报错
p.mkdir(exist_ok=True, parents=True)  
# parents=True 递归创建多级目录 a/b/c

# 删除文件
p.unlink(missing_ok=True)  

# 删除空文件夹
p.rmdir()
```

#### 遍历目录
```python
# 当前目录下所有 md
p.glob("*.md")

# 递归所有子目录 + 所有 md
p.glob("**/*.md")

# 迭代遍历所有子文件/子目录
for item in p.iterdir():
    print(item)

for file in p.glob("**/*.md"):
    print(file)
```

#### 文件读写
```python
# 读文本
text = p.read_text(encoding="utf-8")

# 读字节
data = p.read_bytes()

# 写文本
p.write_text("内容", encoding="utf-8")

# 写字节
p.write_bytes(b"xxx")
```

## pytorch
PyTorch（通常导入名为 torch）是目前 AI / 深度学习领域最主流的框架之一。用 Python 构建和训练神经网络
PyTorch（torch）基础认知文档

一、PyTorch 是什么？

PyTorch 是当前 AI / 深度学习领域最主流的框架之一。

导入方式：

import torch

其中：

* PyTorch：框架名称
* torch：Python 包名

一句话理解：

用 Python 构建和训练神经网络

⸻

二、Torch 的核心能力

能力	说明
张量计算	类似 NumPy 的增强版数组计算
GPU 加速	使用 CUDA 调用显卡计算
深度学习	构建神经网络
自动求导	自动计算梯度
模型训练	训练 AI 模型
模型推理	运行 AI 模型

⸻

三、为什么 AI 大模型都使用 PyTorch？

现代大模型几乎都基于 PyTorch。

例如：

* GPT
* Llama
* Qwen
* DeepSeek
* Gemma

AI 技术栈关系：

PyTorch
    ↓
Transformers
    ↓
LLM
    ↓
Agent / RAG

⸻

四、Torch 最核心概念：Tensor

Tensor（张量）是 PyTorch 最核心的数据结构。

一句话理解：

支持 GPU 的超级数组

类似：

NumPy ndarray

但更强：

* 支持 GPU
* 支持自动求导
* 支持深度学习

⸻

五、Tensor 基础 Demo

1. 创建 Tensor

import torch
x = torch.tensor([1, 2, 3])
print(x)

输出：

tensor([1, 2, 3])

⸻

2. Tensor 运算

import torch
a = torch.tensor([1, 2])
b = torch.tensor([3, 4])
print(a + b)

输出：

tensor([4, 6])

⸻

六、GPU 加速（Torch 最大核心）

CPU 计算

x = torch.tensor([1, 2, 3])

⸻

GPU 计算

x = torch.tensor([1, 2, 3]).cuda()

此时：

Tensor 会在显卡上运行

⸻

七、Torch 与 NumPy 的区别

NumPy	Torch
CPU计算	CPU + GPU
科学计算	AI训练
无自动求导	自动梯度
数值计算	深度学习

⸻

八、神经网络（核心能力）

PyTorch 最重要能力：

构建神经网络

⸻

Demo

import torch.nn as nn
model = nn.Linear(10, 1)

含义：

创建一个线性神经网络层

⸻

九、自动求导（非常重要）

这是深度学习的核心机制。

⸻

Demo

import torch
x = torch.tensor(2.0, requires_grad=True)
y = x ** 2
y.backward()
print(x.grad)

输出：

tensor(4.)

解释：

自动计算导数

这是：

* 反向传播
* AI 训练
* 梯度下降

的核心基础。

⸻

十、Torch 常见模块

模块	作用
torch	核心模块
torch.nn	神经网络
torch.optim	优化器
torch.cuda	GPU
torch.autograd	自动求导
torch.utils.data	数据集处理

⸻

十一、Torch 在 AI Agent 中的作用

你当前学习方向：

Agent
RAG
LLM

大多数情况下：

并不会直接训练模型

更多是：

调用现成模型

例如：

* OpenAI API
* DeepSeek API
* LangChain
* Transformers

⸻

十二、Transformers 与 Torch 的关系

Transformers 底层大量依赖 PyTorch。

例如：

from transformers import AutoModel
model = AutoModel.from_pretrained(
    "bert-base-uncased"
)

底层实际上：

就是 torch 模型

⸻

十三、Torch 安装

CPU 版本

uv add torch

⸻

GPU 版本

需要根据 CUDA 版本安装。

因为：

PyTorch 与 CUDA 强绑定

⸻

十四、验证安装

查看版本

import torch
print(torch.__version__)

⸻

查看 GPU 是否可用

print(torch.cuda.is_available())

输出：

True

说明：

GPU 可用

⸻

十五、Torch 学习重点（推荐顺序）

建议优先学习：

第一阶段

Tensor
CUDA
基础运算

⸻

第二阶段

nn.Module
forward
Dataset

⸻

第三阶段

反向传播
训练流程
优化器

⸻

第四阶段

Transformers
本地模型
Embedding
微调

⸻

十六、AI 工程中的实际定位

当前 AI 开发栈：

PyTorch
    ↓
Transformers
    ↓
LLM
    ↓
Agent / RAG

因此：

Torch 是现代 AI 的基础设施

⸻

十七、前端视角类比（帮助理解）

AI	前端
torch	React Runtime
tensor	state
nn.Module	component
forward	render
backward	diff/update
CUDA	GPU渲染

⸻
建议优先：FastAPI + LangChain + RAG+ Tool Calling
后面再深入：Transformers + PyTorch+ 本地模型 + 模型微调


### langchain
from langchain_core.documents import Document, 
langchain 文档对象，包含：正文内容、元数据、唯一 id
```python
Document(
    page_content="xx",
    metadata={"source": "tweet"},
    id=1,
)
```
文档分片后的列表都是 Document 对象
```python
chunks = splitter.split_documents(documents)
chunks = [
    Document(
        page_content="xx",
        metadata={"source": "xx"},
        id=1,
    ),
]
```