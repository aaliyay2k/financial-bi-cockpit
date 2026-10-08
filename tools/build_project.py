"""Build the Financial BI Cockpit artifacts from one dataset.

The validation rules here match sql/04_usp_validate_and_publish.sql.
Running this file rewrites the seed, the certified CSVs, the report
images, the one-page PDF, the demo clip, and FinancialCockpit.pbix.
"""

from __future__ import annotations

import csv
import json
import subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
DATA = ROOT / "data"
DOCS = ROOT / "docs"
IMAGES = DOCS / "images"

Q = Decimal("0.01")
Q4 = Decimal("0.0001")

QUARTERS = (
    (2024, 1, "2024 Q1", 1),
    (2024, 2, "2024 Q2", 2),
    (2024, 3, "2024 Q3", 3),
    (2024, 4, "2024 Q4", 4),
    (2025, 1, "2025 Q1", 5),
    (2025, 2, "2025 Q2", 6),
    (2025, 3, "2025 Q3", 7),
    (2025, 4, "2025 Q4", 8),
)

COMPANIES = (
    ("NLN", "Northline Stores", "Retail"),
    ("HBR", "Harbor Mart", "Retail"),
    ("FLD", "Field & Co", "Retail"),
    ("MGR", "Metro Grocers", "Retail"),
    ("APC", "Apex Circuits", "Technology"),
    ("LMS", "Lumen Software", "Technology"),
    ("NWC", "Northwind Cloud", "Technology"),
    ("KMF", "Keel Manufacturing", "Industrials"),
    ("RDG", "Ridge Tools", "Industrials"),
    ("HST", "Harbor Steel", "Industrials"),
    ("CDH", "Cedar Health", "Healthcare"),
    ("PND", "Pine Diagnostics", "Healthcare"),
)

NAVY = "#1E2A38"
INK = "#1C1917"
MUTED = "#5C574F"
PAPER = "#F4F1EA"
CARD = "#FFFFFF"
LINE = "#E4DFD6"
TEAL = "#1F6F6A"
RED = "#9B2335"
AMBER = "#8A5A00"
SECTOR_COLOR = {
    "Retail": "#1E2A38",
    "Technology": "#1F6F6A",
    "Industrials": "#3D5A80",
    "Healthcare": "#6B4C3B",
}


def money(value) -> Decimal:
    return Decimal(value).quantize(Q, rounding=ROUND_HALF_UP)


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return (numerator / denominator).quantize(Q4, rounding=ROUND_HALF_UP)


def usd(value: Decimal) -> str:
    return f"${value:,.2f}m"


def pct(value: Decimal) -> str:
    return f"{(value * Decimal(100)):.1f}%"


def pp(value: Decimal) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f} pp"


def de_text(value: Decimal) -> str:
    return f"{value:.2f}"


def blank_row(ticker: str, year: int, quarter: int, index: int) -> dict:
    return {
        "ticker": ticker,
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "quarter_index": index,
        "revenue": None,
        "operating_income": None,
        "net_income": None,
        "total_debt": None,
        "total_equity": None,
        "operating_cash_flow": None,
    }


def fill(row, revenue, margin, equity, debt_to_equity, cash_flow) -> None:
    revenue = money(revenue)
    equity = money(equity)
    row["revenue"] = revenue
    row["operating_income"] = money(Decimal(revenue) * Decimal(str(margin)))
    row["net_income"] = money(row["operating_income"] * Decimal("0.70"))
    row["total_equity"] = equity
    row["total_debt"] = money(Decimal(equity) * Decimal(str(debt_to_equity)))
    row["operating_cash_flow"] = money(cash_flow)


def generic_rows(ticker, base_revenue, margin, equity, debt_to_equity, base_cash) -> list[dict]:
    rows = []
    for offset, (year, quarter, _label, index) in enumerate(QUARTERS):
        row = blank_row(ticker, year, quarter, index)
        revenue = money(Decimal(str(base_revenue)) * (Decimal("1.012") ** offset))
        cash = money(Decimal(str(base_cash)) * (Decimal("1.01") ** offset))
        fill(row, revenue, margin, equity, debt_to_equity, cash)
        rows.append(row)
    return rows


def explicit_rows(ticker, specs) -> list[dict]:
    rows = []
    for (year, quarter, _label, index), spec in zip(QUARTERS, specs):
        row = blank_row(ticker, year, quarter, index)
        fill(row, spec["revenue"], spec["margin"], spec["equity"], spec["de"], spec["ocf"])
        rows.append(row)
    return rows


def series(revenues, margins, equity, debt_to_equity, cash_flows) -> list[dict]:
    specs = []
    for revenue, margin, cash in zip(revenues, margins, cash_flows):
        specs.append(
            {
                "revenue": revenue,
                "margin": margin,
                "equity": equity,
                "de": debt_to_equity,
                "ocf": cash,
            }
        )
    return specs


def northline() -> list[dict]:
    specs = [
        (410, 500, "1.25", 46),
        (418, 498, "1.32", 45),
        (425, 495, "1.40", 44),
        (432, 490, "1.48", 43),
        (440, 480, "1.62", 41),
        (448, 470, "1.90", 38),
        (455, 460, "2.16", 30),
        (462, 450, "2.48", 22),
    ]
    return explicit_rows(
        "NLN",
        [
            {"revenue": r, "margin": "0.065", "equity": e, "de": d, "ocf": c}
            for r, e, d, c in specs
        ],
    )


def harbor_mart() -> list[dict]:
    specs = [
        (390, 430, "1.10", 58),
        (394, 428, "1.18", 57),
        (398, 424, "1.25", 56),
        (402, 420, "1.34", 55),
        (406, 410, "1.50", 53),
        (410, 400, "1.75", 51),
        (414, 390, "2.02", 44),
        (418, 380, "2.31", 36),
    ]
    return explicit_rows(
        "HBR",
        [
            {"revenue": r, "margin": "0.055", "equity": e, "de": d, "ocf": c}
            for r, e, d, c in specs
        ],
    )


