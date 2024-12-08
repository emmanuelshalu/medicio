document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('appointmentForm');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get the submit button
            const submitButton = form.querySelector('button[type="submit"]');
            // Disable the submit button to prevent double submission
            submitButton.disabled = true;
            
            // Create FormData object
            const formData = new FormData(form);
            
            // Send the form data using fetch
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    alert(data.message);
                    // Optional: Reset the form
                    form.reset();
                } else {
                    // Show error message
                    alert(data.message || 'An error occurred');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            })
            .finally(() => {
                // Re-enable the submit button
                submitButton.disabled = false;
            });
        });
    }
}); 