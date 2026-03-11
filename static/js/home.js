document.addEventListener("DOMContentLoaded", () => {

    // =====================
    // Carousel functionality
    // =====================
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.carousel-dot');
    let currentSlide = 0;
    let slideInterval;

    function showSlide(n) {
        if (!slides.length || !dots.length) return;
        slides.forEach(slide => slide.classList.remove('active'));
        dots.forEach(dot => dot.classList.remove('active'));
        slides[n].classList.add('active');
        dots[n].classList.add('active');
        currentSlide = n;
    }

    function nextSlide() {
        if (!slides.length) return;
        let next = currentSlide + 1;
        if (next >= slides.length) next = 0;
        showSlide(next);
    }

    function startCarousel() {
        if (!slides.length) return;
        slideInterval = setInterval(nextSlide, 5000);
    }

    if (dots.length) {
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                clearInterval(slideInterval);
                showSlide(index);
                startCarousel();
            });
        });
    }

    if (slides.length) {
        showSlide(0);
        startCarousel();
    }

    // =====================
    // Back to top button
    // =====================
    const backToTop = document.getElementById('backToTop');
    if (backToTop) {
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) backToTop.classList.add('visible');
            else backToTop.classList.remove('visible');
        });

        backToTop.addEventListener('click', e => {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // =====================
    // Wishlist functionality
    // =====================
    const wishlistButtons = document.querySelectorAll('.btn-wishlist, .action-btn[title="Add to Wishlist"]');
    if (wishlistButtons.length) {
        wishlistButtons.forEach(button => {
            button.addEventListener('click', function() {
                const productCard = this.closest('.product-card');
                if (!productCard) return;
                const productTitleEl = productCard.querySelector('.product-title');
                const productTitle = productTitleEl ? productTitleEl.textContent : "Unknown product";
                const icon = this.querySelector('i');
                if (!icon) return;

                if (icon.classList.contains('far')) {
                    icon.classList.remove('far');
                    icon.classList.add('fas');
                    icon.style.color = '#ff3333';
                    if (this.classList.contains('btn-wishlist')) {
                        this.style.backgroundColor = '#ffe6e6';
                        this.style.color = '#ff3333';
                    }
                    alert(`"${productTitle}" added to your wishlist!`);
                } else {
                    icon.classList.remove('fas');
                    icon.classList.add('far');
                    icon.style.color = '';
                    if (this.classList.contains('btn-wishlist')) {
                        this.style.backgroundColor = '';
                        this.style.color = '';
                    }
                    alert(`"${productTitle}" removed from your wishlist!`);
                }
            });
        });
    }

    // =====================
    // Newsletter subscription
    // =====================
    const newsletterButton = document.querySelector('.newsletter-input button');
    const newsletterInput = document.querySelector('.newsletter-input input');
    if (newsletterButton && newsletterInput) {
        newsletterButton.addEventListener('click', () => {
            const email = newsletterInput.value.trim();
            if (!email) return alert('Please enter your email address');
            if (!validateEmail(email)) return alert('Please enter a valid email address');

            newsletterButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            newsletterButton.disabled = true;

            setTimeout(() => {
                alert(`Thank you for subscribing with ${email}! You'll receive our newsletter soon.`);
                newsletterInput.value = '';
                newsletterButton.innerHTML = 'Subscribe';
                newsletterButton.disabled = false;
            }, 1500);
        });
    }

    const buyButtons = document.querySelectorAll('.btn-buy');

    if (buyButtons.length) {
        buyButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const productCard = this.closest('.product-card');
                if (!productCard) return;

                // Get product ID from data attribute
                const productId = productCard.dataset.productId;
                if (!productId) return;

                // Redirect to backend /buy/<product_id>
                window.location.href = `/buy/${productId}`;
            });
        });
    }
    // =====================
    // Search functionality
    // =====================
    const searchButton = document.querySelector('.search-button');
    const searchInput = document.querySelector('.search-input');
    if (searchButton && searchInput) {
        searchButton.addEventListener('click', () => {
            const searchTerm = searchInput.value.trim();
            if (!searchTerm) return alert('Please enter a search term');
            alert(`Searching for: "${searchTerm}"`);
        });

        searchInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') searchButton.click();
        });
    }

    // =====================
    // Email validation helper
    // =====================
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

});
