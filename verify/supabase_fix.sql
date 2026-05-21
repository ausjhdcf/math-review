-- 修复权限 - 在 Supabase SQL Editor 中执行
-- https://supabase.com/dashboard/project/dohcxwgdcnehmwvqyhcq/sql/new

-- 1. 给 anon 角色授权（允许前端 API 访问）
GRANT SELECT, INSERT, UPDATE, DELETE ON uploads TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ocr_results TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON analysis_records TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_graph TO anon, authenticated;

-- 2. 确保 RLS 策略生效
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_graph ENABLE ROW LEVEL SECURITY;

-- 删除已有策略后重建
DROP POLICY IF EXISTS "Allow all on uploads" ON uploads;
DROP POLICY IF EXISTS "Allow all on ocr_results" ON ocr_results;
DROP POLICY IF EXISTS "Allow all on analysis_records" ON analysis_records;
DROP POLICY IF EXISTS "Allow all on knowledge_graph" ON knowledge_graph;

CREATE POLICY "Allow all on uploads" ON uploads FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on ocr_results" ON ocr_results FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on analysis_records" ON analysis_records FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on knowledge_graph" ON knowledge_graph FOR ALL USING (true) WITH CHECK (true);
