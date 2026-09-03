// MASKOT Petshop & Grooming - JavaScript Principal
document.addEventListener('DOMContentLoaded', function() {
    
    // Inicialización general
    initializeApp();
    
    // Event listeners globales
    setupGlobalEventListeners();
    
    // Inicializar funcionalidades específicas según la página
    initializePageSpecificFeatures();
    
    // Inicializar características del nuevo diseño MASKOT
    initializeMaskotFeatures();
});

// Función principal de inicialización
function initializeApp() {
    console.log('🎨 MASKOT Petshop & Grooming iniciado');
    
    // Configurar fecha mínima en campos de fecha
    setMinDateForDateInputs();
    
    // Inicializar elementos interactivos
    initializeInteractiveElements();

    // Inicializar add-to-cart handlers
    setupAddToCartButtons();
    
    // Inicializar Bootstrap tooltips y popovers
    initializeBootstrapComponents();
    
    // Auto-cerrar alertas después de 5 segundos
    autoCloseAlerts();
    
    // Inicializar scroll to top
    initializeScrollToTop();
    
    // Animaciones de entrada
    initializeScrollAnimations();
}

// Setup listeners for add-to-cart buttons across the site
function setupAddToCartButtons() {
    document.body.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-add-to-cart');
        if (!btn) return;
        e.preventDefault();

        const productId = btn.getAttribute('data-product-id');
        const stock = parseInt(btn.getAttribute('data-stock') || '0', 10) || 0;
        
        // Try to get quantity from form input if button is inside a form, otherwise default to 1
        let qty = 1;
        const form = btn.closest('form');
        if (form) {
            const qtyInput = form.querySelector('input[name="cantidad"]');
            if (qtyInput) {
                qty = parseInt(qtyInput.value || '1', 10) || 1;
            }
        }

            // If no stock, inform user and don't proceed
            if (stock <= 0) {
                showMaskotNotification('Producto sin stock', 'warning');
                return;
            }

            // Disable button briefly to prevent double clicks
        btn.disabled = true;
        btn.classList.add('loading');

        const formData = new URLSearchParams();
        formData.append('producto_id', productId);
        formData.append('cantidad', qty);

        fetch('/carrito/agregar', {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            credentials: 'same-origin',
            body: formData.toString()
        })
        .then(resp => resp.json())
        .then(data => {
            if (data && data.success) {
                // Update cart badge
                const badge = document.getElementById('cart-count');
                if (badge) badge.textContent = data.cart_count || '0';
                showMaskotNotification(data.message || 'Producto agregado al carrito', 'success');
            } else {
                showMaskotNotification((data && data.message) || 'No se pudo agregar el producto', 'error');
            }
        })
        .catch(err => {
            console.error('Error al agregar al carrito:', err);
            showMaskotNotification('Error de conexión. Intenta nuevamente.', 'error');
        })
        .finally(() => {
            btn.disabled = false;
            btn.classList.remove('loading');
        });
    });
}

// Event listeners globales
function setupGlobalEventListeners() {
    // Confirmación para acciones destructivas (reemplaza native confirm con modal)
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-confirm]')) {
            e.preventDefault();
            const message = e.target.getAttribute('data-confirm');
            showConfirmModal(message).then(confirmed => {
                if (confirmed) {
                    // Si es un enlace, seguirlo
                    if (e.target.tagName === 'A' && e.target.href) {
                        window.location.href = e.target.href;
                    } else if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') {
                        // Si es un botón dentro de un form, disparar click original
                        const clickHandler = e.target.getAttribute('data-onconfirm');
                        if (clickHandler) {
                            // Ejecutar función global si existe
                            if (typeof window[clickHandler] === 'function') window[clickHandler]();
                        } else {
                            // Si no hay handler, intentar submit del form
                            const form = e.target.closest('form');
                            if (form) form.submit();
                        }
                    }
                }
            });
        }
    });
    
    // Validación de formularios
    document.addEventListener('submit', function(e) {
        // Skip completamente formularios con no-animation
        if (e.target && e.target.classList && e.target.classList.contains('no-animation')) {
            return true; // Permitir envío normal sin interferencia
        }
        
        // If the form contains an add-to-cart button, handle it via AJAX
        if (e.target && e.target.querySelector && e.target.querySelector('.btn-add-to-cart')) {
            e.preventDefault();

            const form = e.target;
            // Try to get product id and quantity from form fields first
            let productId = form.querySelector('input[name="producto_id"]') ? form.querySelector('input[name="producto_id"]').value : null;
            let qtyInput = form.querySelector('input[name="cantidad"]');
            let qty = qtyInput ? parseInt(qtyInput.value || '1', 10) : 1;

            // Fallback to button dataset if inputs not present
            const btn = form.querySelector('.btn-add-to-cart');
            if ((!productId || productId === '') && btn) {
                productId = btn.getAttribute('data-product-id');
            }

            if (!productId) {
                showMaskotNotification('Producto inválido.', 'error');
                return false;
            }

            // Disable button briefly
            if (btn) {
                btn.disabled = true;
                btn.classList.add('loading');
            }

            const formData = new URLSearchParams();
            formData.append('producto_id', productId);
            formData.append('cantidad', qty);

            fetch('/carrito/agregar', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                credentials: 'same-origin',
                body: formData.toString()
            })
            .then(resp => resp.json())
            .then(data => {
                if (data && data.success) {
                    const badge = document.getElementById('cart-count');
                    if (badge) badge.textContent = data.cart_count || '0';
                    showMaskotNotification(data.message || 'Producto agregado al carrito', 'success');
                } else {
                    showMaskotNotification((data && data.message) || 'No se pudo agregar al producto', 'error');
                }
            })
            .catch(err => {
                console.error('Error al agregar al carrito:', err);
                showMaskotNotification('Error de conexión. Intenta nuevamente.', 'error');
            })
            .finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.classList.remove('loading');
                }
            });

            return false;
        }

        if (e.target.matches('form[data-validate]')) {
            if (!validateForm(e.target)) {
                e.preventDefault();
                return false;
            }
        }
    });
    
    // Auto-resize de textareas
    document.addEventListener('input', function(e) {
        if (e.target.matches('textarea[data-auto-resize]')) {
            autoResizeTextarea(e.target);
        }
    });
    
    // Escape key para cerrar modales
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
}

// Funcionalidades específicas por página
function initializePageSpecificFeatures() {
    const currentPage = document.body.dataset.page || getCurrentPageFromURL();
    
    switch(currentPage) {
        case 'index':
            initializeHomePage();
            break;
        case 'citas':
            initializeCitasPage();
            break;
        case 'servicios':
            initializeServiciosPage();
            break;
        case 'personal':
            initializePersonalPage();
            break;
        case 'asistencia':
            initializeAsistenciaPage();
            break;
        case 'almacen':
            initializeAlmacenPage();
            break;
        case 'dashboard':
            initializeDashboardPage();
            break;
    }
}

// === FUNCIONES ESPECÍFICAS MASKOT ===

// Inicializar características del nuevo diseño MASKOT
function initializeMaskotFeatures() {
    // Animaciones del logo MASKOT
    animateMaskotLogo();
    
    // Efectos parallax suaves
    initializeParallaxEffects();
    
    // Loading overlay moderno
    initializeLoadingOverlay();
    
    // Smooth scroll mejorado
    initializeSmoothScroll();
    
    // Efectos hover modernos
    initializeModernHoverEffects();
    
    // Lazy loading para imágenes
    initializeLazyLoading();
}

// Animaciones del logo MASKOT
function animateMaskotLogo() {
    const logo = document.querySelector('.navbar-brand .brand-icon');
    if (logo) {
        logo.addEventListener('mouseenter', function() {
            this.style.transform = 'rotate(360deg) scale(1.2)';
            this.style.transition = 'transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        });
        
        logo.addEventListener('mouseleave', function() {
            this.style.transform = 'rotate(0deg) scale(1)';
        });
    }
}

// Efectos parallax suaves
function initializeParallaxEffects() {
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const rate = scrolled * -0.5;
        
        // Efecto parallax en hero section
        const hero = document.querySelector('.hero-section');
        if (hero) {
            hero.style.transform = `translateY(${rate}px)`;
        }
        
        // Efecto parallax en elementos flotantes
        document.querySelectorAll('.floating-element').forEach((element, index) => {
            const rate = scrolled * (0.2 + index * 0.1);
            element.style.transform = `translateY(${rate}px)`;
        });
    });
}

