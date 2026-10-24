document.addEventListener("DOMContentLoaded", function () {
    // 1) Get the carousel track and buttons
    const track = document.querySelector(".carousel-track-container");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");

    if (track && prevBtn && nextBtn) {
        // Check function and disappear button when reach the end of the carousel
        function updateArrows() {
            const scrollLeft = track.scrollLeft;
            const maxScrollLeft = track.scrollWidth - track.clientWidth;

            // if in the left end of the carousel, hide the left arrow
            if (scrollLeft <= 5) {
                prevBtn.style.display = "none";
            } else {
                prevBtn.style.display = "flex";
            }

            // if in the right end of the carousel, hide the right arrow
            if (scrollLeft >= maxScrollLeft - 5) {
                nextBtn.style.display = "none";
            } else {
                nextBtn.style.display = "flex";
            }
        }
        // To update the arrows when the page loads, 
        // if the carousel is already scrolled to the end (left or right)
        track.addEventListener("scroll", updateArrows);
        // go to the right
        nextBtn.addEventListener("click", function () {
            const firstCard = track.querySelector(".recipe-card");
            if (firstCard) {
                const cardWidth = firstCard.offsetWidth + 24; // width of 1 card + gap
                track.scrollBy({ left: cardWidth, behavior: "smooth" });
                setTimeout(updateArrows, 300);
            }
        });

        // go to the left
        prevBtn.addEventListener("click", function () {
            const firstCard = track.querySelector(".recipe-card");
            if (firstCard) {
                const cardWidth = firstCard.offsetWidth + 24;
                track.scrollBy({ left: -cardWidth, behavior: "smooth" });
                setTimeout(updateArrows, 300);
            }
        });

        // Update the arrows when the page loads
        updateArrows();
    }


    // 2) Back to Top Button
    const backToTopBtn = document.getElementById("backToTopBtn");
    if (backToTopBtn) {
        // Appear button arrow after roll down 300px
        window.addEventListener("scroll", function () {
            if (window.scrollY > 20 || document.documentElement.scrollTop > 20) {
                backToTopBtn.style.display = "block";
            } else {
                backToTopBtn.style.display = "none";
            }
        });

        // Smooth when click button
        backToTopBtn.addEventListener("click", function () {
            window.scrollTo({
                top: 0,
                behavior: "smooth"
            });
        });
    }

    // 3) Load More Recipes Button
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
        const urlParams = new URLSearchParams(window.location.search);

        let currentPage = parseInt(urlParams.get('page')) || 1;

        loadMoreBtn.addEventListener('click', function () {
            currentPage++;

            const currentParams = new URLSearchParams(window.location.search);
            currentParams.set('page', currentPage);

            // 🌟 Sửa dùng đúng tên biến currentParams
            const newUrl = `${window.location.pathname}?${currentParams.toString()}`;
            window.history.replaceState({ page: currentPage }, '', newUrl);

            loadMoreBtn.classList.add('loading');
            loadMoreBtn.disabled = true;

            fetch(newUrl)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');

                    // Retrieve the new cards from the fetch operation
                    let allFetchedCards = doc.querySelectorAll('#recipe-container .recipe-card-link');

                    const container = document.getElementById('recipe-container');
                    const currentCardCount = container ? container.querySelectorAll('.recipe-card-link').length : 0;

                    // Extract the new cards
                    const newCards = Array.from(allFetchedCards).slice(currentCardCount);

                    if (newCards.length > 0 && container) {
                        // Insert new cards into container
                        newCards.forEach(card => container.appendChild(card));

                        // Update the displayed figure
                        const totalVisibleCards = container.querySelectorAll('.recipe-card-link').length;
                        const countElement = document.getElementById('displayed-count');
                        if (countElement) {
                            countElement.innerText = totalVisibleCards;
                        }

                        // Check if reached end of recipes
                        if (allFetchedCards.length < currentPage * 15) {
                            loadMoreBtn.parentElement.innerHTML = '<div class="reached-end-badge"><span class="end-icon">✨</span><span>You\'ve reached the end of the list!</span></div>';
                        } else {
                            loadMoreBtn.classList.remove('loading');
                            loadMoreBtn.disabled = false;
                        }
                    } else {
                        loadMoreBtn.parentElement.innerHTML = '<div class="reached-end-badge"><span class="end-icon">✨</span><span>You\'ve reached the end of the list!</span></div>';
                    }
                })
                .catch(err => {
                    console.error("Error loading more recipes:", err);
                    loadMoreBtn.classList.remove('loading');
                    loadMoreBtn.disabled = false;
                });
        });
    }
});