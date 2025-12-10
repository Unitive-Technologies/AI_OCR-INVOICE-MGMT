import axios from "axios";

const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
    timeout: 60000,
});

export async function uploadInvoice(file) {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await API.post("/api/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
    });
    return resp.data;
}

// run OCR -> POST /api/ocr/{file_id}
export async function runOCR(fileId) {
    const resp = await API.post(`/api/ocr/${fileId}`);
    return resp.data;
}

// run detect -> POST /api/detect?file_id=...
export async function runDetect(fileId, overrideType = "") {
    const params = { file_id: fileId };
    if (overrideType) params.override_type = overrideType;
    const resp = await API.post("/api/detect", null, { params });
    return resp.data;
}

// run extract -> POST /api/extract/{file_id}?include_summary=true&include_embeddings=true
export async function runExtract(fileId, include_summary = true, include_embeddings = false) {
    const params = {
        include_summary: include_summary ? "true" : "false",
        include_embeddings: include_embeddings ? "true" : "false",
    };
    const resp = await API.post(`/api/extract/${fileId}`, null, { params });
    return resp.data;
}
