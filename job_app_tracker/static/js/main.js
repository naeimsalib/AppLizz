/**
 * Applizz - Main JavaScript Utilities
 */

// Loading state management
const LoadingManager = {
  /**
   * Show a loading overlay on the entire page
   * @param {string} message - Optional message to display
   */
  showPageLoading: function(message = 'Loading...') {
    // Create overlay if it doesn't exist
    if (!document.getElementById('loading-overlay')) {
      const overlay = document.createElement('div');
      overlay.id = 'loading-overlay';
      overlay.className = 'loading-overlay fade-in';
      
      const spinner = document.createElement('div');
      spinner.className = 'loading-spinner';
      
      const text = document.createElement('div');
      text.className = 'loading-text';
      text.textContent = message;
      
      overlay.appendChild(spinner);
      overlay.appendChild(text);
      document.body.appendChild(overlay);
    } else {
      const overlay = document.getElementById('loading-overlay');
      overlay.querySelector('.loading-text').textContent = message;
      overlay.classList.remove('hidden');
      overlay.classList.add('fade-in');
    }
    
    // Prevent scrolling on body
    document.body.style.overflow = 'hidden';
  },
  
  /**
   * Hide the page loading overlay
   */
  hidePageLoading: function() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
      overlay.classList.add('fade-out');
      
      // Remove after animation completes
      setTimeout(() => {
        overlay.classList.add('hidden');
        document.body.style.overflow = '';
      }, 300);
    }
  },
  
  /**
   * Add loading state to a button
   * @param {HTMLElement} button - The button element
   * @param {boolean} isLoading - Whether to show or hide loading state
   */
  setButtonLoading: function(button, isLoading) {
    if (isLoading) {
      // Store original text
      button.dataset.originalText = button.textContent;
      button.classList.add('btn-loading');
      button.disabled = true;
    } else {
      // Restore original text
      button.textContent = button.dataset.originalText || button.textContent;
      button.classList.remove('btn-loading');
      button.disabled = false;
    }
  },
  
  /**
   * Add loading state to a container
   * @param {HTMLElement} container - The container element
   * @param {boolean} isLoading - Whether to show or hide loading state
   * @param {string} message - Optional message to display
   */
  setContainerLoading: function(container, isLoading, message = 'Loading...') {
    // Remove existing loading elements
    const existingLoader = container.querySelector('.loading-container');
    if (existingLoader) {
      existingLoader.remove();
    }
    
    if (isLoading) {
      // Store original content
      if (!container.dataset.originalContent) {
        container.dataset.originalContent = container.innerHTML;
      }
      
      // Create loading element
      const loadingEl = document.createElement('div');
      loadingEl.className = 'loading-container';
      loadingEl.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">${message}</div>
      `;
      
      // Clear and append
      container.innerHTML = '';
      container.appendChild(loadingEl);
    } else if (container.dataset.originalContent) {
      // Restore original content
      container.innerHTML = container.dataset.originalContent;
      delete container.dataset.originalContent;
    }
  }
};

// Form validation utilities
const FormValidator = {
  /**
   * Validate an email address
   * @param {string} email - The email to validate
   * @returns {boolean} Whether the email is valid
   */
  isValidEmail: function(email) {
    const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
  },
  
  /**
   * Validate a password (min 8 chars, at least one letter and one number)
   * @param {string} password - The password to validate
   * @returns {boolean} Whether the password is valid
   */
  isValidPassword: function(password) {
    return password.length >= 8 && /[A-Za-z]/.test(password) && /[0-9]/.test(password);
  },
  
  /**
   * Show validation error on a form field
   * @param {HTMLElement} field - The input field
   * @param {string} message - Error message to display
   */
  showError: function(field, message) {
    // Remove existing error
    this.clearError(field);
    
    // Add error class to input
    field.classList.add('border-red-500');
    
    // Create error message
    const errorEl = document.createElement('p');
    errorEl.className = 'text-red-500 text-xs mt-1';
    errorEl.textContent = message;
    
    // Insert after field
    field.parentNode.insertBefore(errorEl, field.nextSibling);
  },
  
  /**
   * Clear validation error on a form field
   * @param {HTMLElement} field - The input field
   */
  clearError: function(field) {
    field.classList.remove('border-red-500');
    
    // Remove error message if exists
    const nextEl = field.nextElementSibling;
    if (nextEl && nextEl.classList.contains('text-red-500')) {
      nextEl.remove();
    }
  },
  
  /**
   * Validate a form
   * @param {HTMLFormElement} form - The form to validate
   * @param {Object} rules - Validation rules
   * @returns {boolean} Whether the form is valid
   */
  validateForm: function(form, rules) {
    let isValid = true;
    
    // Clear all errors first
    form.querySelectorAll('input, select, textarea').forEach(field => {
      this.clearError(field);
    });
    
    // Apply validation rules
    for (const fieldName in rules) {
      const field = form.elements[fieldName];
      const fieldRules = rules[fieldName];
      
      if (!field) continue;
      
      // Required validation
      if (fieldRules.required && !field.value.trim()) {
        this.showError(field, fieldRules.required === true ? 'This field is required' : fieldRules.required);
        isValid = false;
        continue;
      }
      
      // Skip other validations if field is empty and not required
      if (!field.value.trim()) continue;
      
      // Email validation
      if (fieldRules.email && !this.isValidEmail(field.value)) {
        this.showError(field, fieldRules.email === true ? 'Please enter a valid email address' : fieldRules.email);
        isValid = false;
        continue;
      }
      
      // Password validation
      if (fieldRules.password && !this.isValidPassword(field.value)) {
        this.showError(field, fieldRules.password === true ? 'Password must be at least 8 characters with at least one letter and one number' : fieldRules.password);
        isValid = false;
        continue;
      }
      
      // Min length validation
      if (fieldRules.minLength && field.value.length < fieldRules.minLength.value) {
        this.showError(field, fieldRules.minLength.message || `Must be at least ${fieldRules.minLength.value} characters`);
        isValid = false;
        continue;
      }
      
      // Max length validation
      if (fieldRules.maxLength && field.value.length > fieldRules.maxLength.value) {
        this.showError(field, fieldRules.maxLength.message || `Must be no more than ${fieldRules.maxLength.value} characters`);
        isValid = false;
        continue;
      }
      
      // Custom validation
      if (fieldRules.custom && typeof fieldRules.custom.validate === 'function') {
        const isCustomValid = fieldRules.custom.validate(field.value, form);
        if (!isCustomValid) {
          this.showError(field, fieldRules.custom.message || 'Invalid value');
          isValid = false;
          continue;
        }
      }
    }
    
    return isValid;
  }
};

// Notification utilities
const NotificationManager = {
  /**
   * Show a notification toast
   * @param {string} message - The message to display
   * @param {string} type - The type of notification (success, error, info, warning)
   * @param {number} duration - How long to show the notification in ms
   */
  showNotification: function(message, type = 'info', duration = 5000) {
    // Create container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'notification-container';
      container.className = 'fixed top-4 right-4 z-50 flex flex-col items-end space-y-2';
      document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'rounded-md p-4 shadow-lg transform transition-all duration-300 translate-x-full';
    
    // Set type-specific styles
    switch (type) {
      case 'success':
        notification.classList.add('bg-green-50', 'text-green-800', 'border-l-4', 'border-green-500');
        break;
      case 'error':
        notification.classList.add('bg-red-50', 'text-red-800', 'border-l-4', 'border-red-500');
        break;
      case 'warning':
        notification.classList.add('bg-yellow-50', 'text-yellow-800', 'border-l-4', 'border-yellow-500');
        break;
      default: // info
        notification.classList.add('bg-blue-50', 'text-blue-800', 'border-l-4', 'border-blue-500');
    }
    
    // Add content
    notification.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex-1 mr-2">
          <p class="text-sm">${message}</p>
        </div>
        <button type="button" class="text-gray-400 hover:text-gray-500 focus:outline-none">
          <span class="sr-only">Close</span>
          <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
          </svg>
        </button>
      </div>
    `;
    
    // Add to container
    container.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
      notification.classList.remove('translate-x-full');
    }, 10);
    
    // Add close button handler
    const closeButton = notification.querySelector('button');
    closeButton.addEventListener('click', () => {
      this.closeNotification(notification);
    });
    
    // Auto-close after duration
    if (duration > 0) {
      setTimeout(() => {
        this.closeNotification(notification);
      }, duration);
    }
    
    return notification;
  },
  
  /**
   * Close a notification
   * @param {HTMLElement} notification - The notification element to close
   */
  closeNotification: function(notification) {
    // Animate out
    notification.classList.add('translate-x-full');
    
    // Remove after animation
    setTimeout(() => {
      notification.remove();
    }, 300);
  }
};

