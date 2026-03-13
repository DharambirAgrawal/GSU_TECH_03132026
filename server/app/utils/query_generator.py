# app/utils/query_generator.py
# -----------------------------------------
# Intelligent query generator for brand visibility monitoring.
#
# ARCHITECTURE:
# Instead of rigid templates, this uses a COMPOSITIONAL approach:
#   1. Parse the product input (even if imprecise like "mobile" or "laptops")
#   2. Build query FRAGMENTS (subject, intent, qualifier, context)
#   3. Compose them using natural sentence patterns
#   4. Apply realistic human imperfections (typos aren't needed, but
#      casual phrasing, abbreviations, and varied formality ARE)
#
# The result: every single query is unique, realistic, and relevant.

import random
import time
import re
from typing import Optional
from dataclasses import dataclass, field


# ───────────────────────────────────────────
# OUTPUT DATA CLASS
# ───────────────────────────────────────────

@dataclass
class GeneratedQuery:
    text: str
    is_branded: bool
    query_type: str
    company: str
    product: str
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        tag = "★ BRANDED" if self.is_branded else "○ UNBRANDED"
        return f"[{tag}] {self.text}"


# ───────────────────────────────────────────
# COMPANY PROFILES
# ───────────────────────────────────────────

COMPANY_PROFILES = {
    "capital one": {
        "display_name": "Capital One",
        "role": "financial_provider",
        "owned_brands": [
            "Venture X", "Venture", "Quicksilver", "SavorOne",
            "Savor", "Spark", "Platinum", "360 Checking", "360 Savings",
        ],
        "competitors": [
            "Chase", "Amex", "American Express", "Citi", "Discover",
            "Bank of America", "Wells Fargo", "US Bank", "Ally",
        ],
        "brand_verbs": [
            "apply for", "get", "sign up for", "open",
        ],
    },
    "ebay": {
        "display_name": "eBay",
        "role": "marketplace",
        "owned_brands": [
            "eBay Refurbished", "eBay Motors", "eBay Authenticity Guarantee",
        ],
        "competitors": [
            "Amazon", "Walmart", "Facebook Marketplace", "Mercari",
            "Craigslist", "OfferUp", "Swappa", "Best Buy",
            "Newegg", "B&H Photo", "StockX", "Poshmark",
        ],
        "brand_verbs": [
            "buy on", "sell on", "find on", "shop on", "get from",
        ],
    },
    "heb": {
        "display_name": "HEB",
        "role": "retailer",
        "owned_brands": [
            "Central Market", "H-E-B Organics", "Hill Country Fare",
            "H-E-B Meal Simple", "Mi Tienda",
        ],
        "competitors": [
            "Walmart", "Kroger", "Costco", "Whole Foods", "Trader Joe's",
            "Aldi", "Target", "Publix", "Sprouts", "Sam's Club",
        ],
        "brand_verbs": [
            "buy at", "shop at", "get from", "find at", "order from",
        ],
    },
    "home depot": {
        "display_name": "Home Depot",
        "role": "retailer",
        "owned_brands": [
            "Ryobi", "Milwaukee", "Husky", "Hampton Bay",
            "Glacier Bay", "HDX", "Home Decorators Collection",
        ],
        "competitors": [
            "Lowe's", "Menards", "Ace Hardware", "Amazon",
            "Wayfair", "IKEA", "Harbor Freight",
        ],
        "brand_verbs": [
            "buy at", "get from", "shop at", "find at", "rent from",
        ],
    },
    "dell": {
        "display_name": "Dell",
        "role": "manufacturer",
        "owned_brands": [
            "XPS", "XPS 13", "XPS 14", "XPS 15", "XPS 16",
            "Inspiron", "Inspiron 14", "Inspiron 15", "Inspiron 16",
            "Latitude", "Precision", "Alienware", "G15", "G16",
            "Vostro", "OptiPlex", "UltraSharp",
        ],
        "competitors": [
            "HP", "Lenovo", "Apple", "ASUS", "Acer",
            "Microsoft Surface", "Samsung", "MSI", "Razer",
            "ThinkPad", "MacBook", "Framework",
        ],
        "brand_verbs": [
            "buy", "get", "upgrade to", "switch to",
        ],
    },
    "cisco": {
        "display_name": "Cisco",
        "role": "manufacturer",
        "owned_brands": [
            "Meraki", "Webex", "Catalyst", "Nexus",
            "Umbrella", "Duo", "AnyConnect", "Firepower",
            "ThousandEyes", "SecureX",
        ],
        "competitors": [
            "Juniper", "Aruba", "Palo Alto Networks", "Fortinet",
            "Arista", "Ubiquiti", "Zoom", "Microsoft Teams",
            "Cloudflare", "Zscaler", "CrowdStrike",
        ],
        "brand_verbs": [
            "deploy", "implement", "set up", "migrate to", "use",
        ],
    },
    "nfl": {
        "display_name": "NFL",
        "role": "service_provider",
        "owned_brands": [
            "NFL+", "Sunday Ticket", "NFL RedZone", "NFL Network",
            "NFL Game Pass", "NFL Shop", "NFL Fantasy",
        ],
        "competitors": [
            "NBA", "MLB", "NHL", "MLS", "Premier League",
            "UFC", "ESPN+", "YouTube TV", "Hulu Live",
            "FuboTV", "Peacock", "Amazon Prime Video",
        ],
        "brand_verbs": [
            "watch", "stream", "subscribe to", "get", "sign up for",
        ],
    },
}


# ───────────────────────────────────────────
# PRODUCT KNOWLEDGE — DEEP & REALISTIC
# ───────────────────────────────────────────
# Each product has extensive real-world knowledge that generates
# truly diverse queries. The key insight: real people search with
# SPECIFIC situations, not generic terms.

