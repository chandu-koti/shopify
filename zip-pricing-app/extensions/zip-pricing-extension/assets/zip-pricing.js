/**
 * Shopify Dynamic ZIP Code Pricing Controller
 * Implements stateless UI handling, local verification, and request correlation.
 */
(function () {
  'use strict';

  class ZipPricingWidget {
    constructor(container) {
      this.container = container;
      this.productId = container.getAttribute('data-product-id');
      let resolvedUrl = container.getAttribute('data-api-url') || '/apps/zip-pricing';
      // Defensive Rewrite: Force App Proxy routing if configuration contains direct API domains
      if (resolvedUrl.includes('onrender.com') || resolvedUrl.includes('127.0.0.1:8000') || resolvedUrl.includes('localhost:8000')) {
        resolvedUrl = '/apps/zip-pricing';
      }
      this.apiUrl = resolvedUrl;
      this.merchantSelector = container.getAttribute('data-price-selector');

      // Bind element references
      this.inputField = container.querySelector('#zip-pricing-input');
      this.submitButton = container.querySelector('#zip-pricing-submit');
      this.submitText = this.submitButton.querySelector('.polaris-button__text');
      this.submitSpinner = this.submitButton.querySelector('.polaris-button__spinner');
      this.validationError = container.querySelector('#zip-pricing-validation-error');
      this.banner = container.querySelector('#zip-pricing-banner');
      this.bannerText = container.querySelector('#zip-pricing-banner-text');
      this.bannerTrace = container.querySelector('#zip-pricing-banner-trace');

      // Cache for storefront original price string to restore on fallback/reset
      this.cachedOriginalPrice = null;
      this.targetPriceElement = null;

      // Priority list of standard theme selectors to probe sequentially
      this.fallbackSelectors = [
        '.price-item--regular',
        '.price',
        '.product__price',
        '.price-item'
      ];

      this.init();
    }

    init() {
      if (!this.submitButton || !this.inputField) return;

      // Hook submit click event
      this.submitButton.addEventListener('click', () => this.handlePriceCheck());

      // Bind Enter key press within input
      this.inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.handlePriceCheck();
        }
      });

      // Clear inline errors as soon as user types
      this.inputField.addEventListener('input', () => {
        this.validationError.style.display = 'none';
      });
    }

    /**
     * Generates a request correlation token (UUID v4) for traceability.
     */
    generateCorrelationId() {
      if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
      }
      // Fail-safe manual generation for legacy clients
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      });
    }

    /**
     * Attempts to find the product price DOM element on the storefront.
     * Evaluates prioritized fallback list followed by merchant config overrides.
     */
    findPriceElement() {
      // 1. If merchant specified a selector, search that first
      if (this.merchantSelector) {
        const customEl = document.querySelector(this.merchantSelector);
        if (customEl) return customEl;
      }

      // 2. Iterate standard fallbacks
      for (const selector of this.fallbackSelectors) {
        const element = document.querySelector(selector);
        if (element) return element;
      }

      return null;
    }

    /**
     * Dispatches the API request to calculate the dynamic pricing.
     */
    async handlePriceCheck() {
      const zipCode = this.inputField.value.trim();
      const requestId = this.generateCorrelationId();

      // Clear previous banner displays
      this.hideBanner();

      // Local front-end validation
      const zipRegex = /^\d{5}$/;
      if (!zipRegex.test(zipCode)) {
        this.validationError.style.display = 'block';
        this.inputField.focus();
        return;
      }

      // Set visual UI components to loading state
      this.setLoadingState(true);

      try {
        const response = await fetch(`${this.apiUrl.replace(/\/$/, '')}/api/v1/pricing/calculate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            request_id: requestId,
            product_id: parseInt(this.productId, 10),
            zip_code: zipCode
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP Error Status: ${response.status}`);
        }

        const data = await response.json();
        this.processPricingResult(data);

      } catch (error) {
        console.error(`[Pricing Widget - Request Trace: ${requestId}] calculation failed:`, error);
        this.showBanner(
          'error',
          'Unable to calculate regional price. Please try again later.',
          `Trace ID: ${requestId}`
        );
        this.restoreOriginalPrice();
      } finally {
        this.setLoadingState(false);
      }
    }

    /**
     * Controls form input and button loading visual indicators.
     */
    setLoadingState(isLoading) {
      if (isLoading) {
        this.submitButton.disabled = true;
        this.inputField.disabled = true;
        this.submitText.style.visibility = 'hidden';
        this.submitSpinner.style.display = 'inline-flex';
      } else {
        this.submitButton.disabled = false;
        this.inputField.disabled = false;
        this.submitText.style.visibility = 'visible';
        this.submitSpinner.style.display = 'none';
      }
    }

    /**
     * Parses the pricing response and performs DOM updates.
     */
    processPricingResult(result) {
      // Find the price element if not already cached
      if (!this.targetPriceElement) {
        this.targetPriceElement = this.findPriceElement();
      }

      if (result.is_custom && result.formatted_price) {
        // Cache original text before first modification
        if (this.targetPriceElement && this.cachedOriginalPrice === null) {
          this.cachedOriginalPrice = this.targetPriceElement.innerHTML;
        }

        // Apply price dynamically with animations
        this.updateStorefrontPrice(result.formatted_price);

        // Display Success Banner
        this.showBanner(
          'success',
          `Special pricing applies for your region! Dynamic price of ${result.formatted_price} is active.`
        );
      } else {
        // Fallback or unmapped ZIP
        this.restoreOriginalPrice();
        this.showBanner('info', 'Standard pricing applies for your region.');
      }
    }

    /**
     * Updates the text element of the storefront price container.
     */
    updateStorefrontPrice(newPriceHtml) {
      if (this.targetPriceElement) {
        // Simple micro-fade animation sequence
        this.targetPriceElement.style.transition = 'opacity 0.15s ease';
        this.targetPriceElement.style.opacity = '0';
        
        setTimeout(() => {
          this.targetPriceElement.innerHTML = newPriceHtml;
          this.targetPriceElement.style.opacity = '1';
        }, 150);
      }
    }

    /**
     * Restores the storefront price tag back to standard Shopify settings.
     */
    restoreOriginalPrice() {
      if (this.targetPriceElement && this.cachedOriginalPrice !== null) {
        this.updateStorefrontPrice(this.cachedOriginalPrice);
      }
    }

    /**
     * Renders Polaris Banners with varying contextual styles.
     */
    showBanner(type, message, traceMessage = '') {
      // Reset classes
      this.banner.className = 'polaris-banner';
      this.banner.classList.add(`polaris-banner--${type}`);
      this.bannerText.textContent = message;

      if (traceMessage) {
        this.bannerTrace.textContent = traceMessage;
        this.bannerTrace.style.display = 'block';
      } else {
        this.bannerTrace.style.display = 'none';
      }

      // Smooth show
      this.banner.style.display = 'flex';
      this.banner.style.opacity = '0';
      this.banner.style.transform = 'translateY(-4px)';
      
      setTimeout(() => {
        this.banner.style.opacity = '1';
        this.banner.style.transform = 'translateY(0)';
      }, 50);
    }

    hideBanner() {
      this.banner.style.display = 'none';
    }
  }

  // Self-initialize on DOM ready
  document.addEventListener('DOMContentLoaded', () => {
    const widgetContainer = document.querySelector('.zip-pricing-widget');
    if (widgetContainer) {
      new ZipPricingWidget(widgetContainer);
    }
  });
})();
