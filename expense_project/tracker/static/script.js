document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const form = document.getElementById('expense-form');
    const formTitle = document.getElementById('form-title');
    const submitBtn = document.getElementById('submit-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const editExpenseId = document.getElementById('edit-expense-id');
    const expenseList = document.getElementById('expense-list');
    const clearButton = document.getElementById('clear-expenses-btn');
    const themeToggle = document.getElementById('theme-toggle');
    const toastContainer = document.getElementById('toast-container');
    
    // Budget Elements
    const budgetInput = document.getElementById('budget-input');
    const saveBudgetBtn = document.getElementById('save-budget-btn');
    const budgetProgress = document.getElementById('budget-progress');
    const budgetText = document.getElementById('budget-text');
    
    // Pagination & Filters
    const filterStartDate = document.getElementById('filter-start-date');
    const filterEndDate = document.getElementById('filter-end-date');
    const filterCategory = document.getElementById('filter-category');
    const prevPageBtn = document.getElementById('prev-page-btn');
    const nextPageBtn = document.getElementById('next-page-btn');
    const pageIndicator = document.getElementById('page-indicator');
    
    // Analytics Elements
    const totalExpensesStat = document.getElementById('total-expenses-stat');
    const monthlyExpensesStat = document.getElementById('monthly-expenses-stat');
    const highestCategoryStat = document.getElementById('highest-category-stat');
    let categoryChartInstance = null;

    let currentPage = 1;

    // --- CSRF Token Helper ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // --- Initialization ---
    initTheme();
    fetchBudget();
    fetchExpenses(1);
    fetchAnalytics();
    
    // Default date to today
    document.getElementById('expense-date').valueAsDate = new Date();

    // --- Event Listeners ---
    if (form) form.addEventListener('submit', handleFormSubmit);
    if (clearButton) clearButton.addEventListener('click', handleClearExpenses);
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', cancelEdit);
    if (saveBudgetBtn) saveBudgetBtn.addEventListener('click', saveBudget);
    
    if (filterStartDate) filterStartDate.addEventListener('change', () => { fetchExpenses(1); fetchAnalytics(); });
    if (filterEndDate) filterEndDate.addEventListener('change', () => { fetchExpenses(1); fetchAnalytics(); });
    if (filterCategory) filterCategory.addEventListener('change', () => { fetchExpenses(1); });
    if (prevPageBtn) prevPageBtn.addEventListener('click', () => fetchExpenses(currentPage - 1));
    if (nextPageBtn) nextPageBtn.addEventListener('click', () => fetchExpenses(currentPage + 1));

    // --- Toast Notifications ---
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        
        toastContainer.appendChild(toast);
        
        // Trigger reflow to start animation
        void toast.offsetWidth;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // --- Theme Handling ---
    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        themeToggle.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        themeToggle.textContent = newTheme === 'dark' ? '☀️' : '🌙';
        fetchAnalytics(); // redraw chart with new colors
    }

    // --- Budget Logic ---
    function fetchBudget() {
        fetch('/api/budget/')
            .then(res => res.json())
            .then(data => {
                if (data.amount) {
                    budgetInput.value = parseFloat(data.amount) > 0 ? parseFloat(data.amount) : '';
                }
            })
            .catch(err => console.error("Error fetching budget:", err));
    }

    function saveBudget() {
        const amount = parseFloat(budgetInput.value) || 0;
        fetch('/api/budget/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken 
            },
            body: JSON.stringify({ amount: amount })
        })
        .then(res => {
            if (res.ok) {
                showToast('Budget saved successfully!', 'success');
                fetchAnalytics();
            } else {
                showToast('Failed to save budget.', 'error');
            }
        });
    }

    // --- Expense Logic ---
    function fetchExpenses(page = 1) {
        const startDate = filterStartDate ? filterStartDate.value : '';
        const endDate = filterEndDate ? filterEndDate.value : '';
        const category = filterCategory ? filterCategory.value : '';
        
        let url = `/api/expenses/?page=${page}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        if (category) url += `&category=${category}`;

        fetch(url)
            .then(response => {
                if (response.status === 403) {
                    window.location.href = '/login/';
                    return;
                }
                return response.json();
            })
            .then(data => {
                if(data.expenses) {
                    expenseList.innerHTML = ''; 
                    data.expenses.forEach(expense => {
                        const amount = parseFloat(expense.amount); 
                        // The date returned is ISO, we extract just the YYYY-MM-DD for display/editing
                        const dateOnly = expense.created_at.split('T')[0];
                        addExpenseToDOM(expense.id, expense.description, amount, expense.category, dateOnly);
                    });
                    
                    currentPage = data.current_page;
                    pageIndicator.textContent = `Page ${currentPage} of ${data.total_pages || 1}`;
                    prevPageBtn.disabled = !data.has_previous;
                    nextPageBtn.disabled = !data.has_next;
                }
            })
            .catch(error => console.error('Error fetching expenses:', error));
    }

    function fetchAnalytics() {
        const startDate = filterStartDate ? filterStartDate.value : '';
        const endDate = filterEndDate ? filterEndDate.value : '';
        
        let url = '/api/analytics/?';
        if (startDate) url += `start_date=${startDate}&`;
        if (endDate) url += `end_date=${endDate}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                totalExpensesStat.textContent = `$${parseFloat(data.total_expenses).toFixed(2)}`;
                monthlyExpensesStat.textContent = `$${parseFloat(data.monthly_expenses).toFixed(2)}`;
                highestCategoryStat.textContent = data.highest_category;

                // Update Budget UI
                const budgetAmount = parseFloat(data.budget_amount);
                const monthly = parseFloat(data.monthly_expenses);
                const percent = data.budget_percent;
                
                budgetText.textContent = `$${monthly.toFixed(2)} / $${budgetAmount.toFixed(2)} (${percent}%)`;
                budgetProgress.style.width = `${percent}%`;
                
                if (percent >= 100) {
                    budgetProgress.style.backgroundColor = 'var(--danger)';
                } else if (percent >= 80) {
                    budgetProgress.style.backgroundColor = 'var(--warning)';
                } else {
                    budgetProgress.style.backgroundColor = 'var(--success)';
                }

                updateChart(data.category_data);
            });
    }

    function updateChart(categoryData) {
        const ctx = document.getElementById('categoryChart');
        if (!ctx) return;

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const textColor = isDark ? '#F9FAFB' : '#6B7280';

        const labels = Object.keys(categoryData);
        const values = Object.values(categoryData);

        if (categoryChartInstance) {
            categoryChartInstance.destroy();
        }

        categoryChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Expenses by Category',
                    data: values,
                    backgroundColor: [
                        '#4F46E5', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6'
                    ],
                    borderWidth: isDark ? 2 : 0,
                    borderColor: isDark ? '#1F2937' : '#FFFFFF',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: textColor }
                    }
                }
            }
        });
    }

    function handleFormSubmit(event) {
        event.preventDefault();

        const id = editExpenseId.value;
        const description = document.getElementById('description').value;
        const amount = parseFloat(document.getElementById('amount').value);
        const category = document.getElementById('category').value;
        const date = document.getElementById('expense-date').value;

        if (isNaN(amount) || amount <= 0) {
            showToast('Please enter a valid positive amount.', 'error');
            return;
        }

        const payload = {
            description: description,
            amount: amount.toFixed(2),
            category: category,
            date: date
        };

        const isEdit = id !== "";
        const url = isEdit ? `/api/expenses/${id}/` : '/api/expenses/';
        const method = isEdit ? 'PUT' : 'POST';

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken 
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (response.ok) return response.json();
            throw new Error('Failed to save expense.');
        })
        .then(data => {
            showToast(isEdit ? 'Expense updated successfully!' : 'Expense added successfully!', 'success');
            cancelEdit(); // Reset form
            fetchExpenses(currentPage);
            fetchAnalytics();
        })
        .catch(error => showToast(error.message, 'error'));
    }
    
    function cancelEdit() {
        form.reset();
        document.getElementById('expense-date').valueAsDate = new Date();
        editExpenseId.value = "";
        formTitle.textContent = "Add New Expense";
        submitBtn.textContent = "Add Expense";
        cancelEditBtn.style.display = "none";
    }

    function startEdit(id, description, amount, category, date) {
        editExpenseId.value = id;
        document.getElementById('description').value = description;
        document.getElementById('amount').value = amount;
        document.getElementById('category').value = category;
        document.getElementById('expense-date').value = date;
        
        formTitle.textContent = "Edit Expense";
        submitBtn.textContent = "Update Expense";
        cancelEditBtn.style.display = "block";
        
        // Scroll up to form smoothly
        form.scrollIntoView({ behavior: 'smooth' });
    }
    
    function handleClearExpenses() {
        if (!confirm("Are you sure you want to clear ALL expenses? This cannot be undone.")) {
            return;
        }

        fetch('/api/expenses/', {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrftoken
            }
        })
        .then(response => {
            if (response.status === 204) {
                showToast('All expenses cleared.', 'success');
                fetchExpenses(1);
                fetchAnalytics(); 
            } else {
                showToast('Failed to clear expenses.', 'error');
            }
        });
    }
    
    function addExpenseToDOM(id, description, amount, category, date) {
        if (!expenseList) return; 

        const listItem = document.createElement('li');
        listItem.dataset.id = id;
        listItem.innerHTML = `
            <div class="expense-details">
                <strong>${description}</strong>
                <p>Category: ${category} | Date: ${date}</p>
            </div>
            <div class="expense-actions" style="display: flex; align-items: center; gap: 1rem;">
                <div class="expense-amount">-$${amount.toFixed(2)}</div>
                <button class="btn-edit-item" title="Edit this expense">✏️</button>
                <button class="btn-delete-item" style="background: none; border: none; color: var(--danger); cursor: pointer; font-weight: bold;" title="Delete this expense">X</button>
            </div>
        `;
        
        listItem.querySelector('.btn-delete-item').addEventListener('click', () => {
            if (confirm("Delete this expense?")) {
                fetch('/api/expenses/' + id + '/', {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': csrftoken }
                })
                .then(response => {
                    if (response.status === 204) {
                        showToast('Expense deleted.', 'success');
                        fetchExpenses(currentPage);
                        fetchAnalytics(); 
                    }
                });
            }
        });

        listItem.querySelector('.btn-edit-item').addEventListener('click', () => {
            startEdit(id, description, amount, category, date);
        });

        expenseList.appendChild(listItem);
    }
});