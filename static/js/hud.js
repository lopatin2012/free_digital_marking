document.addEventListener('DOMContentLoaded', () => {
    const eventContainer = document.getElementById('event-container');

    // Подключаемся к SSE endpoint.
    const eventSource = new EventSource('{% url "event_stream" %}');

    eventSource.onmessage = function(event) {
        const events = JSON.parse(event.data);

        if (events.length > 0) {
            // Очищаем контейнер.
            eventContainer.innerHTML = '';

            // Добавляем последние 3 события (чтобы не загромождать).
            events.slice(0, 3).forEach((evt, index) => {
                const eventEl = document.createElement('div');
                eventEl.className = `event-item event-${evt.level}`;

                // Анимация появления для первого (нового) события.
                if (index === 0) {
                    eventEl.classList.add('event-new');
                }

                eventEl.innerHTML = `
                    <span class="event-time">${evt.timestamp}</span>
                    <span class="event-message">${evt.message}</span>
                `;

                eventContainer.appendChild(eventEl);
            });
        }
    };

    eventSource.onerror = function(err) {
        console.error('EventSource failed:', err);
        // Показываем ошибку
        eventContainer.innerHTML = `
            <div class="event-item event-error">
                <span class="event-time">--:--:--</span>
                <span class="event-message">Ошибка подключения к ленте событий</span>
            </div>
        `;
    };

    // Закрытие соединения при уходе со страницы.
    window.addEventListener('beforeunload', () => {
        eventSource.close();
    });
});
