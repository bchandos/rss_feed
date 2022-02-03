let _state = {
    showRead: window.location.toString().includes('show_read=True'),
};

const delegator = (parentSelector, childSelector, eventName, callback) => {
    const parents = document.querySelectorAll(parentSelector);
    for (let parent of parents) {
        parent.addEventListener(eventName, (e) => {
            // console.log(e.target);
            if (e.target.matches(childSelector)) {
                callback(e);
            }
        })
    }
}

const showLoader = (target) => {
    if (target instanceof HTMLElement) {
        target.classList.add('w3-disabled');
        if (target instanceof HTMLAnchorElement) {
            const url = target.getAttribute('href');
            if (url) {
                target.removeAttribute('href');
                target.dataset.originalUrl = url;
            }
        }
    }
    const loaderBgDiv = document.createElement('div');
    loaderBgDiv.id = 'loader-bg';
    const loaderSlowDiv = document.createElement('div');
    loaderSlowDiv.id = 'loader-animation-slow';
    const loaderFastDiv = document.createElement('div');
    loaderFastDiv.id = 'loader-animation-fast';
    loaderBgDiv.appendChild(loaderSlowDiv);
    loaderBgDiv.appendChild(loaderFastDiv);
    const firstChild = document.body.firstElementChild;
    document.body.insertBefore(loaderBgDiv, firstChild);
}

const hideLoader = (target) => {
    if (target) {
        // re-enable the target
        target.classList.remove('w3-disabled');
        if (target instanceof HTMLAnchorElement) {
            const url = target.dataset.originalUrl;
            if (url) {
                target.setAttribute('href', url);
            }
        }
    }
    const loaderBgDiv = document.getElementById('loader-bg');
    if (loaderBgDiv) {
        loaderBgDiv.remove();
    }
}


// Delete feed
const _deleteFeedBtn = document.getElementById('delete-feed-button');
const deleteFeedBtns = [_deleteFeedBtn, ...document.getElementsByClassName('delete-feed-button')];
for (const deleteFeedBtn of deleteFeedBtns) {
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
}

const markRead = async (e) => {
    const target = e.target;
    showLoader(target);
    let label;
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
            article.remove();
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
    hideLoader(target);
}

delegator('#main-content', '.marker', 'click', markRead)

// Mark All Read
const markAllRead = async (e) => {
    // Identify all unread items on the page, and mark them read
    const unreadElems = document.querySelectorAll('.unread');
    const unreadIds = Array.from(unreadElems).map(e => parseInt(e.id));
    if (unreadIds.length) {
        const response = await fetch(`${$SCRIPT_ROOT}/mark_read_all`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                unreadIds
            })
        });
        const json = await response.json();
        if (json.status === 'done') {
            window.location.reload();
        }
    }
}
const markAllReadBtn = document.getElementById('mark-all-read');
if (markAllReadBtn) {
    markAllReadBtn.addEventListener('click', markAllRead);
}


const addBookmark = async (e) => {
    // Because there is a nested span that may fire the click event
    // we need to look for the closest elements with class bookmark
    const target = e.target.closest('.bookmark');
    const response = await fetch(`${$SCRIPT_ROOT}/_bookmark`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            id: target.dataset.id,
            marked: target.dataset.marked
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
}

delegator('#main-content', '.bookmark, .bookmark > i', 'click', addBookmark)

const moreArticles = async (e) => {
    const target = e.target;
    showLoader(target);
    const lastItemId = e.target.dataset.lastItemId;
    const sortOrder = e.target.dataset.sortOrder;
    const showRead = e.target.dataset.showRead;
    const feedId = e.target.dataset.feedId || '';
    const startAt = document.querySelectorAll('article.item').length + 1;
    const response = await fetch(`${$SCRIPT_ROOT}/_more_articles?feed_id=${feedId}&last_item_id=${lastItemId}&sort_order=${sortOrder}&show_read=${showRead}&start_at=${startAt}`);
    const json = await response.json();
    const replaceTarget = document.getElementById('more-articles-target');
    replaceTarget.outerHTML = json.new_contents;
    hideLoader(target);
}

delegator('#main-content', '#more-articles-btn', 'click', moreArticles)

const showArticlePreview = async (e) => {
    const target = e.target.closest('.article-preview')
    showLoader(target);
    const articleId = target.dataset.id;
    const response = await fetch(`${$SCRIPT_ROOT}/_article_contents?id=${articleId}`);
    const json = await response.json();
    const contentTarget = document.getElementById('article-content-target');
    const contentModal = document.getElementById('article-content-modal');
    const contentLink = document.getElementById('link-article-content-modal');
    contentTarget.innerHTML = json.article_contents;
    contentLink.setAttribute('href', json.link);
    contentModal.classList.remove('w3-hide');
    contentModal.classList.add('w3-show');
    hideLoader(target);
}

delegator('#main-content', '.article-preview, .article-preview h3, .article-preview span', 'click', showArticlePreview)

const modalCloseBtn = document.getElementById('close-article-content-modal');
modalCloseBtn.addEventListener('click', (e) => {
    const contentTarget = document.getElementById('article-content-target');
    const contentModal = document.getElementById('article-content-modal');
    contentModal.classList.add('w3-hide');
    contentModal.classList.remove('w3-show');
    contentTarget.innerHTML = '';
})

// Feed selector
const feedSelector = document.getElementById('feed-selector');
if (feedSelector) {
    feedSelector.addEventListener('change', (e) => {
        if (e.target.value) {
            window.location = `/${e.target.value}`;
        }
    })
}

// Add a loader bar at the top of the screen so when in 
// PWA mode, there is some user feedback that something is happening
window.addEventListener('beforeunload', showLoader)


