document.addEventListener("DOMContentLoaded", function() {
    // Select all progress bars
    const progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(bar => {
        // Get the target width from the inline style attribute (e.g., "width: 75%")
        const targetWidth = bar.getAttribute('style').match(/width:\s*(\d+)%/)[1] + '%';
        
        // Reset width to 0 first (to ensure animation plays)
        bar.style.width = '0%';
        
        // Small timeout to allow the browser to register the 0% before animating
        setTimeout(() => {
            bar.style.width = targetWidth;
        }, 100);
    });
});