# tests/test_fact_checker.py
# -----------------------------------------
# Unit tests for the fact-checking service.
# Tests claim extraction, claim verification, and error detection logic.
#
# IMPORTS NEEDED:
#   import pytest
#   from unittest.mock import patch, MagicMock    # Mock LLM API calls
#   from app import create_app
#   from app.extensions import db
#   from app.models.company import Company, IndustryType
#   from app.models.query import QueryRun, QueryTemplate, LLMPlatform, RunStatus, QueryCategory
#   from app.models.accuracy import AccuracyCheck, FactualError, ErrorSeverity
#   from app.services.fact_checker import (
#       check_query_run,
#       extract_claims,
#       verify_claims,
#       determine_error_type,
#       determine_severity
#   )
#
# -----------------------------------------------------------
# FIXTURES:
#   app, client — same pattern as test_models.py
#   sample_query_run — QueryRun with raw_response containing known facts
#
# -----------------------------------------------------------
# TEST CASES TO IMPLEMENT:
#
#   extract_claims():
#   - test_extract_claims_price: response mentioning "$149.99" extracts price claim
#   - test_extract_claims_policy: response mentioning "30-day return policy" extracts policy claim
#   - test_extract_claims_multiple: response with 3 facts returns 3 claims
#   - test_extract_claims_empty_response: returns empty list for response with no facts
#   NOTE: Mock the LLM API call (get_chatgpt_response) to return predefined extraction JSON
#
#   verify_claims():
#   - test_verify_claims_correct_price: claim matches live page → marked correct
#   - test_verify_claims_wrong_price: claim doesn't match → marked wrong with correct_value
#   - test_verify_claims_normalized_numbers: "$149.99" vs "149.99" treated as equal (normalization)
#   - test_verify_claims_string_match: policy text match uses similarity threshold
#
#   check_query_run():
#   - test_full_pipeline_no_errors: all claims correct → AccuracyCheck.overall_accurate = True
#   - test_full_pipeline_with_error: one wrong claim → creates FactualError record
#   - test_full_pipeline_compliance_risk: wrong APR for financial company → compliance_risk = True
#   - test_full_pipeline_failed_run: calling on a FAILED QueryRun returns None
#   NOTE: Mock httpx.get (website fetch) and LLM calls
#
#   determine_severity():
#   - test_severity_wrong_price_financial: CRITICAL for financial company
#   - test_severity_wrong_price_retail: HIGH for retail company
#   - test_severity_wrong_spec: HIGH regardless of industry
#   - test_severity_stale_minor: MEDIUM for non-financial outdated facts
