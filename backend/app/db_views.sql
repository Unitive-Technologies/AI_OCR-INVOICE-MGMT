-- PostgreSQL views for easier querying of DocAI tables

-- =============================
-- Invoice-specific convenience views
-- =============================

-- Summary view: Clean columns without raw_metadata
CREATE OR REPLACE VIEW invoices_summary AS
SELECT
    id,
    document_id,
    vendor,
    invoice_number,
    currency,
    total_amount,
    created_at
FROM invoices
ORDER BY created_at DESC;

-- Detail view: Includes formatted JSON metadata
CREATE OR REPLACE VIEW invoices_detail AS
SELECT
    id,
    document_id,
    vendor,
    invoice_number,
    currency,
    total_amount,
    created_at,
    jsonb_pretty(raw_metadata::jsonb) as formatted_metadata
FROM invoices
ORDER BY created_at DESC;

-- Extended view: Extracts common fields from JSON into columns
CREATE OR REPLACE VIEW invoices_extended AS
SELECT
    i.id,
    i.document_id,
    i.vendor,
    i.invoice_number,
    i.currency,
    i.total_amount,
    i.created_at,
    (i.raw_metadata::jsonb->>'vendor_address')::text as vendor_address,
    (i.raw_metadata::jsonb->>'vendor_email')::text as vendor_email,
    (i.raw_metadata::jsonb->>'customer_name')::text as customer_name,
    (i.raw_metadata::jsonb->>'customer_address')::text as customer_address,
    (i.raw_metadata::jsonb->>'invoice_date')::text as invoice_date,
    (i.raw_metadata::jsonb->>'subtotal')::text as subtotal,
    (i.raw_metadata::jsonb->>'vat_amount')::text as vat_amount,
    (i.raw_metadata::jsonb->>'payment_terms')::text as payment_terms
FROM invoices i
ORDER BY i.created_at DESC;

-- =============================
-- Generic "*_view" helpers for all core tables
-- =============================

-- Documents: one row per stored document
CREATE OR REPLACE VIEW documents_view AS
SELECT *
FROM documents
ORDER BY created_at DESC;

-- OCR results with most recent first
CREATE OR REPLACE VIEW ocr_results_view AS
SELECT *
FROM ocr_results
ORDER BY processed_at DESC;

-- Classifications per document
CREATE OR REPLACE VIEW document_classifications_view AS
SELECT *
FROM document_classifications
ORDER BY processed_at DESC;

-- Processing history / pipeline status
CREATE OR REPLACE VIEW document_processing_view AS
SELECT *
FROM document_processing
ORDER BY processed_at DESC;

-- Receipts table, ordered by creation time
CREATE OR REPLACE VIEW receipts_view AS
SELECT *
FROM receipts
ORDER BY created_at DESC;

-- Purchase orders table, ordered by creation time
CREATE OR REPLACE VIEW purchase_orders_view AS
SELECT *
FROM purchase_orders
ORDER BY created_at DESC;

-- Generic extraction results for non-invoice document types
CREATE OR REPLACE VIEW extraction_results_view AS
SELECT *
FROM extraction_results
ORDER BY created_at DESC;

-- Optional pretty JSON helpers for raw_metadata-heavy tables

CREATE OR REPLACE VIEW receipts_detail AS
SELECT
    id,
    document_id,
    merchant,
    receipt_number,
    transaction_date,
    currency,
    total_amount,
    payment_method,
    created_at,
    jsonb_pretty(raw_metadata::jsonb) AS formatted_metadata
FROM receipts
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW purchase_orders_detail AS
SELECT
    id,
    document_id,
    po_number,
    vendor,
    buyer,
    order_date,
    currency,
    total_amount,
    created_at,
    jsonb_pretty(raw_metadata::jsonb) AS formatted_metadata
FROM purchase_orders
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW extraction_results_detail AS
SELECT
    id,
    document_id,
    document_type,
    created_at,
    jsonb_pretty(raw_metadata::jsonb) AS formatted_metadata
FROM extraction_results
ORDER BY created_at DESC;
