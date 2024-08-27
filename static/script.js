document.addEventListener('DOMContentLoaded', () => {
    const popupContainer1 = document.getElementById('popup1');
    const closePopup1 = document.getElementById('close-popup1');
    const nextButton = document.getElementById('next');
    const iframe1 = document.getElementById('iframe1');
    const registerForm = document.getElementById('registerForm');

    closePopup1.addEventListener('click', () => {
        popupContainer1.classList.remove('active');
        iframe1.src = ''; // Reset iframe src when closing popup
    });

    nextButton.addEventListener('click', (event) => {
        event.preventDefault(); // Prevent default form submission

        // Handle form submission using Fetch API or AJAX
        const formData = new FormData(registerForm);

        fetch(registerForm.action, {
            method: registerForm.method,
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            // Assuming form submission is successful, show the popup with iframe
            popupContainer1.classList.add('active');
            iframe1.src = 'farmback.html'; // Set iframe src to the confirmation page URL
            console.log('Form submitted successfully');
            console.log(iframe1.src);
        })
        .catch(error => {
            console.error('Error:', error);
            // Handle error if form submission fails
        });
    });
});