// Loading overlay moderno
function initializeLoadingOverlay() {
    // Crear overlay si no existe
    if (!document.querySelector('.loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="maskot-loader">
                    <div class="paw-loader">
                        <div class="paw"></div>
                        <div class="paw"></div>
                        <div class="paw"></div>
                        <div class="paw"></div>
                    </div>
                    <h3>MASKOT</h3>
                    <p>Cargando...</p>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }
}

// Mostrar loading overlay
function showLoadingOverlay() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

// Ocultar loading overlay
function hideLoadingOverlay() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 300);
    }
}

// Scroll to top mejorado
function initializeScrollToTop() {
    const scrollTopBtn = document.querySelector('.scroll-to-top');
    if (!scrollTopBtn) return;
    
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollTopBtn.classList.add('visible');
        } else {
            scrollTopBtn.classList.remove('visible');
        }
    });
    
    scrollTopBtn.addEventListener('click', function(e) {
        e.preventDefault();
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Smooth scroll mejorado para toda la página
function initializeSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const headerOffset = 80;
                const elementPosition = target.offsetTop;
                const offsetPosition = elementPosition - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Animaciones de scroll (reveal on scroll)
function initializeScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observar elementos que deben animarse
    document.querySelectorAll('.service-card, .stat-item, .product-card, .feature-item').forEach(el => {
        el.classList.add('animate-on-scroll');
        observer.observe(el);
    });
}

// Efectos hover modernos
function initializeModernHoverEffects() {
    // Efecto ripple en botones
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', createRippleEffect);
    });
    
    // Efectos hover en cards
    document.querySelectorAll('.card, .service-card, .product-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
            this.style.boxShadow = '0 20px 40px rgba(255, 163, 1, 0.3)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
}

