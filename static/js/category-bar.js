function addItem() {
    var scrollableBar = document.getElementById('scrollable-bar');
    var newItem = document.createElement('div');
    newItem.classList.add('scrollable-item');
    newItem.textContent = 'Item ' + (scrollableBar.childElementCount + 1);
    
    // Insert the new item at the beginning of the bar
    scrollableBar.insertBefore(newItem, scrollableBar.firstChild);
}
