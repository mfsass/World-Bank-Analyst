# SKILL: World Bank Data API

**Document Type:** Technical Skill / API Reference  
**Purpose:** Complete reference for the World Bank Indicators API v2 — built specifically for the World Analyst pipeline. Drop this into any AI agent context to enable accurate, idiomatic API usage from first principles.  
**Source:** datahelpdesk.worldbank.org/knowledgebase/topics/125589  
**Last Verified:** April 2026

---

## 1. What This API Is

The **World Bank Indicators API v2** provides free, unauthenticated access to the World Bank's global development data — hundreds of economic, social, and environmental indicators across 200+ countries, dating back decades.

**No API key required.** No rate limit documented. No authentication headers needed.

Base URL:
```
https://api.worldbank.org/v2/
```

All responses default to XML. Always append `?format=json` for JSON output.

---

## 2. Core URL Patterns

The API supports two equivalent query styles. For the World Analyst project, use the **argument-based** style consistently — it's cleaner in Python code.

### Indicator Data (Primary Use Case)

```
GET https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}?format=json&date={date_range}&per_page={n}&mrv={n}
```

**Examples:**

```bash
# GDP for Brazil, 2018–2023
https://api.worldbank.org/v2/country/br/indicator/NY.GDP.MKTP.CD?format=json&date=2018:2023

# All countries, population, single year
https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&date=2022

# Multiple countries, semicolon-separated
https://api.worldbank.org/v2/country/nl;de;be/indicator/NY.GDP.MKTP.CD?format=json&date=2015:2023

# Most recent 5 non-empty values
https://api.worldbank.org/v2/country/za/indicator/NY.GDP.MKTP.CD?format=json&mrnev=5
```

### Country Metadata

```bash
# All countries (paginated, 50/page by default)
https://api.worldbank.org/v2/country?format=json&per_page=300

# Single country by ISO2 code
https://api.worldbank.org/v2/country/za?format=json
```

---

## 3. Query Parameters — Complete Reference

| Parameter | Type | Description | Example |
|---|---|---|---|
| `format` | string | Output format. **Always use `json`** | `format=json` |
| `date` | string | Year, range, month, or quarter | `date=2018:2023` |
| `mrv` | int | Most Recent Values — N most recent years (includes nulls) | `mrv=5` |
| `mrnev` | int | Most Recent Non-Empty Values — N most recent with actual data | `mrnev=5` |
| `per_page` | int | Results per page. Default: 50. Max: varies | `per_page=1000` |
| `page` | int | Page number for paginated results | `page=2` |
| `gapfill` | Y/N | With MRV: back-fills nulls from previous periods | `gapfill=Y` |
| `frequency` | M/Q/Y | With MRV: monthly, quarterly, or yearly data | `frequency=Y` |

### Date Format Rules

| Format | Example | Use Case |
|---|---|---|
| Single year | `date=2022` | Snapshot |
| Year range | `date=2015:2023` | Time series |
| Month | `date=2012M01` | Monthly data |
| Month range | `date=2012M01:2012M08` | Monthly series |
| Quarter | `date=2013Q1` | Quarterly data |
| Quarter range | `date=2013Q1:2013Q4` | Quarterly series |
| Year-to-date | `date=YTD:2013` | High-frequency YTD |

### Delimiter Rules

| Symbol | Meaning | Example |
|---|---|---|
| `:` | Range (numeric) | `date=2015:2023` |
| `;` | Logical AND (multiple values) | `country/nl;de;be` |

---

## 4. Response Format — JSON Structure

**Critical:** The JSON response is a 2-element array, not a simple object.

```python
response = requests.get(url).json()
metadata = response[0]   # Pagination info
data      = response[1]  # List of data points (or None if error)
```

### Pagination Metadata (element 0)

```json
{
  "page": 1,
  "pages": 3,
  "per_page": "50",
  "total": 150,
  "lastupdated": "2024-08-15"
}
```

### Data Points (element 1) — Indicator Query

```json
[
  {
    "indicator": {
      "id": "NY.GDP.MKTP.CD",
      "value": "GDP (current US$)"
    },
    "country": {
      "id": "ZA",
      "value": "South Africa"
    },
    "countryiso3code": "ZAF",
    "date": "2022",
    "value": 405269740754.0,
    "unit": "",
    "obs_status": "",
    "decimal": 0
  },
  ...
]
```