def metro() -> list[dict]:
    specs = [
        (250, 320, "1.80", 14),
        (252, 318, "1.90", 15),
        (255, 316, "2.00", 16),
        (258, 314, "2.05", 16),
        (260, 312, "2.10", 17),
        (263, 310, "2.20", 18),
        (266, 305, "2.30", 22),
        (270, 300, "2.42", 27),
    ]
    return explicit_rows(
        "MGR",
        [
            {"revenue": r, "margin": "0.040", "equity": e, "de": d, "ocf": c}
            for r, e, d, c in specs
        ],
    )


def lumen() -> list[dict]:
    revenues = [240, 244, 247, 250, 255, 260, 264, 268]
    margins = ["0.175", "0.176", "0.178", "0.180", "0.165", "0.148", "0.130", "0.115"]
    cash = [36, 37, 38, 39, 40, 41, 42, 44]
    return explicit_rows("LMS", series(revenues, margins, 800, "0.30", cash))


def ridge() -> list[dict]:
    revenues = [210, 214, 218, 230, 234, 238, 244, 250]
    margins = ["0.125", "0.124", "0.122", "0.120", "0.112", "0.104", "0.092", "0.082"]
    cash = [18, 18, 19, 19, 20, 20, 21, 22]
    return explicit_rows("RDG", series(revenues, margins, 360, "0.70", cash))


def build_extract() -> list[dict]:
    grouped = {
        "NLN": northline(),
        "HBR": harbor_mart(),
        "FLD": generic_rows("FLD", 280, "0.08", 320, "1.05", 24),
        "MGR": metro(),
        "APC": generic_rows("APC", 540, "0.16", 900, "0.42", 70),
        "LMS": lumen(),
        "NWC": generic_rows("NWC", 610, "0.22", 1400, "0.18", 95),
        "KMF": generic_rows("KMF", 360, "0.09", 500, "0.75", 28),
        "RDG": ridge(),
        "HST": generic_rows("HST", 340, "0.07", 480, "1.15", 22),
        "CDH": generic_rows("CDH", 295, "0.11", 520, "0.50", 26),
        "PND": generic_rows("PND", 210, "0.13", 400, "0.35", 18),
    }
    rows = []
    extract_row_id = 1
    for ticker, _name, _sector in COMPANIES:
        for row in grouped[ticker]:
            row["extract_row_id"] = extract_row_id
            extract_row_id += 1
            rows.append(row)

    for row in rows:
        if row["ticker"] == "HST" and row["quarter_index"] == 8:
            row["total_equity"] = None
        if row["ticker"] == "PND" and row["quarter_index"] == 7:
            row["operating_cash_flow"] = None
        if row["ticker"] == "KMF" and row["quarter_index"] == 6:
            row["operating_income"] = money(row["revenue"] + Decimal("25"))

    source = next(row for row in rows if row["ticker"] == "FLD" and row["quarter_index"] == 1)
    duplicate = dict(source)
    duplicate["extract_row_id"] = extract_row_id
    duplicate["revenue"] = money("999.99")
    duplicate["operating_income"] = money("80")
    duplicate["net_income"] = money("56")
    rows.append(duplicate)
    return rows


def failure_reason(row: dict, line_rank: int) -> tuple[str, str] | None:
    if line_rank > 1:
        return (
            "Duplicate company-quarter",
            "Extra extract row. The earliest row for this company and quarter can still pass the other checks.",
        )
    if row["revenue"] is None:
        return ("Required amounts present", "Revenue is null")
    if row["operating_income"] is None:
        return ("Required amounts present", "Operating income is null")
    if row["net_income"] is None:
        return ("Required amounts present", "Net income is null")
    if row["total_debt"] is None:
        return ("Required amounts present", "Total debt is null")
    if row["total_equity"] is None:
        return ("Required amounts present", "Total equity is null")
    if row["operating_cash_flow"] is None:
        return ("Required amounts present", "Operating cash flow is null")
    if row["total_equity"] == 0:
        return ("Equity is not zero", "Total equity is zero, so debt-to-equity is undefined")
    if row["total_debt"] < 0:
        return ("Debt is zero or positive", "Total debt is negative")
    if row["operating_income"] > row["revenue"]:
        return ("Operating income within revenue", "Operating income is greater than revenue")
    return None


def publish(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["ticker"], row["fiscal_year"], row["fiscal_quarter"])
        grouped.setdefault(key, []).append(row)
    certified = []
    exceptions = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: item["extract_row_id"])
        for rank, row in enumerate(ordered, start=1):
            reason = failure_reason(row, rank)
            if reason is None:
                certified.append(row)
            else:
                check_name, detail = reason
                exceptions.append({**row, "check_name": check_name, "detail": detail, "blocking": True})
    return certified, exceptions


def company_map() -> dict[str, tuple[str, str]]:
    return {ticker: (name, sector) for ticker, name, sector in COMPANIES}


def quarter_label(index: int) -> str:
    return next(label for _y, _q, label, idx in QUARTERS if idx == index)


def with_ratios(rows: list[dict]) -> list[dict]:
    names = company_map()
    rated = []
    for row in rows:
        name, sector = names[row["ticker"]]
        rated.append(
            {
                **row,
                "company_name": name,
                "sector": sector,
                "quarter_label": quarter_label(row["quarter_index"]),
                "operating_margin": ratio(row["operating_income"], row["revenue"]),
                "debt_to_equity": ratio(row["total_debt"], row["total_equity"]),
            }
        )
    return rated


