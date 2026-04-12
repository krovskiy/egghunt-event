const timerContainer = document.querySelector('.rules-timer');
const timerLabel = document.getElementById('rulesTimerLabel');
const timerValue = document.getElementById('rulesTimerValue');

if (timerContainer && timerLabel && timerValue) {
  const startDate = timerContainer.dataset.start;
  const endDate = timerContainer.dataset.end;

  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T23:59:59`);

  const pad = (value) => String(value).padStart(2, '0');

  const renderTimer = () => {
    const now = new Date();

    if (now < start) {
      const diff = start.getTime() - now.getTime();
      const days = Math.floor(diff / 86400000);
      const hours = Math.floor((diff % 86400000) / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);

      timerLabel.textContent = 'Event starts in';
      timerValue.textContent = `${days}d ${pad(hours)}h ${pad(minutes)}m ${pad(seconds)}s`;
      return;
    }

    if (now > end) {
      timerLabel.textContent = 'Event ended';
      timerValue.textContent = 'Thanks for hunting!';
      return;
    }

    const diff = end.getTime() - now.getTime();
    const days = Math.floor(diff / 86400000);
    const hours = Math.floor((diff % 86400000) / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    timerLabel.textContent = 'Event ends in';
    timerValue.textContent = `${days}d ${pad(hours)}h ${pad(minutes)}m ${pad(seconds)}s`;
  };

  renderTimer();
  setInterval(renderTimer, 1000);
}
