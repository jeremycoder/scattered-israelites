// Word detail panel open/close
function openWordPanel() {
  document.getElementById('word-panel').classList.add('open');
  document.getElementById('word-panel-overlay').classList.add('open');
}

function closeWordPanel() {
  document.getElementById('word-panel').classList.remove('open');
  document.getElementById('word-panel-overlay').classList.remove('open');
  document.querySelectorAll('.word-cell.active').forEach(el => el.classList.remove('active'));
}

// Open panel after HTMX swaps in word detail content
document.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target.id === 'word-panel-content') {
    openWordPanel();
  }
});
