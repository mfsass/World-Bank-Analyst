---
name: world-bank-api
description: Complete reference for the World Bank Indicators API v2 — the data layer for the World Analyst pipeline.
---

# SKILL: World Bank Data API

**Document Type:** Technical Skill / API Reference  
**Purpose:** Complete reference for the World Bank Indicators API v2 — built specifically for the World Analyst pipeline. Drop this into any AI agent context to enable accurate, idiomatic API usage from first principles.  
**Source:** datahelpdesk.worldbank.org/knowledgebase/topics/125589  
**Last Verified:** April 2026 (live-tested against production API)

---

## 1. What This API Is

The **World Bank Indicators API v2** provides free, unauthenticated access to the World Bank's global development data — hundreds of economic, social, and environmental indicators across 200+ countries, dating back decades.

**No API key required.** No rate limit documented. No authentication headers needed.

Base URL:

```
https://api.worldbank.org/v2/
```

All responses default to XML. Always append `?format=json` for JSON output.

If you open endpoints such as `https://api.worldbank.org/v2/indicator` directly in a browser, the browser will often show a message like "This XML file does not appear to have any style information associated with it." That is normal. It is not an API failure. It just means the endpoint returned raw XML because no `format=json` query string was supplied.

### Official Documentation Map

The official World Bank v2 docs split the API into a few distinct families. That split matters because the JSON shapes are not identical across them.

- `API Basic Call Structures` — query styles, delimiters, paging, MRV/MRNEV, output formats, language prefixes, URL limits
- `Country API Queries` — country metadata and country-code behavior
- `Aggregate API Queries` — region, income-level, and lending-type definitions and aggregate filters
- `Indicator API Queries` — indicator metadata, source notes, topics, and source scoping
- `Topic API Queries` — topic discovery and topic-to-indicator browsing
- `Advanced Data API Queries` — multidimensional source/concept queries; JSON shape differs from the simple indicators API
- `Metadata API Queries` — concept, metatype, and metadata discovery; JSON shape also differs from the simple indicators API

For World Analyst runtime fetching, only the simple indicators API is on the hot path. Topic and metadata endpoints are discovery tools. Advanced Data is out of scope for the live pipeline unless a later ADR explicitly changes that.

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

# Filter countries by region / income level / lending type
https://api.worldbank.org/v2/country?region=LCN&format=json
https://api.worldbank.org/v2/country?incomelevel=UMC&format=json
https://api.worldbank.org/v2/country?lendingtype=IBD&format=json
```

### Discovery and Definition Endpoints

These are the catalog endpoints you use to inspect the available API surface rather than fetch country-indicator time series.

```bash
# List all indicators
https://api.worldbank.org/v2/indicator?format=json&per_page=100

# List income-level definitions
https://api.worldbank.org/v2/incomelevel?format=json

# List lending-type definitions
https://api.worldbank.org/v2/lendingtypes?format=json

# List all data sources
https://api.worldbank.org/v2/sources?format=json

