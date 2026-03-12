from app.extensions import db
from datetime import datetime, timezone
import enum


class SourceType(enum.Enum):
    COMPANY_OWNED  = "company_owned"   # The company's own domain
    NEWS           = "news"            # News sites (CNN, CNBC, Forbes)
    REVIEW_SITE    = "review_site"     # NerdWallet, The Points Guy, Wirecutter
    FORUM          = "forum"           # Reddit, Quora, Stack Exchange
    SOCIAL         = "social"          # Twitter/X, YouTube
    COMPETITOR     = "competitor"      # A rival brand's domain
    AGGREGATOR     = "aggregator"      # Price comparison or shopping aggregator
    WIKI           = "wiki"            # Wikipedia, wikis
    GOVERNMENT     = "government"      # .gov domains


class CitationSource(db.Model):
    """
    A third-party domain that AI uses as a source when talking about a company.
    Master list of all sources observed across all query runs.
    Examples: nerdwallet.com, reddit.com, thewirecutter.com, thepoints guy.com
    """
    __tablename__ = "citation_sources"

    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    domain          = db.Column(db.String(255), nullable=False)
    # e.g. "nerdwallet.com", "reddit.com", "thewirecutter.com"

    source_type     = db.Column(db.Enum(SourceType), nullable=False)

    display_name    = db.Column(db.String(100))
    # Human-friendly name shown in the UI — e.g. "NerdWallet", "Reddit"

    citation_count  = db.Column(db.Integer, default=0)
    # Total times AI cited this domain across all query runs
    # Updated after each completed manual run batch

    positive_count  = db.Column(db.Integer, default=0)
    # Citations where the source said something favorable about the company

    negative_count  = db.Column(db.Integer, default=0)
    # Citations where the source said something unfavorable

    # Risk assessment
    accuracy_concern = db.Column(db.Boolean, default=False)
    # True if this source has caused factual errors (e.g. old NerdWallet article)
    # Flagged by the fact_checker service when errors trace back here

    first_seen_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    mentions = db.relationship("SourceMention", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CitationSource {self.domain} count={self.citation_count}>"

    def to_dict(self):
        return {
            "id":               self.id,
            "company_id":       self.company_id,
            "domain":           self.domain,
            "source_type":      self.source_type.value,
            "display_name":     self.display_name,
            "citation_count":   self.citation_count,
            "positive_count":   self.positive_count,
            "negative_count":   self.negative_count,
            "accuracy_concern": self.accuracy_concern,
            "last_seen_at":     self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class SourceMention(db.Model):
    """
    One instance of a specific source being cited in one query run.
    Links CitationSource records back to individual QueryRuns for
    full traceability — from a source domain to the exact query and response.
    """
    __tablename__ = "source_mentions"

    id            = db.Column(db.Integer, primary_key=True)
    source_id     = db.Column(db.Integer, db.ForeignKey("citation_sources.id"), nullable=False)
    query_run_id  = db.Column(db.Integer, db.ForeignKey("query_runs.id"), nullable=False)
    company_id    = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    cited_url     = db.Column(db.String(1000))
    # The specific URL that was cited (not just the domain)
    # e.g. "https://www.nerdwallet.com/reviews/credit-cards/capital-one-venture"

    citation_context = db.Column(db.Text)
    # Excerpt from the AI response showing how this source was used
    # Useful for understanding if the source is causing errors

    sentiment     = db.Column(db.String(20))
    # "positive", "negative", "neutral" — did this citation help or hurt us?

    caused_error  = db.Column(db.Boolean, default=False)
    # True if this specific citation led to a FactualError in the same QueryRun

    mentioned_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    source    = db.relationship("CitationSource", back_populates="mentions")
    query_run = db.relationship("QueryRun")

    def __repr__(self):
        return f"<SourceMention source={self.source_id} run={self.query_run_id}>"

    def to_dict(self):
        return {
            "id":               self.id,
            "source_id":        self.source_id,
            "query_run_id":     self.query_run_id,
            "cited_url":        self.cited_url,
            "citation_context": self.citation_context,
            "sentiment":        self.sentiment,
            "caused_error":     self.caused_error,
            "mentioned_at":     self.mentioned_at.isoformat() if self.mentioned_at else None,
        }