PRODUCT_KNOWLEDGE = {

    "phone": {
        "aliases": [
            "phone", "mobile", "mobile phone", "smartphone", "cell phone",
            "cellphone", "handset", "iphone", "android phone",
        ],
        "search_nouns": ["phone", "smartphone", "phone"],
        "specific_products": [
            "iPhone 16", "iPhone 16 Pro", "iPhone 16 Pro Max", "iPhone 15",
            "Samsung Galaxy S24", "Galaxy S24 Ultra", "Galaxy S24 FE",
            "Samsung Galaxy A55", "Galaxy A35", "Galaxy A15",
            "Google Pixel 9", "Pixel 9 Pro", "Pixel 8a",
            "OnePlus 12", "OnePlus Nord",
            "Samsung Galaxy Z Fold 6", "Galaxy Z Flip 6",
            "Motorola Edge", "Nothing Phone 2",
        ],
        "specs": [
            "128GB", "256GB", "512GB", "1TB",
            "5G", "dual SIM", "eSIM",
            "48MP camera", "200MP camera", "telephoto lens", "optical zoom",
            "6.1 inch", "6.7 inch", "6.9 inch",
            "AMOLED", "120Hz display", "LTPO", "titanium frame",
            "wireless charging", "fast charging", "IP68",
            "Snapdragon 8 Gen 3", "A17 Pro", "Tensor G4",
        ],
        "price_tiers": {
            "budget": ["under $200", "under $300", "under $250", "around $200", "cheap"],
            "mid": ["under $500", "under $600", "around $400", "around $500", "$300 to $500"],
            "high": ["under $800", "under $1000", "around $800", "$500 to $800"],
            "premium": ["under $1200", "under $1500", "flagship", "premium"],
        },
        "use_cases": [
            "photography", "mobile photography", "video recording", "vlogging",
            "gaming", "mobile gaming",
            "business", "work",
            "everyday use", "daily driver",
            "social media", "TikTok", "Instagram",
            "seniors", "elderly parents",
            "kids", "first phone for teenager",
            "travel", "international travel",
            "battery life", "heavy use",
        ],
        "buyer_personas": [
            "students", "college student", "photographer", "business professional",
            "teenager", "senior citizen", "parent",
            "gamer", "content creator", "developer",
            "someone on a budget", "first-time smartphone buyer",
            "iPhone user switching to Android", "Android user",
        ],
        "qualities_people_want": [
            "best camera", "longest battery life", "most durable",
            "best value for money", "fastest", "smoothest display",
            "lightest", "most compact", "best for one-handed use",
            "best speakers", "most secure", "best software updates",
            "easiest to use", "best build quality",
        ],
        "real_concerns": [
            "camera quality", "battery life", "screen size",
            "durability", "software updates", "storage space",
            "heating issues", "weight", "repairability",
            "resale value", "bloatware", "privacy",
            "screen brightness outdoors", "charging speed",
        ],
        "comparison_angles": [
            "camera comparison", "battery life test", "speed test",
            "display comparison", "durability test", "value for money",
            "which holds value better", "which gets more updates",
        ],
    },

    "laptop": {
        "aliases": [
            "laptop", "laptops", "notebook", "portable computer",
            "ultrabook", "chromebook", "macbook", "thinkpad",
            "gaming laptop", "work laptop", "school laptop",
        ],
        "search_nouns": ["laptop", "notebook", "laptop"],
        "specific_products": [
            "MacBook Air M3", "MacBook Air M4", "MacBook Pro 14", "MacBook Pro 16",
            "Dell XPS 13", "Dell XPS 14", "Dell XPS 15", "Dell XPS 16",
            "Dell Inspiron 14", "Dell Inspiron 15", "Dell Inspiron 16",
            "Dell Latitude 14", "Dell Precision 5690",
            "Lenovo ThinkPad X1 Carbon", "ThinkPad T14", "ThinkPad E14",
            "Lenovo IdeaPad 5", "Lenovo Yoga 9i", "Lenovo Legion Pro 5",
            "HP Spectre x360", "HP Pavilion", "HP EliteBook", "HP Envy",
            "ASUS ZenBook 14", "ASUS ROG Zephyrus", "ASUS Vivobook",
            "Acer Swift Go 14", "Acer Aspire 5", "Acer Nitro 5",
            "Samsung Galaxy Book4", "Microsoft Surface Laptop",
            "Razer Blade 16", "Framework Laptop 16",
        ],
        "specs": [
            "16GB RAM", "32GB RAM", "8GB RAM", "64GB RAM",
            "i7", "i9", "i5", "Core Ultra 7", "Core Ultra 9",
            "Ryzen 7", "Ryzen 9", "M3", "M3 Pro", "M4", "M4 Pro",
            "512GB SSD", "1TB SSD", "2TB SSD",
            "14 inch", "15 inch", "16 inch", "13 inch", "17 inch",
            "OLED", "OLED display", "4K display", "2K display", "touchscreen",
            "Thunderbolt 4", "USB-C", "HDMI",
            "RTX 4060", "RTX 4070", "RTX 4090",
            "fingerprint reader", "IR camera", "backlit keyboard",
        ],
        "price_tiers": {
            "budget": ["under $300", "under $400", "under $500", "around $400", "cheap"],
            "mid": ["under $700", "under $800", "under $1000", "around $700", "$500 to $800"],
            "high": ["under $1200", "under $1500", "around $1200", "$1000 to $1500"],
            "premium": ["under $2000", "under $2500", "over $1500", "money is not an issue"],
        },
        "use_cases": [
            "college", "university", "school work",
            "programming", "software development", "web development", "coding",
            "video editing", "photo editing", "graphic design", "3D rendering",
            "gaming", "casual gaming", "AAA gaming",
            "business", "office work", "working from home", "remote work",
            "data science", "machine learning", "AI development",
            "music production", "streaming on Twitch",
            "everyday use", "browsing and Netflix",
            "architecture", "CAD work", "engineering",
            "writing", "blogging", "journalism",
        ],
        "buyer_personas": [
            "college student", "CS student", "engineering student",
            "software developer", "web developer", "data scientist",
            "graphic designer", "video editor", "photographer",
            "gamer", "casual user", "business traveler",
            "writer", "freelancer", "accountant",
            "teacher", "professor", "researcher",
            "first-time buyer", "someone switching from Mac",
            "someone switching from Windows",
        ],
        "qualities_people_want": [
            "lightweight", "thin and light", "long battery life",
            "fast", "powerful", "quiet fans", "silent",
            "durable", "reliable", "portable",
            "best value", "best bang for buck",
            "best display", "best keyboard", "best trackpad",
            "most upgradable", "easiest to repair",
        ],
        "real_concerns": [
            "battery life", "weight", "screen quality", "keyboard feel",
            "fan noise", "thermals", "overheating",
            "build quality", "port selection", "webcam quality",
            "durability", "repairability", "upgradability",
            "bloatware", "trackpad size", "speaker quality",
            "hinge durability", "flex in the chassis",
        ],
        "comparison_angles": [
            "which is faster", "battery life comparison",
            "build quality comparison", "which is better for",
            "display comparison", "keyboard comparison",
            "which runs cooler", "which is lighter",
            "which has better ports", "value comparison",
        ],
    },

    "tv": {
        "aliases": [
            "tv", "television", "smart tv", "flatscreen", "flat screen",
            "oled tv", "4k tv", "big screen tv",
        ],
        "search_nouns": ["TV", "television", "smart TV"],
        "specific_products": [
            "LG C4 OLED", "LG G4 OLED", "LG B4 OLED",
            "Samsung S95D", "Samsung QN90D", "Samsung The Frame",
            "Sony Bravia XR A95L", "Sony X90L", "Sony A80L",
            "TCL QM8", "TCL S4", "Hisense U8N", "Hisense U7N",
            "Vizio MQX", "Samsung S90D",
        ],
        "specs": [
            '55"', '65"', '75"', '85"', '50"', '43"', '77"',
            "4K", "8K", "OLED", "QLED", "Mini-LED", "Neo QLED", "QD-OLED",
            "120Hz", "144Hz", "HDR10+", "Dolby Vision", "Dolby Atmos",
            "HDMI 2.1", "VRR", "ALLM", "eARC",
            "Google TV", "Roku TV", "Tizen", "webOS", "Fire TV",
        ],
        "price_tiers": {
            "budget": ["under $300", "under $400", "under $500", "cheap", "around $300"],
            "mid": ["under $700", "under $800", "under $1000", "around $700"],
            "high": ["under $1500", "under $2000", "around $1500"],
            "premium": ["under $3000", "over $2000", "money no object"],
        },
        "use_cases": [
            "living room", "bedroom", "gaming", "PS5 gaming", "Xbox gaming",
            "movies", "movie night", "home theater",
            "sports watching", "football", "watching the game",
            "streaming Netflix", "bright room", "dark room",
            "small room", "apartment", "outdoor patio",
            "wall mounting", "above fireplace",
        ],
        "buyer_personas": [
            "gamer", "movie lover", "sports fan", "casual viewer",
            "home theater enthusiast", "apartment dweller",
            "family", "couple", "tech enthusiast",
        ],
        "qualities_people_want": [
            "best picture quality", "brightest", "best for dark rooms",
            "best for gaming", "lowest input lag", "best motion handling",
            "best value", "thinnest", "best built-in speakers",
            "best for sports", "best for movies",
        ],
        "real_concerns": [
            "picture quality", "burn-in", "brightness",
            "viewing angles", "input lag", "motion blur",
            "smart TV interface", "sound quality", "reliability",
            "power consumption", "glare", "blooming",
        ],
        "comparison_angles": [
            "OLED vs QLED", "which has better picture",
            "which is brighter", "which is better for gaming",
            "picture quality comparison", "which one for sports",
        ],
    },

    "headphones": {
        "aliases": [
            "headphones", "earbuds", "wireless earbuds", "earphones",
            "ANC headphones", "noise cancelling headphones", "airpods",
            "over ear headphones", "in ear", "bluetooth headphones",
        ],
        "search_nouns": ["headphones", "earbuds", "headphones"],
        "specific_products": [
            "AirPods Pro 2", "AirPods 4", "AirPods Max",
            "Sony WH-1000XM5", "Sony WF-1000XM5",
            "Bose QuietComfort Ultra", "Bose QC45",
            "Samsung Galaxy Buds3 Pro", "Galaxy Buds FE",
            "Sennheiser Momentum 4", "Sennheiser HD 660S2",
            "JBL Tour One M2", "JBL Tune 770NC",
            "Nothing Ear 2", "Google Pixel Buds Pro 2",
        ],
        "specs": [
            "active noise cancelling", "ANC", "transparency mode",
            "wireless", "Bluetooth 5.3", "Bluetooth 5.4",
            "spatial audio", "lossless audio", "LDAC", "aptX",
            "multipoint", "30 hour battery", "40 hour battery",
            "IP67", "IPX4", "sweatproof", "waterproof",
        ],
        "price_tiers": {
            "budget": ["under $30", "under $50", "under $75", "cheap"],
            "mid": ["under $100", "under $150", "around $100", "$50 to $100"],
            "high": ["under $200", "under $250", "around $200"],
            "premium": ["under $350", "under $400", "under $500", "high end"],
        },
        "use_cases": [
            "commuting", "train commute", "airplane travel",
            "working out", "gym", "running", "jogging",
            "office", "work calls", "zoom meetings",
            "studying", "library", "focus",
            "gaming", "music listening", "audiophile",
            "sleeping", "ASMR", "meditation",
            "podcast listening", "mixing music",
        ],
        "buyer_personas": [
            "commuter", "gym goer", "runner", "audiophile",
            "remote worker", "student", "traveler", "gamer",
            "podcast listener", "music producer",
        ],
        "qualities_people_want": [
            "best sound quality", "best noise cancelling", "most comfortable",
            "longest battery", "best microphone for calls",
            "best bass", "most durable", "best for small ears",
            "best value", "best for glasses wearers",
        ],
        "real_concerns": [
            "comfort", "sound quality", "noise cancellation effectiveness",
            "battery life", "microphone quality", "call quality",
            "fit", "ear pain after long use", "connectivity issues",
            "wind noise", "latency", "case size",
        ],
        "comparison_angles": [
            "sound quality comparison", "comfort comparison",
            "ANC comparison", "which has better bass",
            "which is more comfortable", "which blocks more noise",
        ],
    },

    "monitor": {
        "aliases": [
            "monitor", "monitors", "computer monitor", "display",
            "screen", "external display", "gaming monitor",
            "ultrawide", "ultrawide monitor",
        ],
        "search_nouns": ["monitor", "display", "monitor"],
        "specific_products": [
            "Dell UltraSharp U2724D", "Dell S2722QC", "Dell U3423WE",
            "LG 27GP850-B", "LG 27UK850-W", "LG 34WN80C",
            "Samsung Odyssey G7", "Samsung ViewFinity S9",
            "ASUS ProArt PA278QV", "ASUS ROG Swift PG27AQN",
            "BenQ PD2725U", "BenQ EW3270U",
            "Apple Studio Display", "Apple Pro Display XDR",
        ],
        "specs": [
            '24"', '27"', '32"', '34"', '38"', '49"',
            "4K", "1440p", "5K", "ultrawide", "curved",
            "144Hz", "165Hz", "240Hz", "360Hz",
            "IPS", "OLED", "VA", "Mini-LED", "nano-IPS",
            "USB-C", "USB-C 90W", "KVM switch", "built-in speakers",
            "HDR600", "HDR1000", "HDR400",
            "1ms response", "sRGB 100%", "DCI-P3 95%",
        ],
        "price_tiers": {
            "budget": ["under $150", "under $200", "under $250", "cheap"],
            "mid": ["under $300", "under $400", "under $500", "around $350"],
            "high": ["under $700", "under $800", "under $1000"],
            "premium": ["under $1500", "under $2000", "high end"],
        },
        "use_cases": [
            "programming", "coding", "software development",
            "gaming", "competitive gaming", "casual gaming",
            "photo editing", "video editing", "color grading",
            "graphic design", "UI/UX design", "3D modeling",
            "office work", "spreadsheets", "multitasking",
            "dual monitor setup", "triple monitor",
            "work from home", "day trading",
            "Mac mini setup", "MacBook external display",
        ],
        "buyer_personas": [
            "developer", "programmer", "gamer",
            "designer", "photographer", "video editor",
            "office worker", "day trader", "architect",
            "student", "remote worker",
        ],
        "qualities_people_want": [
            "most color accurate", "highest refresh rate",
            "best for eye strain", "best ergonomic stand",
            "best value", "sharpest text", "best for reading code",
            "best USB-C monitor", "best ultrawide",
        ],
        "real_concerns": [
            "color accuracy", "response time", "eye strain",
            "dead pixels", "backlight bleed", "uniformity",
            "stand quality", "adjustability", "cable management",
            "text clarity", "pixel density",
        ],
        "comparison_angles": [
            "color accuracy comparison", "response time test",
            "which is better for eyes", "text clarity comparison",
            "which has better stand",
        ],
    },

    "tablet": {
        "aliases": [
            "tablet", "tablets", "ipad", "android tablet",
            "drawing tablet", "e-reader", "kindle",
        ],
        "search_nouns": ["tablet", "tablet", "iPad"],
        "specific_products": [
            "iPad Air M2", "iPad Pro M4", "iPad 10th gen", "iPad mini",
            "Samsung Galaxy Tab S9", "Galaxy Tab S9 FE", "Galaxy Tab A9",
            "Google Pixel Tablet", "Amazon Fire HD 10", "Amazon Fire Max 11",
            "Lenovo Tab P12", "OnePlus Pad 2",
            "Microsoft Surface Pro 10", "Surface Go 4",
            "reMarkable 2", "Kindle Scribe",
        ],
        "specs": [
            "10 inch", "11 inch", "12.9 inch", "13 inch", "8 inch",
            "128GB", "256GB", "512GB", "1TB",
            "WiFi", "WiFi + Cellular", "5G",
            "Apple Pencil", "S Pen", "stylus support",
            "keyboard case", "Magic Keyboard",
            "M2 chip", "M4 chip", "Snapdragon",
        ],
        "price_tiers": {
            "budget": ["under $150", "under $200", "under $250", "cheap"],
            "mid": ["under $400", "under $500", "around $400", "$300 to $500"],
            "high": ["under $800", "under $1000", "around $800"],
            "premium": ["under $1500", "under $2000", "high end"],
        },
        "use_cases": [
            "note taking", "college notes", "handwritten notes",
            "drawing", "digital art", "illustration", "procreate",
            "reading", "reading textbooks", "PDF annotation",
            "kids", "kids entertainment", "child's first tablet",
            "Netflix", "watching videos", "streaming",
            "travel", "airplane entertainment",
            "laptop replacement", "light productivity",
            "sheet music", "recipe display in kitchen",
        ],
        "buyer_personas": [
            "student", "artist", "digital artist",
            "parent buying for kids", "reader", "traveler",
            "professional", "musician", "teacher",
        ],
        "qualities_people_want": [
            "best for drawing", "best for note taking",
            "best for reading", "best for kids",
            "best value", "best screen", "longest battery",
            "lightest", "most portable",
        ],
        "real_concerns": [
            "screen quality", "stylus latency", "palm rejection",
            "app availability", "storage space", "battery life",
            "weight", "durability for kids", "accessories cost",
        ],
        "comparison_angles": [
            "vs iPad", "vs laptop", "which is better for notes",
            "which has better stylus", "screen comparison",
        ],
    },

    "credit card": {
        "aliases": [
            "credit card", "credit cards", "rewards card", "cashback card",
            "travel card", "cash back credit card", "first credit card",
            "business credit card", "secured credit card",
        ],
        "search_nouns": ["credit card", "card", "credit card"],
        "specific_products": [
            "Chase Sapphire Preferred", "Chase Sapphire Reserve",
            "Chase Freedom Unlimited", "Chase Freedom Flex",
            "Amex Gold", "Amex Platinum", "Amex Blue Cash Preferred",
            "Capital One Venture X", "Capital One Venture", "Capital One Quicksilver",
            "Capital One SavorOne", "Capital One Spark",
            "Citi Double Cash", "Citi Custom Cash", "Citi Premier",
            "Discover it Cash Back", "Discover it Miles",
            "Bank of America Customized Cash", "US Bank Altitude Go",
            "Wells Fargo Active Cash", "Apple Card",
        ],
        "specs": [
            "no annual fee", "0% intro APR", "0% APR for 18 months",
            "3% cash back", "5% cash back", "2x points", "3x points", "5x points",
            "no foreign transaction fees", "travel insurance",
            "airport lounge access", "Priority Pass",
            "cell phone protection", "purchase protection",
            "balance transfer offer", "welcome bonus",
            "$200 bonus", "$750 bonus", "60,000 points bonus",
        ],
        "price_tiers": {
            "budget": ["no annual fee", "free", "$0 annual fee"],
            "mid": ["under $100 annual fee", "worth the fee", "low annual fee"],
            "high": ["under $400 annual fee", "$250 annual fee"],
            "premium": ["$550 annual fee", "$695 annual fee", "premium annual fee"],
        },
        "use_cases": [
            "everyday spending", "groceries", "gas", "dining out",
            "restaurants", "travel", "international travel",
            "hotels", "flights", "airline miles",
            "building credit", "credit score improvement",
            "balance transfer", "paying off debt",
            "business expenses", "freelance expenses",
            "online shopping", "Amazon purchases",
            "large purchase financing", "wedding expenses",
        ],
        "buyer_personas": [
            "college student", "young professional", "frequent traveler",
            "first-time applicant", "someone with fair credit",
            "someone with excellent credit", "small business owner",
            "family", "couple", "person rebuilding credit",
            "someone who travels internationally",
            "someone who eats out a lot",
        ],
        "qualities_people_want": [
            "highest cash back", "best travel rewards",
            "best sign-up bonus", "best for beginners",
            "most flexible rewards", "best for groceries",
            "best for dining", "best no annual fee",
            "easiest to get approved", "best for building credit",
        ],
        "real_concerns": [
            "APR", "interest rate", "annual fee worth it",
            "credit score requirement", "approval odds",
            "foreign transaction fees", "reward redemption difficulty",
            "customer service", "fraud protection", "app quality",
        ],
        "comparison_angles": [
            "which has better rewards", "which has lower APR",
            "which is easier to get", "rewards comparison",
            "which has better app", "customer service comparison",
        ],
    },

    "savings account": {
        "aliases": [
            "savings account", "savings", "high yield savings",
            "high-yield savings", "hys", "hysa",
            "online savings", "best savings rate",
        ],
        "search_nouns": ["savings account", "high-yield savings account", "savings account"],
        "specific_products": [
            "Marcus by Goldman Sachs", "Ally Bank savings",
            "Capital One 360 Performance Savings",
            "Discover Online Savings", "American Express HYSA",
            "Wealthfront Cash Account", "Betterment Cash Reserve",
            "SoFi Savings", "CIT Bank savings",
            "Bread Savings", "Barclays Online Savings",
        ],
        "specs": [
            "5% APY", "4.5% APY", "4% APY", "high APY",
            "no minimum balance", "no monthly fees", "FDIC insured",
            "no withdrawal limits", "mobile app", "auto-transfer",
            "joint account option", "sub-accounts", "buckets",
        ],
        "price_tiers": {
            "budget": ["no fees", "no minimum", "free"],
            "mid": ["best rate", "competitive APY"],
            "high": ["highest APY", "top rate"],
            "premium": ["best overall", "premium features"],
        },
        "use_cases": [
            "emergency fund", "rainy day fund",
            "saving for a house", "down payment savings",
            "saving for vacation", "travel fund",
            "parking cash", "short-term savings",
            "kids savings account", "baby fund",
            "wedding savings", "car fund",
            "retirement supplement",
        ],
        "buyer_personas": [
            "young adult", "first-time saver", "parent",
            "recent graduate", "couple saving for house",
            "retiree", "freelancer",
        ],
        "qualities_people_want": [
            "highest interest rate", "best APY", "easiest to use",
            "best app", "most trusted", "best customer service",
            "fastest transfers", "best for multiple goals",
        ],
        "real_concerns": [
            "interest rate", "monthly fees", "minimum balance",
            "withdrawal limits", "transfer speed", "FDIC insurance",
            "app quality", "customer service", "rate stability",
        ],
        "comparison_angles": [
            "APY comparison", "which has highest rate",
            "which has best app", "fees comparison",
        ],
    },

    "groceries": {
        "aliases": [
            "groceries", "grocery", "food", "grocery shopping",
            "food shopping", "meal prep", "weekly groceries",
            "organic food", "produce", "meat",
        ],
        "search_nouns": ["groceries", "grocery shopping", "groceries"],
        "specific_products": [
            "organic produce", "grass-fed beef", "free-range chicken",
            "plant-based meat", "meal kits", "prepared meals",
            "store brand products", "bulk items",
        ],
        "specs": [
            "organic", "non-GMO", "gluten-free", "keto", "vegan",
            "locally sourced", "farm fresh", "antibiotic-free",
            "curbside pickup", "same-day delivery", "1-hour delivery",
        ],
        "price_tiers": {
            "budget": ["on a tight budget", "cheapest", "under $50/week", "frugal"],
            "mid": ["reasonable", "good value", "under $100/week", "under $150/week"],
            "high": ["organic budget", "quality over price", "under $200/week"],
            "premium": ["money no object", "best quality", "premium organic"],
        },
        "use_cases": [
            "weekly shopping", "family meal prep", "healthy eating",
            "feeding a family of 4", "feeding a family of 5",
            "cooking for one", "single person meals",
            "baby food", "toddler meals",
            "thanksgiving dinner", "holiday cooking", "christmas dinner",
            "super bowl party food", "game day snacks",
            "summer grilling", "BBQ supplies",
            "packed lunches", "school lunches",
            "diabetes-friendly meals", "heart-healthy diet",
        ],
        "buyer_personas": [
            "busy parent", "family of four", "single person",
            "health-conscious shopper", "budget shopper",
            "meal prepper", "college student",
            "senior on fixed income", "new parent",
        ],
        "qualities_people_want": [
            "freshest produce", "best meat quality", "best store brand",
            "best organic selection", "cheapest overall",
            "fastest delivery", "best curbside pickup experience",
            "cleanest stores", "friendliest staff",
            "best prepared foods section",
        ],
        "real_concerns": [
            "prices", "produce freshness", "meat quality",
            "organic authenticity", "delivery reliability",
            "out-of-stock items", "substitution quality",
            "store cleanliness", "checkout speed",
        ],
        "comparison_angles": [
            "price comparison", "which has fresher produce",
            "which is cheapest overall", "store brand quality comparison",
            "delivery experience comparison",
        ],
    },

    "power tools": {
        "aliases": [
            "power tools", "drill", "impact driver", "circular saw",
            "power tool set", "cordless tools", "tools", "tool set",
        ],
        "search_nouns": ["power tools", "drill", "tools"],
        "specific_products": [
            "DeWalt 20V MAX drill", "DeWalt DCD999", "DeWalt combo kit",
            "Milwaukee M18 Fuel", "Milwaukee 2804-20",
            "Makita 18V LXT", "Makita XFD131",
            "Ryobi ONE+ 18V", "Ryobi HP brushless",
            "Bosch 18V", "Bosch GDX18V-1800",
            "Ridgid 18V", "Craftsman V20",
        ],
        "specs": [
            "20V", "18V", "12V", "brushless motor", "brushed",
            "cordless", "lithium-ion", "4.0Ah battery", "5.0Ah battery",
            "variable speed", "hammer function", "LED light",
            "belt clip", "carrying case",
        ],
        "price_tiers": {
            "budget": ["under $50", "under $75", "under $100", "cheap"],
            "mid": ["under $150", "under $200", "around $150", "$100 to $200"],
            "high": ["under $300", "under $400", "around $300"],
            "premium": ["under $500", "under $600", "professional grade"],
        },
        "use_cases": [
            "home repair", "hanging shelves", "deck building",
            "woodworking", "furniture making", "cabinet building",
            "renovation", "bathroom remodel", "kitchen remodel",
            "DIY projects", "weekend projects",
            "professional construction", "framing",
            "auto repair", "plumbing",
        ],
        "buyer_personas": [
            "homeowner", "first-time homeowner", "DIYer",
            "professional contractor", "woodworker",
            "weekend warrior", "hobbyist", "handyman",
            "someone who's never used power tools",
        ],
        "qualities_people_want": [
            "most powerful", "most reliable", "longest battery life",
            "best starter set", "lightest", "most durable",
            "best value combo kit", "easiest to use",
        ],
        "real_concerns": [
            "battery life", "power", "durability",
            "weight", "battery interchangeability",
            "warranty", "parts availability", "noise level",
        ],
        "comparison_angles": [
            "which battery system is best", "power comparison",
            "durability test", "which brand is most reliable",
            "combo kit comparison",
        ],
    },

    "paint": {
        "aliases": [
            "paint", "wall paint", "interior paint", "exterior paint",
            "house paint", "room paint",
        ],
        "search_nouns": ["paint", "interior paint", "paint"],
        "specific_products": [
            "Benjamin Moore Regal Select", "Benjamin Moore Aura",
            "Sherwin-Williams Duration", "Sherwin-Williams Emerald",
            "Behr Dynasty", "Behr Marquee", "Behr Premium Plus",
            "PPG Diamond", "Valspar Signature",
        ],
        "specs": [
            "flat", "matte", "eggshell", "satin", "semi-gloss", "gloss",
            "one coat", "self-priming", "low VOC", "zero VOC",
            "washable", "scrubbable", "mildew resistant",
            "paint and primer in one",
        ],
        "price_tiers": {
            "budget": ["cheapest", "under $25/gallon", "budget"],
            "mid": ["under $40/gallon", "mid-range", "around $35/gallon"],
            "high": ["under $60/gallon", "premium", "around $50/gallon"],
            "premium": ["under $80/gallon", "best available", "top of the line"],
        },
        "use_cases": [
            "living room", "bedroom", "master bedroom",
            "bathroom", "kitchen", "kitchen cabinets",
            "exterior siding", "front door", "trim",
            "ceiling", "basement", "nursery", "kids room",
            "accent wall", "whole house repaint",
            "rental property", "flipping a house",
        ],
        "buyer_personas": [
            "homeowner", "first-time painter", "DIYer",
            "landlord", "house flipper", "interior designer",
            "professional painter",
        ],
        "qualities_people_want": [
            "best one coat coverage", "most durable",
            "easiest to apply", "lowest odor",
            "best for beginners", "most washable",
            "best color selection", "truest color",
        ],
        "real_concerns": [
            "coverage", "durability", "drying time", "odor",
            "washability", "color accuracy", "dripping",
            "brush marks", "roller marks",
        ],
        "comparison_angles": [
            "coverage comparison", "durability test",
            "which dries fastest", "which smells least",
        ],
    },

    "appliances": {
        "aliases": [
            "appliances", "refrigerator", "fridge", "washer", "dryer",
            "washer and dryer", "dishwasher", "oven", "range",
            "kitchen appliances", "laundry", "washing machine",
        ],
        "search_nouns": ["appliances", "refrigerator", "washer and dryer"],
        "specific_products": [
            "LG InstaView refrigerator", "Samsung Bespoke fridge",
            "Whirlpool top load washer", "LG WashTower",
            "Bosch 800 Series dishwasher", "Samsung Smart dishwasher",
            "GE Profile range", "KitchenAid stand mixer",
        ],
        "specs": [
            "stainless steel", "fingerprint resistant", "Energy Star",
            "smart", "WiFi enabled", "French door",
            "counter depth", "side-by-side", "bottom freezer",
            "front load", "top load", "stackable",
            "quiet operation", "steam clean", "self-clean",
        ],
        "price_tiers": {
            "budget": ["under $500", "under $600", "cheapest", "budget"],
            "mid": ["under $800", "under $1000", "around $800", "$600 to $1000"],
            "high": ["under $1500", "under $2000", "around $1500"],
            "premium": ["under $3000", "high end", "luxury"],
        },
        "use_cases": [
            "small kitchen", "large family", "apartment",
            "new home", "kitchen remodel", "replacing old one",
            "rental property", "energy savings", "first apartment",
        ],
        "buyer_personas": [
            "homeowner", "first-time buyer", "renter",
            "landlord", "new homeowner", "family",
            "couple", "someone downsizing",
        ],
        "qualities_people_want": [
            "most reliable", "quietest", "most energy efficient",
            "best value", "longest lasting", "best looking",
            "easiest to clean", "best smart features",
        ],
        "real_concerns": [
            "reliability", "noise level", "energy cost",
            "repair frequency", "parts availability",
            "size", "warranty", "delivery",
        ],
        "comparison_angles": [
            "reliability comparison", "which brand lasts longest",
            "energy efficiency comparison", "noise comparison",
        ],
    },

    "router": {
        "aliases": [
            "router", "wifi router", "mesh wifi", "wifi", "wireless router",
            "mesh system", "wifi system", "internet router", "wifi 7",
        ],
        "search_nouns": ["router", "WiFi router", "mesh WiFi system"],
        "specific_products": [
            "ASUS RT-AX86U", "ASUS ZenWiFi", "ASUS ROG Rapture",
            "TP-Link Deco", "TP-Link Archer AX73",
            "Netgear Nighthawk", "Netgear Orbi",
            "Eero Pro 6E", "Eero 6+",
            "Google Nest WiFi Pro", "Linksys Velop",
            "Ubiquiti UniFi Dream Machine",
        ],
        "specs": [
            "WiFi 6", "WiFi 6E", "WiFi 7", "tri-band", "dual-band",
            "mesh", "2.5G WAN", "10G Ethernet",
            "WPA3", "VPN server", "MU-MIMO", "OFDMA",
            "parental controls", "QoS", "USB 3.0",
        ],
        "price_tiers": {
            "budget": ["under $50", "under $75", "under $100", "cheap"],
            "mid": ["under $150", "under $200", "around $150", "$100 to $200"],
            "high": ["under $300", "under $400", "around $300"],
            "premium": ["under $500", "under $700", "enterprise grade"],
        },
        "use_cases": [
            "large house", "3000 sq ft home", "2-story house",
            "small apartment", "studio apartment",
            "gaming", "4K streaming", "work from home",
            "smart home with many devices", "50+ devices",
            "home office", "backyard coverage",
            "dead zone elimination",
        ],
        "buyer_personas": [
            "homeowner", "gamer", "remote worker",
            "tech enthusiast", "family with kids",
            "apartment dweller", "IT professional",
            "someone frustrated with slow wifi",
        ],
        "qualities_people_want": [
            "fastest", "best range", "most reliable",
            "easiest to set up", "best for gaming",
            "best parental controls", "best value",
        ],
        "real_concerns": [
            "speed", "range", "dead zones", "reliability",
            "setup difficulty", "firmware updates",
            "security", "ISP compatibility",
        ],
        "comparison_angles": [
            "speed comparison", "range comparison",
            "mesh vs single router", "which covers more area",
            "which is more reliable",
        ],
    },

    "network security": {
        "aliases": [
            "network security", "firewall", "cybersecurity",
            "endpoint security", "enterprise security", "vpn",
            "zero trust", "sase", "siem",
        ],
        "search_nouns": ["network security solution", "firewall", "cybersecurity platform"],
        "specific_products": [
            "Palo Alto PA-Series", "Fortinet FortiGate",
            "Cisco Secure Firewall", "Cisco Meraki MX",
            "CrowdStrike Falcon", "SentinelOne",
            "Zscaler ZIA", "Cloudflare One",
            "SonicWall TZ", "Sophos XGS",
        ],
        "specs": [
            "next-gen firewall", "NGFW", "IPS/IDS", "SSL inspection",
            "SD-WAN integrated", "zero trust architecture",
            "SASE", "XDR", "EDR", "SOAR",
            "cloud-managed", "on-premise", "hybrid",
            "threat intelligence", "sandboxing",
        ],
        "price_tiers": {
            "budget": ["for small business", "startup budget", "affordable"],
            "mid": ["mid-market", "SMB pricing", "reasonable TCO"],
            "high": ["enterprise", "mid-enterprise"],
            "premium": ["large enterprise", "Fortune 500", "government grade"],
        },
        "use_cases": [
            "small business security", "office network protection",
            "remote workforce security", "branch office",
            "cloud migration", "multi-cloud security",
            "compliance", "HIPAA compliance", "PCI DSS",
            "zero trust implementation", "ransomware protection",
            "secure remote access",
        ],
        "buyer_personas": [
            "IT manager", "CISO", "network administrator",
            "small business owner", "CTO", "security engineer",
            "MSP", "IT director",
        ],
        "qualities_people_want": [
            "most secure", "easiest to manage",
            "best support", "most scalable",
            "best integration", "lowest false positives",
            "best threat detection",
        ],
        "real_concerns": [
            "total cost", "management complexity",
            "false positives", "performance impact",
            "vendor lock-in", "support response time",
            "integration with existing tools",
        ],
        "comparison_angles": [
            "threat detection comparison", "TCO comparison",
            "management ease comparison", "which is more scalable",
        ],
    },

    "video conferencing": {
        "aliases": [
            "video conferencing", "video calling", "video calls",
            "virtual meetings", "online meetings", "zoom alternative",
            "video meeting software",
        ],
        "search_nouns": ["video conferencing platform", "video calling app", "virtual meeting tool"],
        "specific_products": [
            "Zoom", "Microsoft Teams", "Google Meet",
            "Cisco Webex", "GoTo Meeting",
            "RingCentral", "Slack Huddles",
            "Discord", "FaceTime",
        ],
        "specs": [
            "HD video", "4K video", "screen sharing",
            "recording", "cloud recording", "local recording",
            "breakout rooms", "virtual background", "AI noise suppression",
            "live captions", "real-time translation",
            "end-to-end encryption", "whiteboard",
            "up to 100 participants", "up to 1000 participants",
        ],
        "price_tiers": {
            "budget": ["free", "free tier", "no cost"],
            "mid": ["under $15/user/month", "under $20/user/month"],
            "high": ["under $30/user/month", "enterprise pricing"],
            "premium": ["custom pricing", "enterprise agreement"],
        },
        "use_cases": [
            "team meetings", "daily standup", "client calls",
            "sales demos", "webinars", "town halls",
            "remote interviews", "online classes",
            "telehealth", "therapy sessions",
            "hybrid meetings", "one-on-ones",
            "international calls",
        ],
        "buyer_personas": [
            "startup", "small business", "enterprise IT",
            "teacher", "remote team lead", "sales team",
            "freelancer", "healthcare provider", "HR manager",
        ],
        "qualities_people_want": [
            "most reliable", "best video quality",
            "easiest to use", "best free tier",
            "best for large meetings", "best recording features",
            "best integration with calendar",
        ],
        "real_concerns": [
            "reliability", "video quality", "audio quality",
            "bandwidth usage", "security", "privacy",
            "recording storage limits", "meeting time limits",
            "calendar integration", "ease of joining",
        ],
        "comparison_angles": [
            "video quality comparison", "reliability comparison",
            "free tier comparison", "security comparison",
            "which is easiest to use",
        ],
    },

    "football streaming": {
        "aliases": [
            "football streaming", "nfl streaming", "watch football",
            "watch nfl", "live football", "sunday football",
            "sports streaming", "live sports",
        ],
        "search_nouns": ["football streaming", "NFL games", "football"],
        "specific_products": [
            "NFL+", "NFL Sunday Ticket on YouTube TV",
            "NFL RedZone", "NFL Network",
            "YouTube TV", "Hulu + Live TV", "FuboTV",
            "Peacock", "Amazon Prime Thursday Night Football",
            "ESPN+ Monday Night Football", "Paramount+ CBS games",
            "Sling TV", "DirecTV Stream",
        ],
        "specs": [
            "4K streaming", "multi-view", "DVR",
            "unlimited DVR", "simultaneous streams",
            "local channels included", "out-of-market games",
            "no contract", "free trial",
        ],
        "price_tiers": {
            "budget": ["free", "cheapest option", "under $10/month"],
            "mid": ["under $40/month", "under $50/month", "around $40/month"],
            "high": ["under $75/month", "under $100/month"],
            "premium": ["under $100/season", "all-inclusive", "every game"],
        },
        "use_cases": [
            "watching every game", "watching my team out of market",
            "Sunday RedZone all day", "cord cutting",
            "watching on phone at work", "tailgate party",
            "watching with friends", "catching highlights",
            "recording games to watch later", "Monday Night Football",
            "Thursday Night Football", "Sunday Night Football",
        ],
        "buyer_personas": [
            "cord cutter", "die-hard fan", "casual fan",
            "fantasy football player", "sports bettor",
            "family", "college student", "expat",
            "someone who just cancelled cable",
        ],
        "qualities_people_want": [
            "cheapest way to watch everything", "no blackouts",
            "best streaming quality", "most games included",
            "best mobile app", "most reliable stream",
            "best multi-game viewing",
        ],
        "real_concerns": [
            "blackout rules", "which games are on which service",
            "streaming delay vs cable", "buffering",
            "device compatibility", "contract cancellation",
            "how many services do I need",
        ],
        "comparison_angles": [
            "which service has most games", "price comparison",
            "streaming quality comparison", "which has RedZone",
        ],
    },

    "fantasy football": {
        "aliases": [
            "fantasy football", "fantasy", "ff", "fantasy draft",
            "fantasy league", "fantasy sports",
        ],
        "search_nouns": ["fantasy football platform", "fantasy football app", "fantasy football"],
        "specific_products": [
            "ESPN Fantasy Football", "Yahoo Fantasy Football",
            "NFL Fantasy", "Sleeper", "CBS Fantasy",
            "Underdog Fantasy", "DraftKings", "FanDuel",
        ],
        "specs": [
            "PPR", "half PPR", "standard scoring",
            "dynasty", "keeper league", "redraft",
            "auction draft", "snake draft", "best ball",
            "superflex", "IDP", "daily fantasy",
        ],
        "price_tiers": {
            "budget": ["free", "no cost", "free leagues"],
            "mid": ["under $20 buy-in", "under $50 buy-in"],
            "high": ["under $100 buy-in", "$50 to $100 buy-in"],
            "premium": ["high stakes", "$200+ buy-in", "competitive"],
        },
        "use_cases": [
            "playing with friends", "work league",
            "family league", "competitive league",
            "first time playing", "daily fantasy",
            "dynasty league startup", "mock drafts",
        ],
        "buyer_personas": [
            "beginner", "first timer", "experienced player",
            "casual player", "competitive player",
            "league commissioner",
        ],
        "qualities_people_want": [
            "best app", "most accurate projections",
            "best draft experience", "most customizable",
            "best trade tools", "best waiver system",
            "best for beginners", "best for competitive leagues",
        ],
        "real_concerns": [
            "app crashes on draft day", "projection accuracy",
            "trade reviewing", "waiver priority system",
            "scoring bugs", "commissioner tools",
            "keeper league support",
        ],
        "comparison_angles": [
            "app comparison", "which has best draft",
            "which is easiest for beginners",
            "customization comparison",
        ],
    },

    "jerseys": {
        "aliases": [
            "jersey", "jerseys", "football jersey", "nfl jersey",
            "sports jersey", "team jersey", "game jersey",
        ],
        "search_nouns": ["jersey", "NFL jersey", "football jersey"],
        "specific_products": [
            "Nike Vapor Limited jersey", "Nike Game jersey",
            "Nike Elite jersey", "Nike Legend jersey",
            "Mitchell & Ness throwback", "Fanatics Breakaway",
        ],
        "specs": [
            "authentic", "game jersey", "limited jersey", "elite",
            "stitched numbers", "screen printed",
            "vapor untouchable", "youth", "women's", "custom name",
        ],
        "price_tiers": {
            "budget": ["under $40", "under $50", "cheap", "knockoff quality"],
            "mid": ["under $100", "under $120", "around $100"],
            "high": ["under $150", "under $200", "authentic"],
            "premium": ["under $350", "game-worn", "autographed"],
        },
        "use_cases": [
            "game day", "going to the game", "tailgating",
            "gift for a fan", "birthday gift", "Christmas gift",
            "collection", "everyday wear", "costume",
        ],
        "buyer_personas": [
            "die-hard fan", "casual fan", "gift shopper",
            "parent buying for kid", "collector",
            "someone going to their first game",
        ],
        "qualities_people_want": [
            "most authentic looking", "best quality stitching",
            "best value", "most comfortable", "best for gifting",
            "closest to what players wear",
        ],
        "real_concerns": [
            "authenticity", "sizing runs small or large",
            "stitched vs screen printed", "return policy",
            "player might get traded", "wash durability",
        ],
        "comparison_angles": [
            "game vs limited vs elite", "Nike vs Fanatics",
            "which tier is worth it", "authentic vs replica",
        ],
    },
}