def analyze(certified: list[dict]) -> dict:
    rated = with_ratios(certified)
    by_key = {(row["ticker"], row["quarter_index"]): row for row in rated}
    latest = [row for row in rated if row["quarter_index"] == 8]
    retail_above_2 = sorted(
        [row for row in latest if row["sector"] == "Retail" and row["debt_to_equity"] > 2],
        key=lambda row: row["debt_to_equity"],
        reverse=True,
    )
    watchlist = []
    for row in retail_above_2:
        prior = by_key.get((row["ticker"], 6))
        if prior is None:
            continue
        if row["debt_to_equity"] > prior["debt_to_equity"] and row["operating_cash_flow"] < prior["operating_cash_flow"]:
            watchlist.append(
                {
                    **row,
                    "debt_to_equity_prior": prior["debt_to_equity"],
                    "operating_cash_flow_prior": prior["operating_cash_flow"],
                }
            )
    watch_tickers = {row["ticker"] for row in watchlist}
    for row in retail_above_2:
        row["on_watchlist"] = "Yes" if row["ticker"] in watch_tickers else "No"

    margin_rows = []
    for row in latest:
        prior = by_key.get((row["ticker"], 4))
        if prior is None:
            continue
        change = ((row["operating_margin"] - prior["operating_margin"]) * 100).quantize(Q, rounding=ROUND_HALF_UP)
        margin_rows.append(
            {
                **row,
                "margin_prior": prior["operating_margin"],
                "margin_change_pp": change,
            }
        )
    margin_rows.sort(key=lambda item: item["margin_change_pp"])

    sector_totals: dict[str, Decimal] = {}
    for row in latest:
        sector_totals[row["sector"]] = sector_totals.get(row["sector"], Decimal("0")) + row["revenue"]
    sectors = [
        {"sector": sector, "revenue": total}
        for sector, total in sorted(sector_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    return {
        "latest": latest,
        "retail_above_2": retail_above_2,
        "watchlist": watchlist,
        "margin_rows": margin_rows,
        "sectors": sectors,
        "latest_revenue": sum(row["revenue"] for row in latest),
    }


def expect(certified, exceptions, findings) -> None:
    assert len(certified) == 93, len(certified)
    assert len(exceptions) == 4, len(exceptions)
    found = {(row["ticker"], row["quarter_index"], row["detail"]) for row in exceptions}
    assert ("HST", 8, "Total equity is null") in found
    assert ("PND", 7, "Operating cash flow is null") in found
    assert ("KMF", 6, "Operating income is greater than revenue") in found
    assert any(row["ticker"] == "FLD" and row["quarter_index"] == 1 and row["check_name"].startswith("Duplicate") for row in exceptions)
    assert [row["ticker"] for row in findings["retail_above_2"]] == ["NLN", "HBR", "MGR"] or sorted(
        row["ticker"] for row in findings["retail_above_2"]
    ) == ["HBR", "MGR", "NLN"]
    assert {row["ticker"] for row in findings["watchlist"]} == {"NLN", "HBR"}
    breaches = [row["ticker"] for row in findings["margin_rows"] if row["margin_change_pp"] <= Decimal("-3")]
    assert breaches == ["LMS", "RDG"], breaches
    assert findings["retail_above_2"][0]["debt_to_equity"] == Decimal("2.4800")


def sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return "N'" + value.replace("'", "''") + "'"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def write_seed(rows: list[dict]) -> None:
    company_sql = []
    for ticker, name, sector in COMPANIES:
        company_sql.append(
            f"    ({sql_literal(ticker)}, {sql_literal(name)}, {sql_literal(sector)})"
        )
    value_rows = []
    for row in rows:
        value_rows.append(
            "    ("
            + ", ".join(
                [
                    sql_literal(row["extract_row_id"]),
                    sql_literal(row["ticker"]),
                    sql_literal(row["fiscal_year"]),
                    sql_literal(row["fiscal_quarter"]),
                    sql_literal(row["revenue"]),
                    sql_literal(row["operating_income"]),
                    sql_literal(row["net_income"]),
                    sql_literal(row["total_debt"]),
                    sql_literal(row["total_equity"]),
                    sql_literal(row["operating_cash_flow"]),
                ]
            )
            + ")"
        )
    text = f"""/*
    Fictional extract for 12 companies, 2024 Q1 through 2025 Q4.
    Amounts are USD millions. Four rows are planted defects.
    Run sql/04 and sql/05 after this file.
*/

USE FinancialCockpit;
GO

DELETE FROM dw.fact_financials;
DELETE FROM dw.quality_exception;
DELETE FROM dw.quality_check;
DELETE FROM dw.refresh_log;
DELETE FROM dw.dim_company;
DELETE FROM stg.financial_extract;
DELETE FROM stg.company;
GO

INSERT INTO stg.company (ticker, company_name, sector)
VALUES
{",\n".join(company_sql)};
GO

INSERT INTO stg.financial_extract
    (extract_row_id, ticker, fiscal_year, fiscal_quarter,
     revenue, operating_income, net_income, total_debt, total_equity, operating_cash_flow)
VALUES
{",\n".join(value_rows)};
GO
"""
    (SQL / "02_seed.sql").write_text(text, encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: "" if row.get(key) is None else row.get(key)
                    for key in fieldnames
                }
            )


def export_tables(extract, certified, exceptions, findings) -> None:
    names = company_map()
    write_csv(
        DATA / "company.csv",
        ["ticker", "company_name", "sector"],
        [{"ticker": t, "company_name": n, "sector": s} for t, n, s in COMPANIES],
    )
    write_csv(
        DATA / "financial_extract.csv",
        [
            "extract_row_id", "ticker", "fiscal_year", "fiscal_quarter",
            "revenue", "operating_income", "net_income",
            "total_debt", "total_equity", "operating_cash_flow",
        ],
        extract,
    )
    write_csv(
        DATA / "fact_financials.csv",
        [
            "ticker", "fiscal_year", "fiscal_quarter",
            "revenue", "operating_income", "net_income",
            "total_debt", "total_equity", "operating_cash_flow",
        ],
        certified,
    )
    exception_rows = []
    for row in exceptions:
        name, sector = names[row["ticker"]]
        exception_rows.append(
            {
                "check_name": row["check_name"],
                "ticker": row["ticker"],
                "company_name": name,
                "sector": sector,
                "quarter_label": quarter_label(row["quarter_index"]),
                "detail": row["detail"],
                "blocking": "Yes",
            }
        )
    write_csv(
        DATA / "quality_exception.csv",
        ["check_name", "ticker", "company_name", "sector", "quarter_label", "detail", "blocking"],
        exception_rows,
    )
    write_csv(
        DATA / "sector_revenue.csv",
        ["sector", "revenue"],
        findings["sectors"],
    )
    write_csv(
        DATA / "margin_change.csv",
        ["company_name", "sector", "operating_margin_prior_year", "operating_margin_latest", "margin_change_pp"],
        [
            {
                "company_name": row["company_name"],
                "sector": row["sector"],
                "operating_margin_prior_year": row["margin_prior"],
                "operating_margin_latest": row["operating_margin"],
                "margin_change_pp": row["margin_change_pp"],
            }
            for row in findings["margin_rows"]
        ],
    )
    write_csv(
        DATA / "retail_above_2.csv",
        ["company_name", "ticker", "debt_to_equity", "operating_cash_flow", "on_watchlist"],
        findings["retail_above_2"],
    )
    write_csv(
        DATA / "leverage_screen.csv",
        [
            "company_name", "debt_to_equity", "debt_to_equity_prior",
            "operating_cash_flow", "operating_cash_flow_prior",
        ],
        findings["watchlist"],
    )


def font(size: int, bold: bool = False):
    path = r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"
    return ImageFont.truetype(path, size)


def mono(size: int):
    return ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", size)


def new_page() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1920, 1080), PAPER)
    return image, ImageDraw.Draw(image)