### Data Points — Country Query

```json
[
  {
    "id": "ZAF",
    "iso2Code": "ZA",
    "name": "South Africa",
    "region": { "id": "SSF", "iso2code": "ZG", "value": "Sub-Saharan Africa" },
    "adminregion": { "id": "SSA", "iso2code": "ZF", "value": "Sub-Saharan Africa (excluding high income)" },
    "incomeLevel": { "id": "UMC", "iso2code": "XT", "value": "Upper middle income" },
    "lendingType": { "id": "IBD", "iso2code": "XF", "value": "IBRD" },
    "capitalCity": "Pretoria",
    "longitude": "28.1871",
    "latitude": "-25.746"
  }
]
```

**Key fields to extract:**
- `value` — the actual data point (can be `null` for missing years)
- `date` — the year string (e.g. `"2022"`)
- `country.value` — country name
- `countryiso3code` — ISO 3166-1 alpha-3 code

---

## 5. Handling Null Values

Many indicators have data gaps. This is normal and expected. The API returns `null` for years with no data.

```python
# Safe extraction pattern
values = {
    item["date"]: item["value"]
    for item in data
    if item["value"] is not None
}
```

For the World Analyst pipeline, use `mrnev=N` (Most Recent Non-Empty Values) instead of `mrv=N` to avoid pulling years that are all nulls. This is critical for World Bank data — many indicators lag 1–3 years.

---

## 6. Pagination

Default page size is 50. For multi-country or multi-year queries, set `per_page=1000` to avoid pagination overhead. Always check `response[0]["pages"]` before assuming you have all data.

```python
def fetch_all_pages(url_base):
    all_data = []
    page = 1
    while True:
        resp = requests.get(f"{url_base}&page={page}&per_page=1000").json()
        meta = resp[0]
        items = resp[1] or []
        all_data.extend(items)
        if page >= meta["pages"]:
            break
        page += 1
    return all_data
```

---

## 7. Country Codes

The API accepts both **ISO 2-letter** and **ISO 3-letter** codes, and WB-specific codes where ISO codes don't exist.

```bash
# Either works:
/country/za/    # ISO 2 (South Africa)
/country/ZAF/   # ISO 3 (South Africa)
/country/all/   # All countries (including aggregates)
```

**Important:** `/country/all/` includes regional aggregates and income group aggregates (e.g. "World", "High income", "Sub-Saharan Africa"). These are not real countries. Filter them by checking that `region.id != "NA"` or that `incomeLevel.id != "NA"`.

```python
# Filter to real countries only
real_countries = [
    c for c in countries
    if c.get("region", {}).get("id") != "NA"
]
```

---

## 8. Indicator Codes — World Analyst Selection

These are the six indicators used in the World Analyst pipeline. All sourced from **WDI (World Development Indicators, source ID 2)**.

| Indicator Code | Name | Unit | Notes |
|---|---|---|---|
| `NY.GDP.MKTP.CD` | GDP (current US$) | USD | Most current data lags 1–2 years |
| `FP.CPI.TOTL.ZG` | Inflation, consumer prices (annual %) | % | Core risk signal |
| `SL.UEM.TOTL.ZS` | Unemployment, total (% of labor force) | % | Modelled ILO estimate |
| `BN.CAB.XOKA.GD.ZS` | Current account balance (% of GDP) | % | Trade balance proxy |
| `GC.DOD.TOTL.GD.ZS` | Central government debt (% of GDP) | % | Fiscal health signal |
| `NY.GDP.MKTP.KD.ZG` | GDP growth (annual %) | % | Most directly interpretable |

**Recommended fetch strategy:**
```python
BASE = "https://api.worldbank.org/v2"
INDICATORS = [
    "NY.GDP.MKTP.CD",
    "FP.CPI.TOTL.ZG",
    "SL.UEM.TOTL.ZS",
    "BN.CAB.XOKA.GD.ZS",
    "GC.DOD.TOTL.GD.ZS",
    "NY.GDP.MKTP.KD.ZG",
]

# Fetch 7 years to give Pandas enough history for trend + anomaly detection
DATE_RANGE = "2017:2023"
```

