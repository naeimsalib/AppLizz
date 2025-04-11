// Mobile menu functionality
(function() {
  // Function to initialize mobile menu
  function initMobileMenu() {
    // Get all mobile menu buttons and menus
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileMenuButtonGuest = document.getElementById('mobile-menu-button-guest');
    const mobileMenuGuest = document.getElementById('mobile-menu-guest');
    
    // Function to toggle a specific menu
    function toggleMenu(button, menu) {
      if (!button || !menu) return;
      
      if (menu.classList.contains('hidden')) {
        menu.classList.remove('hidden');
        button.setAttribute('aria-expanded', 'true');
      } else {
        menu.classList.add('hidden');
        button.setAttribute('aria-expanded', 'false');
      }
    }
    
    // Function to close all menus
    function closeAllMenus() {
      if (mobileMenu) mobileMenu.classList.add('hidden');
      if (mobileMenuGuest) mobileMenuGuest.classList.add('hidden');
      if (mobileMenuButton) mobileMenuButton.setAttribute('aria-expanded', 'false');
      if (mobileMenuButtonGuest) mobileMenuButtonGuest.setAttribute('aria-expanded', 'false');
    }
    
    // Add click event to authenticated user menu button
    if (mobileMenuButton) {
      mobileMenuButton.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleMenu(mobileMenuButton, mobileMenu);
      });
    }
    
    // Add click event to guest menu button
    if (mobileMenuButtonGuest) {
      mobileMenuButtonGuest.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleMenu(mobileMenuButtonGuest, mobileMenuGuest);
      });
    }
    
    // Close menus when clicking outside
    document.addEventListener('click', function(e) {
      // Check if click was inside any menu or on any button
      const isClickInsideMenu = (mobileMenu && mobileMenu.contains(e.target)) || 
                               (mobileMenuGuest && mobileMenuGuest.contains(e.target));
      const isClickOnButton = (mobileMenuButton && mobileMenuButton.contains(e.target)) || 
                             (mobileMenuButtonGuest && mobileMenuButtonGuest.contains(e.target));
      
      if (!isClickInsideMenu && !isClickOnButton) {
        closeAllMenus();
      }
    });
    
    // Prevent menu from closing when clicking inside it
    if (mobileMenu) {
      mobileMenu.addEventListener('click', function(e) {
        e.stopPropagation();
      });
    }
    
    if (mobileMenuGuest) {
      mobileMenuGuest.addEventListener('click', function(e) {
        e.stopPropagation();
      });
    }
  }
  
  // Initialize immediately if DOM is already loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMobileMenu);
  } else {
    // DOM already loaded, initialize immediately
    initMobileMenu();
  }
})(); 