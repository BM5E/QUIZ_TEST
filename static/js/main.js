// main.js - Lightweight JavaScript functionality for BookQuiz

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltipTriggerList.length > 0) {
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
    
    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    if (popoverTriggerList.length > 0) {
        [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    }
    
    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.alert:not(.alert-permanent)');
    flashMessages.forEach(message => {
        setTimeout(() => {
            const alert = new bootstrap.Alert(message);
            alert.close();
        }, 5000);
    });
    
    // Lazy-load feather icons (defer non-critical)
    if (typeof feather !== 'undefined') {
        setTimeout(() => {
            feather.replace({
                'stroke-width': 1.5
            });
        }, 100);
    }
    
    // Quiz form validation
    const quizForm = document.getElementById('quizForm');
    if (quizForm) {
        quizForm.addEventListener('submit', function(event) {
            let allQuestionsAnswered = true;
            
            // Check all radio groups and text inputs
            const radioGroups = {};
            const radioButtons = quizForm.querySelectorAll('input[type="radio"]');
            const textInputs = quizForm.querySelectorAll('input[type="text"][required]');
            
            // Group radio buttons by name
            radioButtons.forEach(radio => {
                if (!radioGroups[radio.name]) {
                    radioGroups[radio.name] = [];
                }
                radioGroups[radio.name].push(radio);
            });
            
            // Check each radio group for a selection
            for (const groupName in radioGroups) {
                let groupChecked = false;
                radioGroups[groupName].forEach(radio => {
                    if (radio.checked) {
                        groupChecked = true;
                    }
                });
                
                if (!groupChecked) {
                    allQuestionsAnswered = false;
                    // Find the parent card and add a subtle highlight
                    const questionCard = radioGroups[groupName][0].closest('.card');
                    if (questionCard) {
                        questionCard.classList.add('border-warning');
                        
                        // Remove the highlight after 2 seconds
                        setTimeout(() => {
                            questionCard.classList.remove('border-warning');
                        }, 2000);
                    }
                }
            }
            
            // Check text inputs
            textInputs.forEach(input => {
                if (!input.value.trim()) {
                    allQuestionsAnswered = false;
                    input.classList.add('is-invalid');
                    
                    // Find the parent card and add a subtle highlight
                    const questionCard = input.closest('.card');
                    if (questionCard) {
                        questionCard.classList.add('border-warning');
                        
                        // Remove the highlight after 2 seconds
                        setTimeout(() => {
                            questionCard.classList.remove('border-warning');
                            input.classList.remove('is-invalid');
                        }, 2000);
                    }
                }
            });
            
            if (!allQuestionsAnswered) {
                event.preventDefault();
                
                // Scroll to the first unanswered question
                const firstHighlightedCard = document.querySelector('.card.border-warning');
                if (firstHighlightedCard) {
                    firstHighlightedCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Show a subtle notification
                const flashContainer = document.querySelector('.container:first-child');
                if (flashContainer) {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-warning alert-dismissible fade show';
                    alertDiv.setAttribute('role', 'alert');
                    alertDiv.innerHTML = `
                        Please answer all questions before submitting.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    flashContainer.appendChild(alertDiv);
                    
                    // Auto-dismiss after 3 seconds
                    setTimeout(() => {
                        const alert = new bootstrap.Alert(alertDiv);
                        alert.close();
                    }, 3000);
                }
            }
        });
    }
    
    // Progressive enhancement for copy functionality
    const copyButtons = document.querySelectorAll('[data-copy-target]');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-copy-target');
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                // Use the Clipboard API if available
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(targetElement.value)
                        .then(() => {
                            // Show success feedback
                            const originalText = this.innerHTML;
                            this.innerHTML = '<i data-feather="check" class="feather-small"></i> Copied!';
                            feather.replace();
                            
                            // Reset button after 2 seconds
                            setTimeout(() => {
                                this.innerHTML = originalText;
                                feather.replace();
                            }, 2000);
                        })
                        .catch(err => {
                            console.error('Failed to copy text: ', err);
                        });
                } else {
                    // Fallback for browsers without clipboard API
                    targetElement.select();
                    document.execCommand('copy');
                    
                    // Show success feedback
                    const originalText = this.innerHTML;
                    this.innerHTML = '<i data-feather="check" class="feather-small"></i> Copied!';
                    feather.replace();
                    
                    // Reset button after 2 seconds
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        feather.replace();
                    }, 2000);
                }
            }
        });
    });
});

// Add simple performance monitoring
window.addEventListener('load', function() {
    // Only log performance in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        const perfData = window.performance.timing;
        const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
        const domReadyTime = perfData.domComplete - perfData.domLoading;
        
        console.log('Page load time:', pageLoadTime, 'ms');
        console.log('DOM ready time:', domReadyTime, 'ms');
    }
});