// Crear efecto ripple
function createRippleEffect(e) {
    const button = e.currentTarget;
    const ripple = document.createElement('span');
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;
    
    ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        background: rgba(255, 255, 255, 0.6);
        border-radius: 50%;
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    `;
    
    button.style.position = 'relative';
    button.style.overflow = 'hidden';
    button.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// Lazy loading para imágenes
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// Inicializar componentes de Bootstrap
function initializeBootstrapComponents() {
    // Inicializar tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Inicializar popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
}

// === PÁGINA DE INICIO MEJORADA ===
function initializeHomePage() {
    console.log('🏠 Inicializando página de inicio MASKOT');
    
    // Contador animado en hero
    animateHeroCounters();
    
    // Formulario flotante de citas
    initializeFloatingAppointmentForm();
    
    // Carousel de testimonios (si existe)
    initializeTestimonialsCarousel();
    
    // Animación de servicios
    initializeServicesAnimation();
    
    // Efectos de partículas (opcional)
    initializeParticleEffects();
}

// Contadores animados en hero
function animateHeroCounters() {
    const counters = document.querySelectorAll('.hero-stat .stat-number');
    counters.forEach(counter => {
        const target = parseInt(counter.textContent.replace(/\D/g, ''));
        if (!isNaN(target)) {
            animateCountUp(counter, 0, target, 2000);
        }
    });
}

// Formulario flotante de citas
function initializeFloatingAppointmentForm() {
    const form = document.getElementById('appointmentForm');
    if (!form) return;
    
    // Validación en tiempo real
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldErrors);
    });
    
    // Submit con animación
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (validateAppointmentForm(this)) {
            showLoadingOverlay();
            
            // Simular envío (reemplazar con fetch real)
            setTimeout(() => {
                hideLoadingOverlay();
                showMaskotNotification('¡Cita agendada exitosamente! Te contactaremos pronto.', 'success');
                this.reset();
            }, 2000);
        }
    });
}

// Validar formulario de cita
function validateAppointmentForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Este campo es obligatorio');
            isValid = false;
        }
    });
    
    // Validar fecha
    const dateField = form.querySelector('input[type="date"]');
    if (dateField && dateField.value) {
        const selectedDate = new Date(dateField.value);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        if (selectedDate < today) {
            showFieldError(dateField, 'No puedes seleccionar fechas pasadas');
            isValid = false;
        }
    }
    
    // Validar email
    const emailField = form.querySelector('input[type="email"]');
    if (emailField && emailField.value && !isValidEmail(emailField.value)) {
        showFieldError(emailField, 'Por favor ingresa un email válido');
        isValid = false;
    }
    
    // Validar teléfono
    const phoneField = form.querySelector('input[type="tel"]');
    if (phoneField && phoneField.value && !isValidPhone(phoneField.value)) {
        showFieldError(phoneField, 'Por favor ingresa un teléfono válido');
        isValid = false;
    }
    
    return isValid;
}

// Validar teléfono
function isValidPhone(phone) {
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
}

// Animación de servicios
function initializeServicesAnimation() {
    const serviceCards = document.querySelectorAll('.service-card');
    serviceCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
}

// Efectos de partículas (opcional)
function initializeParticleEffects() {
    // Implementación simple de partículas flotantes
    const hero = document.querySelector('.hero-section');
    if (!hero) return;
    
    for (let i = 0; i < 20; i++) {
        createFloatingParticle(hero, i);
    }
}

function createFloatingParticle(container, index) {
    const particle = document.createElement('div');
    particle.className = 'floating-particle';
    particle.style.cssText = `
        position: absolute;
        width: ${Math.random() * 10 + 5}px;
        height: ${Math.random() * 10 + 5}px;
        background: rgba(255, 163, 1, 0.3);
        border-radius: 50%;
        left: ${Math.random() * 100}%;
        top: ${Math.random() * 100}%;
        animation: float ${Math.random() * 10 + 10}s infinite linear;
        animation-delay: ${index * 0.5}s;
        pointer-events: none;
    `;
    
    container.appendChild(particle);
}

// === PÁGINA DE CITAS ===
function initializeCitasPage() {
    console.log('📅 Inicializando página de citas');
    
    // Auto-refresh cada 30 segundos
    setInterval(function() {
        if (document.visibilityState === 'visible') {
            refreshCitasData();
        }
    }, 30000);
    
    // Filtros de citas
    initializeCitasFilters();
    
    // Actualización en tiempo real del estado
    initializeRealTimeUpdates();
}

// === PÁGINA DE SERVICIOS ===
function initializeServiciosPage() {
    console.log('🛎️ Inicializando página de servicios');
    
    // Drag and drop para reordenar servicios (futuro)
    initializeServicesDragDrop();
    
    // Validación dinámica de límites
    const maxCitasInputs = document.querySelectorAll('input[name="max_citas"]');
    maxCitasInputs.forEach(input => {
        input.addEventListener('input', function() {
            validateMaxCitas(this);
        });
    });
}

// === PÁGINA DE PERSONAL ===
function initializePersonalPage() {
    console.log('👥 Inicializando página de personal');
    
    // Validación de contraseñas
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            validatePassword(this);
        });
    });
    
    // Formateo automático de salario
    const salarioInputs = document.querySelectorAll('input[name="salario"]');
    salarioInputs.forEach(input => {
        input.addEventListener('blur', function() {
            formatSalary(this);
        });
    });
}

// === PÁGINA DE ASISTENCIA ===
function initializeAsistenciaPage() {
    console.log('🕐 Inicializando página de asistencia');
    
    // Actualización de tiempo en tiempo real
    updateTimeDisplay();
    setInterval(updateTimeDisplay, 1000);
    
    // Geolocalización para registro (opcional)
    if ('geolocation' in navigator) {
        initializeLocationTracking();
    }
    
    // Notificaciones de recordatorio
    scheduleAsistenciaReminders();
}

// === PÁGINA DE ALMACÉN MEJORADA ===
function initializeAlmacenPage() {
    console.log('📦 Inicializando página de almacén MASKOT');
    
    // SKIP: Formularios usan no-animation, funcionan sin JavaScript
    // initializeProductForm();
    
    // Tabla interactiva
    initializeProductTable();
    
    // Alertas de stock y vencimiento
    checkInventoryAlerts();
    
    // Búsqueda en tiempo real
    initializeProductSearch();
    
    // Filtros avanzados
    initializeProductFilters();
}

// Inicializar formulario de productos
function initializeProductForm() {
    const form = document.getElementById('formularioProducto');
    if (!form) return;
    
    // Si el formulario tiene no-animation, no interceptar su envío
    if (form.classList.contains('no-animation')) {
        console.log('Formulario con no-animation detectado, usando envío normal');
        return; // Salir sin agregar interceptores
    }
    
    // Validación en tiempo real
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldErrors);
    });
    
    // Manejo del selector de tipo
    const tipoSelect = form.querySelector('select[name="tipo"]');
    const imagenContainer = document.getElementById('imagenContainer');
    
    if (tipoSelect && imagenContainer) {
        tipoSelect.addEventListener('change', function() {
            if (this.value === 'alimento' || this.value === 'juguete') {
                imagenContainer.style.display = 'block';
                imagenContainer.querySelector('input').setAttribute('required', 'required');
            } else {
                imagenContainer.style.display = 'none';
                imagenContainer.querySelector('input').removeAttribute('required');
            }
        });
        
        // Ejecutar al cargar si ya hay valor seleccionado
        tipoSelect.dispatchEvent(new Event('change'));
    }
    
    // Preview de imagen
    const imageInput = form.querySelector('input[type="file"]');
    if (imageInput) {
        imageInput.addEventListener('change', handleImagePreview);
    }
    
    // Submit con validación
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (validateProductForm(this)) {
            submitProductForm(this);
        }
    });
}

// Manejo del preview de imagen
function handleImagePreview(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validar tipo de archivo
    if (!file.type.startsWith('image/')) {
        showMaskotNotification('Por favor selecciona solo archivos de imagen', 'error');
        e.target.value = '';
        return;
    }
    
    // Validar tamaño (máximo 5MB)
    if (file.size > 5 * 1024 * 1024) {
        showMaskotNotification('La imagen debe ser menor a 5MB', 'error');
        e.target.value = '';
        return;
    }
    
    // Crear preview
    const reader = new FileReader();
    reader.onload = function(e) {
        let preview = document.querySelector('.image-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.className = 'image-preview';
            preview.style.cssText = `
                margin-top: 10px;
                text-align: center;
                padding: 10px;
                border: 2px dashed var(--maskot-primary);
                border-radius: 8px;
                background: var(--maskot-light);
            `;
            e.target.parentNode.appendChild(preview);
        }
        
        preview.innerHTML = `
            <img src="${e.target.result}" alt="Preview" style="
                max-width: 200px;
                max-height: 200px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            ">
            <p style="margin-top: 8px; font-size: 0.9rem; color: var(--maskot-secondary);">
                ${file.name} (${(file.size / 1024).toFixed(1)} KB)
            </p>
        `;
    };
    reader.readAsDataURL(file);
}

// Validar formulario de producto
function validateProductForm(form) {
    let isValid = true;
    
    // Validaciones básicas
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Este campo es obligatorio');
            isValid = false;
        }
    });
    
    // Validar precio
    const precioField = form.querySelector('input[name="precio"]');
    if (precioField && precioField.value) {
        const precio = parseFloat(precioField.value);
        if (isNaN(precio) || precio <= 0) {
            showFieldError(precioField, 'El precio debe ser un número mayor a 0');
            isValid = false;
        }
    }
    
    // Validar cantidad
    const cantidadField = form.querySelector('input[name="cantidad"]');
    if (cantidadField && cantidadField.value) {
        const cantidad = parseInt(cantidadField.value);
        if (isNaN(cantidad) || cantidad < 0) {
            showFieldError(cantidadField, 'La cantidad debe ser un número mayor o igual a 0');
            isValid = false;
        }
    }
    
    // Validar fecha de vencimiento
    const fechaField = form.querySelector('input[name="fecha_vencimiento"]');
    if (fechaField && fechaField.value) {
        const fecha = new Date(fechaField.value);
        const hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        
        if (fecha < hoy) {
            showFieldError(fechaField, 'La fecha de vencimiento no puede ser en el pasado');
            isValid = false;
        }
    }
    
    return isValid;
}

// Enviar formulario de producto
function submitProductForm(form) {
    // Verificación de seguridad
    if (!form || !form.tagName || form.tagName !== 'FORM') {
        console.error('submitProductForm: parámetro no es un formulario válido');
        return;
    }
    
    showLoadingOverlay();
    
    const formData = new FormData(form);
    
    fetch('/almacen', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingOverlay();

        if (data.success) {
            showMaskotNotification('Producto guardado exitosamente', 'success');
            form.reset();

            // Limpiar preview de imagen
            const preview = document.querySelector('.image-preview');
            if (preview) preview.remove();

            // Recargar tabla
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showMaskotNotification(data.message || 'Error al guardar el producto', 'error');
        }
    })
    .catch(error => {
        hideLoadingOverlay();
        console.error('Error:', error);
        showMaskotNotification('Error de conexión. Intenta nuevamente.', 'error');
    });
}

// Inicializar tabla interactiva
function initializeProductTable() {
    const table = document.querySelector('.table-productos');
    if (!table) return;
    
    // Hover effects en filas
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'rgba(255, 163, 1, 0.1)';
            this.style.transform = 'scale(1.01)';
            this.style.transition = 'all 0.2s ease';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
            this.style.transform = 'scale(1)';
        });
    });
    
    // Confirmar eliminaciones
    table.addEventListener('click', function(e) {
        if (e.target.matches('.btn-eliminar')) {
            e.preventDefault();
            
            const productName = e.target.closest('tr').querySelector('.producto-info strong').textContent;
            
            if (confirm(`¿Estás seguro de que quieres eliminar "${productName}"?`)) {
                deleteProduct(e.target.href, e.target.closest('tr'));
            }
        }
    });
}

// Eliminar producto con animación
function deleteProduct(url, row) {
    showLoadingOverlay();
    
    fetch(url, { method: 'DELETE' })
    .then(response => response.json())
    .then(data => {
        hideLoadingOverlay();
        
        if (data.success) {
            // Animar eliminación
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '0';
            row.style.transform = 'translateX(-100px)';
            
            setTimeout(() => {
                row.remove();
                showMaskotNotification('Producto eliminado exitosamente', 'success');
            }, 300);
        } else {
            showMaskotNotification(data.message || 'Error al eliminar el producto', 'error');
        }
    })
    .catch(error => {
        hideLoadingOverlay();
        console.error('Error:', error);
        showMaskotNotification('Error de conexión. Intenta nuevamente.', 'error');
    });
}

// Alertas de inventario
function checkInventoryAlerts() {
    // Stock bajo
    const lowStockItems = document.querySelectorAll('.low-stock');
    lowStockItems.forEach((item, index) => {
        setTimeout(() => {
            const row = item.closest('tr');
            const productName = row.querySelector('.producto-info strong').textContent;
            showMaskotNotification(`Stock bajo: ${productName}`, 'warning', 6000);
        }, index * 1000);
    });
    
    // Productos vencidos
    const expiredItems = document.querySelectorAll('.expired');
    expiredItems.forEach((item, index) => {
        setTimeout(() => {
            const row = item.closest('tr');
            const productName = row.querySelector('.producto-info strong').textContent;
            showMaskotNotification(`Producto vencido: ${productName}`, 'error', 8000);
        }, (lowStockItems.length + index) * 1000);
    });
    
    // Productos por vencer
    const expiringItems = document.querySelectorAll('.expiring-soon');
    expiringItems.forEach((item, index) => {
        setTimeout(() => {
            const row = item.closest('tr');
            const productName = row.querySelector('.producto-info strong').textContent;
            showMaskotNotification(`Producto por vencer: ${productName}`, 'warning', 6000);
        }, (lowStockItems.length + expiredItems.length + index) * 1000);
    });
}

// Búsqueda en tiempo real
function initializeProductSearch() {
    const searchInput = document.querySelector('#productSearch');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        const rows = document.querySelectorAll('.table-productos tbody tr');
        
        rows.forEach(row => {
            const productName = row.querySelector('.producto-info strong').textContent.toLowerCase();
            const productDescription = row.querySelector('.producto-info small')?.textContent.toLowerCase() || '';
            
            if (productName.includes(searchTerm) || productDescription.includes(searchTerm)) {
                row.style.display = '';
                row.style.animation = 'fadeIn 0.3s ease';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

// Filtros de productos
function initializeProductFilters() {
    const typeFilter = document.querySelector('#typeFilter');
    const statusFilter = document.querySelector('#statusFilter');
    
    [typeFilter, statusFilter].forEach(filter => {
        if (filter) {
            filter.addEventListener('change', applyProductFilters);
        }
    });
}

function applyProductFilters() {
    const typeFilter = document.querySelector('#typeFilter')?.value || '';
    const statusFilter = document.querySelector('#statusFilter')?.value || '';
    const rows = document.querySelectorAll('.table-productos tbody tr');
    
    rows.forEach(row => {
        let show = true;
        
        // Filtro por tipo
        if (typeFilter) {
            const productType = row.querySelector('.product-type')?.textContent.toLowerCase() || '';
            if (!productType.includes(typeFilter.toLowerCase())) {
                show = false;
            }
        }
        
        // Filtro por estado
        if (statusFilter) {
            const hasClass = row.classList.contains(statusFilter);
            if (!hasClass) {
                show = false;
            }
        }
        
        row.style.display = show ? '' : 'none';
        if (show) {
            row.style.animation = 'fadeIn 0.3s ease';
        }
    });
}

// === PÁGINA DE DASHBOARD ===
function initializeDashboardPage() {
    console.log('📊 Inicializando dashboard');
    
    // Actualización automática de estadísticas
    setInterval(updateDashboardStats, 60000);
    
    // Gráficos y métricas
    initializeCharts();
    
    // Notificaciones push
    initializePushNotifications();
}

// === FUNCIONES UTILITARIAS ===

// Configurar fecha mínima para inputs de fecha
function setMinDateForDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
        if (!input.hasAttribute('min')) {
            input.setAttribute('min', today);
        }
    });
}

// Inicializar elementos interactivos
function initializeInteractiveElements() {
    // Tooltips simples
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
    
    // Botones de carga (excepto formularios no-animation)
    document.querySelectorAll('.btn[type="submit"]').forEach(button => {
        button.addEventListener('click', function() {
            // Skip completamente si el formulario tiene no-animation
            if (this.form && this.form.classList && this.form.classList.contains('no-animation')) {
                return; // Salir completamente, no agregar estados de carga
            }
            
            if (this.form && this.form.checkValidity()) {
                showLoadingState(this);
            }
        });
    });
}

// Auto-cerrar alertas
function autoCloseAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            fadeOut(alert);
        }, 5000);
    });
}

// Validación de formularios
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'Este campo es obligatorio');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Validaciones específicas
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            showFieldError(field, 'Ingresa un email válido');
            isValid = false;
        }
    });
    
    return isValid;
}

// Validación específica para formulario de citas
function validateCitaForm(form) {
    const fecha = new Date(form.fecha.value);
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    
    if (fecha < hoy) {
        showNotification('No puedes agendar citas para fechas pasadas', 'error');
        return false;
    }
    
    // Validar horario laboral
    const hora = form.hora.value;
    if (!isValidBusinessHour(hora)) {
        showNotification('Selecciona una hora dentro del horario laboral', 'warning');
        return false;
    }
    
    return true;
}

// Funciones de validación
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidBusinessHour(hora) {
    const [hours, minutes] = hora.split(':').map(Number);
    const time = hours * 60 + minutes;
    const start = 8 * 60; // 8:00 AM
    const end = 18 * 60; // 6:00 PM
    const lunchStart = 12 * 60; // 12:00 PM
    const lunchEnd = 13 * 60; // 1:00 PM
    
    return (time >= start && time < lunchStart) || (time >= lunchEnd && time <= end);
}

// Mostrar/ocultar errores de campo
function showFieldError(field, message) {
    clearFieldError(field);
    
    const error = document.createElement('div');
    error.className = 'field-error';
    error.textContent = message;
    error.style.color = 'var(--danger-color)';
    error.style.fontSize = '0.8rem';
    error.style.marginTop = '4px';
    
    field.style.borderColor = 'var(--danger-color)';
    field.parentNode.appendChild(error);
}

function clearFieldError(field) {
    field.style.borderColor = '';
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
}

// Sistema de notificaciones MASKOT mejorado
function showMaskotNotification(message, type = 'info', duration = 4000) {
    // Remover notificaciones existentes del mismo tipo
    document.querySelectorAll(`.maskot-notification.notification-${type}`).forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `maskot-notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-icon">
                <i class="fas fa-${getNotificationIcon(type)}"></i>
            </div>
            <div class="notification-text">
                <div class="notification-title">${getNotificationTitle(type)}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Estilos mejorados
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        background: white;
        padding: 0;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        border-left: 4px solid var(--maskot-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : type === 'success' ? 'primary' : 'secondary'});
        max-width: 400px;
        min-width: 300px;
        animation: slideInRight 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        overflow: hidden;
    `;
    
    // Estilos internos
    const content = notification.querySelector('.notification-content');
    content.style.cssText = `
        display: flex;
        align-items: center;
        padding: 20px;
        gap: 15px;
    `;
    
    const icon = notification.querySelector('.notification-icon');
    icon.style.cssText = `
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--maskot-${type === 'error' ? 'danger' : type === 'warning' ? 'warning' : type === 'success' ? 'primary' : 'secondary'});
        color: white;
        font-size: 18px;
        flex-shrink: 0;
    `;
    
    const textContainer = notification.querySelector('.notification-text');
    textContainer.style.cssText = `
        flex: 1;
        min-width: 0;
    `;
    
    const title = notification.querySelector('.notification-title');
    title.style.cssText = `
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 4px;
        color: #333;
    `;
    
    const messageEl = notification.querySelector('.notification-message');
    messageEl.style.cssText = `
        font-size: 13px;
        color: #666;
        line-height: 1.4;
    `;
    
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: #999;
        cursor: pointer;
        padding: 5px;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
        flex-shrink: 0;
    `;
    
    document.body.appendChild(notification);
    
    // Efecto hover en botón cerrar
    closeBtn.addEventListener('mouseenter', function() {
        this.style.background = 'rgba(0,0,0,0.1)';
        this.style.color = '#333';
    });
    
    closeBtn.addEventListener('mouseleave', function() {
        this.style.background = 'none';
        this.style.color = '#999';
    });
    
    // Auto-remover con animación
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, duration);
}

