-- 考研数学复习助手 - 数据库初始化 SQL
-- 在 Supabase SQL Editor 中执行: https://supabase.com/dashboard/project/dohcxwgdcnehmwvqyhcq/sql/new

-- 1. 上传记录表
CREATE TABLE IF NOT EXISTS uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID DEFAULT '00000000-0000-0000-0000-000000000000',
    type TEXT NOT NULL,
    image_url TEXT,
    subject TEXT,
    knowledge_point TEXT,
    user_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. OCR 识别结果表
CREATE TABLE IF NOT EXISTS ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
    raw_text TEXT,
    formulas JSONB DEFAULT '[]'::jsonb,
    confidence FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. 分析结果表（核心）
CREATE TABLE IF NOT EXISTS analysis_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID REFERENCES uploads(id) ON DELETE CASCADE,
    analysis_type TEXT,
    error_category TEXT,
    error_detail TEXT,
    correct_solution TEXT,
    suggestions TEXT,
    related_knowledge JSONB DEFAULT '[]'::jsonb,
    similar_problems JSONB DEFAULT '[]'::jsonb,
    knowledge_mastery INT DEFAULT 50,
    context_used TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. 知识点掌握度表
CREATE TABLE IF NOT EXISTS knowledge_graph (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID DEFAULT '00000000-0000-0000-0000-000000000000',
    knowledge_point TEXT NOT NULL,
    mastery_score INT DEFAULT 50,
    error_count INT DEFAULT 0,
    last_reviewed TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. 启用行级安全（RLS）— MVP 阶段开放所有权限
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_graph ENABLE ROW LEVEL SECURITY;

-- 创建允许所有操作的策略（MVP 单用户阶段）
CREATE POLICY "Allow all on uploads" ON uploads FOR ALL USING (true);
CREATE POLICY "Allow all on ocr_results" ON ocr_results FOR ALL USING (true);
CREATE POLICY "Allow all on analysis_records" ON analysis_records FOR ALL USING (true);
CREATE POLICY "Allow all on knowledge_graph" ON knowledge_graph FOR ALL USING (true);

-- 6. 创建索引
CREATE INDEX IF NOT EXISTS idx_uploads_knowledge ON uploads(knowledge_point);
CREATE INDEX IF NOT EXISTS idx_knowledge_user ON knowledge_graph(user_id, knowledge_point);
