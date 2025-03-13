/**
 * Applizz - Theme Switcher
 * Handles switching between light and dark mode
 */

const ThemeSwitcher = {
  /**
   * Initialize the theme switcher
   */
  init: function() {
    // Get all theme toggle switches
    this.toggles = document.querySelectorAll('.theme-toggle');
    
    // Set initial state based on saved preference or system preference
    this.setInitialState();
    
    // Add event listeners to all toggle switches
    this.toggles.forEach(toggle => {
      toggle.addEventListener('change', this.handleToggle.bind(this));
    });
    
    // Listen for system preference changes
    this.listenForSystemChanges();
    
    // Make body visible after theme is set to prevent flash
    document.body.style.visibility = 'visible';
  },
  
  /**
   * Set the initial state of the theme toggle
   */
  setInitialState: function() {
    // Check if user has a saved preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
      // Use saved preference
      this.setTheme(savedTheme);
    } else {
      // Use system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      this.setTheme(prefersDark ? 'dark' : 'light');
    }
  },
  
  /**
   * Handle toggle switch change
   * @param {Event} event - The change event
   */
  handleToggle: function(event) {
    const isDark = event.target.checked;
    
    // Update all other toggles to match
    this.toggles.forEach(toggle => {
      toggle.checked = isDark;
    });
    
    // Set theme based on toggle state
    this.setTheme(isDark ? 'dark' : 'light');
    
    // Save preference
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  },
  
  /**
   * Set the theme
   * @param {string} theme - 'dark' or 'light'
   */
  setTheme: function(theme) {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark-mode');
      
      // Update all toggles
      this.toggles.forEach(toggle => {
        toggle.checked = true;
      });
    } else {
      document.documentElement.classList.remove('dark-mode');
      
      // Update all toggles
      this.toggles.forEach(toggle => {
        toggle.checked = false;
      });
    }
    
    // Update charts if they exist
    this.updateCharts();
  },
  
  /**
   * Listen for system preference changes
   */
  listenForSystemChanges: function() {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Only update theme based on system if user hasn't set a preference
    mediaQuery.addEventListener('change', e => {
      if (!localStorage.getItem('theme')) {
        this.setTheme(e.matches ? 'dark' : 'light');
      }
    });
  },
  
  /**
   * Update charts if Chart.js is being used
   */
  updateCharts: function() {
    // Check if Chart is defined and ThemeUtils exists
    if (typeof Chart !== 'undefined' && window.ThemeUtils) {
      // Find all charts in the document
      const chartElements = document.querySelectorAll('canvas[data-chart-id]');
      
      chartElements.forEach(canvas => {
        const chartId = canvas.getAttribute('data-chart-id');
        const chart = Chart.getChart(canvas);
        
        if (chart) {
          window.ThemeUtils.updateChartColors(chart);
        }
      });
    }
  }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  ThemeSwitcher.init();
});

// Export for use in other scripts
window.ThemeSwitcher = ThemeSwitcher; 