function getNotificationTitle(type) {
    switch(type) {
        case 'success': return '¡Perfecto!';
        case 'error': return 'Error';
        case 'warning': return 'Atención';
        case 'info': return 'Información';
        default: return 'MASKOT';
    }
}

// Validación de campos mejorada
function validateField(e) {
    const field = e.target;
    const value = field.value.trim();
    
    // Limpiar errores previos
    clearFieldErrors(field);
    
    // Validar campo requerido
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, 'Este campo es obligatorio');
        return false;
    }
    
    // Validar email
    if (field.type === 'email' && value && !isValidEmail(value)) {
        showFieldError(field, 'Por favor ingresa un email válido');
        return false;
    }
    
    // Validar teléfono
    if (field.type === 'tel' && value && !isValidPhone(value)) {
        showFieldError(field, 'Por favor ingresa un teléfono válido');
        return false;
    }
    
    // Validar fecha
    if (field.type === 'date' && value) {
        const selectedDate = new Date(value);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        if (selectedDate < today) {
            showFieldError(field, 'No puedes seleccionar fechas pasadas');
            return false;
        }
    }
    
    return true;
}

function clearFieldErrors(field) {
    if (typeof field === 'object' && field.target) {
        field = field.target;
    }
    
    // Restaurar estilos del campo
    field.classList.remove('is-invalid');
    field.style.borderColor = '';
    field.style.boxShadow = '';
    
    // Remover mensaje de error
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Remover feedback de Bootstrap si existe
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

// Mostrar error de campo mejorado
function showFieldError(field, message) {
    clearFieldErrors(field);
    
    // Agregar clase de Bootstrap
    field.classList.add('is-invalid');
    
    // Crear mensaje de error
    const error = document.createElement('div');
    error.className = 'field-error invalid-feedback';
    error.textContent = message;
    error.style.cssText = `
        display: block;
        color: #dc3545;
        font-size: 0.875rem;
        margin-top: 0.25rem;
        font-weight: 500;
    `;
    
    // Estilo del campo con error
    field.style.cssText += `
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
    `;
    
    // Insertar después del campo
    field.parentNode.appendChild(error);
    
    // Animar entrada del error
    error.style.opacity = '0';
    error.style.transform = 'translateY(-10px)';
    
    setTimeout(() => {
        error.style.transition = 'all 0.3s ease';
        error.style.opacity = '1';
        error.style.transform = 'translateY(0)';
    }, 10);
}

function getNotificationIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'error': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

// Animaciones
function fadeOut(element) {
    element.style.transition = 'opacity 0.3s ease';
    element.style.opacity = '0';
    setTimeout(() => {
        if (element.parentNode) {
            element.remove();
        }
    }, 300);
}

function showLoadingState(button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    button.disabled = true;
    
    // Restaurar después de 10 segundos como fallback
    setTimeout(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    }, 10000);
}

// Funciones específicas de citas
function refreshCitasData() {
    // Implementar AJAX para actualizar datos
    console.log('🔄 Actualizando datos de citas...');
}

