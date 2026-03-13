# app/utils/query_generator.py
# -----------------------------------------
# Intelligent query generator for brand visibility monitoring.
# Generates realistic consumer-style search queries that simulate
# how real people search for products/services related to tracked brands.
#
# NO LLM calls — uses template-based generation with weighted randomization
# to produce diverse, realistic queries at scale.

import random
import hashlib
import time
from typing import Optional
from dataclasses import dataclass, field


# ───────────────────────────────────────────
# COMPANY PROFILES
# ───────────────────────────────────────────
# Each tracked company has a detailed profile defining:
#   - What they sell (products/services)
#   - Their industry and category
#   - Key competitors consumers compare them against
#   - Price points and customer segments
#   - Seasonal relevance and trending topics
#
# This is the KNOWLEDGE BASE that drives intelligent query generation
# without needing an LLM. The depth of these profiles directly
# determines the quality and diversity of generated queries.

COMPANY_PROFILES = {

    # ─── CAPITAL ONE ───
    "capital one": {
        "display_name": "Capital One",
        "industry": "financial_services",
        "category": "banking & credit cards",
        "products": [
            "credit cards", "savings accounts", "checking accounts",
            "auto loans", "business credit cards", "secured credit cards",
            "rewards credit cards", "travel credit cards", "cash back credit cards",
            "high-yield savings", "CDs", "money market accounts",
            "personal loans", "home loans", "banking app",
        ],
        "product_lines": [
            "Venture X", "Venture", "Quicksilver", "SavorOne", "Savor",
            "Platinum", "Spark Business", "Secured Mastercard",
            "VentureOne", "Quicksilver One", "360 Checking", "360 Savings",
            "360 Performance Savings", "360 CDs",
        ],
        "competitors": [
            "Chase", "American Express", "Citi", "Discover", "Bank of America",
            "Wells Fargo", "US Bank", "Barclays", "HSBC", "Ally Bank",
            "Marcus by Goldman Sachs", "Synchrony", "Navy Federal",
        ],
        "attributes": [
            "no annual fee", "no foreign transaction fees", "cash back",
            "travel rewards", "sign-up bonus", "welcome offer", "APR",
            "interest rate", "credit limit", "credit score requirement",
            "mobile app", "auto purchase eraser", "airport lounge access",
            "TSA PreCheck credit", "price protection", "fraud protection",
        ],
        "customer_segments": [
            "students", "young professionals", "travelers", "small business owners",
            "people with bad credit", "first-time credit card users", "families",
            "frequent flyers", "entrepreneurs", "freelancers", "military",
        ],
        "price_points": [
            "no annual fee", "$0 annual fee", "under $100 annual fee",
            "$395 annual fee", "low interest", "0% intro APR",
            "low APR", "balance transfer",
        ],
        "use_cases": [
            "building credit", "earning travel rewards", "getting cash back",
            "transferring a balance", "financing a car", "opening a savings account",
            "earning sign-up bonus", "booking travel", "everyday purchases",
            "grocery rewards", "dining rewards", "streaming rewards",
            "gas rewards", "online shopping rewards",
        ],
        "seasonal_topics": [
            "best credit cards {year}", "holiday spending",
            "travel credit cards for summer", "back to school banking",
            "tax refund savings", "new year financial goals",
            "black friday credit card deals",
        ],
    },

    # ─── EBAY ───
    "ebay": {
        "display_name": "eBay",
        "industry": "ecommerce",
        "category": "online marketplace",
        "products": [
            "online auctions", "buy it now listings", "used goods",
            "refurbished electronics", "collectibles", "vintage items",
            "sneakers", "trading cards", "auto parts", "fashion",
            "home goods", "electronics", "sporting goods", "toys",
            "jewelry", "watches", "coins", "art", "antiques",
        ],
        "product_lines": [
            "eBay Motors", "eBay Refurbished", "eBay Vault",
            "eBay Authenticity Guarantee", "eBay Live",
            "eBay Stores", "eBay for Charity", "eBay Plus",
        ],
        "competitors": [
            "Amazon", "Mercari", "Poshmark", "Facebook Marketplace",
            "Craigslist", "OfferUp", "Depop", "ThredUp", "Etsy",
            "Walmart Marketplace", "Alibaba", "StockX", "GOAT",
            "Reverb", "Swappa",
        ],
        "attributes": [
            "buyer protection", "seller fees", "free shipping",
            "authenticity guarantee", "money back guarantee",
            "auction format", "best offer", "international shipping",
            "seller ratings", "return policy", "price comparison",
            "bidding", "sniping", "proxy bidding",
        ],
        "customer_segments": [
            "bargain hunters", "collectors", "resellers", "vintage shoppers",
            "sneakerheads", "car enthusiasts", "small sellers",
            "thrift shoppers", "hobbyists", "antique dealers",
            "card collectors", "coin collectors",
        ],
        "price_points": [
            "under $10", "under $25", "under $50", "under $100",
            "cheap", "affordable", "best deals", "lowest price",
            "auction starting at $1", "free shipping",
        ],
        "use_cases": [
            "buying used electronics", "selling old stuff", "finding rare items",
            "buying auto parts", "collecting trading cards",
            "finding vintage clothing", "buying refurbished phones",
            "selling collectibles", "buying sneakers", "flipping items",
            "buying wholesale", "finding discontinued products",
        ],
        "seasonal_topics": [
            "best deals {year}", "holiday shopping",
            "black friday deals", "back to school deals",
            "spring cleaning selling", "tax refund shopping",
        ],
    },

    # ─── HEB ───
    "heb": {
        "display_name": "HEB",
        "industry": "grocery_retail",
        "category": "grocery store & supermarket",
        "products": [
            "groceries", "produce", "meat", "bakery", "deli",
            "organic food", "prepared meals", "meal kits",
            "pharmacy", "curbside pickup", "home delivery",
            "wine", "beer", "floral", "household essentials",
            "pet food", "baby products", "health and beauty",
        ],
        "product_lines": [
            "H-E-B brand", "Central Market", "Joe V's Smart Shop",
            "H-E-B Meal Simple", "H-E-B Organics", "H-E-B Select Ingredients",
            "H-E-B Primo Picks", "H-E-B Texas Tough", "Hill Country Fare",
            "H-E-B Curbside", "H-E-B Delivery", "Favor Delivery",
            "Mi Tienda", "H-E-B Plus",
        ],
        "competitors": [
            "Walmart", "Kroger", "Costco", "Whole Foods", "Trader Joe's",
            "Aldi", "Target", "Publix", "Albertsons", "Sam's Club",
            "Instacart", "Amazon Fresh", "Sprouts",
        ],
        "attributes": [
            "store brand quality", "Texas-based", "curbside pickup",
            "delivery", "weekly deals", "digital coupons", "meal prep",
            "fresh produce", "local products", "community support",
            "store layout", "customer service", "prices",
            "organic selection", "prepared foods",
        ],
        "customer_segments": [
            "Texas families", "budget shoppers", "organic shoppers",
            "meal preppers", "busy parents", "health-conscious shoppers",
            "foodies", "pet owners", "seniors",
        ],
        "price_points": [
            "budget-friendly", "affordable", "best value",
            "weekly specials", "coupon deals", "bulk buying",
            "store brand savings", "price match",
        ],
        "use_cases": [
            "weekly grocery shopping", "meal planning", "buying organic food",
            "ordering groceries online", "curbside grocery pickup",
            "finding fresh produce", "buying Texas products",
            "pharmacy prescriptions", "party catering",
            "holiday meal shopping", "quick dinner solutions",
        ],
        "seasonal_topics": [
            "thanksgiving dinner shopping", "super bowl party food",
            "summer grilling", "back to school lunches",
            "holiday baking ingredients", "spring produce",
        ],
    },

    # ─── HOME DEPOT ───
    "home depot": {
        "display_name": "Home Depot",
        "industry": "home_improvement",
        "category": "home improvement & hardware",
        "products": [
            "power tools", "hand tools", "lumber", "paint", "flooring",
            "appliances", "kitchen cabinets", "bathroom vanities",
            "lighting", "plumbing", "electrical", "roofing",
            "outdoor furniture", "grills", "lawn mowers", "garden supplies",
            "storage", "doors", "windows", "fencing", "decking",
            "smart home devices", "water heaters", "HVAC",
        ],
        "product_lines": [
            "Ryobi", "Milwaukee", "DeWalt", "Husky", "Glacier Bay",
            "Hampton Bay", "HDX", "Vigoro", "Home Decorators Collection",
            "Everbilt", "Commercial Electric", "Defiant",
            "Home Depot Rental", "Pro Xtra",
        ],
        "competitors": [
            "Lowe's", "Menards", "Ace Hardware", "True Value",
            "Tractor Supply", "IKEA", "Wayfair", "Amazon",
            "Sherwin-Williams", "Harbor Freight", "Northern Tool",
        ],
        "attributes": [
            "price match guarantee", "free delivery", "tool rental",
            "installation services", "pro discounts", "military discount",
            "DIY workshops", "online ordering", "in-store pickup",
            "return policy", "bulk pricing", "project calculator",
            "how-to guides", "contractor services",
        ],
        "customer_segments": [
            "homeowners", "DIY enthusiasts", "contractors", "landlords",
            "first-time home buyers", "renovators", "gardeners",
            "professional builders", "interior designers", "flippers",
        ],
        "price_points": [
            "under $50", "under $100", "under $200", "under $500",
            "under $1000", "budget", "best value", "professional grade",
            "affordable", "sale", "clearance",
        ],
        "use_cases": [
            "kitchen renovation", "bathroom remodel", "building a deck",
            "painting a room", "installing flooring", "buying power tools",
            "landscaping", "fence installation", "plumbing repair",
            "electrical work", "appliance shopping", "garage organization",
            "shed building", "patio furniture", "grill shopping",
        ],
        "seasonal_topics": [
            "spring garden prep", "summer outdoor living",
            "fall home maintenance", "winter weatherproofing",
            "memorial day sale", "labor day deals", "black friday tools",
        ],
    },

    # ─── DELL ───
    "dell": {
        "display_name": "Dell",
        "industry": "technology",
        "category": "computers & electronics",
        "products": [
            "laptops", "desktops", "monitors", "workstations",
            "gaming PCs", "servers", "storage solutions", "networking equipment",
            "docking stations", "keyboards", "mice", "webcams",
            "printers", "software", "IT infrastructure",
        ],
        "product_lines": [
            "XPS", "Inspiron", "Latitude", "Precision", "Vostro",
            "Alienware", "G Series", "OptiPlex", "PowerEdge",
            "UltraSharp", "Dell Pro", "Dell Plus", "Dell Premier",
        ],
        "competitors": [
            "HP", "Lenovo", "Apple", "ASUS", "Acer", "Microsoft Surface",
            "Samsung", "MSI", "Razer", "LG", "Toshiba",
            "Framework", "System76",
        ],
        "attributes": [
            "build quality", "battery life", "display quality", "performance",
            "port selection", "weight", "keyboard quality", "touchscreen",
            "upgradability", "warranty", "customer support", "price to performance",
            "repairability", "fan noise", "thermals", "webcam quality",
        ],
        "customer_segments": [
            "students", "business professionals", "gamers", "content creators",
            "software developers", "IT departments", "remote workers",
            "video editors", "graphic designers", "engineers",
            "small businesses", "enterprise",
        ],
        "price_points": [
            "under $300", "under $500", "under $700", "under $1000",
            "under $1500", "under $2000", "budget", "mid-range",
            "premium", "high-end", "affordable",
        ],
        "use_cases": [
            "college", "programming", "gaming", "video editing",
            "photo editing", "office work", "working from home",
            "graphic design", "3D rendering", "data science",
            "everyday use", "business travel", "presentations",
            "music production", "streaming",
        ],
        "seasonal_topics": [
            "back to school laptops", "black friday laptop deals",
            "best laptops {year}", "holiday gift guide",
            "prime day laptop deals", "cyber monday deals",
            "CES new releases", "graduation gifts",
        ],
    },

    # ─── CISCO ───
    "cisco": {
        "display_name": "Cisco",
        "industry": "enterprise_technology",
        "category": "networking & cybersecurity",
        "products": [
            "routers", "switches", "firewalls", "access points",
            "VPN solutions", "SD-WAN", "network security",
            "collaboration tools", "video conferencing", "cloud networking",
            "IoT networking", "data center networking", "wireless controllers",
            "network management software", "cybersecurity solutions",
        ],
        "product_lines": [
            "Meraki", "Webex", "Catalyst", "Nexus", "ISR",
            "ASA", "Firepower", "AnyConnect", "Umbrella", "Duo Security",
            "ThousandEyes", "AppDynamics", "Intersight", "DNA Center",
            "SecureX", "Secure Firewall", "Secure Endpoint",
        ],
        "competitors": [
            "Juniper Networks", "Aruba (HPE)", "Palo Alto Networks",
            "Fortinet", "Arista", "Ubiquiti", "Zoom", "Microsoft Teams",
            "VMware", "Cloudflare", "Zscaler", "CrowdStrike",
            "SonicWall", "Netgear", "TP-Link", "MikroTik",
        ],
        "attributes": [
            "reliability", "enterprise support", "scalability", "security features",
            "ease of management", "cloud-managed", "total cost of ownership",
            "integration", "API support", "licensing model", "performance",
            "throughput", "latency", "uptime", "certifications",
        ],
        "customer_segments": [
            "enterprise IT teams", "network administrators", "small businesses",
            "managed service providers", "government agencies", "education",
            "healthcare", "financial services", "retail",
            "remote workforce", "data center operators",
        ],
        "price_points": [
            "enterprise pricing", "SMB budget", "per-user licensing",
            "subscription model", "one-time purchase", "total cost of ownership",
            "competitive pricing", "value tier", "premium tier",
        ],
        "use_cases": [
            "setting up office network", "securing remote workers",
            "video conferencing", "SD-WAN deployment", "zero trust security",
            "cloud migration", "network monitoring", "branch office connectivity",
            "data center networking", "wireless deployment",
            "VPN for remote access", "network segmentation",
            "compliance", "incident response",
        ],
        "seasonal_topics": [
            "cybersecurity awareness month", "RSA conference",
            "Cisco Live announcements", "fiscal year IT budgeting",
            "back to school network upgrades", "end of year IT spending",
        ],
    },

    # ─── NFL ───
    "nfl": {
        "display_name": "NFL",
        "industry": "sports_entertainment",
        "category": "professional sports & entertainment",
        "products": [
            "game tickets", "streaming", "merchandise", "jerseys",
            "fantasy football", "NFL+", "Sunday Ticket",
            "NFL RedZone", "NFL Network", "NFL app",
            "NFL Shop", "collectibles", "memorabilia",
        ],
        "product_lines": [
            "NFL+", "NFL Sunday Ticket", "NFL RedZone",
            "NFL Network", "NFL Game Pass", "NFL Shop",
            "NFL Fantasy", "NFL Combine", "NFL Draft",
            "NFL Pro Bowl Games", "Super Bowl", "NFL Honors",
        ],
        "competitors": [
            "NBA", "MLB", "NHL", "MLS", "Premier League",
            "UFC", "NCAA Football", "XFL", "USFL",
            "ESPN+", "YouTube TV", "Hulu Live", "FuboTV",
            "Paramount+", "Peacock", "Amazon Prime Video",
        ],
        "attributes": [
            "game schedule", "standings", "scores", "highlights",
            "player stats", "draft picks", "free agency", "trades",
            "streaming quality", "blackout rules", "fantasy projections",
            "injury reports", "power rankings", "playoff picture",
        ],
        "customer_segments": [
            "football fans", "fantasy football players", "sports bettors",
            "cord cutters", "families", "tailgaters", "jersey collectors",
            "season ticket holders", "out-of-market fans", "international fans",
            "casual viewers", "die-hard fans",
        ],
        "price_points": [
            "free", "under $10/month", "under $50", "under $100",
            "season pass", "monthly subscription", "annual subscription",
            "student discount", "bundle deals",
        ],
        "use_cases": [
            "watching games live", "streaming out-of-market games",
            "playing fantasy football", "buying team jerseys",
            "checking scores and highlights", "watching NFL RedZone",
            "attending games", "tailgating", "betting on games",
            "watching the Super Bowl", "following the NFL Draft",
            "keeping up with trades and free agency",
        ],
        "seasonal_topics": [
            "NFL Draft {year}", "Super Bowl {year}", "NFL free agency",
            "NFL schedule release", "NFL preseason", "fantasy football draft",
            "NFL playoffs", "NFL combine", "NFL trade deadline",
            "Monday Night Football", "Thursday Night Football",
        ],
    },
}


