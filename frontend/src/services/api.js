const API_URL = "http://127.0.0.1:8000/api/v1";

export async function analyzeJob(jobData) {
    const response = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(jobData)
    });

    if (!response.ok) {
        throw new Error("Failed to analyze job posting");
    }

    return await response.json();
}

export async function scrapeJobUrl(url) {
    const response = await fetch(`${API_URL}/scrape`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ url })
    });

    const result = await response.json();
    if (!response.ok || !result.success) {
        throw new Error(result.detail || "Failed to fetch job details from URL");
    }

    return result.data;
}