# ───────────────────────────────────────────
# SENTENCE BUILDERS
# ───────────────────────────────────────────
# Instead of templates, we use COMPOSITIONAL sentence building.
# Each function generates one unique query by combining fragments.

class QueryBuilder:
    """
    Builds realistic, diverse search queries by composing sentence fragments.
    Uses a company profile and product knowledge to generate contextually
    appropriate queries that sound like real human searches.
    """

    def __init__(
        self,
        profile: dict,
        product_info: dict,
        product_key: str,
        rng: random.Random,
        year: str,
    ):
        self.profile = profile
        self.p = product_info  # product knowledge
        self.product_key = product_key
        self.rng = rng
        self.year = year
        self.company = profile["display_name"]
        self.role = profile["role"]

    # ── Randomized fragment getters ──

    def noun(self) -> str:
        """Get a search noun for this product."""
        return self.rng.choice(self.p["search_nouns"])

    def spec(self) -> str:
        return self.rng.choice(self.p["specs"]) if self.p.get("specs") else ""

    def price(self, tier: str = None) -> str:
        if tier and tier in self.p.get("price_tiers", {}):
            return self.rng.choice(self.p["price_tiers"][tier])
        all_prices = []
        for prices in self.p.get("price_tiers", {}).values():
            all_prices.extend(prices)
        return self.rng.choice(all_prices) if all_prices else ""

    def use_case(self) -> str:
        return self.rng.choice(self.p["use_cases"])

    def buyer(self) -> str:
        return self.rng.choice(self.p["buyer_personas"])

    def quality(self) -> str:
        return self.rng.choice(self.p["qualities_people_want"])

    def concern(self) -> str:
        return self.rng.choice(self.p["real_concerns"])

    def competitor(self) -> str:
        return self.rng.choice(self.profile["competitors"])

    def owned_brand(self) -> str:
        return self.rng.choice(self.profile["owned_brands"]) if self.profile["owned_brands"] else self.company

    def specific_product(self) -> str:
        return self.rng.choice(self.p["specific_products"]) if self.p.get("specific_products") else self.noun()

    def year_maybe(self) -> str:
        """50% chance to append the year."""
        return f" {self.year}" if self.rng.random() < 0.5 else ""

    def comparison_angle(self) -> str:
        return self.rng.choice(self.p.get("comparison_angles", ["which is better"]))

    # ── BRANDED query generators (by company role) ──

    def branded_manufacturer(self) -> list[str]:
        """When company MAKES the product (Dell, Cisco)."""
        ob = self.owned_brand()
        comp = self.competitor()
        uc = self.use_case()
        pr = self.price()
        sp = self.spec()
        yr = self.year_maybe()
        n = self.noun()
        b = self.buyer()
        q = self.quality()
        c = self.concern()

        return [
            f"best {self.company} {n} for {uc}{yr}",
            f"{self.company} {ob} review{yr}",
            f"is {self.company} {ob} worth buying",
            f"{self.company} {ob} vs {comp}{yr}",
            f"should I buy {self.company} {ob} or {comp}",
            f"{self.company} {ob} for {uc}",
            f"best {self.company} {n} for {b}{yr}",
            f"best {self.company} {n} {pr}",
            f"{self.company} {ob} {c}",
            f"new {self.company} {n} {self.year}",
            f"{self.company} vs {comp} for {uc}",
            f"{self.company} {ob} pros and cons",
            f"is {self.company} {ob} good for {uc}",
            f"which {self.company} {n} should I get",
            f"{self.company} {ob} long term review",
            f"{self.company} {ob} after 6 months",
            f"{self.company} {ob} real user experience",
            f"why I chose {self.company} {ob} over {comp}",
            f"{self.company} {ob} vs {comp} for {b}",
            f"{self.company} {n} deals{yr}",
            f"is {self.company} still good in {self.year}",
            f"{self.company} {ob} {sp} review",
            f"best {self.company} {n} right now",
            f"{self.company} {ob} compared to {comp}",
            f"{self.company} {ob} for {b} {pr}",
            f"cheapest {self.company} {n} that's actually good",
            f"{self.company} {ob} performance for {uc}",
            f"upgrading to {self.company} {ob} from {comp}",
            f"{self.company} {ob} honest opinion",
            f"what I wish I knew before buying {self.company} {ob}",
        ]

    def branded_marketplace(self) -> list[str]:
        """When company SELLS the product (eBay)."""
        comp = self.competitor()
        uc = self.use_case()
        pr = self.price()
        sp = self.spec()
        yr = self.year_maybe()
        n = self.noun()
        b = self.buyer()
        q = self.quality()
        c = self.concern()
        specific = self.specific_product()

        return [
            f"buy {n} on {self.company}",
            f"is it safe to buy {n} on {self.company}",
            f"best {n} deals on {self.company}{yr}",
            f"buying used {n} on {self.company}",
            f"{self.company} vs {comp} for buying {n}",
            f"refurbished {n} on {self.company} worth it",
            f"cheap {n} on {self.company} {pr}",
            f"best place to buy {n} online {self.company} or {comp}",
            f"should I buy {n} from {self.company} or {comp}",
            f"{n} deals on {self.company} right now",
            f"how to find good {n} deals on {self.company}",
            f"buying {specific} on {self.company} vs {comp}",
            f"is {self.company} good for buying {n}",
            f"{self.company} refurbished {n} review",
            f"{self.company} vs {comp} {n} prices",
            f"can you trust {self.company} for expensive {n}",
            f"{self.company} {n} buyer protection how does it work",
            f"found a {n} on {self.company} is it legit",
            f"tips for buying {n} on {self.company}",
            f"{n} {pr} on {self.company}",
            f"best sellers for {n} on {self.company}",
            f"{self.company} vs {comp} which is cheaper for {n}",
            f"buying {n} on {self.company} for {uc}",
            f"used {n} {pr} {self.company} or {comp}",
            f"{self.company} {n} return policy",
            f"is {self.company} or {comp} better for used {n}",
            f"how to spot fake {n} on {self.company}",
            f"best time to buy {n} on {self.company}",
            f"{self.company} certified refurbished {n} vs new",
        ]

    def branded_financial(self) -> list[str]:
        """When company provides financial products (Capital One)."""
        ob = self.owned_brand()
        comp = self.competitor()
        uc = self.use_case()
        pr = self.price()
        sp = self.spec()
        yr = self.year_maybe()
        n = self.noun()
        b = self.buyer()
        q = self.quality()
        c = self.concern()

        return [
            f"best {self.company} {n} for {uc}{yr}",
            f"{self.company} {ob} review{yr}",
            f"{self.company} {ob} worth it",
            f"{self.company} {ob} vs {comp}",
            f"should I get {self.company} {ob} or {comp}",
            f"{self.company} {ob} benefits{yr}",
            f"{self.company} best {n} for {b}",
            f"{self.company} {ob} {sp}",
            f"is {self.company} {ob} good for {uc}",
            f"{self.company} {ob} pros and cons{yr}",
            f"{self.company} {ob} approval odds",
            f"which {self.company} {n} is best for {b}",
            f"{self.company} {ob} vs {comp} for {uc}",
            f"switching to {self.company} from {comp}",
            f"{self.company} {ob} for {b}{yr}",
            f"{self.company} {ob} real review from actual user",
            f"how I use my {self.company} {ob} for {uc}",
            f"{self.company} {ob} {c}",
            f"applying for {self.company} {ob} what to expect",
            f"{self.company} {ob} after 1 year honest review",
            f"best {self.company} {n} with {sp}",
            f"is {self.company} or {comp} better for {b}",
            f"{self.company} {ob} sign up bonus{yr}",
            f"maximizing {self.company} {ob} rewards",
        ]

    def branded_retailer(self) -> list[str]:
        """When company is a retailer (Home Depot, HEB)."""
        comp = self.competitor()
        uc = self.use_case()
        pr = self.price()
        yr = self.year_maybe()
        n = self.noun()
        b = self.buyer()
        q = self.quality()
        c = self.concern()
        ob = self.owned_brand()

        return [
            f"buy {n} at {self.company}",
            f"{self.company} vs {comp} for {n}",
            f"is {self.company} cheaper than {comp} for {n}",
            f"{self.company} {n} sale{yr}",
            f"best {n} at {self.company}",
            f"{self.company} {n} prices vs {comp}",
            f"shopping for {n} at {self.company}",
            f"{self.company} {n} deals this week",
            f"does {self.company} have good {n}",
            f"{self.company} {ob} {n} quality",
            f"is {self.company} or {comp} better for {uc}",
            f"{self.company} {n} for {uc}",
            f"best time to buy {n} at {self.company}",
            f"{self.company} {n} reviews{yr}",
            f"{self.company} vs {comp} for {b}",
            f"{self.company} store brand {n} vs name brand",
            f"why I shop at {self.company} for {n}",
            f"{self.company} {n} curbside pickup",
            f"{self.company} {n} delivery vs {comp}",
            f"{self.company} weekly {n} deals{yr}",
            f"saving money on {n} at {self.company}",
        ]

    def branded_service(self) -> list[str]:
        """When company is a service provider (NFL)."""
        ob = self.owned_brand()
        comp = self.competitor()
        uc = self.use_case()
        pr = self.price()
        sp = self.spec()
        yr = self.year_maybe()
        n = self.noun()
        b = self.buyer()

        return [
            f"best way to watch {self.company}{yr}",
            f"{self.company} {ob} review{yr}",
            f"is {self.company} {ob} worth it{yr}",
            f"{self.company} {ob} vs {comp}",
            f"cheapest way to get {self.company} {ob}",
            f"how to stream {self.company} games{yr}",
            f"{self.company} {ob} price{yr}",
            f"{self.company} vs {comp} for {uc}",
            f"do I need {self.company} {ob} or {comp}",
            f"{self.company} {ob} on which devices",
            f"{self.company} {ob} vs {comp} for {b}",
            f"cancel {self.company} {ob} or keep it",
            f"{self.company} {ob} features{yr}",
            f"how much is {self.company} {ob}{yr}",
            f"{self.company} {ob} for {uc}{yr}",
            f"what comes with {self.company} {ob}",
            f"{self.company} {ob} honest review after full season",
            f"is {self.company} {ob} better than {comp}",
            f"best {self.company} package for {b}",
            f"watching {self.company} without cable{yr}",
        ]

    def get_branded(self) -> str:
        """Get one branded query based on company role."""
        generators = {
            "manufacturer": self.branded_manufacturer,
            "marketplace": self.branded_marketplace,
            "financial_provider": self.branded_financial,
            "retailer": self.branded_retailer,
            "service_provider": self.branded_service,
        }
        gen = generators.get(self.role, self.branded_manufacturer)
        options = gen()
        return self.rng.choice(options)

    # ── UNBRANDED query generators ──

    def unbranded(self) -> str:
        """Generate one unbranded query — no company name."""
        n = self.noun()
        uc = self.use_case()
        b = self.buyer()
        pr = self.price()
        sp = self.spec()
        q = self.quality()
        c = self.concern()
        yr = self.year_maybe()
        specific = self.specific_product()
        comp_angle = self.comparison_angle()

        # Large pool of natural unbranded patterns
        options = [
            # Simple product searches
            f"best {n}{yr}",
            f"best {n} for {uc}",
            f"best {n} for {uc}{yr}",
            f"best {n} {pr}",
            f"best {n} for {b}",
            f"best {n} for {b}{yr}",
            f"top {n}{yr}",

            # With qualifiers
            f"{q} {n}{yr}",
            f"{q} {n} for {b}",
            f"most {c.split()[0] if c else 'reliable'} {n}{yr}",

            # Question format
            f"what {n} should I buy for {uc}",
            f"what is the best {n} for {uc}{yr}",
            f"which {n} is best for {b}",
            f"what {n} do {b} use",
            f"what's the best {n} right now",

            # Price-focused
            f"best {n} {pr}{yr}",
            f"good {n} {pr}",
            f"best {n} for {uc} {pr}",
            f"best budget {n} for {uc}",
            f"{n} {pr} actually worth buying",
            f"best cheap {n} that doesn't suck",

            # Spec-focused
            f"best {n} with {sp}{yr}",
            f"{n} with {sp} {pr}",
            f"{n} with best {c}{yr}",

            # Concern-focused
            f"best {n} for {c}",
            f"{n} {c} comparison{yr}",
            f"{n} with best {c} for {uc}",

            # Help / advice format
            f"help me choose a {n} for {uc}",
            f"I need a {n} for {uc} {pr}",
            f"looking for a {n} for {uc}",
            f"recommend a {n} for {b}",
            f"what {n} do you recommend for {uc}",

            # Buying guide
            f"{n} buying guide{yr}",
            f"how to choose a {n} for {uc}",
            f"what to look for in a {n}",
            f"things to consider before buying a {n}",
            f"{b} guide to buying a {n}{yr}",

            # Comparison
            f"{specific} vs {self.specific_product()}{yr}",
            f"best {n} {comp_angle}{yr}",

            # Trending / current
            f"best {n} to buy right now",
            f"most popular {n}{yr}",
            f"what {n} is everyone buying{yr}",
            f"top rated {n}{yr}",
            f"best new {n}{yr}",
            f"best {n} of {self.year}",

            # Reddit-style
            f"best {n} for {uc} reddit",
            f"honest {n} recommendations",
            f"{n} recommendations {pr}",

            # Review-seeking
            f"best {n} reviews{yr}",
            f"most reliable {n}{yr}",
            f"best overall {n}{yr}",
            f"best {n} for the money",
            f"best value {n}{yr}",

            # Casual / conversational
            f"good {n} for {uc}",
            f"decent {n} {pr}",
            f"solid {n} for {uc} {pr}",
            f"need a {n} for {uc} any suggestions",
        ]

        chosen = self.rng.choice(options)

        # Make sure company name doesn't appear
        if self.company.lower() in chosen.lower():
            return self.unbranded()  # retry

        return chosen