# ───────────────────────────────────────────
# QUERY TEMPLATES
# ───────────────────────────────────────────
# These templates are organized by QUERY INTENT — the different reasons
# a real person searches. Each intent has templates for:
#   - branded (includes the company name)
#   - unbranded (generic category search, no company name)
#
# The templates use placeholders:
#   {company}     → Company display name
#   {product}     → Random product from profile
#   {product_line} → Specific product line name
#   {competitor}  → A competitor name
#   {attribute}   → A product attribute
#   {price}       → A price point
#   {use_case}    → A use case
#   {segment}     → A customer segment
#   {year}        → Current year

QUERY_TEMPLATES = {

    # ── PURCHASE INTENT: User wants to buy something ──
    "purchase_intent": {
        "branded": [
            "best {company} {product} {year}",
            "{company} {product_line} review",
            "is {company} {product_line} worth it",
            "should I buy {company} {product_line}",
            "{company} {product_line} vs {competitor} comparison",
            "{company} {product} {price}",
            "buy {company} {product_line}",
            "{company} {product_line} price",
            "{company} {product_line} deals",
            "{company} {product} for {segment}",
            "{company} {product_line} pros and cons",
            "where to buy {company} {product_line}",
            "{company} {product_line} discount code",
            "is {company} {product_line} good for {use_case}",
            "{company} {product_line} specifications",
            "{company} {product} {price} {year}",
            "new {company} {product_line} {year}",
            "{company} {product_line} sale",
        ],
        "unbranded": [
            "best {product} {year}",
            "best {product} for {use_case}",
            "best {product} {price}",
            "top {product} for {segment}",
            "{product} recommendations {year}",
            "what {product} should I buy",
            "best {product} for {use_case} {year}",
            "affordable {product} for {use_case}",
            "{product} buying guide {year}",
            "top rated {product} {year}",
            "most popular {product} right now",
            "{product} {price} that are actually good",
            "best value {product} {year}",
            "which {product} is best for {segment}",
            "top 10 {product} {year}",
            "best budget {product} for {use_case}",
            "{product} worth buying in {year}",
            "recommended {product} for {segment}",
        ],
    },

    # ── COMPARISON: User is deciding between options ──
    "comparison": {
        "branded": [
            "{company} vs {competitor} which is better",
            "{company} vs {competitor} {product}",
            "{company} or {competitor} for {use_case}",
            "{company} {product_line} vs {competitor} comparison {year}",
            "is {company} better than {competitor}",
            "{company} vs {competitor} {attribute}",
            "{company} compared to {competitor} for {segment}",
            "switching from {competitor} to {company}",
            "why choose {company} over {competitor}",
            "{company} vs {competitor} pros and cons",
            "{company} vs {competitor} {product} for {use_case}",
            "{company} vs {competitor} {year} which should I choose",
        ],
        "unbranded": [
            "best {product} comparison {year}",
            "top {product} compared side by side",
            "which {product} is best for {use_case}",
            "{product} comparison chart {year}",
            "how to choose the right {product}",
            "what to look for when buying {product}",
            "{product} tier list {year}",
            "ranking the best {product} {year}",
        ],
    },

    # ── RESEARCH: User is learning about the category ──
    "research": {
        "branded": [
            "{company} {product} review {year}",
            "{company} {product_line} honest review",
            "{company} {product} quality",
            "is {company} good for {use_case}",
            "{company} customer reviews",
            "{company} {product_line} long term review",
            "what do people think of {company} {product}",
            "{company} {product} reliability",
            "{company} {attribute} how good is it",
            "real user reviews {company} {product_line}",
            "{company} {product_line} after 6 months",
            "{company} {product_line} problems",
            "{company} {product} worth the money",
        ],
        "unbranded": [
            "{product} reviews {year}",
            "are {product} worth it",
            "things to know before buying {product}",
            "{product} buyer guide for {segment}",
            "most reliable {product} {year}",
            "how to pick the best {product} for {use_case}",
            "{product} what to avoid",
            "common mistakes buying {product}",
            "is it worth upgrading {product} in {year}",
            "{product} red flags to watch for",
        ],
    },

    # ── PROBLEM SOLVING: User has an issue or specific need ──
    "problem_solving": {
        "branded": [
            "best {company} {product} for {use_case}",
            "which {company} {product_line} is best for {segment}",
            "{company} {product} for {use_case} setup guide",
            "how to get the most out of {company} {product_line}",
            "{company} {product} tips for {segment}",
            "{company} best {product} for {use_case} {year}",
            "how to choose between {company} {product} models",
        ],
        "unbranded": [
            "best {product} for {use_case}",
            "what {product} do {segment} use",
            "how to choose {product} for {use_case}",
            "{product} recommendations for {use_case}",
            "what {product} do I need for {use_case}",
            "best {product} setup for {segment}",
            "{product} solutions for {use_case}",
            "how to improve {use_case} with the right {product}",
        ],
    },

    # ── DEALS & PRICING: User is price-sensitive ──
    "deals_pricing": {
        "branded": [
            "{company} {product_line} on sale",
            "{company} {product} deals {year}",
            "{company} {product} discount",
            "cheapest {company} {product}",
            "{company} {product_line} price drop",
            "{company} {product} coupon code {year}",
            "when does {company} have sales",
            "{company} {product} refurbished deals",
            "is {company} {product_line} overpriced",
            "{company} student discount {product}",
        ],
        "unbranded": [
            "best {product} deals right now",
            "cheapest good {product} {year}",
            "{product} {price} best options",
            "best {product} on sale today",
            "where to find cheap {product}",
            "best time to buy {product}",
            "{product} deals and coupons {year}",
            "clearance {product} still worth buying",
            "best refurbished {product} {year}",
        ],
    },

    # ── ALTERNATIVES: User is looking for options ──
    "alternatives": {
        "branded": [
            "alternatives to {company} {product}",
            "{product} similar to {company} {product_line}",
            "companies like {company} for {product}",
            "cheaper alternative to {company} {product_line}",
            "better than {company} for {use_case}",
            "brands like {company}",
            "{company} {product_line} alternatives {year}",
            "if you like {company} you might also like",
        ],
        "unbranded": [
            "best alternatives for {product} {year}",
            "underrated {product} brands",
            "hidden gem {product} brands {year}",
            "new {product} brands worth trying",
            "lesser known {product} that are actually good",
            "up and coming {product} brands {year}",
        ],
    },

    # ── SEASONAL / TRENDING: Timely queries ──
    "seasonal": {
        "branded": [
            "{company} {seasonal_topic}",
            "{company} new {product} {year}",
            "{company} latest {product_line} release",
            "what's new at {company} {year}",
            "{company} {product} lineup {year}",
        ],
        "unbranded": [
            "{seasonal_topic}",
            "best {product} for {seasonal_topic}",
            "top {product} picks {seasonal_topic}",
        ],
    },
}


