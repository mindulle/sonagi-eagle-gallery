let offset = 0;
let currentSearch = '';
let isLoading = false;

window.onload = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const querySearch = urlParams.get('search');
    if (querySearch) {
        currentSearch = querySearch;
        document.getElementById('search').value = currentSearch;
    }
    loadItems();
};

async function loadItems() {
    if (isLoading) return;
    isLoading = true;
    document.getElementById('loading').style.display = 'block';

    try {
        const res = await fetch(
            `/api/items?limit=50&offset=${offset}&search=${encodeURIComponent(currentSearch)}`
        );
        const items = await res.json();

        const gallery = document.getElementById('gallery');
        if (offset === 0) gallery.innerHTML = '';

        for (const item of items) {
            const card = document.createElement('div');
            card.className = 'card';
            card.onclick = () => window.open(`/api/image/${item.id}/original`, '_blank');

            const imgSrc = item.has_thumbnail
                ? `/api/image/${item.id}/thumbnail`
                : `/api/image/${item.id}/original`;

            const img = document.createElement('img');
            img.src = imgSrc;
            img.loading = 'lazy';
            img.onerror = () => {
                img.style.display = 'none';
            };

            const info = document.createElement('div');
            info.className = 'card-info';

            const title = document.createElement('h3');
            title.className = 'card-title';
            title.textContent = item.name || 'Untitled';

            const tagsContainer = document.createElement('div');
            for (const t of item.tags.slice(0, 3)) {
                const tagSpan = document.createElement('span');
                tagSpan.className = 'tag';
                tagSpan.textContent = t;
                tagsContainer.appendChild(tagSpan);
            }

            info.appendChild(title);
            info.appendChild(tagsContainer);

            card.appendChild(img);
            card.appendChild(info);
            gallery.appendChild(card);
        }

        offset += 50;
    } catch (e) {
        console.error(e);
    } finally {
        isLoading = false;
        document.getElementById('loading').style.display = 'none';
    }
}

function searchItems() {
    currentSearch = document.getElementById('search').value;
    offset = 0;

    const newUrl = new URL(window.location.href);
    if (currentSearch) {
        newUrl.searchParams.set('search', currentSearch);
    } else {
        newUrl.searchParams.delete('search');
    }
    window.history.pushState({}, '', newUrl.toString());

    loadItems();
}

window.onscroll = () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
        loadItems();
    }
};