# ───────────────────────────────────────────
# PRODUCT ALIAS RESOLVER
# ───────────────────────────────────────────

def _resolve_product(user_input: str) -> Optional[str]:
    """
    Resolve user's product input to a known product key.
    Handles variations like "mobile" → "phone", "laptops" → "laptop",
    "wifi router" → "router", etc.
    """
    normalized = user_input.strip().lower()

    # Direct match
    if normalized in PRODUCT_KNOWLEDGE:
        return normalized

    # Check all aliases
    for product_key, info in PRODUCT_KNOWLEDGE.items():
        for alias in info.get("aliases", []):
            if normalized == alias.lower():
                return product_key
            # Substring match for close hits
            if normalized in alias.lower() or alias.lower() in normalized:
                return product_key

    # Fuzzy: check if input words overlap with aliases
    input_words = set(normalized.split())
    best_match = None
    best_score = 0

    for product_key, info in PRODUCT_KNOWLEDGE.items():
        all_terms = info.get("aliases", []) + [product_key]
        for term in all_terms:
            term_words = set(term.lower().split())
            overlap = len(input_words & term_words)
            total = max(len(input_words | term_words), 1)
            score = overlap / total
            if score > best_score:
                best_score = score
                best_match = product_key

    return best_match if best_score > 0.25 else None


