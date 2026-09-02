from ads_engine import CampaignInput, build_plan, kpi_decision


def test_auto_format_carousel():
    c = CampaignInput(
        campaign_name='Test immobile', platform='Meta + Google', objective='Lead',
        ad_format='Auto', locality='Sant Ambrogio di Torino', property_type='Trilocale',
        property_address='Via Umberto I', price=169000,
        media_refs='a.jpg;b.jpg;c.jpg', target_cpl=20,
    )
    plan = build_plan(c)
    assert plan['category'] == 'Housing / Real Estate'
    assert plan['format'] == 'Carousel'


def test_kpi_continue():
    result = kpi_decision(5000, 100, 8, 120, 20)
    assert result['decision'] == 'CONTINUA'


def test_no_leads_optimizes_landing():
    result = kpi_decision(5000, 80, 0, 100, 20)
    assert result['decision'] == 'OTTIMIZZA LANDING/OFFERTA'
