"""Required coverage manifest and request normalization.

The manifest is a research queue, not a claim that any credential exists.
"""

from __future__ import annotations

import re

JURISDICTIONS: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
    "PR": "Puerto Rico",
    "GU": "Guam",
    "VI": "U.S. Virgin Islands",
    "AS": "American Samoa",
    "MP": "Northern Mariana Islands",
}

REQUIRED_TRADES = (
    "electrical",
    "plumbing",
    "hvac",
    "refrigeration",
    "hydronics",
    "mechanical",
    "general_contracting",
)

# These are search aliases, not a nationwide credential inventory.
TRADE_ALIASES = {
    "electrician": "electrical",
    "electric": "electrical",
    "plumber": "plumbing",
    "heating ventilation air conditioning": "hvac",
    "general contracting": "general_contracting",
    "trade contracting": "general_contracting",
    "contractor": "general_contracting",
    "general/trade contracting": "general_contracting",
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


_NAMES = {_key(name): code for code, name in JURISDICTIONS.items()}
_NAMES.update({"washington dc": "DC", "virgin islands": "VI", "cnmi": "MP"})


def normalize_jurisdiction(value: str) -> tuple[str, str]:
    code = value.strip().upper()
    if code not in JURISDICTIONS:
        code = _NAMES.get(_key(value), "")
    if not code:
        raise ValueError(f"Unknown US jurisdiction: {value!r}")
    return code, JURISDICTIONS[code]


def normalize_trade(value: str) -> str:
    key = _key(value)
    trade = TRADE_ALIASES.get(key, key.replace(" ", "_"))
    if trade not in REQUIRED_TRADES:
        raise ValueError(f"Unknown required trade: {value!r}")
    return trade
