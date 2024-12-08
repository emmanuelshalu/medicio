document.getElementById('department').addEventListener('change', function() {
    const departmentId = this.value;
    const doctorSelect = document.getElementById('doctor');
    
    // Clear current options
    doctorSelect.innerHTML = '<option value="">Select Doctor</option>';
    
    if (departmentId) {
        fetch(`/get-doctors/${departmentId}/`)
            .then(response => response.json())
            .then(data => {
                data.forEach(doctor => {
                    const option = document.createElement('option');
                    option.value = doctor.id;
                    option.textContent = `Dr. ${doctor.doc_name}`;
                    doctorSelect.appendChild(option);
                });
            });
    }
}); 