# ───────────────────────────────────────────
# QUERY MODIFIERS
# ───────────────────────────────────────────
# Natural language additions that make queries more realistic
# and diverse. Real users add qualifiers, context, and phrasing
# variations that we simulate here.

QUERY_PREFIXES = [
    "", "", "", "", "",  # Most queries have no prefix (weighted)
    "what are the ",
    "what is the ",
    "can you recommend ",
    "help me find ",
    "I'm looking for ",
    "I need ",
    "looking for ",
    "searching for ",
    "recommend me ",
    "suggest ",
]

QUERY_SUFFIXES = [
    "", "", "", "", "", "", "",  # Most queries have no suffix (weighted)
    " reddit",
    " review",
    " worth it",
    " honest opinion",
    " in {year}",
    " this year",
    " right now",
    " today",
    " near me",
    " online",
]

CONVERSATIONAL_WRAPPERS = [
    "{query}",
    "{query}",
    "{query}",
    "{query}",
    "{query}",  # Most are plain (weighted heavily)
    "I want to know {query}",
    "Can you tell me about {query}",
    "What do you think about {query}",
    "I've been researching {query}",
    "Help me decide on {query}",
    "I'm trying to figure out {query}",
    "Quick question about {query}",
]


# ───────────────────────────────────────────
# MAIN GENERATION FUNCTION
# ───────────────────────────────────────────