def header(draw, title: str, subtitle: str) -> None:
    draw.rectangle((0, 0, 1920, 132), fill=NAVY)
    draw.text((56, 28), title, font=font(40, True), fill="white")
    draw.text((56, 82), subtitle, font=font(20), fill="#D5DDD8")
    draw.rounded_rectangle((1560, 36, 1864, 96), radius=8, fill=RED)
    draw.text((1592, 52), "Gate blocked", font=font(24, True), fill="white")


def footer(draw, source: str) -> None:
    draw.text((56, 1028), source, font=font(16), fill=MUTED)


def card(draw, box) -> None:
    draw.rectangle(box, fill=CARD, outline=LINE)


def draw_table(draw, origin, widths, headers, rows, tones=None) -> int:
    x, y = origin
    height = 42
    draw.rectangle((x, y, x + sum(widths), y + height), fill=NAVY)
    cursor = x
    for index, title in enumerate(headers):
        draw.text((cursor + 12, y + 10), title, font=font(16, True), fill="white")
        cursor += widths[index]
    y += height
    for r_index, row in enumerate(rows):
        fill = "#F7F4EE" if r_index % 2 else CARD
        draw.rectangle((x, y, x + sum(widths), y + 40), fill=fill, outline=LINE)
        if tones and tones[r_index]:
            draw.rectangle((x, y, x + 6, y + 40), fill=tones[r_index])
        cursor = x
        for index, value in enumerate(row):
            draw.text((cursor + 14, y + 10), str(value), font=font(16), fill=INK)
            cursor += widths[index]
        y += 40
    return y


def page_sector(findings) -> Image.Image:
    image, draw = new_page()
    header(draw, "Sector revenue", "Certified revenue, 2025 Q4. USD millions.")
    draw.text((56, 160), usd(findings["latest_revenue"]), font=font(48, True), fill=INK)
    draw.text((56, 220), "Latest-quarter revenue across certified companies", font=font(20), fill=MUTED)
    draw.text(
        (56, 260),
        "Harbor Steel is absent. Its 2025 Q4 equity is null, so the row never reached the certified model.",
        font=font(18),
        fill=MUTED,
    )
    sectors = findings["sectors"]
    left, top, width, height = 56, 340, 1000, 620
    card(draw, (left, top, left + width, top + height))
    max_value = max(item["revenue"] for item in sectors)
    bar_top = top + 50
    for item in sectors:
        draw.text((left + 24, bar_top), item["sector"], font=font(20, True), fill=INK)
        bar_width = int(720 * float(item["revenue"] / max_value))
        draw.rectangle((left + 220, bar_top + 4, left + 220 + bar_width, bar_top + 32), fill=SECTOR_COLOR[item["sector"]])
        draw.text((left + 236 + bar_width, bar_top + 4), usd(item["revenue"]), font=font(18), fill=INK)
        bar_top += 120
    rows = [[item["sector"], usd(item["revenue"])] for item in sectors]
    draw_table(draw, (1120, 340), [280, 280], ["Sector", "Revenue"], rows)
    footer(draw, "Source: dw.vw_sector_revenue  ·  2025 Q4  ·  certified rows only")
    return image


def page_margin(findings) -> Image.Image:
    image, draw = new_page()
    header(draw, "Operating margin change", "2025 Q4 versus 2024 Q4, in percentage points.")
    draw.text(
        (56, 156),
        "Lumen Software and Ridge Tools fell more than 3 points. Harbor Steel has no certified 2025 Q4 row, so it is not on this page.",
        font=font(18),
        fill=MUTED,
    )
    rows = findings["margin_rows"]
    values = [float(row["margin_change_pp"]) for row in rows]
    low = min(min(values), 0) - 1
    high = max(max(values), 0) + 1
    span = high - low
    left, right = 420, 1680
    zero = left + int((0 - low) / span * (right - left))
    y = 220
    draw.line((zero, 210, zero, 990), fill="#B7B1A6", width=2)
    for row in rows:
        value = float(row["margin_change_pp"])
        x_value = left + int((value - low) / span * (right - left))
        color = RED if row["margin_change_pp"] <= Decimal("-3") else TEAL
        y0, y1 = y, y + 28
        draw.rectangle((min(zero, x_value), y0, max(zero, x_value), y1), fill=color)
        draw.text((56, y - 2), row["company_name"], font=font(18), fill=INK)
        label_x = x_value + 8 if value >= 0 else x_value - 90
        draw.text((label_x, y - 2), pp(row["margin_change_pp"]), font=font(16), fill=INK)
        y += 68
    footer(draw, "Source: dw.vw_margin_change  ·  operating income / revenue, 2025 Q4 minus 2024 Q4")
    return image


