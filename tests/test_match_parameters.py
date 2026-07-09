"""Multi-parameter hybrid scoring and hard prefilters."""

from background_matcher import BackgroundMatcher
from services.vector_service import VectorService
from sqlalchemy_models import Agent, Customer, Property, PropertyMatch


def _make_customer(**kwargs):
    defaults = dict(
        name="Buyer",
        email="buyer_params@example.com",
        phone="100",
        budget_min=100_000,
        budget_max=200_000,
        preferred_bedrooms=3,
        preferred_bathrooms=2,
        preferred_type="apartment",
        location_preference="Jordan",
        preferences="elevator parking 120",
        status="active",
    )
    defaults.update(kwargs)
    return Customer(**defaults)


def _make_property(**kwargs):
    defaults = dict(
        title="Nice apt",
        address="Jordan St 12",
        price=150_000,
        property_type="apartment",
        bedrooms=3,
        bathrooms=2,
        square_feet=120,
        description="Bright unit with parking",
        neighborhood="Jordan",
        status="active",
        has_elevator=True,
        parking_spaces=1,
        property_features="elevator, parking, storage",
    )
    defaults.update(kwargs)
    return Property(**defaults)


class TestScoreBreakdown:
    def test_strong_match_scores_high(self):
        vs = VectorService()
        c = _make_customer()
        p = _make_property()
        b = vs.score_breakdown(c, p, semantic_score=80.0)
        assert b["budget"] >= 100
        assert b["location"] >= 90
        assert b["type"] >= 85
        assert b["rooms"] >= 80
        assert b["hybrid"] >= 70
        assert "semantic" in b and "amenities" in b and "size" in b

    def test_wrong_type_and_location_lowers_score(self):
        vs = VectorService()
        c = _make_customer()
        good = _make_property()
        bad = _make_property(
            property_type="land",
            neighborhood="Far Zone",
            address="Other city road",
            bedrooms=1,
            bathrooms=1,
            price=900_000,
            has_elevator=False,
            parking_spaces=0,
            property_features="",
            square_feet=40,
        )
        good_h = vs.score_breakdown(c, good, 70.0)["hybrid"]
        bad_h = vs.score_breakdown(c, bad, 70.0)["hybrid"]
        assert good_h > bad_h

    def test_match_reasons_include_breakdown(self):
        vs = VectorService()
        reasons = vs._generate_match_reasons(_make_customer(), _make_property(), 75.0)
        assert any("budget" in r.lower() or "Within budget" in r for r in reasons)
        assert any("Score mix" in r for r in reasons)


class TestHardPrefilter:
    def test_excludes_dismissed_and_wrong_beds(self, app, db_setup):
        with app.app_context():
            agent = Agent(name="Ag", email="ag_params@example.com", phone="1")
            db_setup.session.add(agent)
            db_setup.session.flush()

            customer = _make_customer(email="buyer_prefilter@example.com")
            good = _make_property(title="Good", address="Jordan A", agent_id=agent.id)
            wrong_beds = _make_property(
                title="Beds",
                address="Jordan B",
                bedrooms=8,
                agent_id=agent.id,
            )
            expensive = _make_property(
                title="Exp",
                address="Jordan C",
                price=5_000_000,
                agent_id=agent.id,
            )
            db_setup.session.add_all([customer, good, wrong_beds, expensive])
            db_setup.session.commit()

            dismissed_prop = _make_property(
                title="Dismissed",
                address="Jordan D",
                agent_id=agent.id,
            )
            db_setup.session.add(dismissed_prop)
            db_setup.session.commit()

            db_setup.session.add(
                PropertyMatch(
                    property_id=dismissed_prop.id,
                    customer_id=customer.id,
                    agent_id=agent.id,
                    match_score=0.9,
                    status="dismissed",
                )
            )
            db_setup.session.commit()

            matcher = BackgroundMatcher()
            dismissed = matcher._dismissed_property_ids(customer.id)
            assert dismissed_prop.id in dismissed

            assert matcher._passes_hard_filters(customer, good, dismissed) is True
            assert matcher._passes_hard_filters(customer, wrong_beds, dismissed) is False
            assert matcher._passes_hard_filters(customer, expensive, dismissed) is False
            assert matcher._passes_hard_filters(customer, dismissed_prop, dismissed) is False

    def test_basic_score_uses_hybrid(self):
        matcher = BackgroundMatcher()
        score = matcher._calculate_basic_match_score(_make_customer(), _make_property())
        assert 0.0 <= score <= 1.0
        assert score >= 0.5