# Get one source definition
https://api.worldbank.org/v2/sources/2?format=json
```

Notes:

- `indicator` is singular in the path: `/indicator`
- `incomelevel` is singular in the path: `/incomelevel`
- The list endpoint for lending types is plural: `/lendingtypes`
- The source catalog uses `/sources` and source details use `/sources/{id}`

---

## 3. Query Parameters — Complete Reference

| Parameter        | Type          | Description                                                                   | Example              |
| ---------------- | ------------- | ----------------------------------------------------------------------------- | -------------------- |
| `format`         | string        | Output format. Use `json` for application code                                | `format=json`        |
| `date`           | string        | Year, range, month, quarter, or YTD window                                    | `date=2018:2023`     |
| `mrv`            | int           | Most Recent Values — N most recent periods, including nulls                   | `mrv=5`              |
| `mrnev`          | int           | Most Recent Non-Empty Values — N most recent populated periods                | `mrnev=5`            |
| `per_page`       | int           | Results per page. Default is 50                                               | `per_page=1000`      |
| `page`           | int           | Page number for paginated results                                             | `page=2`             |
| `gapfill`        | Y/N           | With `mrv`, back-fills nulls from earlier periods                             | `gapfill=Y`          |
| `frequency`      | M/Q/Y         | With `mrv`, requests monthly, quarterly, or yearly values                     | `frequency=M`        |
| `source`         | int           | Required for some indicator discovery queries and for multi-indicator queries | `source=2`           |
| `footnote`       | Y/N           | Includes footnote detail in data calls                                        | `footnote=y`         |
| `downloadformat` | csv/xml/excel | Returns a downloaded export instead of the normal payload                     | `downloadformat=csv` |

### Multiple Indicators in One Call

The official API does support multiple indicators in a single request:

```bash
https://api.worldbank.org/v2/country/chn;ago/indicator/SI.POV.DDAY;SP.POP.TOTL?source=2
```

Official limits from the docs:

- Maximum 60 indicators in one request
- Maximum 1,500 characters between two `/` separators
- Maximum 4,000 characters in the full URL

For World Analyst, keep one indicator per request anyway. It gives cleaner provenance, cleaner retries, and failure isolation per indicator.

### Date Format Rules

| Format        | Example                | Use Case           |
| ------------- | ---------------------- | ------------------ |
| Single year   | `date=2022`            | Snapshot           |
| Year range    | `date=2015:2023`       | Time series        |
| Month         | `date=2012M01`         | Monthly data       |
| Month range   | `date=2012M01:2012M08` | Monthly series     |
| Quarter       | `date=2013Q1`          | Quarterly data     |
| Quarter range | `date=2013Q1:2013Q4`   | Quarterly series   |
| Year-to-date  | `date=YTD:2013`        | High-frequency YTD |

### Delimiter Rules

| Symbol | Meaning                       | Example            |
| ------ | ----------------------------- | ------------------ |
| `:`    | Range (numeric)               | `date=2015:2023`   |
| `;`    | Logical AND (multiple values) | `country/nl;de;be` |

---

## 4. Response Format — JSON Structure

**Do not assume one JSON shape across the whole World Bank API.**

### Standard Indicators API Endpoints

The standard discovery and data endpoints used by this project usually return a 2-element array on success:

```python
payload = requests.get(url).json()
metadata = payload[0]
rows = payload[1]
```

This covers endpoints such as:

- `/country`
- `/indicator`
- `/topic`
- `/region`, `/incomelevel`, `/lendingtype`, `/lendingtypes`
- `/sources`, `/sources/{id}`
- `/country/{codes}/indicator/{indicator}`

Sample indicator-data metadata:

```json
{
  "page": 1,
  "pages": 1,
  "per_page": 200,
  "total": 4,
  "sourceid": "2",
  "lastupdated": "2026-04-08"
}
```

Sample indicator-data row:

```json
{
  "indicator": {
    "id": "NY.GDP.MKTP.CD",
    "value": "GDP (current US$)"
  },
  "country": {
    "id": "BE",
    "value": "Belgium"
  },
  "countryiso3code": "BEL",
  "date": "2023",
  "value": 651330595110.011,
  "unit": "",
  "obs_status": "",
  "decimal": 0
}
```

**Important nuances:**

- Numeric-looking metadata fields such as `page`, `pages`, `per_page`, and `total` can arrive as either strings or integers depending on endpoint.
- `sourceid` and `lastupdated` are common on indicator-data calls, not on every discovery endpoint.
- When using `mrnev`, `unit` may be absent. Treat it as optional.

### Discovery Endpoint Row Shapes

These are the specific catalog endpoints most likely to matter when validating or expanding the monitored indicator set.

#### `/country?format=json`

Returns the World Bank country catalog, which is not a pure list of sovereign countries. It includes both real countries and aggregate entries.

Live example metadata shape:

```json
{
  "page": 1,
  "pages": 60,
  "per_page": "5",
  "total": 296
}
```

Live example row for a real country:

```json
{
  "id": "ABW",
  "iso2Code": "AW",
  "name": "Aruba",
  "region": {
    "id": "LCN",
    "iso2code": "ZJ",
    "value": "Latin America & Caribbean "
  },
  "adminregion": {
    "id": "",
    "iso2code": "",
    "value": ""
  },
  "incomeLevel": {
    "id": "HIC",
    "iso2code": "XD",
    "value": "High income"
  },
  "lendingType": {
    "id": "LNX",
    "iso2code": "XX",
    "value": "Not classified"
  },
  "capitalCity": "Oranjestad",
  "longitude": "-70.0167",
  "latitude": "12.5167"
}
```

Live example row for an aggregate entry:

```json
{
  "id": "AFE",
  "iso2Code": "ZH",
  "name": "Africa Eastern and Southern",
  "region": {
    "id": "NA",
    "iso2code": "NA",
    "value": "Aggregates"
  },
  "adminregion": {
    "id": "",
    "iso2code": "",
    "value": ""
  },
  "incomeLevel": {
    "id": "NA",
    "iso2code": "NA",
    "value": "Aggregates"
  },
  "lendingType": {
    "id": "",
    "iso2code": "",
    "value": "Aggregates"
  },
  "capitalCity": "",
  "longitude": "",
  "latitude": ""
}
```

What to take from this:

- `/country` includes aggregates such as `AFE`, `AFR`, and `ARB`, not just countries.
- Aggregate rows can be detected reliably via `region.id == "NA"` and usually `incomeLevel.id == "NA"`.
- Fields like `adminregion`, `capitalCity`, `longitude`, and `latitude` can be empty strings.
- The endpoint is paginated and should not be assumed to fit on one page.

The endpoint also supports catalog filters such as `region`, `incomelevel`, and `lendingtype`, which are useful for discovery but not needed in the monitored-set runtime path.

#### `/indicator?format=json`

Returns the global indicator catalog. The result is large and always paginated, so never assume one page is enough.

Live example metadata shape:

```json
{
  "page": 1,
  "pages": 14756,
  "per_page": "2",
  "total": 29511
}
```

Live example indicator row shape:

```json
{
  "id": "1.0.HCount.1.90usd",
  "name": "Poverty Headcount ($1.90 a day)",
  "unit": "",
  "source": {
    "id": "37",
    "value": "LAC Equity Lab"
  },
  "sourceNote": "The poverty headcount index measures the proportion of the population with daily per capita income (in 2011 PPP) below the poverty line.",
  "sourceOrganization": "LAC Equity Lab tabulations of SEDLAC (CEDLAS and the World Bank).",
  "topics": [
    {
      "id": "11",
      "value": "Poverty "
    }
  ]
}
```

Use this endpoint when you need to validate indicator metadata, source ownership, and topic mapping. Do not use it in the monitored-set runtime path.

#### `/incomelevel?format=json`

Returns the small fixed income-level definition list.

Live example row shape:

```json
{
  "id": "HIC",
  "iso2code": "XD",
  "value": "High income"
}
```

Use this endpoint to validate aggregate filters or to explain the meaning of country metadata returned from `/country`.

#### `/lendingtypes?format=json`

Returns the lending-type definition list.

Live example row shape:

```json
{
  "id": "IBD",
  "iso2code": "XF",
  "value": "IBRD"
}
```

Use this endpoint the same way as `incomelevel`: for catalog understanding and filters, not for time-series retrieval.

#### `/sources?format=json` and `/sources/{id}?format=json`

Returns the data-source catalog used across indicators, metadata, and advanced-data queries.

Live example source row shape:

```json
{
  "id": "11",
  "lastupdated": "2013-02-22",
  "name": "Africa Development Indicators",
  "code": "ADI",
  "description": "",
  "url": "",
  "dataavailability": "Y",
  "metadataavailability": "Y",
  "concepts": "3"
}
```

Live example for source `2`:

```json
{
  "id": "2",
  "lastupdated": "2026-04-08",
  "name": "World Development Indicators",
  "code": "WDI",
  "description": "",
  "url": "",
  "dataavailability": "Y",
  "metadataavailability": "Y",
  "concepts": "3"
}
```

This endpoint matters directly for this repo because our monitored indicators come from source `2`, World Development Indicators.

### Standard Error Payloads on HTTP 200

Invalid standard data calls often still return HTTP 200, but the JSON body changes shape to a 1-element list:

```json
[
  {
    "message": [
      {
        "id": "120",
        "key": "Invalid value",
        "value": "The provided parameter value is not valid"
      }
    ]
  }
]
```

That is why payload-level validation is mandatory even after `raise_for_status()`.

### Metadata and Advanced Data Endpoints

`/sources/.../metadata` and `/sources/.../data` do **not** use the same `[meta, rows]` shape. They return JSON objects instead.

Sample metadata response shape:

```json
{
  "page": 1,
  "pages": 1,
  "per_page": "5000",
  "total": 2,
  "source": [
    {
      "id": "2",
      "name": "World Development Indicators",
      "concept": [
        {
          "id": "Country",
          "variable": [
            {
              "id": "JPN",
              "metatype": [
                {
                  "id": "IncomeGroup",
                  "value": "High income"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

Use separate parsers for metadata and advanced-data endpoints. Do not reuse the simple indicator parser there.

---

## 5. Handling Null Values

Many indicators have data gaps. This is normal and expected. The API returns `null` for periods with no data.

```python
values = {
    item["date"]: item["value"]
    for item in rows
    if item["value"] is not None
}
```

**Use `mrnev` carefully.**

- `mrnev=N` is useful for exploratory lookups or latest-point UIs.
- `mrv=N` is useful when you explicitly want the latest N periods including nulls.
- `gapfill=Y` back-fills missing periods and can make sparse series look cleaner than they really are.

For the World Analyst live pipeline, keep the fixed window `date=2010:2024` and avoid `mrnev` and `gapfill` in the core fetch path. We need to see stale and missing years explicitly so quality rules can flag incomplete coverage instead of hiding it.

---

## 6. Pagination

Default page size is 50. For multi-country or multi-year queries, set `per_page=1000` to avoid pagination overhead. Always check `response[0]["pages"]` before assuming you have all data.

```python
def fetch_all_pages(url_base: str) -> list[dict]:
    """Fetch all pages of a paginated World Bank API response."""
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

## 7. Country Codes and Aggregates

The API accepts ISO 2-letter codes, ISO 3-letter codes, and World Bank-specific aggregate codes.

```bash
/country/za/    # ISO2 country code
/country/ZAF/   # ISO3 country code
/country/LCN/   # Aggregate code (Latin America & Caribbean)
/country/all/   # All countries plus aggregates
```

**Important distinctions:**

- Country metadata calls return top-level `id` as ISO3 and `iso2Code` as ISO2 where available.
- Indicator data rows return `country.id` as ISO2 for countries, but aggregate rows can use World Bank 2-character codes there.
- Aggregate indicator rows also carry the aggregate code in `countryiso3code`.
- Some country catalog rows use World Bank-specific fallback codes when ISO codes are unavailable.

Live example for `country/LCN/indicator/NY.GDP.MKTP.CD`:

- `country.id = "ZJ"`
- `country.value = "Latin America & Caribbean"`
- `countryiso3code = "LCN"`

That means code consuming indicator rows should not assume `country.id` is always ISO2.

Live example for `country/chi?format=json`:

- `id = "CHI"`
- `iso2Code = "JG"`
- `name = "Channel Islands"`

That confirms the official docs: when ISO codes are unavailable, the country catalog can return World Bank-specific codes instead.

`/country/all/` includes regional and income-group aggregates. For this project, avoid it in runtime fetching and use the explicit monitored-country list instead.

If you ever need a dynamic country catalog, filter out aggregates like this:

```python
real_countries = [
    country
    for country in countries
    if country.get("region", {}).get("id") != "NA"
]
```

---

## 8. Indicator Codes — World Analyst Selection

These are the six indicators used in the World Analyst pipeline. All sourced from **WDI (World Development Indicators, source ID 2)**.

| Indicator Code      | Name                                   | Unit | Notes                                                                             |
| ------------------- | -------------------------------------- | ---- | --------------------------------------------------------------------------------- |
| `NY.GDP.MKTP.CD`    | GDP (current US$)                      | USD  | Most current data lags 1–2 years                                                  |
| `FP.CPI.TOTL.ZG`    | Inflation, consumer prices (annual %)  | %    | Core risk signal                                                                  |
| `SL.UEM.TOTL.ZS`    | Unemployment, total (% of labor force) | %    | Modelled ILO estimate                                                             |
| `BN.CAB.XOKA.GD.ZS` | Current account balance (% of GDP)     | %    | Trade balance proxy — use % of GDP for cross-country comparison, not absolute BoP |
| `GC.DOD.TOTL.GD.ZS` | Central government debt (% of GDP)     | %    | Fiscal health signal                                                              |
| `NY.GDP.MKTP.KD.ZG` | GDP growth (annual %)                  | %    | Most directly interpretable                                                       |

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

# Fetch the exact-complete 15-year panel used by the live monitored scope
DATE_RANGE = "2010:2024"
```

---

## 9. Python Fetch Pattern (Production-Grade)

This is a general-purpose pattern for the simple indicators API. The production World Analyst pipeline intentionally keeps a stricter version of this pattern: one indicator per request, explicit date window, payload-level error detection, and no `mrnev`/`gapfill` in the main monitored-set path.

```python
import requests
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

WB_BASE = "https://api.worldbank.org/v2"


def _payload_error(payload: list[dict] | list[object]) -> str | None:
    first_item = payload[0] if payload else None
    if not isinstance(first_item, dict) or "message" not in first_item:
        return None

    messages = first_item["message"]
    if not isinstance(messages, list):
        return str(messages)

    return "; ".join(
        str(message.get("value") or message.get("key") or message)
        for message in messages
    )

def fetch_indicator(
    country_code: str,
    indicator: str,
  date_range: str = "2010:2024",
    mrnev: Optional[int] = None,
    retries: int = 3,
) -> list[dict]:
    """Fetch a single indicator for a single country.

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
            payload = resp.json()

            if not isinstance(payload, list) or not payload:
                raise ValueError(f"Unexpected payload shape: {type(payload)}")

            payload_error = _payload_error(payload)
            if payload_error:
                raise ValueError(f"World Bank payload error: {payload_error}")

            if len(payload) < 2 or payload[1] is None:
                return []

            return [
                {"date": item["date"], "value": item["value"]}
                for item in payload[1]
                if item["value"] is not None
            ]
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                logger.warning("Retry %d for %s/%s: %s", attempt + 1, country_code, indicator, e)
            else:
                raise

    return []


def fetch_all_countries_indicator(
    indicator: str,
    country_codes: list[str],
  date_range: str = "2010:2024",
) -> dict[str, list[dict]]:
    """Fetch one indicator for multiple countries via batch request.

    Uses semicolon-separated country codes for a single API call.
    Returns {country_code: [{date, value}, ...]}
    """
    batch = ";".join(country_codes)
    params = {
        "format": "json",
        "per_page": 1000,
        "date": date_range,
    }
    url = f"{WB_BASE}/country/{batch}/indicator/{indicator}"

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Unexpected payload shape: {type(payload)}")

    payload_error = _payload_error(payload)
    if payload_error:
        raise ValueError(f"World Bank payload error: {payload_error}")

    if len(payload) < 2 or payload[1] is None:
        return {}

    result: dict[str, list[dict]] = {}
    for item in payload[1]:
        if item["value"] is None:
            continue
        code = item["country"]["id"].lower()
        if code not in result:
            result[code] = []
        result[code].append({"date": item["date"], "value": item["value"]})

    return result
```

---

## 10. Raw Archive Pattern in This Repo

World Analyst does **not** archive only `response[1]` anymore. The live pipeline stores one request-response envelope per successful indicator request, scoped to the run.

Current envelope fields mirror `pipeline.fetcher._build_raw_payload_envelope()`:

```json
{
    "source_name": "world_bank_indicators_api",
  "source_date_range": "2010:2024",
    "source_last_updated": "2026-04-08",
    "source_id": "2",
    "indicator_code": "NY.GDP.MKTP.CD",
    "indicator_name": "GDP (current US$)",
  "country_codes": ["BR", "CA", "GB"],
    "request": {
    "url": "https://api.worldbank.org/v2/country/br;ca;gb/indicator/NY.GDP.MKTP.CD?format=json&date=2010:2024&per_page=1000&source=2",
        "params": {
            "format": "json",
      "date": "2010:2024",
            "per_page": 1000,
      "source": "2"
        }
    },
    "http_status": 200,
    "fetched_at": "2026-04-11T...Z",
    "response_metadata": {...},
    "response_body": [...]
}
```

Why this matters:

- We retain the exact logical API payload for successful indicator requests.
- Failed indicator requests currently surface through logs and failure summaries rather than archived request-response envelopes.
- We retain request scope and source metadata in the same file.
- Provenance is per run and per indicator, not per country, which matches the actual fetch strategy.

---

## 11. Country List — World Analyst Default Set

17 countries selected for exact 15-year completeness ending at 2024. This is the live core panel used by the backend runtime, not a broad geographic-representation list.

| ISO2 | ISO3 | Country              | Relevance                                 |
| ---- | ---- | -------------------- | ----------------------------------------- |
| BR   | BRA  | Brazil               | Largest Latin American economy            |
| CA   | CAN  | Canada               | North America benchmark                   |
| GB   | GBR  | United Kingdom       | Major European market                     |
| US   | USA  | United States        | Global benchmark                          |
| BS   | BHS  | Bahamas, The         | Exact-complete Caribbean coverage         |
| CO   | COL  | Colombia             | Latin American macro comparator           |
| SV   | SLV  | El Salvador          | Exact-complete Central America coverage   |
| GE   | GEO  | Georgia              | Eurasia bridge market                     |
| HU   | HUN  | Hungary              | EU-converger comparator                   |
| MY   | MYS  | Malaysia             | Asia manufacturing exporter               |
| NZ   | NZL  | New Zealand          | Small developed open economy              |
| RU   | RUS  | Russian Federation   | Mechanically selected energy exposure     |
| SG   | SGP  | Singapore            | Trade and financial hub                   |
| ES   | ESP  | Spain                | Euro-area comparator                      |
| CH   | CHE  | Switzerland          | Safe-haven developed market               |
| TR   | TUR  | Turkiye              | Inflation and external-vulnerability case |
| UY   | URY  | Uruguay              | Stable Latin American comparator          |

**Fetch all 17 in one request:**

```python
COUNTRIES = ["br","ca","gb","us","bs","co","sv","ge","hu","my","nz","ru","sg","es","ch","tr","uy"]
batch = ";".join(COUNTRIES)
url = f"https://api.worldbank.org/v2/country/{batch}/indicator/NY.GDP.MKTP.CD?format=json&date=2010:2024&per_page=1000&source=2"
```

---

## 12. Known Data Quirks and Gotchas

**Public endpoint latency can spike**  
The API is public and occasionally slow. In live checks for this repo, a simple two-country GDP call took about 30 seconds even though other calls returned in under 3 seconds. Timeouts and retries are operational necessities, not optional polish.

**Null-heavy recent years are normal**  
Many indicators lag by one or more years. For exploratory work, `mrnev` can help. For the World Analyst pipeline, fixed date windows are better because they preserve evidence of stale series.

**`mrnev` and `gapfill` can hide quality problems**  
They make latest-value lookups easier, but they also hide whether a series actually stopped years ago. That matters directly for monitored-set quality checks.

**`/country/all/` includes aggregates**  
It is not a clean country-only catalog. Use explicit country lists in runtime code.

**No sorting is supported**  
The API returns data in a reasonable default order, but you cannot request a custom sort. Always sort downstream.

**Pagination defaults to 50**  
If you do not set `per_page`, large discovery queries will paginate. For this project's indicator data calls, `per_page=1000` keeps one-indicator batches on one page.

**Standard data endpoints and metadata endpoints do not share one JSON shape**  
Simple country/indicator/topic/aggregate endpoints are list-shaped. Metadata and advanced-data endpoints are dict-shaped.

**Standard logical errors can still be HTTP 200**  
Treat payload-level `message` arrays as first-class errors.

**Indicator codes are case-sensitive**  
`NY.GDP.MKTP.CD` works. `ny.gdp.mktp.cd` does not.

**Value fields can be `float`, `int`, or `null`**  
Always null-check before casting.

**`unit` is optional**  
Especially with `mrnev`, do not assume it is present.

**Multiple-indicator calls require `source` and complicate parsing**  
The API allows them, but they are not the right default for this repo's live pipeline.

---

## 13. Error Handling

For the simple indicators API, the most important rule is this: **HTTP 200 does not mean the query succeeded logically.** Invalid requests can still come back as JSON with a `message` payload.

Standard error payload:

```json
[
  {
    "message": [
      {
        "id": "120",
        "key": "Invalid value",
        "value": "The provided parameter value is not valid"
      }
    ]
  }
]
```

Robust check pattern for simple country/indicator/topic/aggregate endpoints:

```python
payload = resp.json()
if not isinstance(payload, list) or not payload:
    raise ValueError(f"Unexpected response type: {type(payload)}")

if isinstance(payload[0], dict) and "message" in payload[0]:
    raise ValueError(f"World Bank payload error: {payload[0]['message']}")

if len(payload) < 2 or payload[1] is None:
    return []
```

For metadata and advanced-data endpoints, use a different parser. Those endpoints return JSON objects, not `[meta, rows]` lists.

**Common error IDs:**

| ID  | Key                    | Meaning                                        |
| --- | ---------------------- | ---------------------------------------------- |
| 120 | Invalid value          | Bad country code, indicator code, or parameter |
| 140 | No data                | Valid query but no data exists                 |
| 150 | Language not supported | Unsupported language prefix                    |
| 175 | Resource not found     | Endpoint or resource does not exist            |

---

## 14. Best Practices for This Repo

The official docs do not publish a hard rate limit. Treat the API as a public shared service and code defensively.

- Keep the current pattern of one indicator per request and semicolon-batched countries.
- Keep `format=json`, `source=2`, `per_page=1000`, and a fixed date range in the live pipeline.
- Do not switch the monitored-set runtime path to `mrnev` or `gapfill`; those are discovery conveniences, not quality-safe runtime defaults.
- Keep payload-level error detection even after `raise_for_status()`.
- Check `response[0]["pages"]` on every simple indicator call. The current monitored scope should stay on one page; if that changes, fail loudly and implement pagination deliberately instead of truncating page 1.
- Keep small pauses between requests and exponential backoff on transport errors.
- Treat timeout length as an operational tuning parameter. The repo now defaults to 45 seconds and exposes `WORLD_ANALYST_WORLD_BANK_TIMEOUT_SECONDS` for runtime tuning because slower public responses are a real production condition.

---

## 15. Useful Discovery Endpoints

```bash
# List all available data sources
https://api.worldbank.org/v2/sources?format=json

# Get one source definition
https://api.worldbank.org/v2/sources/2?format=json

# List all indicators (paginated — 10k+ total)
https://api.worldbank.org/v2/indicator?format=json&per_page=100

# Get indicator metadata (description, source, topics)
https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json

# List income-level and lending-type definitions
https://api.worldbank.org/v2/incomelevel?format=json
https://api.worldbank.org/v2/lendingtypes?format=json

# List all topics
https://api.worldbank.org/v2/topic?format=json

# Get all indicators for a topic (topic 3 = Economy & Growth)
https://api.worldbank.org/v2/topic/3/indicator?format=json

# List region / income-level / lending-type definitions
https://api.worldbank.org/v2/region?format=json

# Filter countries by aggregate definition
https://api.worldbank.org/v2/country?region=LCN&format=json

# Retrieve source-specific metadata for one concept/metatype combination
https://api.worldbank.org/v2/sources/2/country/usa;jpn/metatypes/incomegroup/metadata?format=json

# Retrieve topic-aligned indicator candidates when reconsidering coverage
https://api.worldbank.org/v2/topic/3/indicator?format=json&per_page=100
```

---

## 16. What This Means for World Analyst

The current fetcher is aligned with the official API in the places that matter most:

- It uses the standard simple indicators endpoint: `country/{codes}/indicator/{indicator}`.
- It batches countries with semicolons instead of using `country/all`.
- It requests JSON explicitly.
- It uses one indicator per request, which matches the repo's provenance and failure-isolation needs.
- It checks for HTTP-200 logical errors in the response body.

The clarified runtime rules for this project are:

1. Keep the fixed historical window `2010:2024` in the live monitored-set path.
2. Keep one indicator per request even though the API supports multi-indicator requests.
3. Keep topic and metadata endpoints as offline discovery tools for indicator validation, replacement analysis, and source checking.
4. Do not use aggregate codes or `country/all` in runtime fetching unless the product intentionally expands beyond country briefings.
5. Treat transport latency as a real operational concern when deciding whether to tune `REQUEST_TIMEOUT_SECONDS`.

This is the key practical distinction: the World Bank API allows more flexible query shapes than World Analyst should use in production. The repo should prefer the narrower, more auditable subset.

---

## 17. Quick Reference — Cheat Sheet

```python
# The single most useful call pattern for this project:

import requests

def get_indicator_for_countries(
    countries: list[str],
    indicator: str,
  years: str = "2010:2024",
) -> list[dict]:
    """Batch-fetch one indicator for all target countries."""
    batch = ";".join(countries)
    params = {
        "format": "json",
        "date": years,
        "per_page": 1000,
      "source": "2",
    }
    url = f"https://api.worldbank.org/v2/country/{batch}/indicator/{indicator}"
    r = requests.get(url, params=params, timeout=15)
    payload = r.json()
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Unexpected payload type: {type(payload)}")
    if isinstance(payload[0], dict) and "message" in payload[0]:
        raise ValueError(f"World Bank payload error: {payload[0]['message']}")
    if len(payload) < 2 or payload[1] is None:
        return []
    return [
        {
            "country_code": row["country"]["id"].upper(),
            "country_name": row["country"]["value"].strip(),
            "year": int(row["date"]),
            "value": row["value"],
            "indicator": indicator,
        }
        for row in payload[1]
        if row["value"] is not None
    ]

# Usage
COUNTRIES = ["br","ca","gb","us","bs","co","sv","ge","hu","my","nz","ru","sg","es","ch","tr","uy"]
gdp_data = get_indicator_for_countries(COUNTRIES, "NY.GDP.MKTP.CD")
```

---

_Source: World Bank Data Help Desk — Developer Information_  
*https://datahelpdesk.worldbank.org/knowledgebase/topics/125589*  
_All claims live-verified against production API — April 2026_  
_No API key required. Free and open access._
