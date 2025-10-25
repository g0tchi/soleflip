-- Seed Brand Patterns for BrandExtractorService
-- This enables DB-driven brand extraction that's easily maintainable

-- First, ensure we have the main brands
INSERT INTO catalog.brand (id, name, slug, created_at, updated_at)
VALUES
    (gen_random_uuid(), 'Nike', 'nike', NOW(), NOW()),
    (gen_random_uuid(), 'Jordan', 'jordan', NOW(), NOW()),
    (gen_random_uuid(), 'Adidas', 'adidas', NOW(), NOW()),
    (gen_random_uuid(), 'Yeezy', 'yeezy', NOW(), NOW()),
    (gen_random_uuid(), 'New Balance', 'new-balance', NOW(), NOW()),
    (gen_random_uuid(), 'Asics', 'asics', NOW(), NOW()),
    (gen_random_uuid(), 'Puma', 'puma', NOW(), NOW()),
    (gen_random_uuid(), 'Crocs', 'crocs', NOW(), NOW()),
    (gen_random_uuid(), 'Vans', 'vans', NOW(), NOW()),
    (gen_random_uuid(), 'Converse', 'converse', NOW(), NOW()),
    (gen_random_uuid(), 'Reebok', 'reebok', NOW(), NOW()),
    (gen_random_uuid(), 'Salomon', 'salomon', NOW(), NOW()),
    (gen_random_uuid(), 'Hoka', 'hoka', NOW(), NOW()),
    (gen_random_uuid(), 'On Running', 'on-running', NOW(), NOW()),
    (gen_random_uuid(), 'Under Armour', 'under-armour', NOW(), NOW()),
    (gen_random_uuid(), 'Saucony', 'saucony', NOW(), NOW()),
    (gen_random_uuid(), 'Daniel Arsham', 'daniel-arsham', NOW(), NOW()),
    (gen_random_uuid(), 'Off-White', 'off-white', NOW(), NOW()),
    (gen_random_uuid(), 'Fear of God', 'fear-of-god', NOW(), NOW()),
    (gen_random_uuid(), 'Supreme', 'supreme', NOW(), NOW()),
    (gen_random_uuid(), 'Balenciaga', 'balenciaga', NOW(), NOW()),
    (gen_random_uuid(), 'Gucci', 'gucci', NOW(), NOW()),
    (gen_random_uuid(), 'Louis Vuitton', 'louis-vuitton', NOW(), NOW())
ON CONFLICT (slug) DO NOTHING;

-- Now add patterns (keyword-based for simple matching)
INSERT INTO catalog.brand_patterns (id, brand_id, pattern_type, pattern, priority, created_at, updated_at)
SELECT
    gen_random_uuid(),
    b.id,
    'keyword',
    b.name,
    10, -- High priority for exact brand name match
    NOW(),
    NOW()
FROM catalog.brand b
WHERE NOT EXISTS (
    SELECT 1 FROM catalog.brand_patterns bp
    WHERE bp.brand_id = b.id AND bp.pattern = b.name
);

-- Add specific regex patterns for complex cases
INSERT INTO catalog.brand_patterns (id, brand_id, pattern_type, pattern, priority, created_at, updated_at)
SELECT
    gen_random_uuid(),
    patterns.brand_id,
    'regex',
    patterns.pattern,
    patterns.priority,
    NOW(),
    NOW()
FROM (VALUES
    -- Nike patterns
    ((SELECT id FROM catalog.brand WHERE slug = 'nike'), '(?i)^nike\s', 5),
    ((SELECT id FROM catalog.brand WHERE slug = 'nike'), '(?i)\sair\s(force|max|jordan)', 20),

    -- Jordan is often part of Nike but should be separate
    ((SELECT id FROM catalog.brand WHERE slug = 'jordan'), '(?i)^(air\s)?jordan', 3),
    ((SELECT id FROM catalog.brand WHERE slug = 'jordan'), '(?i)jordan\s\d', 3),

    -- Yeezy
    ((SELECT id FROM catalog.brand WHERE slug = 'yeezy'), '(?i)yeezy', 5),

    -- Adidas
    ((SELECT id FROM catalog.brand WHERE slug = 'adidas'), '(?i)^adidas\s', 5),
    ((SELECT id FROM catalog.brand WHERE slug = 'adidas'), '(?i)\s(ultraboost|nmd|superstar)', 20),

    -- Crocs
    ((SELECT id FROM catalog.brand WHERE slug = 'crocs'), '(?i)^crocs\s', 5),

    -- Artist/Designer brands
    ((SELECT id FROM catalog.brand WHERE slug = 'daniel-arsham'), '(?i)daniel\sarsham', 5)
) AS patterns(brand_id, pattern, priority)
WHERE NOT EXISTS (
    SELECT 1 FROM catalog.brand_patterns bp
    WHERE bp.brand_id = patterns.brand_id AND bp.pattern = patterns.pattern
);