function updateAvailability() {
    const servicioId = this.value;
    const fechaInput = document.getElementById('fecha');
    
    if (servicioId && fechaInput.value) {
        // Aquí implementaría una llamada AJAX para verificar disponibilidad
        console.log(`Verificando disponibilidad para servicio ${servicioId}`);
    }
}

// Funciones de tiempo real
function updateTimeDisplay() {
    const timeDisplays = document.querySelectorAll('#currentTime, .current-time span');
    const now = new Date().toLocaleTimeString('es-ES');
    
    timeDisplays.forEach(display => {
        if (display) {
            display.textContent = now;
        }
    });
}

function initializeRealTimeUpdates() {
    // WebSocket o polling para actualizaciones en tiempo real
    if ('WebSocket' in window) {
        // Implementar WebSocket para updates en tiempo real
        console.log('🔌 Inicializando conexión WebSocket...');
    }
}

// Funciones de almacén
function checkLowStockAlerts() {
    document.querySelectorAll('.low-stock').forEach(item => {
        const productName = item.closest('tr').querySelector('.producto-info strong').textContent;
        showNotification(`Stock bajo: ${productName}`, 'warning');
    });
}

function checkExpirationAlerts() {
    document.querySelectorAll('.expiring-soon, .expired').forEach(item => {
        const row = item.closest('tr');
        const productName = row.querySelector('.producto-info strong').textContent;
        const isExpired = item.classList.contains('expired');
        
        showNotification(
            `Producto ${isExpired ? 'vencido' : 'por vencer'}: ${productName}`,
            isExpired ? 'error' : 'warning'
        );
    });
}

// Funciones de dashboard
function updateDashboardStats() {
    // Actualizar estadísticas del dashboard
    console.log('📊 Actualizando estadísticas del dashboard...');
}

function animateCounters() {
    document.querySelectorAll('.stat-content h3').forEach(counter => {
        const target = parseInt(counter.textContent);
        if (!isNaN(target)) {
            animateCountUp(counter, 0, target, 2000);
        }
    });
}

function animateCountUp(element, start, end, duration) {
    const startTime = performance.now();
    
    function updateCount(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = Math.floor(progress * (end - start) + start);
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(updateCount);
        }
    }
    
    requestAnimationFrame(updateCount);
}

// Funciones de modal
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// Funciones de validación específica
function validatePassword(input) {
    const password = input.value;
    const minLength = 6;
    
    if (password.length < minLength) {
        showFieldError(input, `La contraseña debe tener al menos ${minLength} caracteres`);
    } else {
        clearFieldError(input);
    }
}

function formatSalary(input) {
    const value = parseFloat(input.value);
    if (!isNaN(value)) {
        input.value = value.toFixed(2);
    }
}

function validateMaxCitas(input) {
    const value = parseInt(input.value);
    if (value < 1 || value > 50) {
        showFieldError(input, 'El número de citas debe estar entre 1 y 50');
    } else {
        clearFieldError(input);
    }
}

