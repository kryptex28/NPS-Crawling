const HREF_PREFIX = '/services/hub-flask';

const NAVIGATION_ITEMS = [
    {
        label: 'Search',
        href: `${HREF_PREFIX}/`
    },
    {
        label: 'Crawl',
        href: `${HREF_PREFIX}/crawl`
    },
    {
        label: 'Preprocessing',
        href: `${HREF_PREFIX}/preprocessing`
    },
    {
        label: 'Classification',
        href: `${HREF_PREFIX}/classification`
    },
    {
        label: 'Results',
        href: `${HREF_PREFIX}/results`
    },
    {
        label: 'Database',
        href: `${HREF_PREFIX}/database`
    }
];

const buildNavigationBar = () => {
    const currentPath = window.location.pathname.replace(/\/$/, '') || '/';

    const links = NAVIGATION_ITEMS.map(item => {
        const href = item.href.replace(/\/$/, '') || '/';
        const isActive = currentPath === href || currentPath.startsWith(href + '/');
        return `<a href="${item.href}" class="${isActive ? 'active' : ''}">${item.label}</a>`;
    }).join('');

    const bar = document.createElement('div');
    bar.id = 'site-navigation';
    bar.innerHTML = `
        <nav>${links}</nav>
    `;

    const container = document.querySelector('#navigation');
    if (container) {
        container.appendChild(bar);
    }
};

document.addEventListener('DOMContentLoaded', buildNavigationBar);