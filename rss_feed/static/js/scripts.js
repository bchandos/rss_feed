let _state = {
    showRead: false,
};


// Delete feed
const deleteFeedBtn = document.getElementById('delete-feed-button');
if (deleteFeedBtn) {
    deleteFeedBtn.addEventListener('click', (e) => {
        const feedId = e.target.dataset.feedId;
        const deleteWarningModal = document.getElementById('delete-warning-modal');
        const scaryDeleteBtn = document.getElementById('bigScaryDeleteButton');
        deleteWarningModal.style.display = 'block';
        scaryDeleteBtn.addEventListener('click', (e) => {
            window.location.href = `${$SCRIPT_ROOT}/${feedId}/delete`; 
        })
    })
}

// Mark Read
const markers = document.querySelectorAll('.marker');
for (let marker of markers) {
    marker.addEventListener('click', async (e) => {
        let label;
        const target = e.target;
        const response = await fetch(`${$SCRIPT_ROOT}/_mark_read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: target.dataset.id
            })
        });
        const json = await response.json();
        const article = target.closest('article');
        if (!_state.showRead && json.read === 'Read') {
            article.addEventListener('transitionend', (e) => {
                article.classList.remove('unread');
                article.classList.add('read', 'w3-hide', 'w3-border-pale-blue')
            });
            article.style.opacity = 0;
            label = 'Mark Unread';
        } else if (json.read === 'Read') {
            article.classList.remove('unread', 'w3-border-light-blue');
            article.classList.add('read', 'w3-border-pale-blue');
            label = 'Mark Unread';
        } else {
            article.classList.remove('read', 'w3-border-pale-blue');
            article.classList.add('unread', 'w3-border-light-blue');
            label = 'Mark Read';
        }
        target.innerText = label;
    });
}

// Bookmarks
const bookmarks = document.querySelectorAll('.bookmark');
for (let bookmark of bookmarks) {
    bookmark.addEventListener('click', async (e) => {
        const target = e.target;
        const response = await fetch(`${$SCRIPT_ROOT}/_bookmark`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id: bookmark.dataset.id,
                marked: bookmark.dataset.marked
            })
        });
        const json = await response.json();
        if (json.bookmark === 'true') {
            target.firstElementChild.innerText = 'bookmark';
            target.dataset.marked = 'true';
        } else {
            target.firstElementChild.innerText = 'bookmark_border';
            target.dataset.marked = 'false';
        }
    })
}

// Show / hide
const showReadBtn = document.getElementById('show_read');
showReadBtn.addEventListener('click', (e) => {
    _state.showRead = !_state.showRead;
    const articlesBtn = document.getElementById('more-articles-btn');
    if (_state.showRead) {
        const readArticles = document.querySelectorAll('article.read');
        for (let readArticle of readArticles) {
            readArticle.style.opacity = 1;
            readArticle.classList.remove('w3-hide');
        }
        e.target.innerText = 'Hide Read';
        if (articlesBtn.dataset.moreUnread === 'True') {
            articlesBtn.classList.add('w3-show');
            articlesBtn.classList.remove('w3-hide');
        }
    } else {
        const readArticles = document.querySelectorAll('article.read');
        for (let readArticle of readArticles) {
            readArticle.classList.add('w3-hide');
        }
        e.target.innerText = 'Show Read';
        if (articlesBtn.dataset.moreUnread === 'True' && articlesBtn.dataset.moreRead === 'False') {
            articlesBtn.classList.add('w3-hide');
            articlesBtn.classList.remove('w3-show');
        }
    }
})


// Show more button...
const moreArticlesBtn = document.getElementById('more-articles-btn');

// Set initial visibility
if (moreArticlesBtn.dataset.moreRead === 'True') {
    moreArticlesBtn.classList.add('w3-show');
    moreArticlesBtn.classList.remove('w3-hide');
} else if (moreArticlesBtn.dataset.moreUnread === 'True' && _state.showRead) {
    moreArticlesBtn.classList.add('w3-show');
    moreArticlesBtn.classList.remove('w3-hide');
} else {
    moreArticlesBtn.classList.add('w3-hide');
    moreArticlesBtn.classList.remove('w3-show');
}

// Handle click
moreArticlesBtn.addEventListener('click', async (e) => {
    const startAt = e.target.dataset.articleCount;
    const feedId = e.target.dataset.feedId || '';
    const response = await fetch(`${$SCRIPT_ROOT}/_more_articles?feed_id=${feedId}&start_at=${startAt}`);
    const text = await response.text();
    const replaceTarget = document.getElementById('more-articles-target');
    replaceTarget.outerHTML = text;
    // New articles will be hidden by default; set visibility based on current state
    const readArticles = document.querySelectorAll('article.read');
    if (_state.showRead) {
        for (let readArticle of readArticles) {
            readArticle.classList.remove('w3-hide');
        }
    } else {
        for (let readArticle of readArticles) {
            readArticle.classList.add('w3-hide');
        }
        e.target.innerText = 'Show Read';
    }
})

// Article preview modal
const articlePreviewLinks = document.querySelectorAll('.article-preview');
for (let link of articlePreviewLinks) {
    link.addEventListener('click', async (e) => {
        const articleId = e.currentTarget.dataset.id;
        const response = await fetch(`${$SCRIPT_ROOT}/_article_contents?id=${articleId}`);
        const json = await response.json();
        const contentTarget = document.getElementById('article-content-target');
        const contentModal = document.getElementById('article-content-modal');
        contentTarget.innerHTML = json.article_contents;
        contentModal.classList.remove('w3-hide');
        contentModal.classList.add('w3-show');
    })
}

const modalCloseBtn = document.getElementById('close-article-content-modal');
modalCloseBtn.addEventListener('click', (e) => {
    const contentTarget = document.getElementById('article-content-target');
    const contentModal = document.getElementById('article-content-modal');
    contentModal.classList.add('w3-hide');
    contentModal.classList.remove('w3-show');
    contentTarget.innerHTML = '';
})
