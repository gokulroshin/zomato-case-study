/**
 * api.js - Handles communication with the FastAPI backend.
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

/**
 * Fetches available locations, cuisines, and budget tiers for the form.
 * @returns {Promise<Object>} Metadata object
 */
async function fetchMetadata() {
    try {
        const response = await fetch(`${API_BASE_URL}/metadata`);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch metadata:', error);
        throw error;
    }
}

/**
 * Submits user preferences to the Groq-powered recommendation engine.
 * @param {Object} preferences User preferences 
 * @returns {Promise<Object>} Recommendation results
 */
async function fetchRecommendations(preferences) {
    try {
        const response = await fetch(`${API_BASE_URL}/recommend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        });

        const data = await response.json();

        if (!response.ok) {
            // Check if backend returned a user-friendly error message
            if (data.detail) {
                throw new Error(data.detail);
            }
            throw new Error(`Server returned status ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        throw error;
    }
}