@dataclass
class GeneratedQuery:
    """
    A single generated query with metadata.

    Attributes:
        text (str): The actual query text to send to LLMs.
        is_branded (bool): Whether the company name appears in the query.
        intent (str): The query intent category (purchase, comparison, etc.)
        company (str): The target company this query was generated for.
        metadata (dict): Additional context (product, competitor used, etc.)
    """
    text: str
    is_branded: bool
    intent: str
    company: str
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        brand_tag = "BRANDED" if self.is_branded else "UNBRANDED"
        return f"[{brand_tag}|{self.intent}] {self.text}"


def generate_queries(
    company_name: str,
    num_queries: int = 50,
    branded_ratio: float = 0.70,
    seed: Optional[int] = None,
    intents: Optional[list[str]] = None,
) -> list[GeneratedQuery]:
    """
    Generate realistic consumer search queries for brand visibility monitoring.

    This function creates diverse, realistic queries that simulate how real
    people search when they're considering products or services in a company's
    category. The queries are designed to be passed directly to LLM search
    functions (get_chatgpt_response, get_perplexity_response, etc.) to
    measure brand visibility.

    Args:
        company_name: Name of the company to generate queries for.
                      Must match a key in COMPANY_PROFILES (case-insensitive).
                      Supported: "capital one", "ebay", "heb", "home depot",
                                "dell", "cisco", "nfl"

        num_queries: Total number of queries to generate.

        branded_ratio: Fraction of queries that include the company name.
                       Default 0.70 (70% branded, 30% unbranded).
                       Recommended range: 0.60–0.80
                       Higher = more direct brand monitoring
                       Lower = more category visibility monitoring

        seed: Optional random seed for reproducibility.
              If None, uses current timestamp for variety.

        intents: Optional list of intent categories to include.
                 Default: all intents (purchase_intent, comparison, research,
                 problem_solving, deals_pricing, alternatives, seasonal).
                 Pass a subset to focus on specific query types.

    Returns:
        List of GeneratedQuery objects, each containing:
          - text: The query string ready to send to an LLM
          - is_branded: Whether the company name appears
          - intent: The intent category
          - company: The target company
          - metadata: Dict with product, competitor, etc. used

    Raises:
        ValueError: If company_name is not in COMPANY_PROFILES.

    Example:
        queries = generate_queries("dell", num_queries=50, branded_ratio=0.70)
        for q in queries[:5]:
            print(q)
        # [BRANDED|purchase_intent] best Dell XPS laptop 2025
        # [UNBRANDED|comparison] best laptops for programming under $1000
        # [BRANDED|research] Dell Inspiron 16 honest review
        # [UNBRANDED|purchase_intent] top rated laptops 2025
        # [BRANDED|deals_pricing] Dell XPS 13 student discount

    Algorithm Details:
        1. Determine how many branded vs unbranded queries (based on branded_ratio)
        2. Distribute queries across intent categories with weighted sampling:
           - purchase_intent:  30% (most common consumer search)
           - comparison:       20% (high purchase intent)
           - research:         18% (mid-funnel)
           - problem_solving:  12%
           - deals_pricing:    10%
           - alternatives:      5%
           - seasonal:          5%
        3. For each query slot, select a template and fill placeholders
           with randomly chosen values from the company profile
        4. Apply optional natural-language modifiers (prefixes, suffixes,
           conversational wrappers) for variety
        5. Deduplicate and ensure target count is met
    """
    # ── Validate company ──
    company_key = company_name.strip().lower()
    if company_key not in COMPANY_PROFILES:
        available = ", ".join(sorted(COMPANY_PROFILES.keys()))
        raise ValueError(
            f"Unknown company '{company_name}'. "
            f"Available: {available}"
        )

    profile = COMPANY_PROFILES[company_key]

    # ── Setup RNG ──
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random(time.time())

    current_year = time.strftime("%Y")

    # ── Determine branded vs unbranded counts ──
    num_branded = round(num_queries * branded_ratio)
    num_unbranded = num_queries - num_branded

    # ── Intent distribution weights ──
    default_intent_weights = {
        "purchase_intent": 0.30,
        "comparison": 0.20,
        "research": 0.18,
        "problem_solving": 0.12,
        "deals_pricing": 0.10,
        "alternatives": 0.05,
        "seasonal": 0.05,
    }

    if intents:
        # Filter to requested intents and re-normalize weights
        intent_weights = {k: v for k, v in default_intent_weights.items() if k in intents}
        if not intent_weights:
            raise ValueError(f"No valid intents in {intents}. Available: {list(default_intent_weights.keys())}")
        total = sum(intent_weights.values())
        intent_weights = {k: v / total for k, v in intent_weights.items()}
    else:
        intent_weights = default_intent_weights

    # ── Distribute queries across intents ──
    def _distribute_counts(total: int, weights: dict) -> dict:
        """Distribute a total count across categories by weight, handling remainders."""
        counts = {}
        remaining = total
        items = list(weights.items())

        for i, (intent, weight) in enumerate(items):
            if i == len(items) - 1:
                counts[intent] = remaining
            else:
                count = round(total * weight)
                count = min(count, remaining)
                counts[intent] = count
                remaining -= count

        return counts

    branded_distribution = _distribute_counts(num_branded, intent_weights)
    unbranded_distribution = _distribute_counts(num_unbranded, intent_weights)

    # ── Helper: fill template placeholders ──
    def _fill_template(template: str) -> tuple[str, dict]:
        """
        Replace all {placeholder} tokens in a template with random values
        from the company profile. Returns (filled_string, metadata_dict).
        """
        metadata = {}
        result = template

        # {company}
        if "{company}" in result:
            result = result.replace("{company}", profile["display_name"])
            metadata["company_mentioned"] = True

        # {product} — random product from the list
        if "{product}" in result:
            product = rng.choice(profile["products"])
            result = result.replace("{product}", product)
            metadata["product"] = product

        # {product_line} — specific named product
        if "{product_line}" in result:
            if profile["product_lines"]:
                product_line = rng.choice(profile["product_lines"])
            else:
                product_line = rng.choice(profile["products"])
            result = result.replace("{product_line}", product_line)
            metadata["product_line"] = product_line

        # {competitor}
        if "{competitor}" in result:
            competitor = rng.choice(profile["competitors"])
            result = result.replace("{competitor}", competitor)
            metadata["competitor"] = competitor

        # {attribute}
        if "{attribute}" in result:
            attribute = rng.choice(profile["attributes"])
            result = result.replace("{attribute}", attribute)
            metadata["attribute"] = attribute

        # {price}
        if "{price}" in result:
            price = rng.choice(profile["price_points"])
            result = result.replace("{price}", price)
            metadata["price_point"] = price

        # {use_case}
        if "{use_case}" in result:
            use_case = rng.choice(profile["use_cases"])
            result = result.replace("{use_case}", use_case)
            metadata["use_case"] = use_case

        # {segment}
        if "{segment}" in result:
            segment = rng.choice(profile["customer_segments"])
            result = result.replace("{segment}", segment)
            metadata["segment"] = segment

        # {seasonal_topic}
        if "{seasonal_topic}" in result:
            topic = rng.choice(profile["seasonal_topics"])
            topic = topic.replace("{year}", current_year)
            result = result.replace("{seasonal_topic}", topic)
            metadata["seasonal_topic"] = topic

        # {year}
        if "{year}" in result:
            result = result.replace("{year}", current_year)

        return result, metadata

    def _apply_modifier(query_text: str) -> str:
        """
        Optionally apply a natural-language modifier to make the query
        more varied and realistic. Only applied ~30% of the time to
        keep most queries clean and search-like.
        """
        # 70% chance: no modification (most real searches are short & direct)
        if rng.random() > 0.30:
            return query_text

        # Choose a modifier type
        modifier_type = rng.choices(
            ["prefix", "suffix", "wrapper"],
            weights=[0.35, 0.35, 0.30],
            k=1,
        )[0]

        if modifier_type == "prefix":
            prefix = rng.choice(QUERY_PREFIXES)
            if prefix:
                return prefix + query_text

        elif modifier_type == "suffix":
            suffix = rng.choice(QUERY_SUFFIXES)
            if suffix:
                suffix = suffix.replace("{year}", current_year)
                return query_text + suffix

        elif modifier_type == "wrapper":
            wrapper = rng.choice(CONVERSATIONAL_WRAPPERS)
            if wrapper != "{query}":
                return wrapper.replace("{query}", query_text)

        return query_text

    # ── Generate queries ──
    generated = []
    seen_texts = set()  # For deduplication
    max_attempts_per_query = 15  # Prevent infinite loops on small template sets

    def _generate_batch(count: int, is_branded: bool, intent: str):
        """Generate `count` queries for a given intent and branded/unbranded type."""
        template_key = "branded" if is_branded else "unbranded"

        if intent not in QUERY_TEMPLATES:
            return

        templates = QUERY_TEMPLATES[intent].get(template_key, [])
        if not templates:
            return

        attempts = 0
        produced = 0

        while produced < count and attempts < count * max_attempts_per_query:
            attempts += 1

            # Pick a random template
            template = rng.choice(templates)

            # Fill placeholders
            filled, metadata = _fill_template(template)

            # Apply optional natural-language modifier
            filled = _apply_modifier(filled)

            # Clean up whitespace and capitalization
            filled = " ".join(filled.split())  # Normalize whitespace

            # Deduplicate (case-insensitive)
            dedup_key = filled.lower().strip()
            if dedup_key in seen_texts:
                continue

            seen_texts.add(dedup_key)
            metadata["intent"] = intent

            generated.append(GeneratedQuery(
                text=filled,
                is_branded=is_branded,
                intent=intent,
                company=profile["display_name"],
                metadata=metadata,
            ))
            produced += 1

    # Generate branded queries across intents
    for intent, count in branded_distribution.items():
        _generate_batch(count, is_branded=True, intent=intent)

    # Generate unbranded queries across intents
    for intent, count in unbranded_distribution.items():
        _generate_batch(count, is_branded=False, intent=intent)

    # ── Shuffle the final list ──
    # We don't want all branded queries grouped together — interleave them
    # like a real user's search behavior would look (sometimes branded,
    # sometimes generic, switching between intents).
    rng.shuffle(generated)

    # ── Ensure we hit the target count ──
    # If deduplication removed too many, generate extras
    if len(generated) < num_queries:
        deficit = num_queries - len(generated)
        all_intents = list(intent_weights.keys())

        for _ in range(deficit * max_attempts_per_query):
            if len(generated) >= num_queries:
                break

            intent = rng.choice(all_intents)
            is_branded = rng.random() < branded_ratio

            _generate_batch(1, is_branded=is_branded, intent=intent)

        rng.shuffle(generated)

    # Trim to exact count (we might have slightly more from the deficit fill)
    generated = generated[:num_queries]

    return generated


