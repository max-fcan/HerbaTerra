class PhotoGallery {
  constructor() {
    this.slides = document.querySelectorAll('.gallery-slide');
    this.currentSlide = 0;
    this.autoPlayInterval = null;

    if (this.slides.length === 0) {
      console.warn('No gallery slides found');
      return;
    }

    this.init();
  }

  init() {
    this.showSlide(0);
    this.startAutoPlay();
  }

  showSlide(n) {
    this.slides.forEach((slide) => slide.classList.remove('active'));
    this.slides[n].classList.add('active');
    this.currentSlide = n;
  }

  nextSlide() {
    const next = (this.currentSlide + 1) % this.slides.length;
    this.showSlide(next);
  }

  startAutoPlay() {
    this.autoPlayInterval = setInterval(() => this.nextSlide(), 5000);
  }

  stopAutoPlay() {
    clearInterval(this.autoPlayInterval);
  }
}

// Initialize gallery when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new PhotoGallery();
  });
} else {
  new PhotoGallery();
}


