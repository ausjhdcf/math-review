# 考研数学复习助手 — 设计文档

## 概述

面向考研学生的数学复习工具。用户通过手机拍照上传错题/笔记/讲义图片，系统自动 OCR 识别数学内容，调用 DeepSeek API 进行错因分析、知识点梳理，并将分析结果与历史记录存储到 Supabase，实现"教练型"长期知识追踪。

## 架构

```
手机浏览器 → FastAPI 后端（云服务器）
                ├── OCR 服务层（MinerU）
                ├── 分析引擎（DeepSeek API）
                └── Supabase（PostgreSQL + Storage + Auth）
```

前后端通过 REST API 通信。后端负责 OCR、分析、数据存取；前端仅负责展示。

## 前端页面（4 页）

### 1. 上传页（首页）
- 图片/PDF 上传区域（点击上传、拖拽、粘贴）
- 可选：手动选择分类（错题/笔记/讲义）、学科（高数/线代/概率论）
- "开始分析"按钮

### 2. 分析结果页
- 原始图片缩略图
- OCR 识别内容展示
- 错因分析（错误步骤、错误类型、根本原因、改进建议）
- 正确解法
- 关联知识点标签
- 推荐同类题
- "加入错题本"按钮

### 3. 知识库总览页
- 薄弱知识点列表（按掌握度颜色标记：红/黄/绿）
- 最近错题列表
- 按知识点/时间/错因类型筛选

### 4. 讲义分析页
- 例题编排逻辑总结
- 知识点关联图谱
- 复习建议

## 数据库设计（5 张表，PostgreSQL via Supabase）

### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 主键 |
| email | text | 登录邮箱 |
| created_at | timestamp | 注册时间 |

### uploads
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 主键 |
| user_id | uuid → users.id | 所属用户 |
| type | text | 错题/笔记/讲义 |
| image_url | text | Supabase Storage 图片地址 |
| subject | text | 高数/线代/概率论 |
| knowledge_point | text | 知识点标签（AI 自动填充） |
| user_note | text | 用户补充说明（可选） |
| created_at | timestamp | 上传时间 |

### ocr_results
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 主键 |
| upload_id | uuid → uploads.id | 对应上传 |
| raw_text | text | OCR 原始识别文本 |
| formulas | jsonb | 提取的数学公式列表 |
| confidence | float | 识别置信度 |
| created_at | timestamp | 处理时间 |

### analysis_records
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 主键 |
| upload_id | uuid → uploads.id | 对应上传 |
| analysis_type | text | 错题分析/讲义总结 |
| error_category | text | 计算粗心/概念不清/方法选错/审题失误 |
| error_detail | text | 详细错因说明 |
| correct_solution | text | 正确解法 |
| suggestions | text | 改进建议 |
| related_knowledge | jsonb | 关联知识点数组 |
| similar_problems | jsonb | 推荐同类题数组 |
| knowledge_mastery | int | 该知识点当前掌握度(0-100) |
| context_used | text | 传给 DeepSeek 的历史上下文 |
| created_at | timestamp | 分析时间 |

### knowledge_graph
| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid | 主键 |
| user_id | uuid → users.id | 所属用户 |
| knowledge_point | text | 知识点名称 |
| mastery_score | int | 当前掌握度(0-100) |
| error_count | int | 累计错题数 |
| last_reviewed | timestamp | 上次复习时间 |
| created_at | timestamp | 首次记录时间 |

### 表关系
```
users ──1:N──→ uploads ──1:1──→ ocr_results
                    │
                    └──1:1──→ analysis_records
users ──1:N──→ knowledge_graph
```

## 记忆机制

每次分析新题时：
1. 从 analysis_records 查询该知识点的历史错题
2. 从 knowledge_graph 读取当前掌握度
3. 两者作为上下文注入 DeepSeek prompt
4. 分析完成后更新 analysis_records 和 knowledge_graph
5. 掌握度动态调整：新错题→下调，久未犯错→缓慢回升

## 技术栈

| 层级 | 选型 | 理由 |
|------|------|------|
| 后端框架 | Python 3.11 + FastAPI | AI/OCR 生态最好，代码量少 |
| 前端 | FastAPI Jinja2 模板 + Bootstrap 5 | 手机浏览器自适应，无需前端框架 |
| OCR | MinerU（开源） | 中文数学公式支持好，免费 |
| AI 分析 | DeepSeek API（deepseek-chat） | 便宜、中文好、支持图片 |
| 数据库 | Supabase PostgreSQL | 免费 500MB，内置 REST API |
| 文件存储 | Supabase Storage | 免费 1GB |
| 认证 | Supabase Auth（可选，MVP 可略） | 内置，几行代码集成 |
| 部署 | Railway 或阿里云轻量服务器 | ~50元/月，国内访问快 |

## MVP 范围

### 包含
- 上传图片 → OCR → DeepSeek 分析 → 结果展示
- 错题本（按知识点/时间/错因分类浏览）
- 知识点掌握度追踪
- 讲义例题编排分析

### 不包含
- 多用户/登录系统（MVP 自己用）
- PDF 全文 OCR（MVP 先支持图片，PDF 后续加）
- 数据导出/分享
- 图表统计面板（后续加，不阻塞 MVP）

## 可行性验证（4 项）

在正式开发前完成：

1. **OCR 识别验证**：用 MinerU 识别 3 张手写数学题，检查公式提取准确率
2. **DeepSeek 分析质量**：将 OCR 结果发给 DeepSeek，评估错因分类和解题正确性
3. **Supabase 额度估算**：计算单次上传存储+请求开销，确认免费额度够用
4. **部署走通**：在 Railway 上完整走通一次部署，手机浏览器验证
