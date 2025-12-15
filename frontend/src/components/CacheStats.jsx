import React, { useState, useEffect } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function CacheStats() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [lastStatus, setLastStatus] = useState(null); // NEW: Track cache hit/miss

    const fetchStats = async () => {
        try {
            const resp = await axios.get(`${API_URL}/api/cache/stats`);
            setStats(resp.data.cache_stats);
        } catch (err) {
            console.error("Failed to fetch cache stats:", err);
        }
    };

    const clearCache = async (operation = null) => {
        setLoading(true);
        setMessage("");
        try {
            const url = operation
                ? `${API_URL}/api/cache/clear?operation=${operation}`
                : `${API_URL}/api/cache/clear`;

            const resp = await axios.delete(url);
            setMessage(resp.data.message);
            await fetchStats();
        } catch (err) {
            setMessage("Failed to clear cache");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 5000); // Refresh every 5 seconds
        return () => clearInterval(interval);
    }, []);

    // NEW: Listen for cache events from parent
    useEffect(() => {
        const handleCacheEvent = (event) => {
            if (event.detail) {
                setLastStatus(event.detail);
                // Auto-clear after 5 seconds
                setTimeout(() => setLastStatus(null), 5000);
            }
        };

        window.addEventListener('cacheStatus', handleCacheEvent);
        return () => window.removeEventListener('cacheStatus', handleCacheEvent);
    }, []);

    if (!stats) {
        return (
            <div className="glass" style={{ padding: 16, color: "#e9eef6" }}>
                Loading cache stats...
            </div>
        );
    }

    const apiCallsSaved = stats.total_entries || 0;
    const costSaved = (apiCallsSaved * 0.0001).toFixed(4);

    return (
        <div className="glass cache-stats">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ fontWeight: 700, fontSize: 16, color: "#e9eef6" }}>
                    ⚡ Cache Performance
                </div>
                <button
                    className="small-btn"
                    onClick={fetchStats}
                    style={{ fontSize: 12, color: "#e9eef6" }}
                >
                    🔄 Refresh
                </button>
            </div>

            {/* NEW: Cache Hit/Miss Indicator */}
            {lastStatus && (
                <div style={{
                    padding: "10px 12px",
                    marginBottom: 12,
                    borderRadius: 8,
                    background: lastStatus.hit
                        ? "rgba(74, 222, 128, 0.1)"
                        : "rgba(251, 146, 60, 0.1)",
                    border: lastStatus.hit
                        ? "1px solid rgba(74, 222, 128, 0.3)"
                        : "1px solid rgba(251, 146, 60, 0.3)",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    animation: "fadeIn 0.3s ease-in"
                }}>
                    <span style={{ fontSize: 20 }}>
                        {lastStatus.hit ? "✅" : "❌"}
                    </span>
                    <div style={{ flex: 1 }}>
                        <div style={{
                            fontWeight: 600,
                            fontSize: 13,
                            color: lastStatus.hit ? "#4ade80" : "#fb923c"
                        }}>
                            {lastStatus.hit ? "CACHE HIT!" : "CACHE MISS"}
                        </div>
                        <div style={{ fontSize: 11, color: "#c8d6e5", marginTop: 2 }}>
                            {lastStatus.operation} • {lastStatus.hit ? "Saved ~2.5s" : "Called Gemini API"}
                        </div>
                    </div>
                </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 12 }}>
                <div className="metric">
                    <div className="val" style={{ color: "#e9eef6" }}>
                        {stats.total_entries || 0}
                    </div>
                    <div className="label" style={{ color: "#9fb0d8" }}>Cached Items</div>
                </div>
                <div className="metric">
                    <div className="val" style={{ color: "#e9eef6" }}>
                        {stats.total_size_kb || 0} KB
                    </div>
                    <div className="label" style={{ color: "#9fb0d8" }}>Disk Usage</div>
                </div>
                <div className="metric">
                    <div className="val" style={{ color: "#4ade80" }}>
                        ${costSaved}
                    </div>
                    <div className="label" style={{ color: "#9fb0d8" }}>Est. Saved</div>
                </div>
            </div>

            {stats.by_operation && Object.keys(stats.by_operation).length > 0 && (
                <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 13, color: "#9fb0d8", marginBottom: 6 }}>
                        By Operation:
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {Object.entries(stats.by_operation).map(([op, count]) => (
                            <div
                                key={op}
                                style={{
                                    padding: "4px 10px",
                                    background: "rgba(255,255,255,0.03)",
                                    borderRadius: 6,
                                    fontSize: 12,
                                    border: "1px solid rgba(255,255,255,0.05)",
                                    color: "#e9eef6"
                                }}
                            >
                                <strong style={{ color: "#fff" }}>{op}</strong>: {count}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button
                    className="small-btn"
                    onClick={() => clearCache()}
                    disabled={loading}
                    style={{ flex: 1, color: "#e9eef6" }}
                >
                    {loading ? "Clearing..." : "🗑️ Clear All"}
                </button>
                <button
                    className="small-btn"
                    onClick={() => clearCache("classify")}
                    disabled={loading}
                    style={{ flex: 1, color: "#e9eef6" }}
                >
                    Clear Classify
                </button>
                <button
                    className="small-btn"
                    onClick={() => clearCache("extract")}
                    disabled={loading}
                    style={{ flex: 1, color: "#e9eef6" }}
                >
                    Clear Extract
                </button>
            </div>

            {message && (
                <div style={{
                    marginTop: 12,
                    padding: 8,
                    background: "rgba(74, 222, 128, 0.1)",
                    border: "1px solid rgba(74, 222, 128, 0.2)",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#4ade80"
                }}>
                    {message}
                </div>
            )}

            <div style={{
                marginTop: 12,
                fontSize: 11,
                color: "#9fb0d8",
                padding: 8,
                background: "rgba(255,255,255,0.02)",
                borderRadius: 6
            }}>
                💡 <strong style={{ color: "#e9eef6" }}>Tip:</strong> Cache hits save ~2-3 seconds per request and reduce API costs.
            </div>
        </div>
    );
}