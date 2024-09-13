 
    let currentStatus = 'member pending';

    function showNotification(message) {
        if (Notification.permission === 'granted') {
            new Notification('Status Update', { body: message });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification('Status Update', { body: message });
                }
            });
        }
    }

    function checkStatus() {
        fetch('/check_status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'member' && currentStatus === 'member pending') {
                    showNotification('Your status has been updated to "Member".');
                    currentStatus = 'member';
                }
            })
            .catch(error => {
                console.error('Error fetching status:', error);
            });
    }
 
    setInterval(checkStatus, 20000);

    document.addEventListener('DOMContentLoaded', function() {
        if (Notification.permission !== 'granted') {
            Notification.requestPermission();
        }
    });