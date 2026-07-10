"""Behavior tests for AI schemas (pre/post Pydantic V2 field_validator)."""

from __future__ import annotations

import pytest

from schemas import CustomerAI, PropertyAI


class TestPropertyFeaturesValidator:
    def test_list_input_passthrough(self):
        m = PropertyAI(property_features=["pool", "garage"])
        assert m.property_features == ["pool", "garage"]

    def test_delimited_string_split_and_strip(self):
        m = PropertyAI(property_features=" pool , garage, ,yard ")
        assert m.property_features == ["pool", "garage", "yard"]

    def test_empty_string_becomes_empty_list(self):
        m = PropertyAI(property_features="")
        assert m.property_features == []

    def test_none_stays_none(self):
        m = PropertyAI(property_features=None)
        assert m.property_features is None

    def test_missing_defaults_to_none(self):
        m = PropertyAI()
        assert m.property_features is None

    def test_model_dump_serialization(self):
        m = PropertyAI(property_features="a,b")
        data = m.model_dump()
        assert data["property_features"] == ["a", "b"]

    def test_non_string_non_list_passthrough_or_error(self):
        # Current contract: non-str values returned as-is from pre-validator;
        # Pydantic then validates against List[str].
        with pytest.raises(Exception):
            PropertyAI(property_features=123)


class TestDesiredNeighborhoodsValidator:
    def test_list_input_passthrough(self):
        m = CustomerAI(desired_neighborhoods=["Downtown", "West"])
        assert m.desired_neighborhoods == ["Downtown", "West"]

    def test_delimited_string_split_and_strip(self):
        m = CustomerAI(desired_neighborhoods=" Downtown , West, ")
        assert m.desired_neighborhoods == ["Downtown", "West"]

    def test_empty_string_becomes_empty_list(self):
        m = CustomerAI(desired_neighborhoods="")
        assert m.desired_neighborhoods == []

    def test_none_stays_none(self):
        m = CustomerAI(desired_neighborhoods=None)
        assert m.desired_neighborhoods is None

    def test_missing_defaults_to_none(self):
        m = CustomerAI()
        assert m.desired_neighborhoods is None

    def test_model_dump_serialization(self):
        m = CustomerAI(desired_neighborhoods="a, b")
        data = m.model_dump()
        assert data["desired_neighborhoods"] == ["a", "b"]
