document.addEventListener('DOMContentLoaded', () => {
    const connectionUrlInput = document.getElementById('connection-url');
    const refreshBtn = document.getElementById('refresh-btn');
    const collectionsList = document.getElementById('collections-list');
    const documentsContent = document.getElementById('documents-content');
    const searchInput = document.getElementById('search-input');
    const knnInput = document.getElementById('knn-input');
    const searchBtn = document.getElementById('search-btn');

    let activeCollection = null;

    async function fetchCollections() {
        try {
            console.log('Fetching collections...');
            const baseUrl = connectionUrlInput.value;
            const response = await fetch(`${baseUrl}/api/v1/list-collections`);
            console.log('Response:', response);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const collections = await response.json();
            displayCollections(collections);
        } catch (error) {
            console.error('Error fetching collections:', error);
            collectionsList.innerHTML = `<div class="error">Error fetching collections: ${error.message}</div>`;
        }
    }

    async function fetchDocuments(collectionName) {
        try {
            const baseUrl = connectionUrlInput.value;
            const response = await fetch(`${baseUrl}/api/v1/collections/${collectionName}/documents`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const documents = await response.json();
            documentsContent.textContent = JSON.stringify(documents, null, 2);
        } catch (error) {
            console.error('Error fetching documents:', error);
            documentsContent.innerHTML = `<div class="error">Error fetching documents: ${error.message}</div>`;
        }
    }

    function displayCollections(collections) {
        collectionsList.innerHTML = '';
        collections.forEach(collection => {
            const div = document.createElement('div');
            div.className = 'collection-item';
            if (activeCollection === collection.name) {
                div.classList.add('active');
            }
            div.textContent = collection.name;
            div.addEventListener('click', () => {
                // Remove active class from all items
                document.querySelectorAll('.collection-item').forEach(item => {
                    item.classList.remove('active');
                });

                // Add active class to clicked item
                div.classList.add('active');
                activeCollection = collection.name;
                fetchDocuments(collection.name);
            });
            collectionsList.appendChild(div);
        });
    }

    async function searchNearestNeighbors() {
        if (!activeCollection) {
            documentsContent.innerHTML = '<div class="error">Please select a collection first</div>';
            return;
        }

        const query = searchInput.value.trim();
        if (!query) {
            documentsContent.innerHTML = '<div class="error">Please enter a search query</div>';
            return;
        }

        const knn = parseInt(knnInput.value);
        if (isNaN(knn) || knn < 1) {
            documentsContent.innerHTML = '<div class="error">Please enter a valid number for k-nearest neighbors</div>';
            return;
        }

        try {
            const baseUrl = connectionUrlInput.value;
            const response = await fetch(
                `${baseUrl}/api/v1/collections/${activeCollection}/${knn}/get_nearest_neighbors`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query })
                }
            );
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const documents = await response.json();
            documentsContent.textContent = JSON.stringify(documents, null, 2);
        } catch (error) {
            console.error('Error searching documents:', error);
            documentsContent.innerHTML = `<div class="error">Error searching documents: ${error.message}</div>`;
        }
    }

    // Event Listeners
    refreshBtn.addEventListener('click', fetchCollections);
    connectionUrlInput.addEventListener('change', fetchCollections);
    searchBtn.addEventListener('click', searchNearestNeighbors);
    searchInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            searchNearestNeighbors();
        }
    });

    // Initial fetch
    fetchCollections();
});
