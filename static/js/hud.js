// static/js/hud.js

document.addEventListener('DOMContentLoaded', () => {
    const feed = document.getElementById('event-feed');
    const container = document.getElementById('event-container');

    const FEED_URL = feed ? feed.dataset.eventsUrl : null;

    if (!FEED_URL) {
        console.warn('Event feed URL not found');
        return;
    }

    let lastEventCount = 0;

    async function fetchEvents() {
        try {
            const response = await fetch(FEED_URL, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!response.ok) throw new Error('Network error');

            const json = await response.json();
            const events = json.events;

            if (events.length === lastEventCount) return;
            lastEventCount = events.length;

            container.innerHTML = '';
            if (events.length === 0) {
                container.innerHTML = `
                    <div class="event-item event-info">
                        <span class="event-time">--:--:--</span>
                        <span class="event-message">Новых событий нет</span>
                    </div>`;
                return;
            }

            events.forEach(evt => {
                const el = document.createElement('div');
                el.className = `event-item event-${evt.level}`;
                el.innerHTML = `
                    <span class="event-time">${evt.time}</span>
                    <span class="event-message">${evt.message}</span>
                `;
                container.appendChild(el);
            });

        } catch (err) {
            console.warn('Event feed error:', err);
        }
    }

    fetchEvents();
    setInterval(fetchEvents, 3000);
});