// Theme utilities
const ThemeUtils = {
  /**
   * Check if dark mode is currently active
   * @returns {boolean} Whether dark mode is active
   */
  isDarkMode: function() {
    return document.documentElement.classList.contains('dark-mode');
  },
  
  /**
   * Get the current theme name
   * @returns {string} 'dark' or 'light'
   */
  getCurrentTheme: function() {
    return this.isDarkMode() ? 'dark' : 'light';
  },
  
  /**
   * Get color values appropriate for the current theme
   * @param {Object} options - Color options with light and dark variants
   * @returns {string|Object} The appropriate color value for the current theme
   */
  getThemeColor: function(options) {
    const isDark = this.isDarkMode();
    return isDark ? options.dark : options.light;
  },
  
  /**
   * Update chart colors based on the current theme
   * @param {Chart} chart - The Chart.js instance to update
   */
  updateChartColors: function(chart) {
    if (!chart) return;
    
    const isDark = this.isDarkMode();
    
    // Update text colors
    if (chart.options.plugins && chart.options.plugins.legend) {
      chart.options.plugins.legend.labels.color = isDark ? '#d1d5db' : '#374151';
    }
    
    // Update grid colors
    if (chart.options.scales) {
      Object.values(chart.options.scales).forEach(scale => {
        if (scale.ticks) {
          scale.ticks.color = isDark ? '#d1d5db' : '#374151';
        }
        if (scale.grid) {
          scale.grid.color = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        }
      });
    }
    
    // Update the chart
    chart.update();
  }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  // Add loading state to forms with data-loading attribute
  document.querySelectorAll('form[data-loading="true"]').forEach(form => {
    form.addEventListener('submit', function() {
      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton) {
        LoadingManager.setButtonLoading(submitButton, true);
      }
    });
  });
  
  // Initialize any other components

  // Mobile menu functionality
  const mobileMenuButtons = document.querySelectorAll('.mobile-menu-button');
  const mobileMenu = document.getElementById('mobile-menu');

  if (mobileMenuButtons.length > 0 && mobileMenu) {
    let isMenuOpen = false;

    const toggleMenu = (show) => {
      isMenuOpen = show;
      if (show) {
        mobileMenu.classList.remove('hidden');
        setTimeout(() => {
          mobileMenu.style.opacity = '1';
          mobileMenu.style.transform = 'translateY(0)';
        }, 10);
      } else {
        mobileMenu.style.opacity = '0';
        mobileMenu.style.transform = 'translateY(-10px)';
        setTimeout(() => {
          mobileMenu.classList.add('hidden');
        }, 200);
      }

      // Update aria-expanded on all buttons
      mobileMenuButtons.forEach(btn => {
        btn.setAttribute('aria-expanded', show.toString());
      });
    };

    // Add click event to each mobile menu button
    mobileMenuButtons.forEach(button => {
      button.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        toggleMenu(!isMenuOpen);
      });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
      if (isMenuOpen && 
        !mobileMenu.contains(e.target) && 
        !Array.from(mobileMenuButtons).some(button => button.contains(e.target))) {
        toggleMenu(false);
      }
    });

    // Close menu when clicking a menu item
    const menuItems = mobileMenu.querySelectorAll('a');
    menuItems.forEach(item => {
      item.addEventListener('click', () => {
        toggleMenu(false);
      });
    });

    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isMenuOpen) {
        toggleMenu(false);
      }
    });

    // Close menu on resize if switching to desktop view
    window.addEventListener('resize', function() {
      if (window.innerWidth >= 640 && isMenuOpen) {
        toggleMenu(false);
      }
    });
  }
});

// Export utilities for use in other scripts
window.LoadingManager = LoadingManager;
window.FormValidator = FormValidator;
window.NotificationManager = NotificationManager;
window.ThemeUtils = ThemeUtils; 