// Funciones auxiliares
function getCurrentPageFromURL() {
    const path = window.location.pathname;
    if (path === '/' || path === '/index') return 'index';
    return path.substring(1); // Remover el slash inicial
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Tooltips
function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = e.target.dataset.tooltip;
    tooltip.style.cssText = `
        position: absolute;
        background: var(--dark-color);
        color: white;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 0.8rem;
        z-index: 10000;
        pointer-events: none;
        white-space: nowrap;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    e.target._tooltip = tooltip;
}

function hideTooltip(e) {
    if (e.target._tooltip) {
        e.target._tooltip.remove();
        delete e.target._tooltip;
    }
}

// Inicialización de características futuras (placeholder)
function initializeServicesDragDrop() {
    // Implementar drag & drop para reordenar servicios
}

function initializeLocationTracking() {
    // Implementar tracking de ubicación para asistencia
}

function scheduleAsistenciaReminders() {
    // Implementar recordatorios de asistencia
}

function initializeStockCalculator() {
    // Implementar calculadora de stock
}

function initializeBarcodeScanner() {
    // Implementar scanner de códigos de barras
}

function initializeCitasFilters() {
    // Implementar filtros para citas
}

function initializeCharts() {
    // Implementar gráficos del dashboard
}

function initializePushNotifications() {
    // Implementar notificaciones push
}

// Exportar funciones globales para uso en templates
window.MaskotApp = {
    // Notificaciones
    showNotification: showMaskotNotification,
    
    // Validaciones
    validateForm: validateAppointmentForm,
    validateField: validateField,
    
    // UI
    showLoading: showLoadingOverlay,
    hideLoading: hideLoadingOverlay,
    
    // Modales
    closeModals: closeAllModals,
    
    // Utilidades
    formatCurrency: function(amount) {
        return new Intl.NumberFormat('es-CL', {
            style: 'currency',
            currency: 'CLP'
        }).format(amount);
    },
    
    formatDate: function(date) {
        return new Date(date).toLocaleDateString('es-CL');
    },
    
    // Animaciones
    animateCounter: animateCountUp,
    
    // Formularios
    resetForm: function(form) {
        if (typeof form === 'string') {
            form = document.querySelector(form);
        }
        if (form) {
            form.reset();
            // Limpiar errores
            form.querySelectorAll('.is-invalid').forEach(field => {
                clearFieldErrors(field);
            });
            // Limpiar previews
            const previews = form.querySelectorAll('.image-preview');
            previews.forEach(preview => preview.remove());
        }
    }
};

window.carrito = window.carrito || [];
window.total = window.total || 0;
window.ultimaVenta = window.ultimaVenta || null;

window.filtrarProductos = function() {
    const filtro = document.getElementById('filtro-productos').value.toLowerCase();
    const productos = document.querySelectorAll('.producto-card');
    productos.forEach(producto => {
        const nombre = producto.getAttribute('data-nombre');
        if (nombre.includes(filtro)) {
            producto.style.display = 'block';
        } else {
            producto.style.display = 'none';
        }
    });
}

window.filtrarPorCategoria = function(categoria) {
    const productos = document.querySelectorAll('.producto-card');
    const botonesFiltro = document.querySelectorAll('.filtro-btn');
    botonesFiltro.forEach(btn => {
        if (btn.getAttribute('data-categoria') === categoria) {
            btn.style.background = 'linear-gradient(135deg, #ffa301, #e6920e)';
        } else {
            btn.style.background = '#6c757d';
        }
    });
    productos.forEach(producto => {
        const categoriaProducto = producto.getAttribute('data-categoria');
        if (categoria === 'todos' || categoriaProducto === categoria || categoriaProducto.includes(categoria)) {
            producto.style.display = 'block';
        } else {
            producto.style.display = 'none';
        }
    });
    document.getElementById('filtro-productos').value = '';
}

window.agregarProducto = function(id, nombre, precio) {
    precio = parseFloat(precio);
    let itemExistente = window.carrito.find(item => item.id == id);
    if (itemExistente) {
        itemExistente.cantidad++;
    } else {
        window.carrito.push({id, nombre, precio, cantidad: 1});
    }
    window.actualizarCarrito();
    window.actualizarBotonPagar();
}

window.cambiarMetodoPago = function() {
    const metodo = document.getElementById('metodo_pago').value;
    const dineroSection = document.getElementById('dinero-section');
    const multipagoSection = document.getElementById('multipago-section');
    if (metodo === 'efectivo') {
        dineroSection.style.display = 'block';
        multipagoSection.style.display = 'none';
    } else if (metodo === 'multipago') {
        dineroSection.style.display = 'none';
        multipagoSection.style.display = 'block';
        window.calcularMultipago && window.calcularMultipago();
    } else {
        dineroSection.style.display = 'none';
        multipagoSection.style.display = 'none';
    }
    window.actualizarBotonPagar && window.actualizarBotonPagar();
}

window.actualizarCarrito = function() {
    const carritoVacio = document.getElementById('carrito-vacio');
    const carritoItems = document.getElementById('carrito-items');
    let total = 0;
    if (window.carrito.length === 0) {
        carritoVacio.style.display = 'block';
        carritoItems.style.display = 'none';
        window.total = 0;
        window.calcularCambio && window.calcularCambio();
        window.actualizarBotonPagar && window.actualizarBotonPagar();
        return;
    }
    carritoVacio.style.display = 'none';
    carritoItems.style.display = 'block';
    let html = '';
    window.carrito.forEach(item => {
        const subtotal = item.precio * item.cantidad;
        total += subtotal;
        html += `
            <div style="background: #fff; border-radius: 12px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #ffa301; box-shadow: 0 4px 10px rgba(255,163,1,0.1); border: 1px solid #e9ecef;">
                <div style="margin-bottom: 5px;">
                    <strong style="color: #2c3e50; display: block; font-size: 15px; font-weight: 700;">${item.nombre}</strong>
                    <span style="color: #ffa301; font-weight: 600; font-size: 14px;">S/ ${item.precio.toFixed(2)} x ${item.cantidad}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; margin: 8px 0; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <button onclick="window.cambiarCantidad('${item.id}', -1)" style="background: #ffa301; color: white; border: none; border-radius: 6px; width: 28px; height: 28px; cursor: pointer; font-weight: 700; font-size: 14px; box-shadow: 0 2px 8px rgba(255,163,1,0.3); padding:0;">-</button>
                        <span style="font-weight: 600; color: #2c3e50; min-width: 24px; text-align: center; font-size: 14px;">${item.cantidad}</span>
                        <button onclick="window.cambiarCantidad('${item.id}', 1)" style="background: #ffa301; color: white; border: none; border-radius: 6px; width: 28px; height: 28px; cursor: pointer; font-weight: 700; font-size: 14px; box-shadow: 0 2px 8px rgba(255,163,1,0.3); padding:0;">+</button>
                    </div>
                    <button onclick="window.eliminarItem('${item.id}')" style="background: #dc3545; color: white; border: none; border-radius: 6px; width: 28px; height: 28px; cursor: pointer; font-size: 16px; box-shadow: 0 2px 8px rgba(220,53,69,0.3); padding:0; display: flex; align-items: center; justify-content: center;">×</button>
                </div>
                <div style="text-align: right; font-weight: 700; color: #ffa301; font-size: 15px;">S/ ${subtotal.toFixed(2)}</div>
            </div>
        `;
    });
    html += `
        <div style="background: linear-gradient(135deg, #ffa301, #6ccae2); color: white; padding: 20px; border-radius: 15px; text-align: center; font-size: 20px; font-weight: 700; margin-top: 20px; box-shadow: 0 8px 25px rgba(255,163,1,0.15); text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            <strong>Total: S/ ${total.toFixed(2)}</strong>
        </div>
    `;
    carritoItems.innerHTML = html;
    window.total = total;
    window.calcularCambio && window.calcularCambio();
    window.calcularMultipago && window.calcularMultipago();
    window.actualizarBotonPagar && window.actualizarBotonPagar();
}

window.eliminarItem = function(id) {
    window.carrito = window.carrito.filter(item => item.id != id);
    window.actualizarCarrito();
}

window.cambiarCantidad = function(id, cambio) {
    let item = window.carrito.find(item => item.id == id);
    if (item) {
        item.cantidad += cambio;
        if (item.cantidad <= 0) {
            window.eliminarItem(id);
        } else {
            window.actualizarCarrito();
        }
    }
}

window.calcularCambio = function() {
    const montoRecibido = parseFloat(document.getElementById('monto_recibido').value) || 0;
    const cambio = montoRecibido - window.total;
    document.getElementById('cambio').value = cambio.toFixed(2);
}

window.calcularMultipago = function() {
    const monto1Input = document.getElementById('monto1');
    const monto2Input = document.getElementById('monto2');
    const total = window.total;
    if (total > 0) {
        const monto1 = parseFloat(monto1Input.value) || 0;
        const monto2 = total - monto1;
        monto2Input.value = monto2 > 0 ? monto2.toFixed(2) : '0.00';
    } else {
        monto2Input.value = '0.00';
    }
}

window.actualizarBotonPagar = function() {
    const btnPagar = document.getElementById('btn-pagar');
    const metodo = document.getElementById('metodo_pago').value;
    let puedeProceder = false;
    if (window.carrito.length === 0) {
        btnPagar.disabled = true;
        btnPagar.style.background = '#adb5bd';
        btnPagar.style.cursor = 'not-allowed';
        btnPagar.innerHTML = '<i class="fas fa-credit-card"></i> Pagar';
        return;
    }
    if (metodo === 'efectivo') {
        const montoRecibido = parseFloat(document.getElementById('monto_recibido').value) || 0;
        puedeProceder = montoRecibido >= window.total && window.total > 0;
    } else if (metodo === 'multipago') {
        const monto1 = parseFloat(document.getElementById('monto1').value) || 0;
        const monto2 = parseFloat(document.getElementById('monto2').value) || 0;
        puedeProceder = (monto1 + monto2) >= window.total && monto1 > 0 && monto2 > 0 && window.total > 0;
    } else {
        puedeProceder = window.total > 0;
    }
    if (puedeProceder) {
        btnPagar.disabled = false;
        btnPagar.style.background = 'linear-gradient(135deg, #ffa301, #6ccae2)';
        btnPagar.style.cursor = 'pointer';
        btnPagar.innerHTML = '<i class="fas fa-check"></i> Procesar Pago';
    } else {
        btnPagar.disabled = true;
        btnPagar.style.background = '#adb5bd';
        btnPagar.style.cursor = 'not-allowed';
        btnPagar.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Monto Insuficiente';
    }
}

window.procesarPago = function() {
    if (window.carrito.length === 0) {
        if (typeof window.mostrarAlertaUI === 'function') window.mostrarAlertaUI('El carrito está vacío', 'warning');
        else showMaskotNotification('El carrito está vacío', 'warning');
        return;
    }
    const metodo = document.getElementById('metodo_pago').value;
    const total = window.total;
    if (metodo === 'efectivo') {
        const montoRecibido = parseFloat(document.getElementById('monto_recibido').value) || 0;
        if (montoRecibido < total) {
            if (typeof window.mostrarAlertaUI === 'function') window.mostrarAlertaUI('El monto recibido es insuficiente', 'warning');
            else showMaskotNotification('El monto recibido es insuficiente', 'warning');
            return;
        }
        // Aquí iría la lógica de procesamiento de pago efectivo
        // Registro básico de venta
        console.log('Pago en efectivo aceptado, monto recibido:', montoRecibido);
    } else if (metodo === 'multipago') {
        const monto1 = parseFloat(document.getElementById('monto1').value) || 0;
        const monto2 = parseFloat(document.getElementById('monto2').value) || 0;
        if ((monto1 + monto2) < total) {
            if (typeof window.mostrarAlertaUI === 'function') window.mostrarAlertaUI('El monto total de multipago es insuficiente', 'warning');
            else showMaskotNotification('El monto total de multipago es insuficiente', 'warning');
            return;
        }
        // Aquí iría la lógica de procesamiento de multipago
        console.log('Pago multipago aceptado, montos:', monto1, monto2);
    } else {
        // Tarjeta o Yape
        console.log('Pago con método', metodo, 'procesado');
    }
    // Construir objeto de última venta
    try {
        const venta = {
            numero: (Math.floor(Math.random() * 900000) + 100000).toString(),
            fecha: new Date().toLocaleString(),
            productos: JSON.parse(JSON.stringify(window.carrito || [])),
            subtotal: Number((window.total / 1.18).toFixed(2)),
            igv: Number((window.total - (window.total / 1.18)).toFixed(2)),
            total: Number(window.total.toFixed(2)),
            metodo_pago: metodo
        };

        if (metodo === 'efectivo') {
            // support both dash and underscore id variants depending on template
            const montoRecElem = document.getElementById('monto_recibido') || document.getElementById('monto-recibido');
            venta.monto_recibido = montoRecElem ? parseFloat(montoRecElem.value) || 0 : 0;
            venta.cambio = Number((venta.monto_recibido - venta.total).toFixed(2));
        }

        if (metodo === 'multipago') {
            venta.detalle_multipago = {
                metodo1: document.getElementById('metodo1').value,
                monto1: parseFloat(document.getElementById('monto1').value) || 0,
                metodo2: document.getElementById('metodo2').value,
                monto2: parseFloat(document.getElementById('monto2').value) || 0
            };
        }

        // Guardar venta en variable global para imprimir/mostrar
        window.ultimaVenta = venta;

        // Evitar envíos duplicados: deshabilitar botón
        const btnPagar = document.getElementById('btn-pagar');
        if (btnPagar) {
            btnPagar.disabled = true;
            btnPagar.style.cursor = 'not-allowed';
            btnPagar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        }

        // Enviar la venta al backend para persistencia
        (async function() {
            try {
                // collect referencia_pago if present in the page (tarjeta / yape flows)
                const referenciaTarjetaElem = document.getElementById('referencia-tarjeta');
                const referenciaYapeElem = document.getElementById('referencia-yape');
                const referenciaTarjeta = referenciaTarjetaElem ? (referenciaTarjetaElem.value || '').trim() : '';
                const referenciaYape = referenciaYapeElem ? (referenciaYapeElem.value || '').trim() : '';

                const payload = {
                    productos: venta.productos.map(p => ({id: p.id, nombre: p.nombre, precio: p.precio, cantidad: p.cantidad})),
                    subtotal: venta.subtotal,
                    igv: venta.igv,
                    total: venta.total,
                    metodo_pago: venta.metodo_pago,
                    monto_recibido: venta.monto_recibido,
                    cambio_entregado: venta.cambio,
                    detalle_multipago: venta.detalle_multipago || null
                };

                // Attach referencia_pago when applicable so server-side validation passes
                if (venta.metodo_pago === 'tarjeta' && referenciaTarjeta) {
                    payload.referencia_pago = referenciaTarjeta;
                } else if (venta.metodo_pago === 'yape' && referenciaYape) {
                    payload.referencia_pago = `Yape - Op: ${referenciaYape}`;
                }

                const resp = await fetch('/ventas/procesar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                const data = await resp.json();
                if (data && data.success) {
                    // Backend devolvió éxito: asignar id/numero si vienen
                    if (data.venta_id) venta.id = data.venta_id;
                    if (data.numero_venta) venta.numero = data.numero_venta;

                    // Mostrar confirmación y permitir imprimir
                    if (data.venta_id) {
                        venta.id = data.venta_id;
                        // Abrir la ruta del ticket en nueva pestaña para impresión/reimpresión
                        const ticketUrl = `/venta/${venta.id}/ticket`;
                        window.open(ticketUrl, '_blank');
                    }

                    if (typeof window.mostrarConfirmacionPago === 'function') {
                        window.mostrarConfirmacionPago();
                    } else if (typeof window.mostrarAlertaUI === 'function') {
                        window.mostrarAlertaUI('Pago registrado. Total S/ ' + venta.total.toFixed(2), 'success');
                    } else {
                        showMaskotNotification('Pago registrado. Total S/ ' + venta.total.toFixed(2), 'success');
                    }

                    // Limpiar carrito tras persistir (pero conservar `ultimaVenta` para impresión)
                    window.carrito = [];
                    window.actualizarCarrito && window.actualizarCarrito();
                    window.actualizarBotonPagar && window.actualizarBotonPagar();

                } else {
                    console.error('Error backend registrar venta:', data);
                    const msg = data.error || JSON.stringify(data);
                    // Prefer in-UI alert; fallback to the Maskot notification system; never call native alert()
                    if (typeof window.mostrarAlertaUI === 'function') {
                        window.mostrarAlertaUI(msg, 'error');
                    } else if (typeof window.showMaskotNotification === 'function') {
                        window.showMaskotNotification(msg, 'error');
                    } else {
                        // As ultimate fallback log to console (no native alert)
                        console.error('Venta error (no UI notifier available):', msg);
                    }
                    // Rehabilitar botón para reintentos
                    if (btnPagar) {
                        btnPagar.disabled = false;
                        btnPagar.style.cursor = 'pointer';
                        btnPagar.innerHTML = '<i class="fas fa-credit-card"></i> Pagar';
                    }
                }
                } catch (err) {
                console.error('Fetch error procesar venta:', err);
                if (typeof window.mostrarAlertaUI === 'function') {
                    window.mostrarAlertaUI('No se pudo conectar con el servidor para registrar la venta.', 'error');
                } else {
                    showMaskotNotification('No se pudo conectar con el servidor para registrar la venta.', 'error');
                }
                if (btnPagar) {
                    btnPagar.disabled = false;
                    btnPagar.style.cursor = 'pointer';
                    btnPagar.innerHTML = '<i class="fas fa-credit-card"></i> Pagar';
                }
            }
        })();

    } catch (err) {
        console.error('Error al procesar la venta:', err);
        if (typeof window.mostrarAlertaUI === 'function') {
            window.mostrarAlertaUI('Ocurrió un error procesando la venta. Revisa la consola.', 'error');
        } else {
            showMaskotNotification('Ocurrió un error procesando la venta. Revisa la consola.', 'error');
        }
    }
}

// Log de inicialización
console.log('✅ MASKOT JavaScript cargado correctamente');
console.log('🎨 Todas las funcionalidades interactivas están activas');
console.log('🐾 ¡Bienvenido a MASKOT Petshop & Grooming!');

// Remover loading overlay inicial después de cargar

// Mostrar la modal personalizada de confirmación usando el contenedor en pos.html
window.mostrarConfirmacionPago = window.mostrarConfirmacionPago || function() {
    try {
        const modal = document.getElementById('modal-confirmacion');
        const resumen = document.getElementById('resumen-venta');
        if (!modal || !resumen) {
            console.warn('No existe modal-confirmacion o resumen-venta en la plantilla');
            return;
        }
        const venta = window.ultimaVenta || {};
        // Normalize detalle_multipago into array of {metodo, monto}
        function _normalizeDetalle(det) {
            if (!det) return null;
            // If already array
            if (Array.isArray(det)) return det.map(d => ({metodo: d.metodo || d.met || d[0], monto: parseFloat(d.monto || d.amount || d[1] || 0) || 0}));
            // If object: check metodo1/monto1 pattern
            try {
                const keys = Object.keys(det || {});
                // metodo1/monto1 pattern
                if (keys.some(k => /^metodo\d+$/.test(k)) || keys.some(k => /^monto\d+$/.test(k))) {
                    const arr = [];
                    let i = 1;
                    while (i < 21) {
                        const mk = 'metodo' + i;
                        const nk = 'monto' + i;
                        if (det[mk] || det[nk]) {
                            arr.push({metodo: det[mk] || det[mk.toLowerCase()] || '', monto: parseFloat(det[nk] || 0) || 0});
                        } else break;
                        i++;
                    }
                    if (arr.length) return arr;
                }
                // Otherwise assume keys are method names with amounts
                const arr2 = [];
                for (const k of keys) {
                    const v = det[k];
                    const monto = parseFloat(v || 0) || 0;
                    arr2.push({metodo: k, monto});
                }
                return arr2.length ? arr2 : null;
            } catch (e) {
                return null;
            }
        }
        let html = '';
        html += `<div style="font-weight:700; margin-bottom:8px;">Nº: ${venta.numero || ''}</div>`;
        html += `<div style="font-size:14px; color:#6c757d; margin-bottom:12px;">Fecha: ${venta.fecha || ''}</div>`;
        html += '<div style="max-height:260px; overflow:auto; margin-bottom:12px;">';
        (venta.productos || []).forEach(p => {
            html += `<div style="display:flex; justify-content:space-between; margin-bottom:6px;"><div>${p.nombre} x ${p.cantidad}</div><div>S/ ${(p.precio * p.cantidad).toFixed(2)}</div></div>`;
        });
        html += '</div>';
        html += `<div style="display:flex; justify-content:space-between; font-weight:700; margin-top:8px;"><div>Subtotal</div><div>S/ ${venta.subtotal?.toFixed(2) || '0.00'}</div></div>`;
        html += `<div style="display:flex; justify-content:space-between; font-weight:700;"><div>IGV</div><div>S/ ${venta.igv?.toFixed(2) || '0.00'}</div></div>`;
        html += `<div style="display:flex; justify-content:space-between; font-size:20px; font-weight:900; margin-top:10px;"><div>Total</div><div>S/ ${venta.total?.toFixed(2) || '0.00'}</div></div>`;
        if (venta.monto_recibido !== undefined) {
            html += `<div style="margin-top:8px; display:flex; justify-content:space-between;"><div>Monto recibido</div><div>S/ ${venta.monto_recibido?.toFixed(2) || '0.00'}</div></div>`;
            html += `<div style="display:flex; justify-content:space-between;"><div>Cambio</div><div>S/ ${venta.cambio?.toFixed(2) || '0.00'}</div></div>`;
        }
        if (venta.detalle_multipago) {
            const detArr = _normalizeDetalle(venta.detalle_multipago);
            if (detArr && detArr.length) {
                html += `<div style="margin-top:8px; font-weight:700;">Detalle Multipago</div>`;
                detArr.forEach(mp => {
                    html += `<div style="display:flex; justify-content:space-between;"><div>${mp.metodo}</div><div>S/ ${Number(mp.monto || 0).toFixed(2)}</div></div>`;
                });
            }
        }
        resumen.innerHTML = html;
        modal.style.display = 'block';
    } catch (err) {
        console.error('mostrarConfirmacionPago error', err);
    }
}

// Cerrar la modal de confirmación
window.cerrarModal = window.cerrarModal || function() {
    const modal = document.getElementById('modal-confirmacion');
    if (modal) modal.style.display = 'none';
}

// Limpiar pedido (llamado desde el botón Limpiar y al finalizar venta)
window.limpiarPedido = window.limpiarPedido || function() {
    window.carrito = [];
    // reset inputs
    document.getElementById('monto_recibido') && (document.getElementById('monto_recibido').value = '0.00');
    document.getElementById('cambio') && (document.getElementById('cambio').value = '0.00');
    document.getElementById('monto1') && (document.getElementById('monto1').value = '');
    document.getElementById('monto2') && (document.getElementById('monto2').value = '0.00');
    // reset metodo
    document.getElementById('metodo_pago') && (document.getElementById('metodo_pago').value = 'efectivo');
    window.actualizarCarrito && window.actualizarCarrito();
    window.actualizarBotonPagar && window.actualizarBotonPagar();
    window.cambiarMetodoPago && window.cambiarMetodoPago();
}

// Imprimir ticket usando la venta en window.ultimaVenta
window.imprimirTicket = window.imprimirTicket || function() {
    try {
        const venta = window.ultimaVenta;
        if (!venta) {
            if (typeof window.mostrarAlertaUI === 'function') window.mostrarAlertaUI('No hay venta para imprimir', 'warning');
            else showMaskotNotification('No hay venta para imprimir', 'warning');
            return;
        }
        // Crear una ventana nueva con contenido estilo térmico / vertical estrecho
        let contenido = '<div style="font-family:monospace; width:320px; padding:10px;">';
        contenido += '<div style="text-align:center;">';
        contenido += '<img src="/static/img/LOGOTIPO%20EDITABLE%20MASKOT_Mesa%20de%20trabajo%201%20copia.png" style="max-width:160px; display:block; margin:0 auto 6px;"/>';
        contenido += '<div style="font-size:18px; font-weight:800; letter-spacing:2px;">MASKOT</div>';
        contenido += '<div style="font-size:12px;">Veterinaria & Pet Shop</div>';
        contenido += '<div style="font-size:12px;">Centro Veterinario y Tienda</div>';
        contenido += '<div style="font-size:12px;">Tel: (555) 123-4567</div>';
        contenido += '<div style="font-size:12px;">ventas@maskotveterinaria.com</div>';
        contenido += '</div>';
        contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';
        contenido += '<div style="text-align:center; font-weight:700;">COMPROBANTE DE COMPRA</div>';
        contenido += `<div style="text-align:center;">Ticket #: ${venta.numero || '1'}</div>`;
        contenido += `<div style="text-align:left; font-size:12px; margin-top:6px;">Fecha emisión: ${venta.fecha || ''}</div>`;
        contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';

        // Datos del cliente si vienen
        if (venta.cliente) {
            contenido += '<div style="font-weight:700; margin-bottom:6px;">DATOS DEL CLIENTE</div>';
            if (venta.cliente.nombre) contenido += `<div>Nombre: ${venta.cliente.nombre}</div>`;
            if (venta.cliente.email) contenido += `<div>Email: ${venta.cliente.email}</div>`;
            if (venta.cliente.telefono) contenido += `<div>Teléfono: ${venta.cliente.telefono}</div>`;
            contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';
        }

        contenido += '<div style="font-weight:700; margin-bottom:6px;">PRODUCTOS COMPRADOS</div>';
        (venta.productos || []).forEach(p => {
            contenido += `<div style="display:block; margin-bottom:4px;">`;
            contenido += `<div style="font-weight:700;">${p.nombre}</div>`;
            contenido += `<div style="font-size:12px;">${p.cantidad} x S/ ${Number(p.precio).toFixed(2)}    S/ ${(p.precio * p.cantidad).toFixed(2)}</div>`;
            contenido += `</div>`;
        });

        contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';
        contenido += `<div style="display:flex; justify-content:space-between; font-weight:700;">`;
        contenido += `<div>Subtotal:</div><div>S/ ${venta.subtotal?.toFixed(2) || '0.00'}</div>`;
        contenido += `</div>`;
        contenido += `<div style="display:flex; justify-content:space-between;">`;
        contenido += `<div>IGV (18%):</div><div>S/ ${venta.igv?.toFixed(2) || '0.00'}</div>`;
        contenido += `</div>`;
        contenido += `<div style="display:flex; justify-content:space-between; font-size:16px; font-weight:900; margin-top:8px;">`;
        contenido += `<div>TOTAL:</div><div>S/ ${venta.total?.toFixed(2) || '0.00'}</div>`;
        contenido += `</div>`;

        contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';
        contenido += '<div style="font-weight:700;">INFORMACIÓN DE PAGO</div>';
        contenido += `<div>Método: ${venta.metodo_pago || ''}</div>`;
        contenido += `<div>Estado: Pagado</div>`;

        contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';
        contenido += '<div style="font-size:11px;">INFORMACIÓN IMPORTANTE</div>';
        contenido += '<div style="font-size:11px;">* Conserve este ticket como comprobante</div>';
        contenido += '<div style="font-size:11px;">* Garantía según políticas de la tienda</div>';
        contenido += '<div style="font-size:11px;">* Devoluciones dentro de 15 días</div>';
        contenido += '<hr style="border:none; border-top:1px dashed #000; margin:8px 0;"/>';
        contenido += '<div style="text-align:center; font-weight:700;">¡Gracias por su compra!</div>';
        contenido += `<div style="text-align:center; font-size:10px; margin-top:8px;">${new Date().toLocaleString()}</div>`;
        contenido += '</div>';
        const w = window.open('', 'PRINT', 'width=400,height=600');
        if (!w) {
            if (typeof window.mostrarAlertaUI === 'function') window.mostrarAlertaUI('El navegador bloqueó la apertura de la ventana de impresión. Permite popups para imprimir.', 'error');
            else showMaskotNotification('El navegador bloqueó la apertura de la ventana de impresión. Permite popups para imprimir.', 'error');
            return;
        }
        w.document.write(contenido);
        w.document.close();
        w.focus();
        setTimeout(() => { w.print(); w.close(); }, 300);
    } catch (err) {
        console.error('Error imprimirTicket', err);
        if (typeof window.mostrarAlertaUI === 'function') window.mostrarAlertaUI('No se pudo imprimir el ticket. Revisa la consola.', 'error');
        else showMaskotNotification('No se pudo imprimir el ticket. Revisa la consola.', 'error');
    }
}

