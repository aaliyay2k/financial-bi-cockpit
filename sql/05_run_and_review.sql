/*
    Run the gate, then review the three demo questions.
*/

USE FinancialCockpit;
GO

EXEC dw.usp_validate_and_publish;
GO

SELECT refresh_id, run_at, gate_status, raw_rows, certified_rows, exception_rows
FROM dw.refresh_log;

SELECT check_name, status, blocking, observed, rule_text
FROM dw.quality_check
ORDER BY check_name;

SELECT check_name, ticker, fiscal_year, fiscal_quarter, detail
FROM dw.quality_exception
ORDER BY ticker, fiscal_year, fiscal_quarter;

/* Which retail companies have debt-to-equity above 2? */
SELECT company_name, quarter_label, debt_to_equity, operating_cash_flow
FROM dw.vw_retail_debt_to_equity
ORDER BY debt_to_equity DESC;

/* Retail names that also lost operating cash flow over the last three quarters. */
SELECT
    company_name,
    debt_to_equity,
    debt_to_equity_prior,
    operating_cash_flow,
    operating_cash_flow_prior
FROM dw.vw_retail_leverage_screen
ORDER BY debt_to_equity DESC;

/* Operating margin down more than 3 percentage points versus the same quarter last year. */
SELECT company_name, sector, operating_margin_prior_year, operating_margin_latest, margin_change_pp
FROM dw.vw_margin_change
WHERE margin_change_pp <= -3
ORDER BY margin_change_pp;

SELECT sector, revenue
FROM dw.vw_sector_revenue
ORDER BY revenue DESC;
GO
