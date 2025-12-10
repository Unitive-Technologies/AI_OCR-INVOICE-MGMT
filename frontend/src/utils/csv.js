export function jsonToCSV(arr) {
    if (!Array.isArray(arr)) arr = [arr];
    const keys = Array.from(
        new Set(arr.flatMap((r) => Object.keys(r)))
    );
    const lines = [keys.join(",")];
    for (const row of arr) {
        const vals = keys.map((k) => {
            const v = row[k] ?? "";
            const s = typeof v === "object" ? JSON.stringify(v) : String(v);
            // escape quotes
            return `"${s.replace(/"/g, '""')}"`;
        });
        lines.push(vals.join(","));
    }
    return lines.join("\n");
}