def page_question(findings) -> Image.Image:
    image, draw = new_page()
    header(draw, "Ask a question", "Read-only SQL against the certified view. Latest quarter, 2025 Q4.")
    card(draw, (56, 164, 1864, 280))
    draw.text((80, 184), "Question", font=font(16, True), fill=MUTED)
    draw.text((80, 214), "which retail companies have debt-to-equity above 2?", font=font(28, True), fill=INK)
    card(draw, (56, 304, 1864, 470))
    draw.text((80, 320), "SQL  ·  dw.vw_retail_debt_to_equity", font=font(16, True), fill=MUTED)
    sql = (
        "SELECT company_name, debt_to_equity, operating_cash_flow\n"
        "FROM dw.vw_ratios\n"
        "WHERE sector = N'Retail' AND is_latest = 1 AND debt_to_equity > 2\n"
        "ORDER BY debt_to_equity DESC;"
    )
    draw.multiline_text((80, 352), sql, font=mono(20), fill=INK, spacing=6)
    table_rows = []
    tones = []
    for row in findings["retail_above_2"]:
        table_rows.append(
            [
                row["company_name"],
                de_text(row["debt_to_equity"]),
                usd(row["operating_cash_flow"]),
                row["on_watchlist"],
            ]
        )
        tones.append(TEAL if row["on_watchlist"] == "Yes" else AMBER)
    draw_table(
        draw,
        (56, 510),
        [460, 320, 420, 360],
        ["Company", "Debt to equity", "Operating cash flow", "Cash flow also fell"],
        table_rows,
        tones,
    )
    draw.text(
        (56, 760),
        "Metro Grocers is above 2, and its operating cash flow rose from $18.00m to $27.00m. It answers this question and stays off the leverage watchlist.",
        font=font(20),
        fill=INK,
    )
    footer(draw, "Source: dw.vw_retail_debt_to_equity  ·  debt and equity are the 2025 Q4 balances, not an eight-quarter sum")
    return image


def page_watchlist(findings) -> Image.Image:
    image, draw = new_page()
    header(draw, "Retail leverage watchlist", "Debt-to-equity rose above 2 and operating cash flow fell from 2025 Q2 to 2025 Q4.")
    rows = []
    for row in sorted(findings["watchlist"], key=lambda item: item["debt_to_equity"], reverse=True):
        rows.append(
            [
                row["company_name"],
                de_text(row["debt_to_equity_prior"]),
                de_text(row["debt_to_equity"]),
                usd(row["operating_cash_flow_prior"]),
                usd(row["operating_cash_flow"]),
            ]
        )
    draw_table(
        draw,
        (56, 200),
        [360, 300, 300, 420, 420],
        ["Company", "D/E, 2025 Q2", "D/E, 2025 Q4", "Cash flow, 2025 Q2", "Cash flow, 2025 Q4"],
        rows,
        [RED, RED],
    )
    draw.text(
        (56, 420),
        "Northline Stores moved from 1.90 to 2.48 while cash flow fell from $38.00m to $22.00m.",
        font=font(22),
        fill=INK,
    )
    draw.text(
        (56, 460),
        "Harbor Mart moved from 1.75 to 2.31 while cash flow fell from $51.00m to $36.00m.",
        font=font(22),
        fill=INK,
    )
    footer(draw, "Source: dw.vw_retail_leverage_screen  ·  certified rows only")
    return image


def page_exceptions(exceptions) -> Image.Image:
    image, draw = new_page()
    header(draw, "Validation exceptions", "dw.usp_validate_and_publish held these extract rows out of the certified model.")
    names = company_map()
    checks = [
        ["Duplicate company-quarter", "Fail", "1 extra extract row"],
        ["Required amounts present", "Fail", "2 rows missing an amount"],
        ["Operating income within revenue", "Fail", "1 row above revenue"],
        ["Equity is not zero", "Pass", "0 rows"],
        ["Debt is zero or positive", "Pass", "0 rows"],
        ["Certified rows tie to the extract", "Pass", "Raw 97, certified 93, exceptions 4"],
    ]
    tones = [RED, RED, RED, TEAL, TEAL, TEAL]
    draw_table(
        draw,
        (56, 168),
        [560, 160, 700],
        ["Check", "Result", "Observed"],
        checks,
        tones,
    )
    detail = []
    detail_tones = []
    order = {"HST": 0, "PND": 1, "KMF": 2, "FLD": 3}
    for row in sorted(exceptions, key=lambda item: order[item["ticker"]]):
        name, _sector = names[row["ticker"]]
        detail.append([row["check_name"], name, quarter_label(row["quarter_index"]), row["detail"]])
        detail_tones.append(RED)
    draw_table(
        draw,
        (56, 520),
        [420, 300, 180, 900],
        ["Check", "Company", "Quarter", "Detail"],
        detail,
        detail_tones,
    )
    footer(draw, "Source: dw.quality_check and dw.quality_exception  ·  gate status Blocked  ·  8 Oct 2026 publish preview")
    return image


