export async function saveExtractionToDB(result, file) {
    const db = window.db; // from CDN
    if (!db) {
        console.error("Firestore not initialized");
        return;
    }

    const doc = {
        file_name: file?.name || "unknown",
        created_at: new Date(),
        extraction: result.extraction || {},
        summary: result.summary || "",
        raw: result
    };

    try {
        const ref = await addDoc(collection(db, "invoices"), doc);
        console.log("Stored to Firestore:", ref.id);
    } catch (err) {
        console.error("Error saving:", err);
    }
}