# ───────────────────────────────────────────
# MAIN FUNCTION
# ───────────────────────────────────────────

def generate_queries(
    company_name: str,
    product: str,
    num_queries: int = 50,
    branded_ratio: float = 0.70,
    seed: Optional[int] = None,
) -> list[GeneratedQuery]:
    """
    Generate realistic consumer search queries for brand visibility monitoring.

    Every query sounds like something a real person would type into
    ChatGPT, Perplexity, or Google while genuinely shopping.

    The function understands each company's ROLE:
      - Dell MAKES laptops → "best Dell XPS for programming"
      - eBay SELLS laptops → "refurbished laptop on eBay worth it"
      - Capital One provides FINANCIAL products → "Capital One Venture X review"
      - HEB is a RETAILER → "HEB vs Kroger for groceries"
      - NFL provides SERVICES → "cheapest way to watch NFL games"

    Args:
        company_name: Company to track (case-insensitive).
        product: What the consumer is shopping for. Accepts natural input:
                 "mobile", "laptop", "phone", "credit card", "groceries",
                 "router", "tv", "headphones", "power tools", etc.
        num_queries: How many queries to generate.
        branded_ratio: Fraction mentioning the company (0.70 = 70%).
        seed: Random seed for reproducibility.

    Returns:
        List of GeneratedQuery objects, shuffled.

    Examples:
        generate_queries("ebay", "mobile", 30)
        generate_queries("dell", "laptop", 50)
        generate_queries("capital one", "credit card", 40)
        generate_queries("nfl", "football streaming", 30)
        generate_queries("heb", "groceries", 25)
        generate_queries("home depot", "power tools", 30)
        generate_queries("cisco", "network security", 30)
    """

    # ── Validate company ──
    company_key = company_name.strip().lower()
    if company_key not in COMPANY_PROFILES:
        available = ", ".join(sorted(COMPANY_PROFILES.keys()))
        raise ValueError(f"Unknown company '{company_name}'. Available: {available}")
    profile = COMPANY_PROFILES[company_key]

    # ── Resolve product ──
    product_key = _resolve_product(product)
    if product_key is None:
        available = ", ".join(sorted(PRODUCT_KNOWLEDGE.keys()))
        raise ValueError(
            f"Could not match product '{product}' to any known category. "
            f"Available: {available}"
        )
    product_info = PRODUCT_KNOWLEDGE[product_key]

    # ── Setup ──
    rng = random.Random(seed if seed is not None else time.time_ns())
    year = time.strftime("%Y")
    num_branded = round(num_queries * branded_ratio)
    num_unbranded = num_queries - num_branded

    builder = QueryBuilder(profile, product_info, product_key, rng, year)

    # ── Generate ──
    results = []
    seen = set()

    def _add_query(text: str, is_branded: bool, qtype: str):
        text = " ".join(text.split()).strip()
        norm = text.lower()
        if norm in seen or len(text) < 8:
            return False
        seen.add(norm)
        results.append(GeneratedQuery(
            text=text,
            is_branded=is_branded,
            query_type=qtype,
            company=profile["display_name"],
            product=product_key,
        ))
        return True

    # Generate branded queries
    attempts = 0
    branded_count = 0
    while branded_count < num_branded and attempts < num_branded * 25:
        attempts += 1
        text = builder.get_branded()
        if _add_query(text, True, f"branded_{profile['role']}"):
            branded_count += 1

    # Generate unbranded queries
    attempts = 0
    unbranded_count = 0
    while unbranded_count < num_unbranded and attempts < num_unbranded * 25:
        attempts += 1
        text = builder.unbranded()
        # Double-check no brand leak
        if profile["display_name"].lower() in text.lower():
            continue
        if _add_query(text, False, "unbranded"):
            unbranded_count += 1

    # Shuffle so branded and unbranded are interleaved
    rng.shuffle(results)

    return results[:num_queries]