def page_one(findings, exceptions) -> Image.Image:
    image, draw = new_page()
    header(draw, "Quarterly briefing", "One page for Q4 2025. Certified preview while the gate is blocked.")
    cards = [
        (usd(findings["latest_revenue"]), "Certified revenue"),
        (str(len(findings["watchlist"])), "Leverage watchlist"),
        (str(sum(1 for row in findings["margin_rows"] if row["margin_change_pp"] <= Decimal("-3"))), "Margin breaches"),
        (str(len(exceptions)), "Rows held out"),
    ]
    x = 56
    for value, label in cards:
        card(draw, (x, 164, x + 420, 300))
        draw.text((x + 24, 184), value, font=font(36, True), fill=INK)
        draw.text((x + 24, 240), label, font=font(18), fill=MUTED)
        x += 452
    draw.text((56, 340), "Sector revenue, 2025 Q4", font=font(22, True), fill=INK)
    sector_rows = [[item["sector"], usd(item["revenue"])] for item in findings["sectors"]]
    draw_table(draw, (56, 384), [280, 240], ["Sector", "Revenue"], sector_rows)
    draw.text((760, 340), "Who needs a look", font=font(22, True), fill=INK)
    look = [
        ["Northline Stores", "D/E 2.48", "Cash flow down"],
        ["Harbor Mart", "D/E 2.31", "Cash flow down"],
        ["Lumen Software", "-6.5 pp", "Margin"],
        ["Ridge Tools", "-3.8 pp", "Margin"],
    ]
    draw_table(draw, (760, 384), [360, 220, 280], ["Company", "Signal", "Topic"], look, [RED, RED, AMBER, AMBER])
    draw.text(
        (56, 760),
        "Do not publish this preview to the service workspace. Four blocking checks failed, including a missing equity balance",
        font=font(20),
        fill=INK,
    )
    draw.text((56, 796), "that removes Harbor Steel from the quarter. Fix the extract and rerun dw.usp_validate_and_publish.", font=font(20), fill=INK)
    footer(draw, "Source: dw.vw_sector_revenue, dw.vw_retail_leverage_screen, dw.vw_margin_change, dw.quality_exception")
    return image


def page_title() -> Image.Image:
    image, draw = new_page()
    draw.rectangle((0, 0, 1920, 1080), fill=NAVY)
    draw.text((80, 360), "Financial BI Cockpit", font=font(64, True), fill="white")
    draw.text((80, 460), "Q4 2025 certified preview", font=font(32), fill="#D5DDD8")
    draw.text((80, 540), "Validation gate: Blocked    ·    4 exceptions    ·    93 certified rows", font=font(24), fill="#F2C4C8")
    return image


def save_pages(pages: dict[str, Image.Image]) -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    for name, image in pages.items():
        image.save(IMAGES / name, "PNG")


def write_pdf(findings, exceptions) -> None:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.set_fill_color(30, 42, 56)
    pdf.rect(0, 0, 297, 24, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(10, 6)
    pdf.cell(0, 8, "Quarterly briefing  -  Q4 2025")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(210, 7)
    pdf.cell(70, 8, "Gate blocked", align="R")
    pdf.set_text_color(28, 25, 23)
    pdf.set_xy(10, 30)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        270,
        6,
        "Certified preview. Power BI should not refresh the published report until dw.usp_validate_and_publish returns Passed.",
    )
    blocks = [
        (usd(findings["latest_revenue"]), "Certified revenue"),
        (str(len(findings["watchlist"])), "Leverage watchlist"),
        ("2", "Margin breaches"),
        (str(len(exceptions)), "Rows held out"),
    ]
    x = 10
    for value, label in blocks:
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(228, 223, 214)
        pdf.rect(x, 48, 64, 22, "DF")
        pdf.set_xy(x + 3, 50)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(58, 8, value)
        pdf.set_xy(x + 3, 58)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(58, 6, label)
        x += 70
    pdf.set_xy(10, 78)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Sector revenue, 2025 Q4")
    pdf.set_font("Helvetica", "", 11)
    y = 88
    for item in findings["sectors"]:
        pdf.set_xy(10, y)
        pdf.cell(50, 7, item["sector"])
        pdf.cell(40, 7, usd(item["revenue"]))
        y += 7
    pdf.set_xy(120, 78)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Who needs a look")
    pdf.set_font("Helvetica", "", 11)
    lines = [
        "Northline Stores    D/E 2.48    operating cash flow down",
        "Harbor Mart         D/E 2.31    operating cash flow down",
        "Lumen Software      margin -6.5 pp versus 2024 Q4",
        "Ridge Tools         margin -3.8 pp versus 2024 Q4",
        "Harbor Steel        held out, 2025 Q4 equity is null",
    ]
    y = 88
    for line in lines:
        pdf.set_xy(120, y)
        pdf.cell(160, 7, line)
        y += 7
    pdf.set_xy(10, 150)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        270,
        5,
        "Question answered by dw.vw_retail_debt_to_equity: which retail companies have debt-to-equity above 2? "
        "Northline Stores 2.48, Harbor Mart 2.31, Metro Grocers 2.42. Metro's cash flow rose, so it is not on the watchlist. "
        "Source: certified fact table after dw.usp_validate_and_publish.",
    )
    pdf.output(str(DOCS / "quarterly-briefing-2025-q4.pdf"))


def write_gif(pages: list[Image.Image]) -> None:
    frames = [page.resize((1280, 720), Image.Resampling.LANCZOS).convert("P", palette=Image.Palette.ADAPTIVE) for page in pages]
    frames[0].save(
        DOCS / "demo.gif",
        save_all=True,
        append_images=frames[1:],
        duration=2500,
        loop=0,
        optimize=True,
    )


