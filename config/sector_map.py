"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Canonical Sector Taxonomy                               ║
║                                                                              ║
║  ALL sector labels across the app must pass through normalize_sector().      ║
║  This is the single source of truth for sector classification.               ║
║                                                                              ║
║  Usage:                                                                      ║
║      from config.sector_map import normalize_sector, CANONICAL_SECTORS       ║
║      clean = normalize_sector(yf_info.get("sector"))                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

# ── 15 canonical India-market sector labels ────────────────────────────────────
CANONICAL_SECTORS: list[str] = [
    "IT & Technology",
    "Banking & Finance",
    "Pharma & Healthcare",
    "FMCG & Consumer",
    "Auto & Auto Ancillaries",
    "Capital Goods & Engineering",
    "Metals & Mining",
    "Oil, Gas & Energy",
    "Real Estate",
    "Chemicals & Specialty",
    "Infrastructure",
    "Telecom & Media",
    "Textiles & Apparel",
    "Agri & Food Processing",
    "Others",
]

# ── Alias map: raw Yahoo Finance / screener.in strings → canonical ─────────────
_SECTOR_ALIAS_MAP: dict[str, str] = {
    # ── IT & Technology ──────────────────────────────────────────────────────
    "technology":               "IT & Technology",
    "information technology":   "IT & Technology",
    "it":                       "IT & Technology",
    "software":                 "IT & Technology",
    "tech":                     "IT & Technology",
    "it services":              "IT & Technology",
    "computer software":        "IT & Technology",
    "electronic components":    "IT & Technology",
    "semiconductor":            "IT & Technology",

    # ── Banking & Finance ────────────────────────────────────────────────────
    "financial services":       "Banking & Finance",
    "banking":                  "Banking & Finance",
    "finance":                  "Banking & Finance",
    "bank":                     "Banking & Finance",
    "nbfc":                     "Banking & Finance",
    "insurance":                "Banking & Finance",
    "asset management":         "Banking & Finance",
    "diversified financials":   "Banking & Finance",
    "capital markets":          "Banking & Finance",
    "mortgage finance":         "Banking & Finance",

    # ── Pharma & Healthcare ──────────────────────────────────────────────────
    "healthcare":               "Pharma & Healthcare",
    "pharmaceuticals":          "Pharma & Healthcare",
    "pharma":                   "Pharma & Healthcare",
    "health care":              "Pharma & Healthcare",
    "biotechnology":            "Pharma & Healthcare",
    "hospitals":                "Pharma & Healthcare",
    "medical devices":          "Pharma & Healthcare",
    "diagnostics":              "Pharma & Healthcare",
    "drug manufacturers":       "Pharma & Healthcare",

    # ── FMCG & Consumer ──────────────────────────────────────────────────────
    "consumer defensive":       "FMCG & Consumer",
    "consumer staples":         "FMCG & Consumer",
    "fmcg":                     "FMCG & Consumer",
    "consumer goods":           "FMCG & Consumer",
    "food & beverage":          "FMCG & Consumer",
    "personal products":        "FMCG & Consumer",
    "household products":       "FMCG & Consumer",
    "beverages":                "FMCG & Consumer",
    "tobacco":                  "FMCG & Consumer",
    "food products":            "FMCG & Consumer",

    # ── Auto & Auto Ancillaries ───────────────────────────────────────────────
    "automobiles":              "Auto & Auto Ancillaries",
    "auto":                     "Auto & Auto Ancillaries",
    "automobile":               "Auto & Auto Ancillaries",
    "auto components":          "Auto & Auto Ancillaries",
    "auto ancillaries":         "Auto & Auto Ancillaries",
    "consumer cyclical":        "Auto & Auto Ancillaries",
    "auto manufacturers":       "Auto & Auto Ancillaries",
    "auto parts":               "Auto & Auto Ancillaries",
    "farm & heavy construction machinery": "Auto & Auto Ancillaries",

    # ── Capital Goods & Engineering ───────────────────────────────────────────
    "capital goods":            "Capital Goods & Engineering",
    "industrials":              "Capital Goods & Engineering",
    "engineering":              "Capital Goods & Engineering",
    "industrial machinery":     "Capital Goods & Engineering",
    "electrical equipment":     "Capital Goods & Engineering",
    "defense":                  "Capital Goods & Engineering",
    "aerospace & defense":      "Capital Goods & Engineering",
    "specialty industrial machinery": "Capital Goods & Engineering",
    "tools & accessories":      "Capital Goods & Engineering",
    "conglomerates":            "Capital Goods & Engineering",

    # ── Metals & Mining ───────────────────────────────────────────────────────
    "basic materials":          "Metals & Mining",
    "metals":                   "Metals & Mining",
    "mining":                   "Metals & Mining",
    "steel":                    "Metals & Mining",
    "aluminium":                "Metals & Mining",
    "non-ferrous metals":       "Metals & Mining",
    "copper":                   "Metals & Mining",
    "other metals/minerals":    "Metals & Mining",
    "iron & steel":             "Metals & Mining",

    # ── Oil, Gas & Energy ─────────────────────────────────────────────────────
    "energy":                   "Oil, Gas & Energy",
    "oil & gas":                "Oil, Gas & Energy",
    "utilities":                "Oil, Gas & Energy",
    "power":                    "Oil, Gas & Energy",
    "renewable energy":         "Oil, Gas & Energy",
    "oil & gas e&p":            "Oil, Gas & Energy",
    "oil & gas integrated":     "Oil, Gas & Energy",
    "oil & gas refining":       "Oil, Gas & Energy",
    "independent power producers": "Oil, Gas & Energy",

    # ── Real Estate ───────────────────────────────────────────────────────────
    "real estate":              "Real Estate",
    "realty":                   "Real Estate",
    "construction":             "Real Estate",
    "real estate services":     "Real Estate",
    "reit":                     "Real Estate",

    # ── Chemicals & Specialty ─────────────────────────────────────────────────
    "chemicals":                "Chemicals & Specialty",
    "specialty chemicals":      "Chemicals & Specialty",
    "fertilizers":              "Chemicals & Specialty",
    "pesticides":               "Chemicals & Specialty",
    "paints":                   "Chemicals & Specialty",
    "agrochemicals":            "Chemicals & Specialty",
    "coatings & adhesives":     "Chemicals & Specialty",

    # ── Infrastructure ────────────────────────────────────────────────────────
    "infrastructure":           "Infrastructure",
    "cement":                   "Infrastructure",
    "logistics":                "Infrastructure",
    "transportation":           "Infrastructure",
    "shipping":                 "Infrastructure",
    "ports":                    "Infrastructure",
    "building materials":       "Infrastructure",
    "roads & highways":         "Infrastructure",

    # ── Telecom & Media ───────────────────────────────────────────────────────
    "communication services":   "Telecom & Media",
    "telecom":                  "Telecom & Media",
    "media":                    "Telecom & Media",
    "entertainment":            "Telecom & Media",
    "broadcasting":             "Telecom & Media",
    "telecommunications":       "Telecom & Media",
    "internet content & information": "Telecom & Media",

    # ── Textiles & Apparel ────────────────────────────────────────────────────
    "textiles":                 "Textiles & Apparel",
    "garments":                 "Textiles & Apparel",
    "apparel":                  "Textiles & Apparel",
    "textile manufacturing":    "Textiles & Apparel",
    "footwear & accessories":   "Textiles & Apparel",
    "luxury goods":             "Textiles & Apparel",

    # ── Agri & Food Processing ────────────────────────────────────────────────
    "agriculture":              "Agri & Food Processing",
    "food processing":          "Agri & Food Processing",
    "agri":                     "Agri & Food Processing",
    "packaged foods":           "Agri & Food Processing",
    "confectioners":            "Agri & Food Processing",
    "farm products":            "Agri & Food Processing",
}


def normalize_sector(raw_sector: str | None) -> str:
    """
    Convert any raw sector string → canonical India-market sector label.

    Always returns a string from CANONICAL_SECTORS. Never raises.

    Args:
        raw_sector: Raw sector string from Yahoo Finance, screener.in, or any source.
                    May be None, empty, or use US-style labels like "Consumer Defensive".

    Returns:
        One of the 15 strings in CANONICAL_SECTORS.

    Examples:
        normalize_sector("Industrials")         → "Capital Goods & Engineering"
        normalize_sector("Consumer Defensive")  → "FMCG & Consumer"
        normalize_sector("Financial Services")  → "Banking & Finance"
        normalize_sector(None)                  → "Others"
        normalize_sector("Gibberish")           → "Others"
    """
    if not raw_sector:
        return "Others"
    key = raw_sector.strip().lower()
    return _SECTOR_ALIAS_MAP.get(key, "Others")
