
    let lastMember = '';  // Variable to store the last member who joined

    function showMemberNotification(member) {
        if (Notification.permission === 'granted') {
            new Notification('New Member Joined', { body: `${member} has joined your farm!` });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification('New Member Joined', { body: `${member} has joined your farm!` });
                }
            });
        }
    }

    function checkNewMembers() {
        fetch('/check_new_members')
            .then(response => response.json())
            .then(data => {
                if (data.new_member && data.new_member !== lastMember) {
                    // Notify if a new member joined and is different from the last one
                    showMemberNotification(data.new_member);
                    lastMember = data.new_member;  // Update the last member
                }
            })
            .catch(error => {
                console.error('Error checking for new members:', error);
            });
    }

    // Polling the server every 30 seconds to check for new members
    setInterval(checkNewMembers, 30000);

    // Request permission for notifications when the page loads
    document.addEventListener('DOMContentLoaded', function() {
        if (Notification.permission !== 'granted') {
            Notification.requestPermission();
        }
    });