def write_video(frames: list[tuple[Image.Image, float]]) -> None:
    import imageio_ffmpeg

    clip = DOCS / "_clip.txt"
    lines = ["ffconcat version 1.0"]
    temp_names = []
    for index, (image, seconds) in enumerate(frames):
        name = f"_frame_{index}.png"
        image.save(DOCS / name)
        temp_names.append(name)
        lines.append(f"file '{name}'")
        lines.append(f"duration {seconds:.3f}")
    lines.append(f"file '{temp_names[-1]}'")
    clip.write_text("\n".join(lines), encoding="utf-8")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(clip),
            "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-movflags", "+faststart",
            str(DOCS / "demo.mp4"),
        ],
        check=True,
        cwd=DOCS,
        capture_output=True,
    )
    clip.unlink(missing_ok=True)
    for name in temp_names:
        (DOCS / name).unlink(missing_ok=True)


def dec_float(value: Decimal) -> float:
    return float(value)


def build_pbix(certified, exceptions, findings) -> None:
    from pbix_mcp.builder import PBIXBuilder

    names = company_map()
    builder = PBIXBuilder()
    builder.add_table(
        "Company",
        [
            {"name": "Ticker", "data_type": "String"},
            {"name": "Company", "data_type": "String"},
            {"name": "Sector", "data_type": "String"},
        ],
        rows=[{"Ticker": t, "Company": n, "Sector": s} for t, n, s in COMPANIES],
    )
    builder.add_table(
        "Period",
        [
            {"name": "Quarter Index", "data_type": "Int64"},
            {"name": "Quarter", "data_type": "String"},
            {"name": "Year", "data_type": "Int64"},
            {"name": "Quarter Number", "data_type": "Int64"},
            {"name": "Is Latest", "data_type": "Int64"},
        ],
        rows=[
            {
                "Quarter Index": index,
                "Quarter": label,
                "Year": year,
                "Quarter Number": quarter,
                "Is Latest": 1 if index == 8 else 0,
            }
            for year, quarter, label, index in QUARTERS
        ],
    )
    builder.add_table(
        "Financials",
        [
            {"name": "Ticker", "data_type": "String"},
            {"name": "Quarter Index", "data_type": "Int64"},
            {"name": "Revenue", "data_type": "Double"},
            {"name": "Operating Income", "data_type": "Double"},
            {"name": "Net Income", "data_type": "Double"},
            {"name": "Total Debt", "data_type": "Double"},
            {"name": "Total Equity", "data_type": "Double"},
            {"name": "Operating Cash Flow", "data_type": "Double"},
        ],
        rows=[
            {
                "Ticker": row["ticker"],
                "Quarter Index": row["quarter_index"],
                "Revenue": dec_float(row["revenue"]),
                "Operating Income": dec_float(row["operating_income"]),
                "Net Income": dec_float(row["net_income"]),
                "Total Debt": dec_float(row["total_debt"]),
                "Total Equity": dec_float(row["total_equity"]),
                "Operating Cash Flow": dec_float(row["operating_cash_flow"]),
            }
            for row in certified
        ],
    )
    builder.add_relationship("Financials", "Ticker", "Company", "Ticker")
    builder.add_relationship("Financials", "Quarter Index", "Period", "Quarter Index")
    builder.add_measure(
        "Financials",
        "Total Revenue",
        "SUM ( Financials[Revenue] )",
        "Quarterly revenue in USD millions. Safe to sum across quarters.",
        format_string="#,0.00",
    )
    builder.add_measure(
        "Financials",
        "Revenue Latest Quarter",
        "CALCULATE ( [Total Revenue], Period[Is Latest] = 1 )",
        "Revenue for 2025 Q4 only.",
        format_string="#,0.00",
    )
    builder.add_measure(
        "Financials",
        "Debt to Equity",
        "DIVIDE ( CALCULATE ( SUM ( Financials[Total Debt] ), Period[Is Latest] = 1 ), CALCULATE ( SUM ( Financials[Total Equity] ), Period[Is Latest] = 1 ) )",
        "Latest-quarter debt divided by latest-quarter equity. These are balances and are not summed across quarters.",
        format_string="0.00",
    )
    builder.add_measure(
        "Financials",
        "Operating Margin",
        "DIVIDE ( CALCULATE ( SUM ( Financials[Operating Income] ), Period[Is Latest] = 1 ), [Revenue Latest Quarter] )",
        "Latest-quarter operating income divided by latest-quarter revenue.",
        format_string="0.0%",
    )

    builder.add_table(
        "SectorRevenue",
        [
            {"name": "Sector", "data_type": "String"},
            {"name": "Revenue", "data_type": "Double"},
        ],
        rows=[{"Sector": item["sector"], "Revenue": dec_float(item["revenue"])} for item in findings["sectors"]],
    )
    builder.add_measure("SectorRevenue", "Sector Revenue", "SUM ( SectorRevenue[Revenue] )", format_string="#,0.00")

    builder.add_table(
        "MarginChange",
        [
            {"name": "Company", "data_type": "String"},
            {"name": "Sector", "data_type": "String"},
            {"name": "Margin Change PP", "data_type": "Double"},
        ],
        rows=[
            {
                "Company": row["company_name"],
                "Sector": row["sector"],
                "Margin Change PP": dec_float(row["margin_change_pp"]),
            }
            for row in findings["margin_rows"]
        ],
    )
    builder.add_measure(
        "MarginChange",
        "Margin Change",
        "SUM ( MarginChange[Margin Change PP] )",
        "Percentage-point change in operating margin, 2025 Q4 versus 2024 Q4.",
        format_string="0.00",
    )

    builder.add_table(
        "RetailAbove2",
        [
            {"name": "Company", "data_type": "String"},
            {"name": "Sector", "data_type": "String"},
            {"name": "Debt to Equity", "data_type": "Double"},
            {"name": "Operating Cash Flow", "data_type": "Double"},
            {"name": "Cash Flow Also Fell", "data_type": "String"},
        ],
        rows=[
            {
                "Company": row["company_name"],
                "Sector": "Retail",
                "Debt to Equity": dec_float(row["debt_to_equity"]),
                "Operating Cash Flow": dec_float(row["operating_cash_flow"]),
                "Cash Flow Also Fell": row["on_watchlist"],
            }
            for row in findings["retail_above_2"]
        ],
    )
    builder.add_table(
        "LeverageScreen",
        [
            {"name": "Company", "data_type": "String"},
            {"name": "DE 2025 Q2", "data_type": "Double"},
            {"name": "DE 2025 Q4", "data_type": "Double"},
            {"name": "Cash Flow 2025 Q2", "data_type": "Double"},
            {"name": "Cash Flow 2025 Q4", "data_type": "Double"},
        ],
        rows=[
            {
                "Company": row["company_name"],
                "DE 2025 Q2": dec_float(row["debt_to_equity_prior"]),
                "DE 2025 Q4": dec_float(row["debt_to_equity"]),
                "Cash Flow 2025 Q2": dec_float(row["operating_cash_flow_prior"]),
                "Cash Flow 2025 Q4": dec_float(row["operating_cash_flow"]),
            }
            for row in findings["watchlist"]
        ],
    )
    builder.add_table(
        "QualityException",
        [
            {"name": "Check", "data_type": "String"},
            {"name": "Company", "data_type": "String"},
            {"name": "Quarter", "data_type": "String"},
            {"name": "Detail", "data_type": "String"},
        ],
        rows=[
            {
                "Check": row["check_name"],
                "Company": names[row["ticker"]][0],
                "Quarter": quarter_label(row["quarter_index"]),
                "Detail": row["detail"],
            }
            for row in exceptions
        ],
    )

    def table(name, columns, width=1200, height=640):
        return {
            "type": "tableEx",
            "name": name,
            "x": 40,
            "y": 30,
            "width": width,
            "height": height,
            "config": {"columns": [{"table": table_name, "column": column} for table_name, column in columns]},
        }

    builder.add_page(
        "Sector revenue",
        visuals=[
            {
                "type": "clusteredBarChart",
                "name": "sector_bars",
                "x": 40,
                "y": 30,
                "width": 1200,
                "height": 640,
                "config": {
                    "category": {"table": "SectorRevenue", "column": "Sector"},
                    "measure": "Sector Revenue",
                    "sort": {"by": "Sector Revenue", "direction": "desc"},
                },
            }
        ],
    )
    builder.add_page(
        "Margin change",
        visuals=[
            {
                "type": "clusteredBarChart",
                "name": "margin_bars",
                "x": 40,
                "y": 30,
                "width": 1200,
                "height": 640,
                "config": {
                    "category": {"table": "MarginChange", "column": "Company"},
                    "measure": "Margin Change",
                    "sort": {"by": "Margin Change", "direction": "asc"},
                },
            }
        ],
    )
    builder.add_page(
        "Retail debt to equity",
        visuals=[
            table(
                "retail_answer",
                [
                    ("RetailAbove2", "Company"),
                    ("RetailAbove2", "Debt to Equity"),
                    ("RetailAbove2", "Operating Cash Flow"),
                    ("RetailAbove2", "Cash Flow Also Fell"),
                ],
            )
        ],
    )
    builder.add_page(
        "Leverage watchlist",
        visuals=[
            table(
                "watchlist",
                [
                    ("LeverageScreen", "Company"),
                    ("LeverageScreen", "DE 2025 Q2"),
                    ("LeverageScreen", "DE 2025 Q4"),
                    ("LeverageScreen", "Cash Flow 2025 Q2"),
                    ("LeverageScreen", "Cash Flow 2025 Q4"),
                ],
            )
        ],
    )
    builder.add_page(
        "Validation exceptions",
        visuals=[
            table(
                "exceptions",
                [
                    ("QualityException", "Check"),
                    ("QualityException", "Company"),
                    ("QualityException", "Quarter"),
                    ("QualityException", "Detail"),
                ],
            )
        ],
    )
    builder.save(str(ROOT / "FinancialCockpit.pbix"))


