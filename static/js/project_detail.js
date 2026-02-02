/* static/js/project_detail.js */

document.addEventListener("DOMContentLoaded", function() {
    
    // Handle "Edit Task" Modal Population
    const editButtons = document.querySelectorAll('.edit-task-btn');
    const editModalElement = document.getElementById('editTaskModal');
    
    if (editModalElement) {
        editButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                // 1. Get data from the clicked button
                const taskId = this.getAttribute('data-task-id');
                const description = this.getAttribute('data-desc');
                const hours = this.getAttribute('data-hours');
                
                // 2. Find elements inside the modal
                const modalDescInput = editModalElement.querySelector('input[name="description"]');
                const modalHoursInput = editModalElement.querySelector('input[name="hours"]');
                const modalForm = editModalElement.querySelector('form');
                
                // 3. Populate values
                modalDescInput.value = description;
                modalHoursInput.value = hours;
                
                // 4. Update the form action dynamically to point to the correct task
                // We replace the placeholder '0000' with the actual ID
                const baseUrl = modalForm.getAttribute('data-base-action');
                modalForm.action = baseUrl.replace('TASK_ID_PLACEHOLDER', taskId);
            });
        });
    }
});