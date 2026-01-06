import React, { useState, useRef, useEffect } from "react";
import { createSession, uploadMultipleFiles, processSession, searchSession } from "../api/invoice";
import { jsonToCSV } from "../utils/csv";

export default function MultiDocumentMode() {
    const [sessionId, setSessionId] = useState(null);
    const [files, setFiles] = useState([]);
    const [processing, setProcessing] = useState(false);
    const [processed, setProcessed] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const fileInputRef = useRef();

    const handleFileSelect = (e) => {
        const selectedFiles = Array.from(e.target.files || []);
        setFiles(prev => [...prev, ...selectedFiles]);
    };

    const handleCreateSession = async () => {
        try {
            const session = await createSession();
            setSessionId(session.session_id);
            setFiles([]);
            setProcessed(false);
            setSearchResults(null);
        } catch (err) {
            console.error(err);
            alert("Failed to create session");
        }
    };

    const handleUpload = async () => {
        if (!sessionId || files.length === 0) {
            alert("Please create a session and select files first");
            return;
        }

        setLoading(true);
        try {
            await uploadMultipleFiles(sessionId, files);
            setLoading(false);
            alert(`Uploaded ${files.length} file(s)`);
        } catch (err) {
            console.error(err);
            alert("Failed to upload files");
            setLoading(false);
        }
    };

    const handleProcess = async () => {
        if (!sessionId) return;

        setProcessing(true);
        try {
            const result = await processSession(sessionId);
            setProcessed(true);
            setProcessing(false);
            alert(`Processed ${result.processed} document(s), ${result.failed} failed`);
        } catch (err) {
            console.error(err);
            alert("Failed to process documents");
            setProcessing(false);
        }
    };

    const handleSearch = async () => {
        if (!sessionId || !searchQuery.trim()) {
            alert("Please enter a search query");
            return;
        }

        setLoading(true);
        try {
            const results = await searchSession(sessionId, searchQuery);
            setSearchResults(results);
            setLoading(false);
        } catch (err) {
            console.error(err);
            alert("Search failed");
            setLoading(false);
        }
    };

    // Debounced search
    useEffect(() => {
        if (!sessionId || !searchQuery.trim() || !processed) return;

        const timer = setTimeout(() => {
            handleSearch();
        }, 500);

        return () => clearTimeout(timer);
    }, [searchQuery, sessionId, processed]);

    const downloadJSON = () => {
        if (!searchResults) return;
        const blob = new Blob([JSON.stringify(searchResults, null, 2)], { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `session-search-${sessionId}-${Date.now()}.json`;
        a.click();
    };

    const downloadCSV = () => {
        if (!searchResults?.table_data) return;
        const csv = jsonToCSV(searchResults.table_data);
        const blob = new Blob([csv], { type: "text/csv" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `session-search-${sessionId}-${Date.now()}.csv`;
        a.click();
    };

    const getTableHeaders = () => {
        if (!searchResults?.table_data?.length) return [];
        return Object.keys(searchResults.table_data[0]);
    };

    return (
        <div style={{ padding: "20px", maxWidth: "1400px", margin: "0 auto" }}>
            {/* Upload Section */}
            <div className="glass" style={{ marginBottom: "20px", padding: "20px" }}>
                <h2 style={{ marginTop: 0, marginBottom: "20px", fontSize: "24px", fontWeight: 700 }}>
                    Upload Documents
                </h2>

                {!sessionId ? (
                    <button className="action-btn" onClick={handleCreateSession}>
                        Create New Session
                    </button>
                ) : (
                    <div>
                        <div style={{ marginBottom: "15px", color: "var(--muted)", fontSize: "14px" }}>
                            <strong>Session ID:</strong> {sessionId}
                        </div>

                        <div style={{ marginBottom: "15px", display: "flex", gap: "10px", alignItems: "center" }}>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.jpg,.jpeg,.png"
                                multiple
                                onChange={handleFileSelect}
                                style={{ display: "none" }}
                            />
                            <button
                                className="action-btn"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                Choose Files (Multiple)
                            </button>
                            <button
                                className="action-btn"
                                onClick={handleUpload}
                                disabled={files.length === 0 || loading}
                            >
                                Upload Files
                            </button>
                            {files.length > 0 && (
                                <span style={{ color: "#9fb0d8", fontSize: 14 }}>
                                    {files.length} file(s) selected
                                </span>
                            )}
                        </div>

                        <button
                            className="action-btn"
                            onClick={handleProcess}
                            disabled={processing || !sessionId}
                        >
                            {processing ? "Processing..." : "Process All Documents"}
                        </button>
                    </div>
                )}
            </div>

            {/* Search Section - Under Heading */}
            {processed && sessionId && (
                <div className="glass" style={{ marginBottom: "20px", padding: "20px" }}>
                    <h2 style={{ marginTop: 0, marginBottom: "20px", fontSize: "24px", fontWeight: 700 }}>
                        Search Documents
                    </h2>

                    <div style={{ display: "flex", gap: "10px", marginBottom: "20px", alignItems: "center" }}>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Enter keywords (e.g., 'date', 'vendor name', 'invoice number')..."
                            style={{
                                flex: 1,
                                padding: "12px 16px",
                                fontSize: "16px",
                                borderRadius: "8px",
                                border: "1px solid rgba(255,255,255,0.12)",
                                background: "rgba(255,255,255,0.02)",
                                color: "#e9eef6",
                                outline: "none",
                            }}
                            onKeyPress={(e) => {
                                if (e.key === "Enter" && !loading) {
                                    handleSearch();
                                }
                            }}
                        />
                        <button
                            className="action-btn"
                            onClick={handleSearch}
                            disabled={loading || !searchQuery.trim()}
                            style={{ padding: "12px 24px", fontSize: "16px" }}
                        >
                            {loading ? "Searching..." : "Search"}
                        </button>
                    </div>

                    {searchResults && (
                        <div style={{ marginTop: "30px" }}>
                            <div style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                marginBottom: "20px"
                            }}>
                                <div style={{ fontSize: "18px", fontWeight: 600 }}>
                                    Results: <span style={{ color: "#9fb0d8" }}>{searchResults.total_results} found</span>
                                </div>
                                <div style={{ display: "flex", gap: "10px" }}>
                                    <button className="small-btn" onClick={downloadJSON}>
                                        Download JSON
                                    </button>
                                    <button className="small-btn" onClick={downloadCSV}>
                                        Download CSV
                                    </button>
                                </div>
                            </div>

                            {/* Table View - Bigger and Centered */}
                            {searchResults.table_data && searchResults.table_data.length > 0 && (
                                <div style={{
                                    marginBottom: "30px",
                                    background: "rgba(255,255,255,0.01)",
                                    borderRadius: "12px",
                                    padding: "20px",
                                    border: "1px solid rgba(255,255,255,0.05)"
                                }}>
                                    <div style={{
                                        fontSize: "18px",
                                        fontWeight: 600,
                                        marginBottom: "15px",
                                        color: "#e9eef6"
                                    }}>
                                        Table View
                                    </div>
                                    <div className="table-wrap" style={{
                                        maxHeight: "500px",
                                        overflowY: "auto",
                                        overflowX: "auto",
                                    }}>
                                        <table className="items-table" style={{
                                            width: "100%",
                                            fontSize: "14px",
                                            minWidth: "800px"
                                        }}>
                                            <thead>
                                                <tr>
                                                    {getTableHeaders().map(header => (
                                                        <th key={header} style={{
                                                            padding: "14px 16px",
                                                            fontSize: "13px",
                                                            textTransform: "uppercase",
                                                            letterSpacing: "0.5px",
                                                            fontWeight: 600,
                                                        }}>
                                                            {header}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {searchResults.table_data.map((row, idx) => (
                                                    <tr key={idx}>
                                                        {getTableHeaders().map(header => (
                                                            <td key={header} style={{
                                                                padding: "12px 16px",
                                                            }}>
                                                                {row[header] || "-"}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* JSON View */}
                            <div className="glass" style={{ padding: "20px" }}>
                                <div style={{
                                    fontWeight: 700,
                                    marginBottom: "15px",
                                    fontSize: "18px",
                                    color: "#e9eef6"
                                }}>
                                    JSON Format
                                </div>
                                <pre className="result-box" style={{
                                    maxHeight: "500px",
                                    overflow: "auto",
                                    fontSize: "13px",
                                    padding: "16px"
                                }}>
                                    {JSON.stringify(searchResults, null, 2)}
                                </pre>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}