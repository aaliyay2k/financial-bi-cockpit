/*
    Ratio definitions live here, not in the report.

    Debt-to-equity uses the quarter's own debt and equity.
    Do not sum debt or equity across quarters. They are balances.
    Operating margin is operating income divided by revenue.
*/

USE FinancialCockpit;
GO

CREATE OR ALTER VIEW dw.vw_ratios
AS
SELECT
    c.ticker,
    c.company_name,
    c.sector,
    p.fiscal_year,
    p.fiscal_quarter,
    p.quarter_label,
    p.quarter_index,
    p.is_latest,
    f.revenue,
    f.operating_income,
    f.net_income,
    f.total_debt,
    f.total_equity,
    f.operating_cash_flow,
    CAST(f.operating_income / NULLIF(f.revenue, 0) AS decimal(12, 4)) AS operating_margin,
    CAST(f.total_debt / NULLIF(f.total_equity, 0) AS decimal(12, 4)) AS debt_to_equity
FROM dw.fact_financials AS f
JOIN dw.dim_company AS c
    ON c.ticker = f.ticker
JOIN dw.dim_period AS p
    ON p.fiscal_year = f.fiscal_year
   AND p.fiscal_quarter = f.fiscal_quarter;
GO

/*
    Answers: which retail companies have debt-to-equity above 2?
    Latest quarter only. Certified rows only.
*/
CREATE OR ALTER VIEW dw.vw_retail_debt_to_equity
AS
SELECT
    ticker,
    company_name,
    quarter_label,
    debt_to_equity,
    operating_cash_flow
FROM dw.vw_ratios
WHERE sector = N'Retail'
  AND is_latest = 1
  AND debt_to_equity > 2;
GO

/*
    Stricter screen used by the watchlist page.
    Over the three quarters ending in the latest quarter
    (2025 Q2 through 2025 Q4):
      - latest debt-to-equity is above 2
      - latest debt-to-equity is higher than 2025 Q2
      - latest operating cash flow is lower than 2025 Q2
*/
CREATE OR ALTER VIEW dw.vw_retail_leverage_screen
AS
SELECT
    cur.ticker,
    cur.company_name,
    cur.quarter_label,
    cur.debt_to_equity,
    prior.debt_to_equity AS debt_to_equity_prior,
    cur.operating_cash_flow,
    prior.operating_cash_flow AS operating_cash_flow_prior
FROM dw.vw_ratios AS cur
JOIN dw.vw_ratios AS prior
    ON prior.ticker = cur.ticker
   AND prior.quarter_index = cur.quarter_index - 2
WHERE cur.sector = N'Retail'
  AND cur.is_latest = 1
  AND cur.debt_to_equity > 2
  AND cur.debt_to_equity > prior.debt_to_equity
  AND cur.operating_cash_flow < prior.operating_cash_flow;
GO

CREATE OR ALTER VIEW dw.vw_margin_change
AS
SELECT
    cur.ticker,
    cur.company_name,
    cur.sector,
    prior.operating_margin AS operating_margin_prior_year,
    cur.operating_margin AS operating_margin_latest,
    CAST((cur.operating_margin - prior.operating_margin) * 100 AS decimal(8, 2)) AS margin_change_pp
FROM dw.vw_ratios AS cur
JOIN dw.vw_ratios AS prior
    ON prior.ticker = cur.ticker
   AND prior.quarter_index = cur.quarter_index - 4
WHERE cur.is_latest = 1;
GO

CREATE OR ALTER VIEW dw.vw_sector_revenue
AS
SELECT
    sector,
    SUM(revenue) AS revenue
FROM dw.vw_ratios
WHERE is_latest = 1
GROUP BY sector;
GO
