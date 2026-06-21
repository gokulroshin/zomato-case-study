/**
 * app.js - Main application logic for UI interactions and state management.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // DOM Elements
    const form = document.getElementById('preferences-form');
    const locationSelect = document.getElementById('location');
    const budgetSlider = document.getElementById('budget');
    const budgetValLabel = document.getElementById('budget-val');
    const dietSelect = document.getElementById('diet');
    const cuisineSelect = document.getElementById('cuisine');
    const minRatingSlider = document.getElementById('min-rating');
    const ratingValLabel = document.getElementById('rating-val');
    
    // States
    const loadingState = document.getElementById('loading-state');
    const errorState = document.getElementById('error-state');
    const errorMsg = document.getElementById('error-msg');
    const resultsState = document.getElementById('results-state');
    const emptyState = document.getElementById('empty-state');
    
    // Results DOM
    const summaryText = document.getElementById('summary-text');
    const metaStats = document.getElementById('meta-stats');
    const recommendationsGrid = document.getElementById('recommendations-grid');


    // Initialize the app by fetching metadata
    try {
        const metadata = await fetchMetadata();
        populateForm(metadata);
    } catch (error) {
        showError("Failed to connect to the backend. Please ensure the server is running.");
    }

    function populateForm(metadata) {
        // 1. Populate Locations
        locationSelect.innerHTML = '<option value="" disabled selected>Select a location</option>';
        metadata.locations.forEach(loc => {
            const option = document.createElement('option');
            option.value = loc;
            option.textContent = loc;
            locationSelect.appendChild(option);
        });

        // 2. Populate Cuisines
        cuisineSelect.innerHTML = '<option value="" disabled selected>Select a cuisine</option>';
        if (metadata.cuisines) {
            metadata.cuisines.forEach(c => {
                const option = document.createElement('option');
                option.value = c;
                option.textContent = c.charAt(0).toUpperCase() + c.slice(1);
                cuisineSelect.appendChild(option);
            });
        }
    }

    // Update rating label on slider change
    minRatingSlider.addEventListener('input', (e) => {
        ratingValLabel.textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Update budget label on slider change
    budgetSlider.addEventListener('input', (e) => {
        budgetValLabel.textContent = e.target.value;
    });

    // Handle Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Hide all previous states, show loading
        emptyState.classList.add('hidden');
        errorState.classList.add('hidden');
        resultsState.classList.add('hidden');
        loadingState.classList.remove('hidden');
        
        // Gather values
        const location = locationSelect.value;
        const budget = parseFloat(budgetSlider.value);
        const diet = dietSelect.value;
        const cuisine = cuisineSelect.value;
        const minRating = parseFloat(minRatingSlider.value);
        const additionalPrefs = document.getElementById('additional').value.trim();

        if (!location) {
            showError("Please select a location.");
            return;
        }

        const payload = {
            location: location,
            budget: budget,
            diet: diet,
            cuisine: cuisine,
            min_rating: minRating,
            additional_preferences: additionalPrefs,
            top_n: 5
        };

        try {
            // Fetch recommendations
            const data = await fetchRecommendations(payload);
            renderResults(data);
        } catch (error) {
            showError(error.message);
        }
    });

    function showError(message) {
        loadingState.classList.add('hidden');
        resultsState.classList.add('hidden');
        emptyState.classList.add('hidden');
        errorState.classList.remove('hidden');
        errorMsg.innerHTML = message;
    }

    function renderResults(data) {
        loadingState.classList.add('hidden');
        errorState.classList.add('hidden');
        emptyState.classList.add('hidden');
        resultsState.classList.remove('hidden');

        // Populate Summary
        summaryText.textContent = data.summary;
        metaStats.textContent = `Analyzed ${data.candidates_considered} candidate restaurants in ${(data.latency_ms / 1000).toFixed(2)} seconds via Groq API.`;

        // Clear grid
        recommendationsGrid.innerHTML = '';

        // Render Cards
        data.recommendations.forEach(rec => {
            const card = document.createElement('div');
            card.className = 'restaurant-card';
            
            card.innerHTML = `
                <div class="card-header">
                    <h2>${rec.restaurant_name}</h2>
                    <span class="rank-badge">#${rec.rank}</span>
                </div>
                
                <div class="card-stats">
                    <div class="stat">
                        <span class="stat-icon">★</span>
                        <span>${rec.rating ? rec.rating : 'N/A'}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">₹</span>
                        <span>${rec.estimated_cost ? rec.estimated_cost + ' for two' : 'N/A'}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-icon">🍽️</span>
                        <span>${rec.cuisine}</span>
                    </div>
                </div>

                <div class="explanation-box">
                    <strong>Why this fits:</strong><br>
                    ${rec.explanation}
                </div>
            `;
            
            recommendationsGrid.appendChild(card);
        });
    }
});