// Helper que muestra modal confirm y retorna una Promise<boolean>
function showConfirmModal(message) {
    return new Promise(resolve => {
        const modalEl = document.getElementById('globalConfirmModal');
        if (!modalEl) {
            // Fallback a confirm() si el modal no existe (muy raro)
            resolve(confirm(message));
            return;
        }
        const msgEl = modalEl.querySelector('#globalConfirmMessage');
        const okBtn = modalEl.querySelector('#globalConfirmOk');
        const cancelBtn = modalEl.querySelector('#globalConfirmCancel');

        msgEl.textContent = message;
        const bsModal = new bootstrap.Modal(modalEl);
        function cleanup() {
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
        }

        function onOk() { cleanup(); bsModal.hide(); resolve(true); }
        function onCancel() { cleanup(); bsModal.hide(); resolve(false); }
        function onHidden() { cleanup(); resolve(false); }

        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
        modalEl.addEventListener('hidden.bs.modal', onHidden);
        bsModal.show();
    });
}

// ==================== WhatsApp Consult Handler ====================
// Añade el comportamiento para botones que consultan por WhatsApp sin afectar el diseño
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn-consultar-wsp');
    if (!btn) return;
    e.preventDefault();

    const phone = '+51959703099'; // Número solicitado
    const productName = btn.getAttribute('data-product-name') || '';

    // Pedir nombre al usuario con prompt (no cambia el diseño)
    let nombre = prompt('Por favor escribe tu nombre para incluirlo en el mensaje (o presiona cancelar):', '');
    if (nombre === null) {
        // Si el usuario cancela el prompt, usar placeholder y continuar
        nombre = '.....';
    }

    const message = `Hola mi nombre es ${nombre} quisisra consultar si cuentan con stock de ${productName}`;
    const encoded = encodeURIComponent(message);
    const url = `https://wa.me/${phone.replace(/[^0-9]/g,'')}?text=${encoded}`;

    // Abrir en nueva pestaña para no afectar la navegación
    window.open(url, '_blank');
});
