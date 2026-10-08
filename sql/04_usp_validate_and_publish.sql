/*
    Publish certified financials, or hold the row back.

    A row is certified only when all of these are true:
      - it is the earliest extract row for that company and quarter
      - revenue, operating income, net income, debt, equity, and
        operating cash flow are present
      - equity is not zero
      - debt is zero or positive
      - operating income does not exceed revenue

    The procedure still fills dw.fact_financials with the rows that pass,
    and records every failure in dw.quality_exception. If any blocking
    check fails, dw.refresh_log.gate_status is Blocked. Power BI should
    keep the last published report until the gate is Passed. The report
    file in this repo shows the certified preview, with the failures
    on the Validation exceptions page.

    Expected result on the committed seed:
      gate            Blocked
      raw rows        97
      certified rows  93
      exceptions      4
        Harbor Steel, 2025 Q4, total equity is null
        Pine Diagnostics, 2025 Q3, operating cash flow is null
        Keel Manufacturing, 2025 Q2, operating income exceeds revenue
        Field & Co, 2024 Q1, extra extract row
*/

USE FinancialCockpit;
GO

CREATE OR ALTER PROCEDURE dw.usp_validate_and_publish
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM dw.quality_exception;
    DELETE FROM dw.fact_financials;
    DELETE FROM dw.quality_check;

    DELETE FROM dw.dim_company;
    INSERT INTO dw.dim_company (ticker, company_name, sector)
    SELECT ticker, company_name, sector
    FROM stg.company;

    IF OBJECT_ID(N'tempdb..#ranked') IS NOT NULL
        DROP TABLE #ranked;

    SELECT
        extract_row_id,
        ticker,
        fiscal_year,
        fiscal_quarter,
        revenue,
        operating_income,
        net_income,
        total_debt,
        total_equity,
        operating_cash_flow,
        ROW_NUMBER() OVER (
            PARTITION BY ticker, fiscal_year, fiscal_quarter
            ORDER BY extract_row_id
        ) AS line_rank
    INTO #ranked
    FROM stg.financial_extract;

    INSERT INTO dw.quality_exception
        (check_name, ticker, fiscal_year, fiscal_quarter, detail, blocking)
    SELECT
        CASE
            WHEN line_rank > 1 THEN N'Duplicate company-quarter'
            WHEN revenue IS NULL
              OR operating_income IS NULL
              OR net_income IS NULL
              OR total_debt IS NULL
              OR total_equity IS NULL
              OR operating_cash_flow IS NULL
            THEN N'Required amounts present'
            WHEN total_equity = 0 THEN N'Equity is not zero'
            WHEN total_debt < 0 THEN N'Debt is zero or positive'
            ELSE N'Operating income within revenue'
        END,
        ticker,
        fiscal_year,
        fiscal_quarter,
        CASE
            WHEN line_rank > 1
                THEN N'Extra extract row. The earliest row for this company and quarter can still pass the other checks.'
            WHEN revenue IS NULL THEN N'Revenue is null'
            WHEN operating_income IS NULL THEN N'Operating income is null'
            WHEN net_income IS NULL THEN N'Net income is null'
            WHEN total_debt IS NULL THEN N'Total debt is null'
            WHEN total_equity IS NULL THEN N'Total equity is null'
            WHEN operating_cash_flow IS NULL THEN N'Operating cash flow is null'
            WHEN total_equity = 0
                THEN N'Total equity is zero, so debt-to-equity is undefined'
            WHEN total_debt < 0 THEN N'Total debt is negative'
            ELSE N'Operating income is greater than revenue'
        END,
        1
    FROM #ranked
    WHERE line_rank > 1
       OR revenue IS NULL
       OR operating_income IS NULL
       OR net_income IS NULL
       OR total_debt IS NULL
       OR total_equity IS NULL
       OR operating_cash_flow IS NULL
       OR total_equity = 0
       OR total_debt < 0
       OR operating_income > revenue;

    INSERT INTO dw.fact_financials
    (
        ticker, fiscal_year, fiscal_quarter,
        revenue, operating_income, net_income,
        total_debt, total_equity, operating_cash_flow
    )
    SELECT
        ticker, fiscal_year, fiscal_quarter,
        revenue, operating_income, net_income,
        total_debt, total_equity, operating_cash_flow
    FROM #ranked
    WHERE line_rank = 1
      AND revenue IS NOT NULL
      AND operating_income IS NOT NULL
      AND net_income IS NOT NULL
      AND total_debt IS NOT NULL
      AND total_equity IS NOT NULL
      AND total_equity <> 0
      AND total_debt >= 0
      AND operating_income <= revenue;

    DECLARE @duplicate_rows int = (
        SELECT COUNT(*) FROM dw.quality_exception
        WHERE check_name = N'Duplicate company-quarter'
    );
    DECLARE @missing_rows int = (
        SELECT COUNT(*) FROM dw.quality_exception
        WHERE check_name = N'Required amounts present'
    );
    DECLARE @zero_equity_rows int = (
        SELECT COUNT(*) FROM dw.quality_exception
        WHERE check_name = N'Equity is not zero'
    );
    DECLARE @negative_debt_rows int = (
        SELECT COUNT(*) FROM dw.quality_exception
        WHERE check_name = N'Debt is zero or positive'
    );
    DECLARE @margin_rows int = (
        SELECT COUNT(*) FROM dw.quality_exception
        WHERE check_name = N'Operating income within revenue'
    );
    DECLARE @raw_rows int = (SELECT COUNT(*) FROM stg.financial_extract);
    DECLARE @certified_rows int = (SELECT COUNT(*) FROM dw.fact_financials);
    DECLARE @exception_rows int = (SELECT COUNT(*) FROM dw.quality_exception);

    INSERT INTO dw.quality_check (check_name, status, blocking, observed, rule_text)
    VALUES
    (
        N'Duplicate company-quarter',
        CASE WHEN @duplicate_rows = 0 THEN N'Pass' ELSE N'Fail' END,
        1,
        CONCAT(@duplicate_rows, N' extra extract row(s)'),
        N'One row per company and quarter. The earliest extract row is the candidate.'
    ),
    (
        N'Required amounts present',
        CASE WHEN @missing_rows = 0 THEN N'Pass' ELSE N'Fail' END,
        1,
        CONCAT(@missing_rows, N' row(s) missing an amount'),
        N'Revenue, income, debt, equity, and operating cash flow are present.'
    ),
    (
        N'Equity is not zero',
        CASE WHEN @zero_equity_rows = 0 THEN N'Pass' ELSE N'Fail' END,
        1,
        CONCAT(@zero_equity_rows, N' row(s) with zero equity'),
        N'Equity is not zero, so debt-to-equity is defined.'
    ),
    (
        N'Debt is zero or positive',
        CASE WHEN @negative_debt_rows = 0 THEN N'Pass' ELSE N'Fail' END,
        1,
        CONCAT(@negative_debt_rows, N' row(s) with negative debt'),
        N'Total debt is zero or positive.'
    ),
    (
        N'Operating income within revenue',
        CASE WHEN @margin_rows = 0 THEN N'Pass' ELSE N'Fail' END,
        1,
        CONCAT(@margin_rows, N' row(s) with operating income above revenue'),
        N'Operating income is less than or equal to revenue.'
    ),
    (
        N'Certified rows tie to the extract',
        CASE WHEN @raw_rows = @certified_rows + @exception_rows THEN N'Pass' ELSE N'Fail' END,
        1,
        CONCAT(N'Raw ', @raw_rows, N', certified ', @certified_rows, N', exceptions ', @exception_rows),
        N'Every extract row is either certified or listed as an exception.'
    );

    DECLARE @gate nvarchar(16) = CASE
        WHEN EXISTS (
            SELECT 1 FROM dw.quality_check
            WHERE status = N'Fail' AND blocking = 1
        ) THEN N'Blocked'
        ELSE N'Passed'
    END;

    INSERT INTO dw.refresh_log
        (run_at, gate_status, raw_rows, certified_rows, exception_rows)
    VALUES
        (SYSDATETIME(), @gate, @raw_rows, @certified_rows, @exception_rows);
END;
GO
