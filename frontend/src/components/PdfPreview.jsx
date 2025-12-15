import React from "react";

export default function PdfPreview({ fileUrl }) {
    if (!fileUrl) {
        return (
            <div className="pdf-empty" style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: 360,
                color: "#9fb0d8",
                fontSize: 14
            }}>
                No preview available
            </div>
        );
    }

    // Check if it's a PDF
    const isPdf = fileUrl.includes('.pdf') || fileUrl.startsWith('blob:');

    return (
        <div className="pdf-preview">
            {isPdf ? (
                <iframe
                    className="pdf-frame"
                    src={`${fileUrl}#toolbar=0&navpanes=0`}
                    title="PDF preview"
                    style={{
                        width: "100%",
                        height: "100%",
                        border: "none",
                        borderRadius: 8
                    }}
                />
            ) : (
                <img
                    className="pdf-img"
                    src={fileUrl}
                    alt="preview"
                    style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "contain",
                        borderRadius: 8
                    }}
                />
            )}
        </div>
    );
}