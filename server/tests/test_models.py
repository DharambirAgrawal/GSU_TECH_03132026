# tests/test_models.py
# -----------------------------------------
# Unit tests for all SQLAlchemy models.
# Tests that models can be created, saved, and queried correctly.
# Uses an in-memory SQLite database (TestingConfig) for isolation.
#
# IMPORTS NEEDED:
#   import pytest
#   from app import create_app
#   from app.extensions import db
#   from app.models.company import Company, IndustryType, CompanyConfig
#   from app.models.query import QueryTemplate, QueryRun, LLMPlatform, RunStatus, QueryCategory
#   from app.models.accuracy import AccuracyCheck, FactualError, ErrorType, ErrorSeverity, RootCause
#   from app.models.crawl import CrawlJob, PageAudit, SchemaIssue, CrawlStatus, SchemaIssueType
#   from app.models.content import ContentFix, FixType, FixStatus
#   from app.models.competitor import Competitor, CompetitorRanking
#   from app.models.source import CitationSource, SourceMention, SourceType
#   from app.models.ethics import EthicsFlag, ComplianceAlert, EthicsCategory, EthicsSeverity
#   from datetime import datetime, timezone
#
# -----------------------------------------------------------
# FIXTURE: app
# -----------------------------------------------------------
# Create the Flask app with TestingConfig (in-memory SQLite).
# Create all tables before tests, drop them after.
#
#   @pytest.fixture
#   def app():
#       app = create_app("testing")
#       with app.app_context():
#           db.create_all()
#           yield app
#           db.drop_all()
#
# -----------------------------------------------------------
# FIXTURE: client
# -----------------------------------------------------------
#   @pytest.fixture
#   def client(app): return app.test_client()
#
# -----------------------------------------------------------
# FIXTURE: sample_company(app)
# -----------------------------------------------------------
# Creates and commits a test Company to the DB.
# Used by most other tests as a dependency.
#
# -----------------------------------------------------------
# TEST CASES TO IMPLEMENT:
#
#   Company model:
#   - test_company_creation: create company, check all fields save correctly
#   - test_company_slug_unique: creating two companies with same slug raises IntegrityError
#   - test_company_to_dict: to_dict() returns expected keys and types
#   - test_company_defaults: ai_visibility_score defaults to 0.0, bot_allowed defaults to True
#
#   QueryTemplate model:
#   - test_query_template_creation: create template linked to company
#   - test_query_template_relationship: company.query_templates returns templates
#   - test_query_template_cascade_delete: deleting company deletes its templates
#
#   QueryRun model:
#   - test_query_run_creation: create run linked to template and company
#   - test_query_run_brand_mention: brand_mentioned and brand_position save correctly
#   - test_query_run_citations_json: citations_found stores and retrieves list of strings
#
#   AccuracyCheck model:
#   - test_accuracy_check_one_to_one: second AccuracyCheck for same query_run raises IntegrityError
#   - test_accuracy_percentage: accuracy_percentage() returns correct calculation
#
#   FactualError model:
#   - test_factual_error_creation: create error with all required fields
#   - test_factual_error_content_fix_relationship: one error → one content fix
#
#   CrawlJob + PageAudit + SchemaIssue:
#   - test_crawl_job_creation: create job with correct defaults
#   - test_page_audit_creation: create page audit linked to crawl job
#   - test_schema_issue_cascade: deleting page audit deletes its schema issues
#
#   ContentFix model:
#   - test_content_fix_creation: create fix with fix_type and status
#   - test_content_fix_without_error: fix can be created with factual_error_id = None (content gap)
#
#   Competitor + CompetitorRanking:
#   - test_competitor_creation: create competitor linked to company
#   - test_competitor_ranking: create ranking with our_position vs their_position
#
#   CitationSource + SourceMention:
#   - test_citation_source_creation: create source with domain and type
#   - test_source_mention_link: mention links source to query run
#
#   EthicsFlag + ComplianceAlert:
#   - test_ethics_flag_creation: create flag with category and severity
#   - test_compliance_alert_creation: create alert linked to flag
