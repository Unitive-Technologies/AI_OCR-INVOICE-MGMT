import React, { useState, useRef } from "react";
import { uploadInvoice, runOCR, runDetect, runExtract } from "./api/invoice";
import DragDrop from "./components/DragDrop";
import PdfPreview from "./components/PdfPreview";
import { jsonToCSV } from "./utils/csv";
import { marked } from "marked";

export default function App() {
    const [file, setFile] = useState(null);
    const [fileUrl, setFileUrl] = useState("");
    const [loadingStep, setLoadingStep] = useState("");
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");
    const fileInputRef = useRef();

    const setLocalFile = (f) => {
        setFile(f);
        const url = URL.createObjectURL(f);
        setFileUrl(url);
        setResult(null);
        setError("");
    };

    const handleChoose = (e) => {
        const f = e.target.files?.[0];
        if (f) setLocalFile(f);
    };

    const handleStart = async () => {
        if (!file) {
            setError("No file chosen");
            return;
        }
        setError("");
        setLoadingStep("Uploading file...");
        try {
            const up = await uploadInvoice(file);
            const fileId = up.file_id ?? up.file_id ?? up.id ?? up?.id;
            setLoadingStep("Running OCR...");
            await runOCR(fileId);

            setLoadingStep("Running detection...");
            await runDetect(fileId);

            setLoadingStep("Running extract...");
            const extracted = await runExtract(fileId, true, false);

            setResult(extracted);
            setLoadingStep("");
        } catch (err) {
            console.error(err);
            setError(err?.response?.data?.detail || err.message || "Unknown error");
            setLoadingStep("");
        }
    };

    const downloadJSON = () => {
        if (!result) return;
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `docai-extract-${result.file_id || Date.now()}.json`;
        a.click();
    };

    const downloadCSV = () => {
        if (!result) return;
        // prefer line_items if present, else whole extraction
        const data = result?.extraction?.line_items ?? result?.extraction ?? result;
        const csv = jsonToCSV(data);
        const blob = new Blob([csv], { type: "text/csv" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `docai-extract-${result.file_id || Date.now()}.csv`;
        a.click();
    };

    const copyJSON = async () => {
        if (!result) return;
        await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
        alert("JSON copied to clipboard");
    };

    const renderSummaryHTML = () => {
        const summary = result?.summary || result?.extraction?.summary || "";
        if (!summary) return "<p style='color:#c8d6e5'>No summary available</p>";
        return marked.parse(summary);
    };

    return (
        <div className="app-wrap">
            {/* LEFT */}
            <div className="left-col">
                <div className="glass header">
                    <div>
                        <div className="logo">DocAI – Invoice Extractor</div>
                        <div className="subtitle">Upload → OCR → Detect → Extract</div>
                    </div>
                </div>

                <div className="glass controls">
                    <label className="choose-btn" htmlFor="file">Choose File</label>
                    <input id="file" ref={fileInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={handleChoose} />
                    <button className="action-btn" onClick={() => fileInputRef.current.click()}>Choose File</button>

                    <button className="action-btn" onClick={handleStart} disabled={!file}>
                        {loadingStep ? `${loadingStep}` : "Start Processing"}
                    </button>
                    <div style={{ marginLeft: "auto", color: "#9fb0d8" }}>{file?.name}</div>
                </div>

                <DragDrop onFile={setLocalFile} />

                <div className="glass summary-card">
                    <div className="summary-title">Summary</div>
                    <div
                        className="summary-text"
                        dangerouslySetInnerHTML={{ __html: renderSummaryHTML() }}
                    />
                    <div className="summary-metrics" style={{ marginTop: 12 }}>
                        <div className="metric">
                            <div className="val">{result?.extraction?.total_amount ?? "-"}</div>
                            <div className="label">Total</div>
                        </div>
                        <div className="metric">
                            <div className="val">{result?.extraction?.vat_amount ?? "-"}</div>
                            <div className="label">VAT</div>
                        </div>
                        <div className="metric">
                            <div className="val">{result?.extraction?.subtotal ?? "-"}</div>
                            <div className="label">Subtotal</div>
                        </div>
                    </div>
                </div>

                <div className="glass items-card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ fontWeight: 700 }}>Line Items</div>
                        <div style={{ color: "var(--muted)", fontSize: 13 }}>
                            {result?.extraction?.line_items?.length ?? 0} items
                        </div>
                    </div>

                    <div className="table-wrap" style={{ marginTop: 8 }}>
                        <table className="items-table">
                            <thead>
                            <tr>
                                <th>Description</th>
                                <th style={{ width: 80 }}>Qty</th>
                                <th style={{ width: 100 }}>Unit Price</th>
                                <th style={{ width: 100 }}>Total</th>
                            </tr>
                            </thead>
                            <tbody>
                            {result?.extraction?.line_items?.length ? (
                                result.extraction.line_items.map((li, idx) => (
                                    <tr key={idx}>
                                        <td>{li.description || li.desc || "-"}</td>
                                        <td>{li.quantity ?? li.qty ?? 0}</td>
                                        <td>{li.unit_price ?? li.unit_price ?? "-"}</td>
                                        <td>{li.total_amount ?? li.total ?? "-"}</td>
                                    </tr>
                                ))
                            ) : (
                                <tr><td colSpan="4" style={{ color: "var(--muted)", padding: 18 }}>No line items found</td></tr>
                            )}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="glass" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                        <div style={{ fontWeight: 700 }}>Invoice Details</div>
                        <div className="kv" style={{ marginTop: 8 }}>
                            <strong>Invoice #</strong><span>{result?.extraction?.invoice_number ?? "-"}</span>
                        </div>
                        <div className="kv"><strong>Invoice Date</strong><span>{result?.extraction?.invoice_date ?? "-"}</span></div>
                        <div className="kv"><strong>Customer #</strong><span>{result?.extraction?.customer_number ?? result?.extraction?.customer_id ?? "-"}</span></div>
                    </div>

                    <div style={{ textAlign: "right" }}>
                        <div className="kv"><strong>Supplier</strong><span>{result?.extraction?.supplier_info?.name ?? result?.extraction?.vendor_name ?? "-"}</span></div>
                        <div className="kv"><strong>Currency</strong><span>{result?.extraction?.currency ?? result?.extraction?.currency_code ?? "-"}</span></div>
                    </div>
                </div>

            </div>

            {/* RIGHT */}
            <div className="right-col">
                <div className="glass raw-card">
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div style={{ fontWeight: 700 }}>PDF / Image Preview</div>
                        <div style={{ color: "var(--muted)", fontSize: 13 }}>{file?.type || ""}</div>
                    </div>

                    <PdfPreview fileUrl={fileUrl} />

                    <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "space-between" }}>
                        <div className="downloads">
                            <button className="small-btn" onClick={downloadJSON} disabled={!result}>Download JSON</button>
                            <button className="small-btn" onClick={downloadCSV} disabled={!result}>Download CSV</button>
                            <button className="small-btn" onClick={copyJSON} disabled={!result}>Copy JSON</button>
                        </div>

                        <div style={{ color: "var(--muted)", fontSize: 12 }}>
                            {error ? <span style={{ color: "#ff7b7b" }}>{error}</span> : (loadingStep || "Ready")}
                        </div>
                    </div>
                </div>

                <div className="glass raw-card">
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                        <div style={{ fontWeight:700 }}>Raw JSON</div>
                        <div style={{ color: "var(--muted)", fontSize: 12 }}>Preview of backend response</div>
                    </div>

                    <pre className="result-box">{result ? JSON.stringify(result, null, 2) : "// No response yet"}</pre>
                </div>
            </div>
        </div>
    );
}