# ───────────────────────────────────────────
# CONVENIENCE
# ───────────────────────────────────────────

def get_supported_companies() -> list[dict]:
    return [
        {
            "key": k,
            "display_name": v["display_name"],
            "role": v["role"],
            "relevant_products": [
                pk for pk, pi in PRODUCT_KNOWLEDGE.items()
            ],
        }
        for k, v in COMPANY_PROFILES.items()
    ]


def get_supported_products() -> list[dict]:
    return [
        {
            "key": k,
            "aliases": v.get("aliases", []),
            "category": v.get("search_nouns", [k])[0],
        }
        for k, v in PRODUCT_KNOWLEDGE.items()
    ]


def print_queries(queries: list[GeneratedQuery]) -> None:
    branded = sum(1 for q in queries if q.is_branded)
    total = len(queries)
    print(f"\n{'═'*65}")
    print(f"  {total} queries | {queries[0].company} + {queries[0].product}")
    print(f"  ★ Branded: {branded} ({branded/total*100:.0f}%)  ○ Unbranded: {total-branded} ({(total-branded)/total*100:.0f}%)")
    print(f"{'═'*65}")
    for i, q in enumerate(queries, 1):
        icon = "★" if q.is_branded else "○"
        print(f"  #{i:<3} {icon}  {q.text}")
    print()