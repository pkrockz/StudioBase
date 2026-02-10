document.addEventListener("DOMContentLoaded", function () {
    const clientSelect = document.querySelector('select[name="client_name"]');
    const projectSelect = document.querySelector('select[name="project_title"]');

    if (!clientSelect || !projectSelect) return;

    function filterProjects() {
        const selectedClient = clientSelect.value;

        Array.from(projectSelect.options).forEach(option => {
            const projectClient = option.getAttribute("data-client");

            // Always allow General Service
            if (option.value === "General Service") {
                option.hidden = false;
                return;
            }

            option.hidden = projectClient !== selectedClient;
        });

        projectSelect.value = "";
    }

    clientSelect.addEventListener("change", filterProjects);

    // Run once on load (important for prefills)
    filterProjects();
});