def main() -> None:
    extract = build_extract()
    certified, exceptions = publish(extract)
    findings = analyze(certified)
    expect(certified, exceptions, findings)
    write_seed(extract)
    export_tables(extract, certified, exceptions, findings)

    pages = {
        "sector-revenue.png": page_sector(findings),
        "margin-change.png": page_margin(findings),
        "retail-question.png": page_question(findings),
        "leverage-watchlist.png": page_watchlist(findings),
        "validation-exceptions.png": page_exceptions(exceptions),
        "quarterly-briefing.png": page_one(findings, exceptions),
    }
    save_pages(pages)
    write_pdf(findings, exceptions)
    write_gif(
        [
            pages["sector-revenue.png"],
            pages["retail-question.png"],
            pages["validation-exceptions.png"],
            pages["quarterly-briefing.png"],
        ]
    )
    write_video(
        [
            (page_title(), 4),
            (pages["sector-revenue.png"], 6),
            (pages["retail-question.png"], 11),
            (pages["validation-exceptions.png"], 6),
            (pages["quarterly-briefing.png"], 3),
        ]
    )
    build_pbix(certified, exceptions, findings)

    summary = {
        "raw_rows": len(extract),
        "certified_rows": len(certified),
        "exception_rows": len(exceptions),
        "latest_revenue": str(findings["latest_revenue"]),
        "sectors": [{**item, "revenue": str(item["revenue"])} for item in findings["sectors"]],
        "retail_above_2": [
            {
                "company": row["company_name"],
                "de": str(row["debt_to_equity"]),
                "ocf": str(row["operating_cash_flow"]),
                "watchlist": row["on_watchlist"],
            }
            for row in findings["retail_above_2"]
        ],
        "watchlist": [row["company_name"] for row in findings["watchlist"]],
        "margin_breaches": [
            {"company": row["company_name"], "pp": str(row["margin_change_pp"])}
            for row in findings["margin_rows"]
            if row["margin_change_pp"] <= Decimal("-3")
        ],
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