# ───────────────────────────────────────────
# CONVENIENCE FUNCTIONS
# ───────────────────────────────────────────

def get_supported_companies() -> list[str]:
    """Return list of supported company names."""
    return [profile["display_name"] for profile in COMPANY_PROFILES.values()]


def get_company_profile(company_name: str) -> dict:
    """Return the full profile dict for a company."""
    company_key = company_name.strip().lower()
    if company_key not in COMPANY_PROFILES:
        raise ValueError(f"Unknown company: {company_name}")
    return COMPANY_PROFILES[company_key]


def generate_queries_summary(queries: list[GeneratedQuery]) -> dict:
    """
    Generate a statistical summary of a batch of generated queries.
    Useful for verifying the distribution looks right.

    Returns dict with counts by intent, branded ratio, etc.
    """
    total = len(queries)
    branded_count = sum(1 for q in queries if q.is_branded)
    unbranded_count = total - branded_count

    intent_counts = {}
    for q in queries:
        intent_counts[q.intent] = intent_counts.get(q.intent, 0) + 1

    return {
        "total": total,
        "branded": branded_count,
        "unbranded": unbranded_count,
        "branded_ratio": round(branded_count / total, 2) if total > 0 else 0,
        "by_intent": intent_counts,
        "company": queries[0].company if queries else None,
        "sample_branded": [q.text for q in queries if q.is_branded][:5],
        "sample_unbranded": [q.text for q in queries if not q.is_branded][:5],
    }