---

## 9. Python Fetch Pattern (Production-Grade)

```python
import requests
import time
from typing import Optional

WB_BASE = "https://api.worldbank.org/v2"

def fetch_indicator(
    country_code: str,
    indicator: str,
    date_range: str = "2017:2023",
    mrnev: Optional[int] = None,
    retries: int = 3,
) -> list[dict]:
    """
    Fetch a single indicator for a single country.
    Returns list of {date, value} dicts with nulls removed.
    """
    params = {
        "format": "json",
        "per_page": 100,
    }
    if mrnev:
        params["mrnev"] = mrnev
    else:
        params["date"] = date_range

    url = f"{WB_BASE}/country/{country_code}/indicator/{indicator}"

    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, list) or len(data) < 2 or data[1] is None:
                return []

            return [
                {"date": item["date"], "value": item["value"]}
                for item in data[1]
                if item["value"] is not None
            ]
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise

    return []


def fetch_all_countries_indicator(
    indicator: str,
    country_codes: list[str],
    date_range: str = "2017:2023",
) -> dict[str, list[dict]]:
    """
    Fetch one indicator for multiple countries.
    Returns {country_code: [{date, value}, ...]}
    """
    # Batch via semicolon-separated codes
    batch = ";".join(country_codes)
    params = {
        "format": "json",
        "per_page": 1000,
        "date": date_range,
    }
    url = f"{WB_BASE}/country/{batch}/indicator/{indicator}"

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list) or len(data) < 2 or data[1] is None:
        return {}

    result: dict[str, list[dict]] = {}
    for item in data[1]:
        if item["value"] is None:
            continue
        code = item["country"]["id"].lower()
        if code not in result:
            result[code] = []
        result[code].append({"date": item["date"], "value": item["value"]})

    return result
```

---

## 10. GCS Raw Backup — Storage Pattern

The pipeline stores raw API responses to GCS before any processing. File naming convention:

```
gs://{BUCKET}/raw/{indicator_code}/{country_code}/{YYYY-MM-DD}.json
```

Example:
```
gs://world-analyst-raw/raw/NY.GDP.MKTP.CD/za/2024-01-15.json
```

The raw file is the exact `response[1]` list from the API, serialised as JSON. This creates a clean audit trail: raw data in GCS, processed insights in Firestore.

---

## 11. Country List — World Analyst Default Set

15 countries selected for geographic, economic, and narrative diversity. Includes ML6's home markets.

| ISO2 | ISO3 | Country | Relevance |
|---|---|---|---|
| BE | BEL | Belgium | ML6 HQ — Ghent |
| NL | NLD | Netherlands | ML6 Amsterdam office |
| DE | DEU | Germany | ML6 Berlin/Munich offices |
| GB | GBR | United Kingdom | ML6 London office |
| FR | FRA | France | Major EU economy |
| US | USA | United States | Global benchmark |
| CN | CHN | China | Largest emerging market |
| JP | JPN | Japan | Major developed Asia |
| IN | IND | India | Fastest-growing large economy |
| BR | BRA | Brazil | Largest Latin American economy |
| ZA | ZAF | South Africa | ML6 adjacent; load-shedding narrative |
| NG | NGA | Nigeria | Largest African economy |
| EG | EGY | Egypt | North Africa / MENA |
| AU | AUS | Australia | Commodities benchmark |
| CA | CAN | Canada | G7 / North America |

**Fetch all 15 in one request:**
```python
COUNTRIES = ["be","nl","de","gb","fr","us","cn","jp","in","br","za","ng","eg","au","ca"]
batch = ";".join(COUNTRIES)
url = f"https://api.worldbank.org/v2/country/{batch}/indicator/NY.GDP.MKTP.CD?format=json&date=2017:2023&per_page=500"
```

---

## 12. Known Data Quirks and Gotchas

**Null-heavy recent years**  
Many indicators for 2023 and even 2022 are null because national statistics offices report with a 1–2 year lag. Use `mrnev=5` or `date=2015:2022` to get reliable data.

