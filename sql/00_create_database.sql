/*
    Create the database, then run the rest of the scripts in order
    while connected to FinancialCockpit:

        01_schema.sql
        02_seed.sql
        03_views.sql
        04_usp_validate_and_publish.sql
        05_run_and_review.sql

    The seed is a fictional 12-company panel. It is supposed to fail
    the validation gate.
*/

IF DB_ID(N'FinancialCockpit') IS NULL
    CREATE DATABASE FinancialCockpit;
GO
