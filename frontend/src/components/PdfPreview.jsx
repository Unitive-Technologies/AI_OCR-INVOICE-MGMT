import React from "react";

export default function PdfPreview({ fileUrl }) {
    if (!fileUrl) return <div className="pdf-empty">No preview</div>;
    return (
        <div className="pdf-preview">
            {/* use iframe for pdf or img fallback */}
            {fileUrl.endsWith(".pdf") ? (
                <iframe className="pdf-frame" src={fileUrl} title="PDF preview" />
            ) : (
                <img className="pdf-img" src={fileUrl} alt="preview" />
            )}
        </div>
    );
}
