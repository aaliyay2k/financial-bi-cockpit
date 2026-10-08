/*
    Staging extract, certified facts, and the quality-gate tables.

    Balance-sheet amounts (debt, equity) are point-in-time.
    Revenue, operating income, and operating cash flow are quarterly flows.
    Amounts are USD millions.
*/

USE FinancialCockpit;
GO

IF OBJECT_ID(N'dw.vw_retail_debt_to_equity', N'V') IS NOT NULL DROP VIEW dw.vw_retail_debt_to_equity;
IF OBJECT_ID(N'dw.vw_retail_leverage_screen', N'V') IS NOT NULL DROP VIEW dw.vw_retail_leverage_screen;
IF OBJECT_ID(N'dw.vw_margin_change', N'V') IS NOT NULL DROP VIEW dw.vw_margin_change;
IF OBJECT_ID(N'dw.vw_sector_revenue', N'V') IS NOT NULL DROP VIEW dw.vw_sector_revenue;
IF OBJECT_ID(N'dw.vw_ratios', N'V') IS NOT NULL DROP VIEW dw.vw_ratios;
IF OBJECT_ID(N'dw.usp_validate_and_publish', N'P') IS NOT NULL DROP PROCEDURE dw.usp_validate_and_publish;
GO

IF OBJECT_ID(N'stg.financial_extract', N'U') IS NOT NULL DROP TABLE stg.financial_extract;
IF OBJECT_ID(N'stg.company', N'U') IS NOT NULL DROP TABLE stg.company;
IF OBJECT_ID(N'dw.fact_financials', N'U') IS NOT NULL DROP TABLE dw.fact_financials;
IF OBJECT_ID(N'dw.quality_exception', N'U') IS NOT NULL DROP TABLE dw.quality_exception;
IF OBJECT_ID(N'dw.quality_check', N'U') IS NOT NULL DROP TABLE dw.quality_check;
IF OBJECT_ID(N'dw.refresh_log', N'U') IS NOT NULL DROP TABLE dw.refresh_log;
IF OBJECT_ID(N'dw.dim_company', N'U') IS NOT NULL DROP TABLE dw.dim_company;
IF OBJECT_ID(N'dw.dim_period', N'U') IS NOT NULL DROP TABLE dw.dim_period;
GO

IF SCHEMA_ID(N'stg') IS NULL EXEC(N'CREATE SCHEMA stg');
IF SCHEMA_ID(N'dw') IS NULL EXEC(N'CREATE SCHEMA dw');
GO

CREATE TABLE stg.company
(
    ticker        nvarchar(10)  NOT NULL PRIMARY KEY,
    company_name  nvarchar(80)  NOT NULL,
    sector        nvarchar(40)  NOT NULL
);

CREATE TABLE stg.financial_extract
(
    extract_row_id        int            NOT NULL PRIMARY KEY,
    ticker                nvarchar(10)   NOT NULL,
    fiscal_year           int            NOT NULL,
    fiscal_quarter        int            NOT NULL,
    revenue               decimal(18, 2) NULL,
    operating_income      decimal(18, 2) NULL,
    net_income            decimal(18, 2) NULL,
    total_debt            decimal(18, 2) NULL,
    total_equity          decimal(18, 2) NULL,
    operating_cash_flow   decimal(18, 2) NULL
);

CREATE TABLE dw.dim_company
(
    ticker        nvarchar(10) NOT NULL PRIMARY KEY,
    company_name  nvarchar(80) NOT NULL,
    sector        nvarchar(40) NOT NULL
);

CREATE TABLE dw.dim_period
(
    fiscal_year     int          NOT NULL,
    fiscal_quarter  int          NOT NULL,
    quarter_label   nvarchar(12) NOT NULL,
    quarter_index   int          NOT NULL,
    period_end      date         NOT NULL,
    is_latest       bit          NOT NULL,
    CONSTRAINT pk_dim_period PRIMARY KEY (fiscal_year, fiscal_quarter),
    CONSTRAINT uq_dim_period_index UNIQUE (quarter_index)
);

INSERT INTO dw.dim_period
    (fiscal_year, fiscal_quarter, quarter_label, quarter_index, period_end, is_latest)
VALUES
    (2024, 1, N'2024 Q1', 1, '2024-03-31', 0),
    (2024, 2, N'2024 Q2', 2, '2024-06-30', 0),
    (2024, 3, N'2024 Q3', 3, '2024-09-30', 0),
    (2024, 4, N'2024 Q4', 4, '2024-12-31', 0),
    (2025, 1, N'2025 Q1', 5, '2025-03-31', 0),
    (2025, 2, N'2025 Q2', 6, '2025-06-30', 0),
    (2025, 3, N'2025 Q3', 7, '2025-09-30', 0),
    (2025, 4, N'2025 Q4', 8, '2025-12-31', 1);
GO

CREATE TABLE dw.fact_financials
(
    ticker               nvarchar(10)   NOT NULL,
    fiscal_year          int            NOT NULL,
    fiscal_quarter       int            NOT NULL,
    revenue              decimal(18, 2) NOT NULL,
    operating_income     decimal(18, 2) NOT NULL,
    net_income           decimal(18, 2) NOT NULL,
    total_debt           decimal(18, 2) NOT NULL,
    total_equity         decimal(18, 2) NOT NULL,
    operating_cash_flow  decimal(18, 2) NOT NULL,
    CONSTRAINT pk_fact_financials PRIMARY KEY (ticker, fiscal_year, fiscal_quarter)
);

CREATE TABLE dw.quality_exception
(
    exception_id    int IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    check_name      nvarchar(80)  NOT NULL,
    ticker          nvarchar(10)  NOT NULL,
    fiscal_year     int           NOT NULL,
    fiscal_quarter  int           NOT NULL,
    detail          nvarchar(300) NOT NULL,
    blocking        bit           NOT NULL
);

CREATE TABLE dw.quality_check
(
    check_name  nvarchar(80)  NOT NULL PRIMARY KEY,
    status      nvarchar(8)   NOT NULL,
    blocking    bit           NOT NULL,
    observed    nvarchar(200) NOT NULL,
    rule_text   nvarchar(300) NOT NULL
);

CREATE TABLE dw.refresh_log
(
    refresh_id      int IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    run_at          datetime2     NOT NULL,
    gate_status     nvarchar(16)  NOT NULL,
    raw_rows        int           NOT NULL,
    certified_rows  int           NOT NULL,
    exception_rows  int           NOT NULL
);
GO
