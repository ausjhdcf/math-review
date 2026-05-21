-- 给 math-images 存储桶添加访问权限
-- https://supabase.com/dashboard/project/dohcxwgdcnehmwvqyhcq/sql/new

-- 允许 anon 角色上传和读取文件
CREATE POLICY "Allow upload to math-images"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'math-images');

CREATE POLICY "Allow select from math-images"
ON storage.objects FOR SELECT
USING (bucket_id = 'math-images');

CREATE POLICY "Allow update in math-images"
ON storage.objects FOR UPDATE
USING (bucket_id = 'math-images');

CREATE POLICY "Allow delete from math-images"
ON storage.objects FOR DELETE
USING (bucket_id = 'math-images');
