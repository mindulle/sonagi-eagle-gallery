let offset = 0;
let currentSearch = '';
let isLoading = false;
let hasMore = true;
let totalItems = 0;

window.onload = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const querySearch = urlParams.get('search');
    if (querySearch) {
        currentSearch = querySearch;
        document.getElementById('search').value = currentSearch;
    }

    // CEO-228: Load Sidebar Data
    loadSidebarFilters();

    loadItems();
};

async function loadSidebarFilters() {
    try {
        const [tagsRes, extsRes] = await Promise.all([fetch('/api/tags'), fetch('/api/exts')]);

        const tags = await tagsRes.json();
        const exts = await extsRes.json();

        const tagList = document.getElementById('tag-list');
        tagList.innerHTML = '';
        for (const t of tags) {
            const li = document.createElement('li');
            const label = document.createElement('span');
            label.textContent = `# ${t.tag}`;
            const count = document.createElement('span');
            count.className = 'count';
            count.textContent = t.count;
            li.appendChild(label);
            li.appendChild(count);
            li.onclick = () => setFilter(t.tag);
            tagList.appendChild(li);
        }

        const extList = document.getElementById('ext-list');
        extList.innerHTML = '';
        for (const e of exts) {
            const li = document.createElement('li');
            const label = document.createElement('span');
            label.textContent = `. ${e.ext.toUpperCase()}`;
            const count = document.createElement('span');
            count.className = 'count';
            count.textContent = e.count;
            li.appendChild(label);
            li.appendChild(count);
            li.onclick = () => setFilter(e.ext);
            extList.appendChild(li);
        }
    } catch (e) {
        console.error('Failed to load sidebar filters:', e);
        document.getElementById('tag-list').innerHTML =
            '<li class="loading-text" style="color:red;">Error loading tags</li>';
        document.getElementById('ext-list').innerHTML =
            '<li class="loading-text" style="color:red;">Error loading exts</li>';
    }
}

function setFilter(term) {
    document.getElementById('search').value = term;
    searchItems();
}

async function loadItems() {
    if (isLoading || !hasMore) return;
    isLoading = true;
    document.getElementById('loading').style.display = 'flex';

    try {
        const res = await fetch(
            `/api/items?limit=50&offset=${offset}&search=${encodeURIComponent(currentSearch)}`
        );
        const data = await res.json();

        totalItems = data.total;
        const items = data.items;

        const gallery = document.getElementById('gallery');
        const stats = document.getElementById('stats');

        if (offset === 0) {
            gallery.innerHTML = '';
            stats.innerHTML = '';

            const foundSpan = document.createElement('span');
            foundSpan.innerHTML = `Found <strong>${totalItems}</strong> items`;
            stats.appendChild(foundSpan);

            if (currentSearch) {
                const searchSpan = document.createElement('span');
                searchSpan.textContent = ` for "${currentSearch}"`;
                stats.appendChild(searchSpan);
            }

            if (totalItems === 0) {
                gallery.innerHTML =
                    '<div class="no-results">No items found matching your search.</div>';
            }
        }

        if (items.length < 50) {
            hasMore = false;
        }

        for (const item of items) {
            const card = document.createElement('div');
            card.className = 'card';
            card.onclick = () => openModal(item.id);

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

            if (item.ext) {
                const extSpan = document.createElement('span');
                extSpan.className = 'tag tag-ext';
                extSpan.textContent = item.ext.toUpperCase();
                tagsContainer.appendChild(extSpan);
            }

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
        const stats = document.getElementById('stats');
        stats.innerHTML = '';
        const errorSpan = document.createElement('span');
        errorSpan.style.color = 'red';
        errorSpan.textContent = 'Error loading items. Please try again.';
        stats.appendChild(errorSpan);
    } finally {
        isLoading = false;
        document.getElementById('loading').style.display = 'none';
    }
}

function searchItems() {
    currentSearch = document.getElementById('search').value;
    offset = 0;
    hasMore = true;

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

/* CEO-229: Lightbox Modal Logic */
async function openModal(itemId) {
    const lightbox = document.getElementById('lightbox');
    const img = document.getElementById('modal-img');

    lightbox.classList.add('active');
    img.src = '';
    document.getElementById('modal-title').textContent = 'Loading...';
    document.getElementById('modal-ext').textContent = '...';
    document.getElementById('modal-url').textContent = '';
    document.getElementById('modal-url').removeAttribute('href');
    document.getElementById('modal-tags').innerHTML = '';
    document.getElementById('modal-annotation').textContent = '';

    img.src = `/api/image/${itemId}/original`;

    try {
        const res = await fetch(`/api/items/${itemId}`);
        const item = await res.json();

        document.getElementById('modal-title').textContent = item.name || 'Untitled';
        document.getElementById('modal-ext').textContent = (item.ext || 'Unknown').toUpperCase();

        const urlEl = document.getElementById('modal-url');
        if (item.url && (item.url.startsWith('http://') || item.url.startsWith('https://'))) {
            urlEl.textContent = item.url;
            urlEl.href = item.url;
            urlEl.target = '_blank';
            urlEl.rel = 'noopener noreferrer';
        } else {
            urlEl.textContent = 'N/A';
            urlEl.removeAttribute('href');
        }

        const tagsContainer = document.getElementById('modal-tags');
        tagsContainer.innerHTML = '';
        for (const t of item.tags) {
            const span = document.createElement('span');
            span.className = 'tag';
            span.textContent = t;
            tagsContainer.appendChild(span);
        }

        document.getElementById('modal-annotation').textContent =
            item.annotation || 'No notes available.';

        const originalLink = document.getElementById('modal-original-link');
        originalLink.href = `/api/image/${itemId}/original`;
        originalLink.target = '_blank';
        originalLink.rel = 'noopener noreferrer';
    } catch (e) {
        console.error('Failed to fetch item details', e);
        document.getElementById('modal-title').textContent = 'Error loading details';
    }
}

function closeModal() {
    document.getElementById('lightbox').classList.remove('active');
    document.getElementById('modal-img').src = '';
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});
