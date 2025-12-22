-- PostgreSQL views for easier invoice querying

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

