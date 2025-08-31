import asyncio

import asyncpg


async def create_brand_deep_dive_views():
    conn = await asyncpg.connect(
        "postgresql://metabaseuser:metabasepass@192.168.2.45:2665/soleflip"
    )

    print("=== CREATING BRAND DEEP DIVE ANALYTICS VIEWS ===")

    # 1. Brand Encyclopedia View
    print("1. Creating Brand Encyclopedia view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_encyclopedia AS
        SELECT 
            b.id,
            b.name,
            b.founder_name,
            b.founded_year,
            b.headquarters_city || ', ' || b.headquarters_country as headquarters,
            b.parent_company,
            b.category,
            b.segment,
            b.brand_type,
            b.target_demographic,
            b.price_tier,
            b.brand_story,
            b.brand_mission,
            b.brand_values,
            b.sustainability_score,
            b.innovation_focus,
            b.key_technologies,
            b.website_url,
            b.instagram_handle,
            b.annual_revenue_usd,
            b.employee_count,
            b.market_cap_usd,
            CASE 
                WHEN b.annual_revenue_usd > 10000000000 THEN 'Mega Brand ($10B+)'
                WHEN b.annual_revenue_usd > 1000000000 THEN 'Large Brand ($1B+)'
                WHEN b.annual_revenue_usd > 100000000 THEN 'Medium Brand ($100M+)'
                ELSE 'Emerging Brand'
            END as company_size,
            EXTRACT(YEAR FROM CURRENT_DATE) - b.founded_year as brand_age_years
        FROM core.brands b
        WHERE b.brand_story IS NOT NULL
        ORDER BY b.annual_revenue_usd DESC NULLS LAST
    """
    )
    print("OK Created Brand Encyclopedia view")

    # 2. Brand Timeline View
    print("2. Creating Brand Timeline view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_timeline AS
        SELECT 
            b.name as brand_name,
            bh.event_date,
            bh.event_type,
            bh.event_title,
            bh.event_description,
            bh.impact_level,
            EXTRACT(YEAR FROM bh.event_date) as event_year,
            EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM bh.event_date) as years_ago,
            CASE 
                WHEN bh.event_type = 'founded' THEN '🏢'
                WHEN bh.event_type = 'milestone' THEN '🚀'
                WHEN bh.event_type = 'collaboration' THEN '🤝'
                WHEN bh.event_type = 'ipo' THEN '💰'
                WHEN bh.event_type = 'acquired' THEN '🏪'
                WHEN bh.event_type = 'controversy' THEN '⚠️'
                ELSE '📅'
            END as event_icon,
            ROW_NUMBER() OVER (PARTITION BY b.name ORDER BY bh.event_date) as timeline_position
        FROM core.brands b
        JOIN core.brand_history bh ON bh.brand_id = b.id
        ORDER BY b.name, bh.event_date
    """
    )
    print("OK Created Brand Timeline view")

    # 3. Brand Collaboration Network
    print("3. Creating Brand Collaboration Network view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_collaboration_network AS
        SELECT 
            pb.name as primary_brand,
            cb.name as collaborator_brand,
            bc.collaboration_name,
            bc.collaboration_type,
            bc.launch_date,
            bc.success_level,
            bc.estimated_revenue_usd,
            bc.hype_score,
            bc.resale_multiplier,
            CASE 
                WHEN bc.success_level = 'legendary' THEN '🔥'
                WHEN bc.success_level = 'high' THEN '⭐'
                WHEN bc.success_level = 'medium' THEN '👍'
                ELSE '👌'
            END as success_icon,
            (CURRENT_DATE - bc.launch_date)::integer as days_since_launch,
            CASE 
                WHEN bc.launch_date >= CURRENT_DATE - INTERVAL '1 year' THEN 'Recent'
                WHEN bc.launch_date >= CURRENT_DATE - INTERVAL '3 years' THEN 'Modern Era'
                WHEN bc.launch_date >= CURRENT_DATE - INTERVAL '10 years' THEN 'Established'
                ELSE 'Classic'
            END as collaboration_era
        FROM core.brand_collaborations bc
        JOIN core.brands pb ON pb.id = bc.primary_brand_id
        JOIN core.brands cb ON cb.id = bc.collaborator_brand_id
        ORDER BY bc.estimated_revenue_usd DESC NULLS LAST, bc.hype_score DESC
    """
    )
    print("OK Created Brand Collaboration Network view")

    # 4. Brand Innovation Timeline
    print("4. Creating Brand Innovation Timeline view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_innovation_timeline AS
        WITH innovation_events AS (
            SELECT 
                b.name as brand_name,
                bh.event_date,
                bh.event_title,
                bh.event_description,
                b.key_technologies,
                b.innovation_focus,
                CASE 
                    WHEN bh.event_title ILIKE '%technology%' 
                      OR bh.event_title ILIKE '%innovation%' 
                      OR bh.event_title ILIKE '%patent%'
                      OR bh.event_title ILIKE '%material%'
                      OR bh.event_title ILIKE '%air%'
                      OR bh.event_title ILIKE '%boost%'
                      OR bh.event_title ILIKE '%gel%'
                    THEN true
                    ELSE false
                END as is_innovation_event
            FROM core.brands b
            JOIN core.brand_history bh ON bh.brand_id = b.id
        )
        SELECT 
            brand_name,
            event_date,
            event_title,
            event_description,
            key_technologies,
            innovation_focus,
            EXTRACT(YEAR FROM event_date) as innovation_year,
            ROW_NUMBER() OVER (PARTITION BY brand_name ORDER BY event_date) as innovation_sequence
        FROM innovation_events
        WHERE is_innovation_event = true
        ORDER BY brand_name, event_date
    """
    )
    print("OK Created Brand Innovation Timeline view")

    # 5. Brand Financial Evolution
    print("5. Creating Brand Financial Evolution view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_financial_evolution AS
        SELECT 
            b.name as brand_name,
            bf.fiscal_year,
            bf.revenue_usd,
            bf.profit_usd,
            bf.market_cap_usd,
            bf.employee_count,
            bf.growth_rate_percentage,
            bf.online_sales_percentage,
            CASE 
                WHEN bf.profit_usd > 0 AND bf.revenue_usd > 0 
                THEN ROUND((bf.profit_usd::decimal / bf.revenue_usd * 100), 2)
                ELSE NULL
            END as profit_margin_percentage,
            LAG(bf.revenue_usd) OVER (PARTITION BY b.name ORDER BY bf.fiscal_year) as prev_year_revenue,
            CASE 
                WHEN LAG(bf.revenue_usd) OVER (PARTITION BY b.name ORDER BY bf.fiscal_year) > 0
                THEN ROUND(((bf.revenue_usd - LAG(bf.revenue_usd) OVER (PARTITION BY b.name ORDER BY bf.fiscal_year))::decimal / LAG(bf.revenue_usd) OVER (PARTITION BY b.name ORDER BY bf.fiscal_year) * 100), 2)
                ELSE NULL
            END as calculated_growth_rate,
            CASE 
                WHEN bf.revenue_usd > 50000000000 THEN 'Titan ($50B+)'
                WHEN bf.revenue_usd > 10000000000 THEN 'Giant ($10B+)'
                WHEN bf.revenue_usd > 1000000000 THEN 'Major ($1B+)'
                WHEN bf.revenue_usd > 100000000 THEN 'Significant ($100M+)'
                ELSE 'Emerging'
            END as revenue_tier
        FROM core.brands b
        JOIN core.brand_financials bf ON bf.brand_id = b.id
        ORDER BY b.name, bf.fiscal_year DESC
    """
    )
    print("OK Created Brand Financial Evolution view")

    # 6. Brand Personality & Attributes Analysis
    print("6. Creating Brand Personality Analysis view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_personality_analysis AS
        SELECT 
            b.name as brand_name,
            b.category,
            b.segment,
            b.target_demographic,
            b.brand_values,
            b.sustainability_score,
            STRING_AGG(
                CASE ba.attribute_category
                    WHEN 'personality' THEN ba.attribute_value
                    ELSE NULL
                END, ', '
            ) as personality_traits,
            STRING_AGG(
                CASE ba.attribute_category
                    WHEN 'style' THEN ba.attribute_value
                    ELSE NULL
                END, ', '
            ) as style_attributes,
            STRING_AGG(
                CASE ba.attribute_category
                    WHEN 'quality' THEN ba.attribute_value
                    ELSE NULL
                END, ', '
            ) as quality_attributes,
            COUNT(DISTINCT ba.attribute_category) as attribute_diversity,
            AVG(ba.confidence_score) as avg_confidence_score,
            CASE 
                WHEN b.sustainability_score >= 8 THEN 'Highly Sustainable'
                WHEN b.sustainability_score >= 6 THEN 'Moderately Sustainable'
                WHEN b.sustainability_score >= 4 THEN 'Somewhat Sustainable'
                ELSE 'Limited Sustainability Focus'
            END as sustainability_tier
        FROM core.brands b
        LEFT JOIN core.brand_attributes ba ON ba.brand_id = b.id
        WHERE b.brand_values IS NOT NULL
        GROUP BY b.id, b.name, b.category, b.segment, b.target_demographic, b.brand_values, b.sustainability_score
        ORDER BY b.sustainability_score DESC, b.name
    """
    )
    print("OK Created Brand Personality Analysis view")

    # 7. Brand Influence & Cultural Impact
    print("7. Creating Brand Cultural Impact view...")

    await conn.execute(
        """
        CREATE OR REPLACE VIEW analytics.brand_cultural_impact AS
        WITH brand_metrics AS (
            SELECT 
                b.name as brand_name,
                b.founded_year,
                EXTRACT(YEAR FROM CURRENT_DATE) - b.founded_year as brand_age,
                COUNT(DISTINCT bh.id) as historical_events_count,
                COUNT(DISTINCT bc.id) as collaboration_count,
                AVG(bc.hype_score) as avg_hype_score,
                SUM(bc.estimated_revenue_usd) as total_collaboration_revenue,
                COUNT(DISTINCT CASE WHEN bh.impact_level = 'critical' THEN bh.id END) as critical_moments,
                COUNT(DISTINCT CASE WHEN bh.event_type = 'milestone' THEN bh.id END) as major_milestones
            FROM core.brands b
            LEFT JOIN core.brand_history bh ON bh.brand_id = b.id
            LEFT JOIN core.brand_collaborations bc ON bc.primary_brand_id = b.id
            GROUP BY b.id, b.name, b.founded_year
        )
        SELECT 
            brand_name,
            brand_age,
            historical_events_count,
            collaboration_count,
            COALESCE(avg_hype_score, 0) as avg_hype_score,
            COALESCE(total_collaboration_revenue, 0) as total_collaboration_revenue,
            critical_moments,
            major_milestones,
            CASE 
                WHEN avg_hype_score >= 9 THEN 'Cultural Icon'
                WHEN avg_hype_score >= 7 THEN 'Highly Influential'
                WHEN avg_hype_score >= 5 THEN 'Moderately Influential'
                WHEN collaboration_count > 0 THEN 'Emerging Influence'
                ELSE 'Traditional Brand'
            END as cultural_influence_tier,
            ROUND(
                (historical_events_count * 10 + 
                 collaboration_count * 15 + 
                 COALESCE(avg_hype_score, 0) * 10 + 
                 critical_moments * 25) / 4.0, 1
            ) as cultural_impact_score
        FROM brand_metrics
        WHERE brand_age > 0
        ORDER BY cultural_impact_score DESC, brand_name
    """
    )
    print("OK Created Brand Cultural Impact view")

    print("\n8. Testing new deep dive views...")

    # Test the views
    try:
        encyclopedia_count = await conn.fetchval(
            "SELECT COUNT(*) FROM analytics.brand_encyclopedia"
        )
        print(f"  Brand Encyclopedia: {encyclopedia_count} detailed brand profiles")

        timeline_count = await conn.fetchval("SELECT COUNT(*) FROM analytics.brand_timeline")
        print(f"  Brand Timeline: {timeline_count} historical events")

        collab_count = await conn.fetchval(
            "SELECT COUNT(*) FROM analytics.brand_collaboration_network"
        )
        print(f"  Collaboration Network: {collab_count} partnerships")

        impact_sample = await conn.fetch(
            """
            SELECT brand_name, cultural_influence_tier, cultural_impact_score
            FROM analytics.brand_cultural_impact
            ORDER BY cultural_impact_score DESC
            LIMIT 5
        """
        )

        print("  Top Cultural Impact Brands:")
        for brand in impact_sample:
            print(
                f"    {brand['brand_name']}: {brand['cultural_influence_tier']} (Score: {brand['cultural_impact_score']})"
            )

    except Exception as e:
        print(f"  ERROR testing views: {e}")

    print("\n=== BRAND DEEP DIVE ANALYTICS VIEWS CREATED ===")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(create_brand_deep_dive_views())
