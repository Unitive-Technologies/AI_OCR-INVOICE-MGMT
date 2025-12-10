import React from "react";

export default function DragDrop({ onFile }) {
    const handleDrop = (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files?.[0];
        if (file) onFile(file);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    return (
        <div
            className="drag-drop"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            title="Drop invoice here"
        >
            <div className="drag-content">
                <div className="drag-icon">📁</div>
                <div className="drag-text">Drag & drop invoice here — or click Choose File</div>
            </div>
        </div>
    );
}