**Aggregates in "all" queries**  
`/country/all/` returns ~300 entries including regional/income aggregates. Filter these out by checking `region.id != "NA"`.

**No sorting supported**  
The API returns data in a fixed order (usually newest year first, or alpha by country). You cannot control sort order. Sort in Pandas after fetching.

**Pagination default is 50**  
The most common mistake is forgetting to set `per_page=1000`. With 15 countries × 7 years × 6 indicators that's up to 630 data points per indicator call — well within a single page at `per_page=1000`.

**Response is always a 2-element list**  
`response[0]` is pagination metadata. `response[1]` is the data array. Accessing `response["data"]` or `response.get("value")` directly will raise a TypeError. Always index by position.

**Indicator codes are case-sensitive**  
`NY.GDP.MKTP.CD` works. `ny.gdp.mktp.cd` does not.

**Value field can be float, int, or null**  
Do not assume numeric type. Always cast: `float(item["value"])` after null check.

---

## 13. Error Handling

The API returns HTTP 200 even for invalid queries. Errors are embedded in the response body.

```json
// Error response (still HTTP 200)
[
  { "message": [{ "id": "120", "key": "Invalid value", "value": "The provided parameter value is not valid" }] },
  null
]
```

**Robust check pattern:**
```python
data = resp.json()
if not isinstance(data, list):
    raise ValueError(f"Unexpected response type: {type(data)}")
if len(data) < 2 or data[1] is None:
    # Check for error message
    if "message" in data[0]:
        raise ValueError(f"API error: {data[0]['message']}")
    return []  # Valid but empty result
```

**Common error IDs:**

| ID | Key | Meaning |
|---|---|---|
| 120 | Invalid value | Bad country code, indicator code, or parameter |
| 140 | No data | Valid query but no data exists |
| 150 | Language not supported | Unsupported language prefix |
| 175 | Resource not found | Endpoint or resource does not exist |

---

## 14. Rate Limits and Best Practices

No documented rate limit, but follow these conventions:

- Add `time.sleep(0.1)` between sequential requests in loops
- For parallel fetching with `asyncio`, limit concurrency to ~5 simultaneous requests
- Set `timeout=10` on all requests to handle slow responses gracefully
- Implement exponential backoff on failures (start at 1s, max at 8s, 3 attempts)

The World Bank API is a public service. Be a respectful consumer.

---

## 15. Useful Discovery Endpoints

```bash
# List all available data sources
https://api.worldbank.org/v2/sources?format=json

# List all indicators (paginated — 10k+ total)
https://api.worldbank.org/v2/indicator?format=json&per_page=100

# Search indicators by keyword (partial name match)
https://api.worldbank.org/v2/indicator?format=json&per_page=100&q=GDP

# Get indicator metadata (description, source, topics)
https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json

# List all topics
https://api.worldbank.org/v2/topics?format=json

# Get all indicators for a topic (topic 3 = Economy & Growth)
https://api.worldbank.org/v2/topic/3/indicator?format=json
```

---

## 16. Quick Reference — Cheat Sheet

```python
# The single most useful call pattern for this project:

import requests

def get_indicator_for_countries(countries, indicator, years="2016:2023"):
    batch = ";".join(countries)
    url = (
        f"https://api.worldbank.org/v2/country/{batch}"
        f"/indicator/{indicator}"
        f"?format=json&date={years}&per_page=1000"
    )
    r = requests.get(url, timeout=10)
    data = r.json()
    if not isinstance(data, list) or len(data) < 2 or data[1] is None:
        return []
    return [
        {
            "country_code": row["country"]["id"].upper(),
            "country_name": row["country"]["value"],
            "year": int(row["date"]),
            "value": row["value"],
            "indicator": indicator,
        }
        for row in data[1]
        if row["value"] is not None
    ]

# Usage
COUNTRIES = ["be","nl","de","gb","fr","us","cn","jp","in","br","za","ng","eg","au","ca"]
gdp_data = get_indicator_for_countries(COUNTRIES, "NY.GDP.MKTP.CD")
```

---

*Source: World Bank Data Help Desk — Developer Information*  
*https://datahelpdesk.worldbank.org/knowledgebase/topics/125589*  
*No API key required. Free and open access.*
