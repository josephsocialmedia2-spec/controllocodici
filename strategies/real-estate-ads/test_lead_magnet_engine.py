from lead_magnet_engine import BuyerProfile, choose_offer, qualification_score, lead_record


def test_hot_buyer_gets_reserved_list():
    p = BuyerProfile(locality='Avigliana', budget_max=220000, timeframe_days=60, off_market_interest=True)
    offer = choose_offer(p)
    assert offer.code == 'reserved-list'
    assert qualification_score(p)['class'] == 'CALDO'


def test_first_home_gets_checklist():
    p = BuyerProfile(locality='Rivoli', first_home=True, mortgage_needed=True, timeframe_days=180)
    assert choose_offer(p).code == 'first-home-checklist'


def test_contact_required_and_consent_required():
    p = BuyerProfile(locality='Susa')
    try:
        lead_record('Mario', '', '', True, p)
        assert False
    except ValueError:
        pass
    try:
        lead_record('Mario', 'mario@example.com', '', False, p)
        assert False
    except ValueError:
        pass


def test_valid_lead_creates_crm_stage():
    p = BuyerProfile(locality='Sant Ambrogio di Torino', budget_max=180000, timeframe_days=120)
    r = lead_record('Mario Rossi', 'mario@example.com', '3331234567', True, p)
    assert r['crm_stage'] == 'Acquirente - nuovo lead'
    assert r['lead_magnet']['code'] in {'buyer-guide','first-home-checklist','reserved-list'}
