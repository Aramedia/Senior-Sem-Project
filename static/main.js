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
            track.scrollBy({ left: 344, behavior: "smooth" });
        });

        // go to the left
        prevBtn.addEventListener("click", function () {
            track.scrollBy({ left: -344, behavior: "smooth" });
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
});
