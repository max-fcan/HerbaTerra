'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const gradientBg = document.querySelector('.gradient-bg');
  const interBubble = gradientBg?.querySelector('.interactive');
  if (!gradientBg || !interBubble) return;

  let curX = window.innerWidth / 2;
  let curY = window.innerHeight / 2;
  let tgX = curX;
  let tgY = curY;

  function move() {
    curX += (tgX - curX) / 20;
    curY += (tgY - curY) / 20;
    interBubble.style.left = `${Math.round(curX)}px`;
    interBubble.style.top = `${Math.round(curY)}px`;
    requestAnimationFrame(move);
  }

  window.addEventListener('mousemove', event => {
    const rect = gradientBg.getBoundingClientRect();
    tgX = event.clientX - rect.left;
    tgY = event.clientY - rect.top;
  });

  move();
});
