document.addEventListener("DOMContentLoaded", function() {
    var modalElement = document.getElementById("addInvoiceModal");
    if (!modalElement) return;

    var prefillActive = modalElement.dataset.prefillActive === "true";
    var prefillClient = modalElement.dataset.prefillClient;
    var prefillProject = modalElement.dataset.prefillProject;

    if (!prefillActive) return;

    var invoiceModal = new bootstrap.Modal(modalElement);
    invoiceModal.show();

    var clientSelect = modalElement.querySelector('select[name="client_name"]');
    if (clientSelect && prefillClient) {
        clientSelect.value = prefillClient;
    }

    var projectSelect = modalElement.querySelector('select[name="project_title"]');
    if (projectSelect && prefillProject) {
        projectSelect.value = prefillProject;
    }
});
